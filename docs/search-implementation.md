# ICD-10-CM Search — How It Works

This document describes **Stage 1** of the coding pipeline: how we find the right ICD-10-CM codes for a clinical phrase. It covers what data we load, how each code is made searchable (full-text, trigram, embeddings), how the Alphabetic Index was added to improve accuracy, and how a search request is ranked.

The coding pipeline (Stage 2, the Jev decision layer) takes the **top 100 billable candidates** from this search for each condition. Search recall — whether the correct code is in those 100 — is what this stage is optimised for.

| | |
|---|---|
| Code set | ICD-10-CM **FY2027** (CDC/NCHS release, effective 2026-10-01) |
| Database | PostgreSQL 17 + **pgvector 0.8.6** + **pg_trgm** (Docker, port 5433) |
| Embedding model | **Qwen3-Embedding-0.6B** (Q8_0 GGUF) served by LM Studio, 1024 dimensions |
| Evaluation | [Report 01](report/01-search-evaluation.md) · [Report 02](report/02-index-terms-and-variant-collapse.md) · [Report 03](report/03-ranking-fixes.md) |

---

## 1. Big picture

```
                        LOAD TIME (once per release)
 ┌────────────────────────────────────────────────────────────────────────────┐
 │ icd10cm-order-2027.txt ──► 98,403 codes (billable + category headers)      │
 │                            parent → child hierarchy                        │
 │ icd10cm-tabular-2027.xml ─► 13,541 inclusion terms (synonyms) · notes     │
 │ icd10cm-index-2027.xml ───► 57,057 Alphabetic Index terms (20% held out)   │
 │                                                                            │
 │ For every code AND every index term:                                       │
 │   • full-text vector (tsvector, GIN)    • trigram index (GIN)              │
 │   • embedding vector(1024) (HNSW, cosine) via Qwen3 in LM Studio           │
 └────────────────────────────────────────────────────────────────────────────┘

                        QUERY TIME (per search)
 "acute appendicitis with localized peritonitis"
        │
        ├── code-shaped? ("K35.3", "k3530") ──► prefix lookup on the code ──► done
        │
        ├── TEXT      full-text + trigram over codes AND index terms   (200 + 200)
        ├── SEMANTIC  embed query → nearest codes AND index terms      (200 + 200)
        │
        │   each method: merge per code → expand categories → collapse 7th-char variants
        │
        └── HYBRID    reciprocal rank fusion of the two rankings
                         │
                         ▼
          ranked codes, each with: score · text_rank · semantic_rank ·
          matched_on (index term that matched) · variants
```

---

## 2. Source data

All files come from the official CDC/NCHS FY2027 release:
<https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Publications/ICD10CM/2027/>. Nothing is hand-curated.

| File (inside the zips in `data/`) | What we take from it |
|---|---|
| `icd10cm-order-2027.txt` (fixed-width) | Every code: order number, code, **billable flag**, short description (60 chars), long description |
| `icd10cm-tabular_-2027.xml` | Per-code **inclusion terms** (synonyms) and **instructional notes** (Excludes1/2, Code first, Use additional code, Code also, 7th-character definitions) |
| `icd10cm-index-2027.xml` | The **Alphabetic Index** — the coder's lookup book mapping terms, synonyms and eponyms to codes |

### 2.1 Codes — the order file

- **98,403 rows**: **74,879 billable codes** and **23,524 category headers** (non-billable, e.g. `K35.3`).
- Codes are stored in dotted form (`K3530` → `K35.30`; the dot always follows the 3rd character).
- Each row keeps both descriptions:
  - `display` — long description, e.g. *"Acute appendicitis with localized peritonitis, without perforation or gangrene"*
  - `short_display` — short description, e.g. *"Acute appendicitis with loc peritonitis, w/o perf or gangr"*
- **Hierarchy**: each code's parent is the nearest existing prefix (`K35.30 → K35.3 → K35`). This also handles 7th-character codes with an `X` placeholder: `S01.00XA → S01.00`.

### 2.2 Synonyms and notes — the tabular XML

