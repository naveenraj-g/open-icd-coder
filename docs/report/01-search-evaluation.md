# Report 01 — Stage 1 Search Evaluation (text vs semantic vs hybrid)

| | |
|---|---|
| **Date** | 2026-09-26 |
| **Scope** | Stage 1 terminology search (`/api/v1/terminology/search`), before the Jev decision layer |
| **Code set** | ICD-10-CM FY2027 (98,403 codes, 74,879 billable) |
| **Embedding model** | Qwen3-Embedding-0.6B (Q8_0 GGUF) via LM Studio, 1024 dims, HNSW cosine index |
| **Raw results** | [`search-eval-results-report01.md`](search-eval-results-report01.md) (generated tables) · [`data/search_eval_results_report01.json`](data/search_eval_results_report01.json) (every query, every mode) — frozen copies; later runs overwrite the live files |

---

## 1. Summary

- **Hybrid search is the best mode overall.** It had the highest Recall@10 on all six test sets, tying with semantic on one.
- **Text search alone isn't viable for Stage 1.** It breaks on typos, lay wording, abbreviations and full sentences, and returns *nothing* for note-style sentences.
- **Stage 1 is not at its recall target yet.** The prototype goal is for the correct code to be in the top 50–100 candidates for ≥ 95% of queries (Recall@50–100 ≥ 95%). Hybrid reaches **75% Recall@100** on the official index terms, and only **57%** when the query shares few words with the code's description.
- **The main gap is vocabulary, not ranking.** Most misses are synonyms, eponyms and rare terms (e.g. *Variola → Smallpox*, *Electric feet syndrome → E53.8*) whose link to a code exists only in the official Alphabetic Index. Search doesn't use the index yet.
- **Latency is fine:** hybrid p50 ≈ 100 ms and p95 < 200 ms per query on a local RX 6600.

**Verdict:** hybrid is the right Stage 1 design, but recall must improve before the decision layer is evaluated on top of it. Otherwise Jev would be judged partly on candidates it never received. The top recommendation (§7) is to **add the Alphabetic Index terms to search**, along with a clean evaluation split so that doesn't inflate the results.

---

## 2. What was measured

For every test query, each of the three modes returned its top 100 **billable** codes. This is the realistic Stage 1 setting: the decision layer later chooses among the top 50–100. We recorded where the gold code ranked.

| Metric | Meaning | Why it matters |
|---|---|---|
| **R@k** (Recall@k) | % of queries whose gold code is in the top *k* | **R@50 / R@100** = can Stage 2 even see the right answer? |
| **R@10** | Gold code in the top 10 | What a human reviewer sees without scrolling |
| **Fam@10** | Gold code's **3-character category** in the top 10 | "Right area, wrong specificity", a near-miss |
| **MRR** | Mean of 1/rank (0 if not in the top 100) | Overall ranking quality |
| **p50 / p95 ms** | Per-query latency, including query embedding | Interactive feel |

**Modes:**
- **text** = PostgreSQL full-text search plus trigram similarity over the description and inclusion terms.
- **semantic** = pgvector cosine similarity on Qwen3 embeddings.
- **hybrid** = reciprocal rank fusion (RRF, k = 60) of the top 100 from each.

---

## 3. Test sets

| Set | n | Gold labels from | What it tests |
|---|---|---|---|
| **Official index terms** | 600 | **ICD-10-CM FY2027 Alphabetic Index (CDC/NCHS)** | Real coder terminology, including synonyms and eponyms. Sampled 200 each at depth 0 / 1 / 2+ across all 22 chapters, from 63,202 unambiguous index entries |
| Index terms + 1 typo | 150 | same | One character deleted, swapped or substituted |
| Index terms, words shuffled | 150 | same | Word order changed, connectives dropped |
| Lay terms | 40 | hand-labeled ⚠ | "heart attack", "pink eye", "lockjaw" |
| Abbreviations | 30 | hand-labeled ⚠ | "MI", "HTN", "T2DM", "COPD" |
| Note-style sentences | 20 | hand-labeled ⚠ | "Crushing substernal chest pain, troponin elevated, ST elevations in anterior leads" |

The index-derived sets are the **primary evidence**. Their gold codes come from the official source, not from us. Trailing-dash index codes (e.g. `S72.9-`) count as correct for any code beneath them.

⚠ **The hand-labeled sets (90 queries) were labeled by the author and need review by a clinician or certified coder.** Treat their numbers as indicative. Gold codes are family prefixes where the query lacks detail, and every label was checked to exist in the code set.

---

## 4. Results

### 4.1 By test set (Recall@10 and Recall@100; best in bold)

