# Architecture

How the system is put together: components, data model, request flows, and the design decisions behind them. For the search internals (indexing, embeddings, ranking) see **[docs/search-implementation.md](docs/search-implementation.md)**; for the original proposal see [docs/goal.md](docs/goal.md).

---

## 1. Components

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ Browser                                                                      │
│   Next.js 16 frontend — App Router (src/), React 19, shadcn/ui on Base UI    │
│   Server components fetch pages; client components handle review actions    │
└───────────────┬──────────────────────────────────────────────────────────────┘
                │ HTTP/JSON — typed client (openapi-fetch) generated from the
                │ backend's OpenAPI spec, so the two can't drift silently
┌───────────────▼──────────────────────────────────────────────────────────────┐
│ FastAPI backend (Python, async)                                              │
│                                                                              │
│   /api/v1/terminology/*            /api/v1/coding/*                          │
│   ── search, code detail ──        ── encounters, review, rescore ──         │
│          │                                │                                  │
│   TerminologyService ◄──── retrieve() ── CodingService ──► DecisionEngine    │
│          │                                │                 ├ jev-opencode ──┼──► OpenCode Zen  (Jev)
│          │                                │                 ├ jev-vercel  ───┼──► Vercel AI Gateway (Jev)
│          │                                │                 └ search-rank    │    (stand-in, no API)
│          │ EmbeddingClient ───────────────┼──────────────────────────────────┼──► LM Studio (Qwen3-Embedding-0.6B)
│          ▼                                ▼                                  │
│   TerminologyRepository            CodingRepository                          │
└───────────────┬────────────────────────────┬─────────────────────────────────┘
                │ SQLAlchemy 2 (asyncpg)      │
┌───────────────▼────────────────────────────▼─────────────────────────────────┐
│ PostgreSQL 17 + pgvector 0.8 + pg_trgm  (Docker, 127.0.0.1:5433)             │
│   terminology_* : code systems, concepts, synonyms, index terms,             │
│                   embeddings (HNSW cosine), full-text + trigram indexes      │
│   coding_*      : encounters, items, candidates, decisions, scores, audit    │
└──────────────────────────────────────────────────────────────────────────────┘

Offline: loaders (CLI) ──► ICD-10-CM files in data/ ──► terminology tables
         embedding job  ──► LM Studio ──► embedding tables
         eval harness   ──► search service ──► docs/report/
```

| Component | Tech | Notes |
|---|---|---|
| Frontend | Next.js 16.3 (Turbopack), React 19, TypeScript, Tailwind 4, shadcn/ui (`base-nova`, Base UI) | Server components render data pages; mutations are client-side and update from the API response |
| API | FastAPI, Pydantic 2, dependency-injector | Router → Service → Repository → Model; one error shape for all failures |
| Persistence | PostgreSQL 17, SQLAlchemy 2 async, asyncpg, Alembic | pgvector HNSW for embeddings, GIN for full-text and trigram |
| Embeddings | Qwen3-Embedding-0.6B (GGUF) via an OpenAI-compatible server | LM Studio locally; 1024-d, cosine |
| Decision model | Jev (TypeSafe AI) | `choice` question over the candidate codes → probability per code |

---

## 2. Backend layering

Every feature follows the same path, and layers are never skipped:

```
routers/      HTTP only: validate input, call the service, shape the response
services/     orchestration and business rules (no SQL, no HTTP)
repository/   all database I/O (sessions, queries, transactions)
models/       SQLAlchemy ORM tables
```

- **Dependency injection** (`app/di/`): each feature has a container module (repository + service factories); routes get services via `Depends(get_*_service)`. The coding container depends on the terminology container, so the pipeline reuses the exact search the API exposes.
- **Pure logic is isolated and unit-tested**: ranking (`services/search_ranking.py` — merge, category expansion, variant collapsing, rank fusion) and decision rules (`coding/decision.py` — ranking probabilities, assignment, flags, review queue) have no I/O.
- **Configuration** (`app/core/config.py`): `.env` holds secrets (DB URL, API keys); `configs/config.yaml` holds behaviour (search modes, thresholds, engine routes). Precedence: env var > `.env` > YAML > defaults. Validation errors never echo values.
- **Errors**: every failure leaves the API as `{"error": {"code", "message", "details?"}}` — `NOT_FOUND` 404, `RESOURCE_CONFLICT` 409, `BUSINESS_RULE_VIOLATION` 422, `VALIDATION_ERROR` 422, `EMBEDDING_UNAVAILABLE` 503.

### Modules

| Module | Responsibility | Key files |
|---|---|---|
| **Terminology** | Load ICD-10-CM; search (code prefix / text / semantic / hybrid); code detail with hierarchy and inherited notes | `routers/terminology.py`, `services/terminology_service.py`, `services/search_ranking.py`, `repository/terminology_repository.py`, `terminology/import_/` |
| **Coding** | Encounter pipeline (search → score → flag → route), review, approval, rescoring, candidate inspection | `routers/coding.py`, `services/coding_service.py`, `coding/decision.py`, `coding/engines/`, `repository/coding_repository.py` |
| **Core** | Settings, database engine (slow-query logging), structured logging, embedding client | `core/` |

---

## 3. Data model

### Terminology (loaded per release, read-mostly)

```
terminology_code_system 1──* terminology_concept 1──* terminology_concept_synonym
  (ICD-10-CM, version 2027)     │  code, display, short_display, is_billable,
                                │  sort_order, parent_concept_id (hierarchy),
                                │  notes (JSONB), search_vector (tsvector)
                                ├──* terminology_concept_embedding   (vector(1024), per model)
                                └──* terminology_index_term ──* terminology_index_term_embedding
                                       term, depth, via_see,           (vector(1024), per model)
                                       search_vector
```

- Several releases can coexist (`canonical_url` + `version` unique); search uses the latest active one unless a version is given.
- Embeddings are keyed by `(row, model)` so two embedding models can be stored and compared.
- Index terms are separate rows (not merged into synonyms) so catch-all codes with hundreds of index terms don't blur one embedding.

### Coding (per encounter, written by the pipeline and reviewers)

```
coding_encounter 1──* coding_item 1──* coding_candidate            (top-100 search results)
  encounter_id,        item_type,         code, display, search_rank,
  soap_note, status,   text, status,      text/semantic rank, matched_on
  review_queue,        assigned_* (AI),          ▲
  is_human_reviewed    final_* (human)           │
                       │                         │
                       1──* coding_decision 1──* coding_candidate_score
                             engine, model,        probability, rank
                             latency, cost,        (candidate NULL = "none of the above")
                             raw_response,
                             is_active
coding_audit_event  (append-only: received, scored, approve/override/remove, approved)
```

Design rules:
- **The AI's output is never overwritten.** `assigned_*` is the active decision; the reviewer's choice is stored beside it in `final_*` / `review_*`.
- **Candidates are engine-independent; probabilities belong to a decision.** The same 100 candidates can be scored by Jev and by a baseline (`rescore`) and compared; earlier decisions stay, marked inactive.
- **Snapshots, not just references**: code and description are copied onto candidates and items, so reloading terminology doesn't change what a reviewer saw.

---

## 4. Request flows

### 4.1 Search — `GET /api/v1/terminology/search`

```
q ──► code-shaped ("K35.3")? ──yes──► prefix lookup (falls through if no code matches, e.g. "T2DM")
        │ no
        ├─ text:     full-text + trigram over codes and index terms   (top 200 each)
        ├─ semantic: embed q (LM Studio) → HNSW over both embedding tables (top 200 each)
        │    per method: merge per code → expand categories to billable codes → collapse 7th-char variants
        └─ hybrid:   reciprocal rank fusion (k = 60)
```

Full detail: [docs/search-implementation.md §4](docs/search-implementation.md#4-how-a-search-is-ranked).

### 4.2 Coding pipeline — `POST /api/v1/coding/encounters`

```
EncounterCreate (note + conditions/observations/service & medication requests)
  1. store encounter + one item per finding
       coded types (config: [condition]) → pending · others → not_coded
  2. per coded item
       terminology.retrieve(text) → top 100 billable candidates → coding_candidate
       engine.score(note, item, candidates) → probability per candidate + NOTA
       rank → assign best real candidate → flags:
         LOW_CONFIDENCE  probability < 0.75
         NONE_OF_THE_ABOVE  NOTA ≥ 0.2 or ranked first
       one failing item → status failed, flag SCORING_FAILED (encounter continues)
  3. route encounter: any flag or failure → close_review, else standard
  4. return EncounterOut (per item: assigned code, probability, flags, top 15 alternatives)
```

Synchronous for the prototype (~0.2 s search + ~0.5–1.2 s Jev per condition). The tables already support moving to a background job.

### 4.3 Review

```
POST …/items/{id}/review   approve | override {code} | remove      (reviewer name required)
   override accepts any billable code; audit records whether it was among the candidates
POST …/approve             only when every coded item is resolved → is_human_reviewed = true
POST …/rescore?engine=     re-score stored candidates (no new search), clears item reviews
GET  …/items/{id}/candidates   all 100 candidates with search ranks and the decision's probabilities
```

---

## 5. Decision engines

```python
class DecisionEngine(Protocol):
    name: str
    async def score(self, soap_note: str, item_text: str,
                    candidates: list[EngineCandidate]) -> EngineResult
    # EngineResult: probabilities {candidate_id: p}, nota_probability, model, cost, raw_response
```

| Engine | How it scores |
|---|---|
| `jev-opencode` | `POST https://opencode.ai/zen/v1/systemone` |
| `jev-vercel` | `POST https://ai-gateway.vercel.sh/v1/evaluate` |
| `search-rank` | `exp(-(rank − 1))`, normalised — a placeholder, **not calibrated** |

Both Jev routes send the same TypeSafe-style request — the note and the condition as `state`, and one `choice` question whose options are the candidate codes plus `NONE_OF_THE_ABOVE`:

```json
{
  "model": "jev-1.13",
  "state": { "soap_note": "…", "condition_to_code": "acute appendicitis with localized peritonitis" },
  "questions": { "icd10cm": { "type": "choice", "instructions": "…",
      "criteria": { "K35.30": "Acute appendicitis with localized peritonitis, without …", "…": "…",
                    "NONE_OF_THE_ABOVE": "None of the listed ICD-10-CM codes fits …" } } }
}
```

The answer carries a probability for **every** option. Because the options are exactly the search candidates, the engine cannot return a code that doesn't exist; anything outside the offered set is discarded. Retries cover 429/5xx/network errors only; account and request errors fail fast and are recorded on the decision. Adding an engine = one class + one line in `di/modules/coding.py`.

---

## 6. Frontend

```
src/app/                         routes (App Router)
  page.tsx                       dashboard — queue counts, recent encounters, pipeline summary
  coding/new/                    submit a note (examples, engine picker)
  coding/encounters/             review queue (filters in the URL)
  coding/encounters/[id]/        review screen
  terminology/                   ICD-10-CM search (mode, billable filter; state in the URL)
  terminology/codes/[code]/      code detail — hierarchy, synonyms, notes, inherited notes
  system/                        health, terminology/embedding coverage, engines, thresholds
src/components/coding/           review card, override picker, candidates sheet (resizable)
src/lib/api/                     generated schema (schema.d.ts), typed client, type aliases
```

- **Data**: pages are server components that fetch on each request (`no-store`); interactive parts are client components that call the API and update local state from the response.
- **Contract**: `just openapi` (backend) → `pnpm gen:api` (frontend) regenerates `schema.d.ts`; a backend change that breaks the UI fails `tsc`.
- **No login in the prototype**: the reviewer types a name once (stored in the browser) and it is sent with every review action.
- Next.js 16 specifics: async `params`/`searchParams`; Turbopack's on-disk cache is **disabled** in `next.config.ts` because it served stale Tailwind CSS.

---

## 7. Evaluation

`backend/eval/` builds test sets and measures search quality; results are written up in [docs/report](docs/report/README.md).

- **Gold labels from the official Alphabetic Index**, not hand-made: 600 index terms + typo and word-shuffle variants.
- **Held-out split**: 20% of index terms (stable hash of the term text) are never loaded into search; test queries come only from them. A separate **dev split** is used for tuning; test sets are never tuned on.
- Ablations run every configuration on identical queries; per-query results are kept as JSON.

---

## 8. Key decisions and trade-offs

| Decision | Why | Trade-off |
|---|---|---|
| Retrieve-then-decide (search → Jev over a closed set) | No hallucinated codes; recall and decision quality measured separately | Jev can't pick a code search missed — mitigated by NOTA and reviewer override |
| Hybrid search, equal weights | Text and semantic fail on different queries; fusion is best overall | Two searches per query (~180 ms p50) |
| Alphabetic Index as separate searchable rows | Biggest single recall gain (held-out R@100 80% → 94%) | ~450 MB more HNSW index; 57k more embeddings |
| Local embeddings (LM Studio) | Clinical text for search stays on the machine; free | ~1.5 h to embed on a mid-range GPU |
| Conditions only (ICD-10-CM) for now | Validate search + Jev on one code set first | Observations/orders/medications stored but not coded (SNOMED, LOINC, RxNorm later) |
| Synchronous pipeline | Simple to build and debug | Long notes block the request; easy to move to a job later |
| Never overwrite AI output; append-only audit | Measurable AI-vs-human agreement; accountability | More tables and writes |
| Rejected: any-word text matching, tuned fusion weights | Both lowered recall on held-out data (Report 03) | Kept as switches for reproducibility |

---

## 9. Known limitations

- Prototype: no authentication, single tenant, synchronous processing.
- Only ICD-10-CM diagnoses (conditions) are coded; no sequencing / principal-diagnosis logic, no procedure codes.
- Jev's free tier may use prompts for training — synthetic data only. The paid tier's zero-retention policy must be confirmed before any real data.
- Search evaluation uses index-derived and small hand-labeled sets; a note-level, coder-labeled test set is still needed to measure end-to-end accuracy.