- **13,541 inclusion terms on 7,215 codes**, stored in `terminology_concept_synonym`. Example: `K35.32` → *"Perforated appendix NOS"*, *"Ruptured appendix (with localized peritonitis) NOS"*.
- **Notes on 4,599 codes**, stored as JSON on the code (`excludes1`, `excludes2`, `code_first`, `code_also`, `use_additional_code`, `notes`, `seventh_character`, `seventh_character_note`).
- Only a code's *own* notes are stored. Notes on parent categories apply to every code beneath them (ICD-10-CM convention), so the concept detail API returns them as `inherited_notes`, walked up the hierarchy at query time.

### 2.3 Alphabetic Index terms — the accuracy boost (Report 02)

The official descriptions often don't use the words a clinician writes (*Variola* vs *Smallpox*, eponyms like *Kopp's asthma*). The Alphabetic Index is exactly the bridge coders use, so we load it as searchable text.

**How index terms are built** (`app/terminology/import_/loaders/icd10cm_index.py`):

1. Every path from a main term down through its sub-terms that ends in a code becomes one term:
   `Appendicitis > with > gangrene > with localized peritonitis` → term *"Appendicitis with gangrene with localized peritonitis"* → **K35.31**.
2. Non-essential modifiers in parentheses (`<nemod>`) and the abbreviations *NOS*/*NEC* are dropped from the term text.
3. **"See" cross-references are resolved.** Many lay terms have no code of their own, only a pointer:
   `Attack, attacks > heart` — *see* `Infarct, myocardium` → resolved to the code at that path → **I21.9**.
   Titles list word variants (*"Infarct, infarction"*, *"myocardium, myocardial"*), so every combination of variants at every level is registered as a lookup key (capped at 32 per path).
4. A partial code with a trailing dash (`S72.9-`, `A30.-`) means "a category — pick a code beneath it"; the term is linked to that **category** concept and expanded at query time (§4.4).

| | Count |
|---|---|
| Index paths parsed | **71,265** (63,260 with a code on the path + 8,005 resolved "see" references) |
| **Loaded** (after 20% held out) | **57,057** (6,365 of them via "see") |

Each index term is its **own row** in `terminology_index_term` (not merged into the code's synonym list). Catch-all codes like *"Other specified …"* have hundreds of index terms; packing them into one text would blur that code's embedding, so each term is matched and embedded separately and grouped back to its code at query time.

### 2.4 The evaluation hold-out

Because the evaluation also uses index terms as test queries, **20% of index terms are never loaded** (`terminology.index_holdout_percent: 20`). The split is a stable hash of the term text, so the same term is always on the same side. Test queries come only from the held-out 20%; without this, the evaluation would test lookup of text search already contains (loaded terms score 100% — see Report 02, F3).

> **For production:** set `index_holdout_percent: 0`, re-run `just terminology-index` and `just terminology-embeddings index-terms`. Evaluation then needs independent test sets.

---

## 3. What is indexed

### 3.1 Full-text search vectors (PostgreSQL `tsvector`, English stemming)

**Per code** — built by the loader, weighted so the official description counts most:

| Weight | Text |
|---|---|
| **A** | `display` (long description) |
| **B** | all inclusion terms (synonyms), concatenated |
| **D** | `short_display` (abbreviated description) |

**Per index term**: `to_tsvector('english', term)`.

Both use GIN indexes: `ix_terminology_concept_search_vector`, `ix_terminology_index_term_search_vector`.

### 3.2 Trigram indexes (`pg_trgm`) — typos and partial words

GIN trigram indexes on the code's `display` (`ix_terminology_concept_display_trgm`, 40 MB) and on each index term (`ix_terminology_index_term_term_trgm`, 13 MB). They power the `<%` word-similarity operator (pg_trgm default threshold 0.6), which matches *"apendicitis"* to *"appendicitis"*.

### 3.3 Embeddings (pgvector)

| What is embedded | Text sent to the model | Rows | Table · index |
|---|---|---|---|
| **Every code** (billable and headers) | `display` + inclusion terms: `"<display>. Includes: <syn1>; <syn2>…"` | **98,403** | `terminology_concept_embedding` · HNSW cosine (765 MB) |
| **Every loaded index term** | the term itself, e.g. `"Attack, attacks heart"` | **57,057** | `terminology_index_term_embedding` · HNSW cosine (446 MB) |

Example document text for `K35.32`:
> *Acute appendicitis with perforation, localized peritonitis, and gangrene, without abscess. Includes: (Acute) appendicitis with perforation NOS; Perforated appendix NOS; Ruptured appendix (with localized peritonitis) NOS*

Details:

- **Model**: Qwen3-Embedding-0.6B (Q8_0 GGUF, 639 MB) in LM Studio, called through its OpenAI-compatible `/v1/embeddings` endpoint. Output: 1024 dimensions, unit-normalised.
- **Documents are embedded as-is. Queries get an instruction prefix** (Qwen3 is instruction-aware; omitting it costs 1–5% recall per Qwen's model card):
  ```
  Instruct: Given a clinical phrase, retrieve the matching ICD-10-CM diagnosis
  Query: <the search text>
  ```
- **The short description is not embedded** — it is abbreviated (*"w/o perf or gangr"*) and adds noise; it is only in the full-text vector at the lowest weight.
- **Stored per model**: rows are keyed by `(concept or term, model)`, so a second model (e.g. Qwen3-4B) can be embedded side by side and compared without deleting the first.
- **Index**: HNSW with `vector_cosine_ops`.

**The embedding job** (`app/terminology/import_/loaders/embeddings.py`, `just terminology-embeddings`):
- Selects only rows **without** an embedding for the configured model, and writes each batch as soon as it's embedded — **resumable**: Ctrl+C and re-run continues.
- Batches of 64 texts, 4 requests in flight; retries transient HTTP errors 3 times with backoff (LM Studio sometimes returns a 400 while loading models).
- Throughput on the dev machine (RX 6600 + LM Studio, Vulkan): **~25 texts/s** — about 1 h for all codes, ~40 min for index terms. The GPU is only ~50% busy: LM Studio embeds one text at a time, so per-request overhead dominates. llama.cpp's `llama-server` with batching (`-ub 8192 --pooling last`) would be several times faster if re-embedding becomes frequent.

### 3.4 Model choice

Measured on the dev machine (10 lay-term queries vs 14 real descriptions with near-duplicate distractors):

| Model | Correct at top | Avg. margin over runner-up | Speed | 98k codes |
|---|---|---|---|---|
| **Qwen3-0.6B Q8** (chosen) | 9/10 | +0.056 | ~25 texts/s | ~1 h |
| Qwen3-4B Q4_K_M | 9/10 | +0.100 | ~2.6 texts/s | ~10 h |

The 4B separates close candidates better but is ~4× slower and wasn't more often correct on this small test. It can be cut to 1024 dims (Matryoshka) and stored alongside the 0.6B for a proper comparison later (recommendation R5).

---

## 4. How a search is ranked

Code: `app/services/terminology_service.py` (orchestration), `app/repository/terminology_repository.py` (SQL), `app/services/search_ranking.py` (pure ranking steps, unit-tested).

### 4.1 Code-shaped queries → prefix lookup

A query like `K35`, `k3530` or `K35.3` (letter, digit, alphanumeric, optional dot + up to 4 characters) is looked up by **code prefix** in tabular order, whatever the mode. If a code-shaped query matches **no** code — abbreviations like `T2DM` look like a code — it falls through to a normal search.

### 4.2 Text search

Two SQL queries, **top 200 from each**:

| Source | Matches when | Score |
|---|---|---|
| **Codes** (description + synonyms + short description) | full-text matches **all** query words (stemmed, any order) **OR** the query is trigram word-similar to the description | `ts_rank_cd(vector, query, 32)` + `word_similarity(query, display)` |
| **Index terms** | full-text matches all words **OR** the query is trigram word-similar to the term | `ts_rank_cd(vector, query, 33)` + `(word_similarity + similarity) / 2` |

- `ts_rank_cd` normalisation 32 scales the rank to 0–1; **33** additionally divides by the term length.
- **Index-term length penalty** (Report 03, R4a): `word_similarity` alone scores 1.0 whenever the query appears *inside* a longer term, so *"Intoxication caffeine"* tied with *"Intoxication caffeine **with dependence**"*. Averaging with symmetric `similarity` prefers the term that *is* the query. Adopted: rank-1 hits 47% → 49%, recall unchanged.

### 4.3 Semantic search

1. Embed the query (with the instruction prefix).
2. Two HNSW nearest-neighbour queries, **top 200 from each**: code embeddings and index-term embeddings, by cosine distance. Score = cosine similarity.
3. Per query: `SET LOCAL hnsw.ef_search = 200` and `hnsw.iterative_scan = strict_order`, so filters applied after the index scan (code system, model) still return enough rows in exact distance order.

### 4.4 Per-method post-processing (same for text and semantic)

1. **Merge** — rows from codes and index terms are grouped **per code**, keeping the best score. If the best score came from an index term, the hit records it as `matched_on` (e.g. `B03 Smallpox ← "Variola"`), shown in the UI as *"via Alphabetic Index: …"*.
2. **Expand categories** — with `billable_only` (always on for the coding pipeline), a hit on a non-billable category (often from index terms like `S72.9-`) is replaced by up to **10** of its billable descendants' stems, in tabular order, inheriting the category's score (minus a tiny per-position decay). A descendant that scored better on its own keeps its own score.
3. **Collapse 7th-character variants** — codes differing only in the 7th character (encounter/episode: `S72.92XA`, `S72.92XD`, `S72.92XS`) become one hit represented by the best-scoring code; the others are listed in `variants`. The 7th character comes from encounter context, not from the diagnosis wording, so variants shouldn't take up separate slots. Before this, **14%** of top-100 slots (over half in 6% of queries) were such siblings (Report 01, F6).

### 4.5 Hybrid — reciprocal rank fusion (default mode)

```
score(code) = Σ over methods  weight / (60 + rank of the code in that method)
```

- `k = 60`, the standard RRF constant. Uses only rank positions, so text and cosine scores (different scales) never have to be compared.
- Hits are keyed by 7th-character stem, so a collapsed hit in one list meets its sibling in the other.
- Each hit reports `text_rank` and `semantic_rank` — the UI shows which method found the code, and how highly.
- Text weight = semantic weight = **1.0**. Lower text weights were tuned on a dev split and improved ranking at the top, but lowered recall on the test set, so equal weights were kept (Report 03, F4).

### 4.6 What the coding pipeline uses

`TerminologyService.retrieve()` = hybrid search, `billable_only=true`, **top 100**, returning concept records (not just codes) so candidates are stored with foreign keys. Each stored candidate keeps search rank, RRF score, text/semantic ranks, `matched_on` and variants — visible in the encounter screen's **"All 100 candidates"** panel next to Jev's probability for each.

---

## 5. Configuration

`backend/configs/config.yaml` (current values):

```yaml
search:
  default_mode: hybrid          # text | semantic | hybrid
  use_index_terms: true         # §2.3
  collapse_variants: true       # §4.4
  candidate_pool: 200           # rows per source per method before merging
  text_match: all               # all | any | fallback  (any/fallback rejected, §7)
  index_length_penalty: true    # §4.2
  hybrid_text_weight: 1.0       # §4.5

terminology:
  index_holdout_percent: 20     # §2.4 — set 0 for production

embedding:
  base_url: http://localhost:1234/v1
  model: text-embedding-qwen3-embedding-0.6b
  dimensions: 1024
  query_instruction: "Instruct: Given a clinical phrase, retrieve the matching ICD-10-CM diagnosis\nQuery: "
  batch_size: 64
  concurrency: 4
  max_retries: 3
```

Constants in code: RRF `k = 60`, category expansion cap `10` stems (`search_ranking.py`).

---

## 6. Results so far

Held-out Alphabetic Index terms (never loaded into search), hybrid mode, `billable_only`:

| Configuration | R@1 | R@10 | **R@100** | Report |
|---|---|---|---|---|
| Codes only (descriptions + synonyms) | 42% | 64% | 80% | 02 (baseline) |
| + Alphabetic Index terms | 47% | 77% | 92% | 02 |
| + 7th-character collapsing | 47% | 78% | 94% | 02 |
| **+ index-term length penalty (current)** | **49%** | **78%** | **94%** | 03 |

Other test sets with the current setup (Report 03, hybrid):

| Test set | R@10 | R@100 |
|---|---|---|
| Held-out terms phrased unlike the description (low word overlap) | 64% | 87% |
| Held-out terms + one typo | 62% | 85% |
| Lay terms ⚠ | 95% | 98% |
| Abbreviations ⚠ | 83% | 93% |
| Note-style sentences ⚠ | 75% | 100% |

⚠ Small, author-labeled sets (90 queries) — indicative only.

The prototype goal is **R@100 ≥ 95%**; we're at 94%. The remaining misses are mostly rare eponyms (*Cheadle's disease* → scurvy) and generic terms outranked by more specific siblings.

Latency: hybrid p50 ≈ 178 ms, p95 ≈ 352 ms per query on the dev machine (mostly the query embedding in LM Studio).

---

## 7. What we tried and rejected (Report 03)

| Idea | Result | Why rejected |
|---|---|---|
| Text search matches **any** word instead of all | Held-out R@100 94% → 92% | Eponym queries (*"Devic's disease"*) pull in every "… disease" code; fusion rewards that noise |
| Any-word only as a **fallback** when all-words finds < 10 | R@100 94% → 92% | Fires on exactly the rare-eponym queries it hurts |
| **Lower text weight** in hybrid (0.2–0.4, tuned on a dev split) | Better MRR, R@100 −1 to −3 pts | Stage 1 is judged on recall; the decision layer re-ranks the top 100 anyway |

All three remain available as settings so the results can be reproduced.

---

## 8. Operations

From `backend/` (Postgres and LM Studio running):

```bash
just migrate                              # schema (terminology + coding tables)
just terminology-icd10cm                  # codes, hierarchy, synonyms, notes, full-text vectors
just terminology-index                    # Alphabetic Index terms (20% held out)
just terminology-embeddings               # embed codes + index terms (resumable)
just terminology-embeddings index-terms   # or one target; add a number for a trial run
```

Re-running a load replaces that release's rows (embeddings cascade and must be re-run). A new release (e.g. FY2028) is stored alongside, keyed by version.

Evaluation:

```bash
just eval-build     # datasets (held-out test, dev split, contrast set, hand-labeled)
just eval-search    # all configurations -> docs/report/search-eval-results.md
just eval-tune      # dev-split tuning only
```

API: `GET /api/v1/terminology/search?q=…&mode=hybrid&billable_only=true` · `GET /api/v1/terminology/concepts/{code}` · `GET /api/v1/terminology/code-systems` (load and embedding coverage). The frontend's **ICD-10-CM search** page uses the same endpoint.

**Windows note:** use `127.0.0.1`, not `localhost`, in `DATABASE_URL` — each new Postgres connection via `localhost` cost ~2 s (IPv6 tried first, Docker listens on IPv4 only).

---

## 9. Key files

| File | Role |
|---|---|
| `app/terminology/import_/loaders/icd10cm.py` | Order file + tabular XML → codes, hierarchy, synonyms, notes, full-text vectors |
| `app/terminology/import_/loaders/icd10cm_index.py` | Alphabetic Index parsing, "see" resolution, hold-out split, index-term loader |
| `app/terminology/import_/loaders/embeddings.py` | Resumable embedding job for codes and index terms |
| `app/core/embeddings.py` | OpenAI-compatible embedding client (instruction prefix, retries, dimension check) |
| `app/repository/terminology_repository.py` | Text and semantic candidate SQL, category descendants, concept detail |
| `app/services/search_ranking.py` | Merge, category expansion, variant collapsing, RRF fusion (pure, unit-tested) |
| `app/services/terminology_service.py` | Search modes, code-prefix routing, `retrieve()` for the coding pipeline |
| `app/models/terminology/terminology.py` | Tables: code system, concept, synonym, index term, both embedding tables |
| `eval/` | Dataset builder, evaluation harness, fusion tuning |