| Test set | text R@10 | semantic R@10 | **hybrid R@10** | text R@100 | semantic R@100 | **hybrid R@100** |
|---|---|---|---|---|---|---|
| Official index terms (600) | 43% | 56% | **61%** | 47% | 69% | **75%** |
| + 1 typo (150) | 26% | 56% | **58%** | 27% | 65% | **67%** |
| Words shuffled (150) | 41% | 65% | **68%** | 45% | 75% | **81%** |
| Lay terms (40) ⚠ | 30% | 68% | **75%** | 40% | 78% | **85%** |
| Abbreviations (30) ⚠ | 10% | 77% | **80%** | 13% | **90%** | 83% |
| Note-style sentences (20) ⚠ | 0% | **70%** | **70%** | 0% | **80%** | **80%** |

### 4.2 Official index terms, by word overlap with the gold description

| Overlap (share of query words in the description) | n | text R@10 | semantic R@10 | hybrid R@10 | hybrid R@100 |
|---|---|---|---|---|---|
| High (≥ 67%) | 141 | 91% | 88% | **94%** | **100%** |
| Partial (34–66%) | 152 | 51% | 71% | **74%** | 88% |
| Low (< 34%) | 307 | 17% | 35% | **39%** | 57% |

About half of the official index terms (307/600) share little wording with the code they map to. This is the real vocabulary gap that coders bridge with the index.

### 4.3 Official index terms, by specificity (index depth)

| Depth | n | text R@10 | semantic R@10 | hybrid R@10 | hybrid R@100 |
|---|---|---|---|---|---|
| Main term only (e.g. "Arthropathy") | 200 | 44% | 45% | **52%** | 64% |
| 1 sub-term | 200 | 37% | 52% | **57%** | 75% |
| 2+ sub-terms (most specific) | 200 | 48% | 72% | **74%** | 86% |

### 4.4 Latency (per query, local RX 6600)

| Mode | p50 | p95 |
|---|---|---|
| text | 16–104 ms | 56–148 ms |
| semantic | 58–76 ms | 71–128 ms |
| hybrid | 70–172 ms | 109–197 ms |

Ranges are across test sets. Semantic and hybrid include embedding the query in LM Studio.

---

## 5. Findings

### F1. Hybrid is the most robust mode, because the two methods fail on different queries
Hybrid is best or tied on R@10 in every set. The benefit comes from complementary failures: text is precise when the wording matches (91% R@10 at high overlap), and semantic carries lay wording, typos and abbreviations. Rank fusion keeps what each gets right.

### F2. Text search breaks on four realistic conditions
- **Typos:** R@100 falls from 47% to 27%. The trigram fallback compares the whole query to the whole description, so one typo in a multi-word query rarely clears its similarity threshold.
- **Full sentences: 0%.** `websearch_to_tsquery` requires **every** word to match. A 15-word sentence never does.
- **Abbreviations: 10%.** "MI", "HTN" and "COPD" don't appear in official descriptions.
- **Lay terms: 30%.** "heart attack" isn't how ICD words it.

Text's value in hybrid is precision on exact clinical phrasing, not coverage.

### F3. On abbreviations, text search slightly *hurts* hybrid
Semantic alone beats hybrid on abbreviations: R@1 60% vs 47%, and R@100 90% vs 83%. The few text hits for a bare "MI" or "RA" are noise, and fusion ranks them above correct semantic hits. It's a small set (30), but it points at a fix: either weight the fusion or skip text search for short all-caps tokens (see R4).

### F4. Short, bare terms are hard for every mode
Main-term-only queries ("Dermatosis", "Arthropathy", "Thrombosis") reach only 64% hybrid R@100. These map to "unspecified" or "other" codes whose descriptions are generic ("Disorder of the skin and subcutaneous tissue, unspecified"). Semantic is weakest here (24% R@1): a single word gives the embedding little to work with.

### F5. Specific queries are easier than vague ones
Deeper index paths (2+ sub-terms) score *higher* (86% hybrid R@100) than main terms (64%). More detail in the query gives both methods more to match. That's good news for Stage 1, whose inputs (extracted Assessment-line diagnoses) will usually be specific.

### F6. 7th-character variants crowd the candidate list
Measured on 100 index queries with hybrid:
- On average, **14% of the top-100 slots** hold 7th-character siblings of a code already listed. Example: T23.529**A** and T23.529**D** differ only in encounter type (initial vs. subsequent).
- 26% of slots hold 7-character codes (injuries, burns, fractures) at all.
- In **6 of 100 queries, more than half the list** was sibling duplicates, e.g. burn codes flooding "Spoon nail" and "Gamna's disease".

