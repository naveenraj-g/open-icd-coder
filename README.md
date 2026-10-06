# Open ICD Coder — AI-Augmented ICD-10-CM Medical Coding

A prototype that suggests **ICD-10-CM diagnosis codes** for the conditions in a clinical SOAP note, and keeps a **human coder in the loop** for every code that gets billed.

1. **Search** — hybrid search (full-text + semantic embeddings + the official Alphabetic Index) narrows ~98,000 ICD-10-CM codes to the **top 100 candidates** for each condition.
2. **Decide** — [Jev](https://vercel.com/ai-gateway/models/jev) (TypeSafe AI's evaluation model) scores every candidate, plus a "none of the above" option, and returns a **probability for each**. It can only pick a code that search supplied — no invented codes.
3. **Review** — the highest-probability code is pre-selected; low-confidence or doubtful items are routed to close review. A coder approves, overrides or removes each code, then approves the encounter. The AI's suggestion is never overwritten and every action is audited.

> ⚠️ **Prototype — not a medical device.** It is not validated for clinical or billing use. Use **synthetic or de-identified notes only**: notes are sent to a third-party API (Jev), and the default *free* tier may use prompts for training.

<!-- Screenshot: add docs/images/encounter-review.png -->

---

## Features

- **ICD-10-CM FY2027** loaded from the official CDC/NCHS release: 98,403 codes (74,879 billable), hierarchy, 13,541 inclusion terms, instructional notes (Excludes1/2, Code first, …), and **57,057 Alphabetic Index terms** — including resolved "see" cross-references such as *heart attack → I21.9*.
- **Hybrid search** — PostgreSQL full-text + trigram (typos) + pgvector semantic search, fused by reciprocal rank fusion. Each hit explains itself (text rank, semantic rank, the index term that matched).
- **Local embeddings** with **Qwen3-Embedding-0.6B** (1024-d) through any OpenAI-compatible server (LM Studio by default) — no clinical text leaves your machine for search.
- **Pluggable decision engines** — Jev via **OpenCode Zen** or **Vercel AI Gateway**, plus an uncalibrated `search-rank` stand-in that works with no API key.
- **Review UI** (Next.js) — submit a note, review each condition with its probability, flags and ranked alternatives, inspect all 100 candidates, override with live code search, approve with an audit trail.
- **Evaluation harness** — held-out test sets built from the official index, ablation runs, and written reports on every search change ([docs/report](docs/report/README.md)).

---

## Architecture at a glance

```
   Browser ──► Next.js 16 frontend (App Router, shadcn/ui)
                     │  typed client generated from the API's OpenAPI spec
                     ▼
              FastAPI backend ──────────────► LM Studio  (Qwen3-Embedding-0.6B)
               │  terminology search                      query + document embeddings
               │  coding pipeline ──────────► Jev        (OpenCode Zen / Vercel AI Gateway)
               ▼                                          probability per candidate
     PostgreSQL 17 + pgvector + pg_trgm  (Docker)
       ICD-10-CM codes · index terms · embeddings (HNSW) · encounters · audit trail
```

Details: **[ARCHITECTURE.md](ARCHITECTURE.md)** · how search and embeddings work: **[docs/search-implementation.md](docs/search-implementation.md)** · original proposal: [docs/goal.md](docs/goal.md).

---

## Prerequisites

| Tool | Version | Used for |
|---|---|---|
| [Docker](https://www.docker.com/) | any recent | PostgreSQL 17 + pgvector |
| [uv](https://docs.astral.sh/uv/) | ≥ 0.5 | Python env + dependencies (Python ≥ 3.12; `.python-version` pins 3.14) |
| [just](https://github.com/casey/just) | any | Backend task runner |
| [Node.js](https://nodejs.org/) | ≥ 20.9 | Frontend (Next.js 16) |
| [pnpm](https://pnpm.io/) | ≥ 9 | Frontend packages |
| [LM Studio](https://lmstudio.ai/) | any | Serves the embedding model (or any OpenAI-compatible `/v1/embeddings` server) |
| Jev API key | — | [OpenCode Zen](https://opencode.ai/zen) or [Vercel AI Gateway](https://vercel.com/ai-gateway) — optional, see below |

A GPU helps for embedding (~1.5 h total on an RX 6600) but isn't required.

---

## 0. Get the code

```bash
git clone https://github.com/naveenraj-g/open-icd-coder.git
cd open-icd-coder
```

---

## 1. Download the ICD-10-CM data

The code set is free from CDC/NCHS (no account) and is **not redistributed** in this repository.

**<https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Publications/ICD10CM/2027/>**

Download these two files into [`data/`](data/README.md) and leave them zipped:

| File | Contains |
|---|---|
| `icd10cm-code-descriptions-2027.zip` | All codes, billable flags, short + long descriptions |
| `icd10cm-table-and-index-2027.zip` | Tabular list (inclusion terms, notes) and the Alphabetic Index |

Optional reference: `ICD-10-CM-October-1-2026-FY27-Guidelines.pdf` (official coding guidelines).

---

## 2. Set up the embedding model

Search embeds every code and index term with **[Qwen3-Embedding-0.6B](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B-GGUF)**.

1. In LM Studio, download **`Qwen/Qwen3-Embedding-0.6B-GGUF`** → file **`Qwen3-Embedding-0.6B-Q8_0.gguf`** (639 MB).
2. In *Settings → Runtime*, pick a GPU runtime (e.g. Vulkan / CUDA / Metal) if you have one.
3. Load the model and start the local server (*Developer* tab, port **1234**).
4. Check the model id LM Studio reports and that it matches `embedding.model` in [`backend/configs/config.yaml`](backend/configs/config.yaml) (default `text-embedding-qwen3-embedding-0.6b`):
   ```bash
   curl http://localhost:1234/v1/models
   ```

**What gets embedded** (details in [docs/search-implementation.md §3](docs/search-implementation.md#3-what-is-indexed)):

| Rows | Text embedded |
|---|---|
| 98,403 codes | the long description plus its inclusion terms — `"<description>. Includes: <synonym>; …"` |
| 57,057 index terms | the Alphabetic Index term itself, e.g. `"Attack, attacks heart"` |
| each search query | prefixed with `Instruct: Given a clinical phrase, retrieve the matching ICD-10-CM diagnosis\nQuery: ` (Qwen3 is instruction-aware) |

Vectors are 1024-d, stored in pgvector with **HNSW cosine** indexes. The embedding job is **resumable** (Ctrl+C and re-run). Any OpenAI-compatible embeddings endpoint works — change `embedding.base_url`/`model`; a model with a different dimension needs a new migration.

---

## 3. Choose a decision engine (optional key)

| Engine | Needs | Notes |
|---|---|---|
| `jev` (default) → OpenCode Zen | `OPENCODE_API_KEY` | Model `jev-1.13-free` (prompts may be used for training — **synthetic data only**) or paid `jev-1.13` (zero-retention per OpenCode's docs). Set in `jev.routes.opencode.model` |
| `jev-vercel` → Vercel AI Gateway | `AI_GATEWAY_API_KEY` | Model `typesafe-ai/jev`; the account needs a card on file |
| `search-rank` | nothing | Uncalibrated stand-in: probabilities derived from search rank. Lets you run everything without a key |

Without a key, set `coding.default_engine: search-rank` in `backend/configs/config.yaml`.

---

## 4. Run it

```bash
# Database (PostgreSQL 17 + pgvector, port 5433)
docker compose up -d

# Backend — from backend/
cd backend
cp .env.example .env              # add your Jev key(s)
uv sync
just migrate                      # create tables
just terminology-icd10cm          # load codes, hierarchy, synonyms, notes   (~1 min)
just terminology-index            # load Alphabetic Index terms              (seconds)
just terminology-embeddings       # embed codes + index terms (LM Studio up; ~1.5 h, resumable)
just dev                          # API on http://127.0.0.1:8001  (docs: /docs)

# Frontend — from frontend/ (new terminal)
cd frontend
cp .env.example .env.local
pnpm install
pnpm dev                          # UI on http://localhost:3000
```

Try it: **New encounter → Load example → Code encounter**, then review the suggestions. Check a live Jev route with `just jev-check` (sends a synthetic note only).

---

## Development

```bash
# backend/
just test                 # pytest — integration tests create/drop their own DB (jev_coding_test)
uv run ruff check app tests
just openapi              # export the API spec for the frontend …
# frontend/
pnpm gen:api              # … and regenerate the typed client
pnpm lint && pnpm build
```

Search evaluation (see [docs/report](docs/report/README.md)):

```bash
just eval-build           # build datasets (held-out test, dev split, hand-labeled)
just eval-search          # run all configurations -> docs/report/search-eval-results.md
```

---

## Results so far

On **held-out** official index terms (never loaded into search), hybrid search finds the correct code in the top 100 for **94%** of queries (goal ≥ 95%), at the top 10 for 78%, and first for 49% — up from 80% / 64% / 42% before the Alphabetic Index was added. Lay terms reach 98% and note-style sentences 100% in the top 100 (small hand-labeled sets). Full numbers, methodology and rejected experiments: [docs/report](docs/report/README.md).

---

## Project structure

```
.
├── backend/                  FastAPI + SQLAlchemy (async) + Alembic
│   ├── app/
│   │   ├── routers/          HTTP endpoints (terminology, coding)
│   │   ├── services/         orchestration + pure ranking logic
│   │   ├── repository/       all database I/O
│   │   ├── models/           ORM models (terminology, coding)
│   │   ├── coding/           decision engines (jev, search-rank) + flag/routing logic
│   │   ├── terminology/      ICD-10-CM loaders, index parser, embedding job
│   │   ├── core/             config, database, logging, embedding client
│   │   └── di/               dependency-injector wiring
│   ├── configs/config.yaml   all non-secret settings
│   ├── migrations/           Alembic
│   ├── eval/                 evaluation datasets + harness
│   └── tests/
├── frontend/                 Next.js 16 (App Router, src/) + shadcn/ui (Base UI)
├── db/init/                  Postgres extensions (vector, pg_trgm)
├── data/                     ICD-10-CM downloads (not committed)
├── docs/                     goal, search implementation, evaluation reports
└── docker-compose.yml
```

---

## Acknowledgements

- ICD-10-CM data: [CDC National Center for Health Statistics](https://www.cdc.gov/nchs/icd/icd-10-cm/)
- Decision model: [Jev by TypeSafe AI](https://vercel.com/ai-gateway/models/jev)
- Embeddings: [Qwen3-Embedding](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B-GGUF)
- [pgvector](https://github.com/pgvector/pgvector), [FastAPI](https://fastapi.tiangolo.com/), [Next.js](https://nextjs.org/), [shadcn/ui](https://ui.shadcn.com/)

## License

[MIT](LICENSE) — covers the code in this repository. The ICD-10-CM data is not included; it is downloaded from CDC/NCHS. Jev, Qwen3-Embedding and other third-party services and models are used under their own terms.