Duplicates take up slots that other candidates could use. The encounter character isn't a search question anyway: it comes from the encounter context, not the diagnosis wording.

### F7. Why hybrid misses: mostly vocabulary, sometimes specificity
Of the 149 index queries where hybrid missed the gold code in the top 100, **55 (37%) still had the right 3-character category** in the list. Those are specificity near-misses, e.g. "Infarction, cerebral, aborted" → gold I63.9, found I63.039. The other ~63% were vocabulary misses:

| Query (official index term) | Gold code | Why search can't find it today |
|---|---|---|
| Variola | B03 Smallpox | Synonym known only to the index |
| Electric feet syndrome | E53.8 Deficiency of other specified B group vitamin | Eponym → "other specified" catch-all |
| Angioendotheliomatosis | C85.8 Other specified types of non-Hodgkin lymphoma | Rare term → catch-all |
| Shaver's disease | J63.1 Bauxite fibrosis (of lung) | Eponym |
| Spoon nail | L60.3 Nail dystrophy | Lay/descriptive synonym |
| Snuffles | R06.5 Mouth breathing | Colloquial synonym |

This mapping knowledge is exactly what the Alphabetic Index contains. It's also why "low overlap" terms are hard: the words simply aren't in the code's description or inclusion terms.

---

## 6. Limitations

- **The query builder produced some unnatural text.** Index paths are joined mechanically, so some queries read like "Ulcer, ulcerated, ulcerating, ulceration, ulcerative lower limb" or "Disease, diseased Gamna's". A clinician wouldn't type these. This likely *understates* real-world performance on the index sets somewhat.
- **The index terms are a proxy for real input.** Stage 1 will actually receive concepts extracted from SOAP notes (Stage 0). Index terms test terminology coverage, not extraction-shaped input. The note-style set (20) is the closest proxy, and it's small and hand-labeled.
- **The hand-labeled sets are small (90 queries) and author-labeled.** They're indicative only, pending clinical review.
- **Single run, single embedding model.** Qwen3-0.6B only. A spot check earlier (10 queries) suggested Qwen3-4B separates close candidates better, but it hasn't been evaluated here.
- **Exact-code recall understates usefulness.** The goal is for the decision layer to choose the exact code. A candidate list with the right category but not the exact code (37% of misses) is still partly useful, but R@k counts it as a miss.

---

## 7. Recommendations (in priority order)

| # | Change | Expected effect | Effort |
|---|---|---|---|
| **R1** | **Load the Alphabetic Index as searchable terms** (63k term → code links) into the synonym table, and embed them | Directly targets F7, the largest failure group; should lift the low-overlap slice most | Medium: loader + re-embed |
| **R2** | **Split the evaluation data before doing R1.** Once index terms are searchable, testing on index terms becomes circular. Hold out part of the index (terms not loaded) plus independent sets (hand-labeled, and later MIMIC-IV or coder-labeled notes) | Keeps the numbers honest | Low |
| **R3** | **Collapse 7th-character variants** in search results (one entry per code stem; pick the extension later from encounter context) | Frees ~14% of candidate slots on average, far more in the worst cases (F6) | Low |
| **R4** | **Improve text search's failure modes:** match *any* word (OR) with rank weighting instead of *all* words; per-word trigram matching for typos; weighted fusion or skipping text for bare abbreviations | Stops text from contributing noise (F2, F3) | Low–Medium |
| **R5** | **Evaluate Qwen3-4B** (cut down to 1024 dims, so no schema change) on the same harness | Possible semantic gain on hard terms; ~4× longer to embed | Medium (~10 h embed) |
| **R6** | **Normalize input in Stage 0.** Have the extraction step rewrite lay terms and abbreviations into clinical wording ("heart attack" → "acute myocardial infarction") before search | Moves hard queries into the high-overlap regime, where hybrid scores 94% R@10 | Part of Stage 0 work |

**Suggested next step:** R2 → R1 → R3, then re-run this evaluation and write Report 02 comparing before and after.

---

## 8. Reproducing

From `backend/`, with Postgres and LM Studio (Qwen3-Embedding-0.6B) running:

```bash
just eval-build    # rebuild datasets (deterministic, seed 20260926)
just eval-search   # ~4 min: runs 990 queries x 3 modes
```

Outputs: `docs/report/search-eval-results.md` (tables) and `docs/report/data/search_eval_results.json` (per-query ranks and top-3 codes). Datasets live in `backend/eval/datasets/`; hand-written labels are in `backend/eval/handwritten.py`.

> **Note:** after this report, `just eval-build` samples index terms only from the held-out share (Report 02), so re-running today does not reproduce these exact queries. The frozen per-query data above is the record.
