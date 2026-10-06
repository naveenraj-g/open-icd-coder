# Report 02 — Alphabetic Index Terms + Variant Collapsing

| | |
|---|---|
| **Date** | 2026-09-26 |
| **Scope** | Stage 1 search: acting on Report 01's recommendations R1 (Alphabetic Index as searchable terms), R2 (held-out evaluation) and R3 (collapse 7th-character variants) |
| **Code set** | ICD-10-CM FY2027: 98,403 codes, and 57,057 index terms loaded (20% held out) |
| **Embedding model** | Qwen3-Embedding-0.6B (Q8_0) via LM Studio, 1024 dims. All 98,403 concepts and 57,057 index terms embedded |
| **Raw results** | [`search-eval-results-report02.md`](search-eval-results-report02.md) (generated tables, all 3 configurations) · [`data/search_eval_results_report02.json`](data/search_eval_results_report02.json) (every query × config × mode) — frozen copies |
| **Previous** | [Report 01](01-search-evaluation.md) |

---

## 1. Summary

- **Recall has nearly reached the goal.** Recall@100 means the correct code is somewhere in the top 100 candidates. On official index terms that search has **never seen** (held out), hybrid Recall@100 rose from **80% to 94%**, against a prototype goal of ≥ 95%. Recall@10 rose from **64% to 78%**.
- **The hardest cases improved most.** When a query shares few words with the code's description, R@100 went from **61% to 87%**. With one typo, **64% → 85%**. Lay terms reached **98%** and note-style sentences **100%**.
- **The index is doing real work:** in 137 of 283 queries where hybrid ranked the correct code first, the top result came from matching an index term.
- **Holding out test terms was necessary.** On index terms that *were* loaded, hybrid scores **100%** R@100. Testing on those would have reported a perfect result that says nothing about search quality.
- **Costs:**
  - 25 held-out queries dropped out of the top 10, mostly because a more specific index term outranked the generic code (§5.3).
  - Hybrid latency rose from about 148 to 177 ms at p50 and from 214 to 350 ms at p95.
- **Variant collapsing adds a little** (+1–2 points) on top of the index terms. Its main value is freeing candidate slots (Report 01 F6).

**Verdict:** R1 + R3 go into the default configuration (both are on by default in `configs/config.yaml`). The remaining gap to 95% comes from a known ranking bias and rare eponyms, and §7 lists targeted fixes.

---

## 2. What changed since Report 01

| Change | Detail |
|---|---|
| **Alphabetic Index loaded** | 71,265 index paths parsed: 63,260 with a code printed on them, plus **8,005 "see" cross-references resolved to their target's code** (e.g. *Attack, heart → see Infarct, myocardium → I21.9*). Resolving these handles word variants at every level of the path: "Infarct, **infarction**" and "myocardium, **myocardial**". 57,057 unique terms were loaded after the hold-out |
| **Separate searchable rows** | Each index term has its own full-text vector, trigram index and embedding, rather than being folded into one text per code. Catch-all codes have hundreds of index terms, which would blur a single embedding. Matches are grouped back to their code, keeping the best score |
| **Explainable hits** | Each result reports `matched_on`, the index term that produced it (e.g. `B03 Smallpox ← "Variola"`) |
| **Category expansion** | Index terms often name a category ("S72.9-"). With `billable_only`, a category hit expands to up to 10 of its billable descendants |
| **Variant collapsing** | Codes differing only in the 7th character (S72.92X**A**/**D**/**S**) become one hit, with the others listed in `variants` |
| **Held-out evaluation** | A stable hash of the term text puts 20% of index terms outside search (`terminology.index_holdout_percent`). All primary index test queries come from that 20% |
| **Bug found and fixed** | Rank fusion grouped hits by variant stem even when collapsing was off. A stem with *n* variants then collected *n* separate scores, so injury families outranked heart codes for "heart attack". It now groups by exact code when not collapsing, with a regression test |

---

## 3. Evaluation design

Three configurations ran on the same queries, so the only difference is the pipeline (ablation):

| Config | Index terms | Collapse variants |
|---|---|---|
| **baseline** | ✗ | ✗ (the system evaluated in Report 01) |
| **+index** | ✓ | ✗ |
| **+index +collapse** | ✓ | ✓ (**new default**) |

The test sets are the same kinds as in Report 01, but **re-sampled**. The 600 index queries (plus 150 typo and 150 shuffled variants) now come only from the **held-out 20%**, drawn from 12,555 eligible held-out terms. So the baseline numbers here differ slightly from Report 01's; compare configurations **within this report**.

Two contamination checks:
- **index_terms_seen** (200): terms that *are* loaded, run on purpose to show how inflated a non-held-out evaluation would be.
- 14 of the 40 hand-written lay terms ("stroke", "hives", "lockjaw"…) and 2 abbreviations ("GERD", "HIV") turned out to be verbatim loaded index terms, so they're scored separately.

Settings: billable_only = true, top 100 results, 200 candidates per source (description / index term) per method, hybrid = RRF k = 60. A hit counts if its code **or one of its collapsed variants** matches the gold code.

---

## 4. Results (hybrid mode)

### 4.1 By test set

| Test set | n | baseline R@10 | baseline R@100 | +index R@10 | +index R@100 | **+index +collapse R@10** | **+index +collapse R@100** |
|---|---|---|---|---|---|---|---|
| **Index terms (held out)** | 600 | 64% | 80% | 77% | 92% | **78%** | **94%** |
| Held-out + 1 typo | 150 | 49% | 64% | 61% | 83% | **63%** | **85%** |
| Held-out, words shuffled | 150 | 69% | 81% | 85% | 96% | **87%** | **96%** |
| Lay terms ⚠ | 40 | 78% | 90% | 92% | 98% | **92%** | **98%** |
| Abbreviations ⚠ | 30 | 83% | 90% | 83% | 93% | **83%** | **93%** |
| Note sentences ⚠ | 20 | 70% | 80% | 75% | 100% | **75%** | **100%** |
| *Index terms, LOADED (contrast only)* | 200 | 68% | 88% | 98% | 100% | 98% | 100% |

⚠ Hand-labeled by the author; pending clinical review.

### 4.2 Held-out index terms, sliced

| Slice | n | baseline R@10 | baseline R@100 | +index +collapse R@10 | +index +collapse R@100 |
|---|---|---|---|---|---|
| High word overlap with description | 155 | 95% | 100% | 94% | 100% |
| Partial overlap | 161 | 80% | 95% | 88% | 99% |
| **Low overlap** (the vocabulary gap) | 284 | 39% | 61% | **64%** | **87%** |
| Main term only ("Chylothorax") | 200 | 54% | 68% | 68% | 86% |
| 1 sub-term | 200 | 61% | 80% | 80% | 98% |
| 2+ sub-terms (most specific) | 200 | 78% | 93% | 86% | 98% |
| Lay: verbatim index term ⚠ | 14 | 79% | 93% | 100% | 100% |
| Lay: *not* an index term ⚠ | 26 | 77% | 88% | 88% | 96% |

### 4.3 Mode comparison in the new default (+index +collapse)

| Test set | text R@10 | semantic R@10 | hybrid R@10 | hybrid R@100 |
|---|---|---|---|---|
| Index terms (held out) | 66% | 77% | **78%** | 94% |
| + 1 typo | 51% | 61% | **63%** | 85% |
| Lay terms ⚠ | 62% | **92%** | **92%** | 98% |
| Abbreviations ⚠ | 30% | **87%** | 83% | 93% |
| Note sentences ⚠ | 0% | **75%** | **75%** | 100% |

### 4.4 Latency (hybrid, per query, includes query embedding)

| Config | p50 (held-out set) | p95 (held-out set) |
|---|---|---|
| baseline | 148 ms | 214 ms |
| +index +collapse | 177 ms | 350 ms |

---

## 5. Findings

### F1. Index terms close most of the vocabulary gap
The low-overlap slice, where the query shares few words with the code's description, was Report 01's main failure (§5 F7). It improved the most: R@100 **61% → 87%**, R@10 **39% → 64%**. Examples of held-out queries that went from *not found in the top 100* to *found*:

| Held-out query | Gold | Rank now | Matched through loaded index term |
|---|---|---|---|
| Kopp's asthma | E32.8 | 1 | "Asthma, asthmatic Kopp's" |
| Weber-Gubler syndrome | G46.3 | 1 | "Syndrome Gubler-Millard" |
| Disease, diseased Gaisböck's | D75.1 | 1 | "Gaisböck's disease" |
| Impervious urethra | Q64.39 | 1 | "Imperforate urethra" |
| Toxicity fava bean | D55.0 | 1 | "Poisoning fava bean" |

The index lists many conditions under more than one entry (e.g. under both the disease and the eponym), so a held-out entry is often reachable through a loaded sibling phrased differently. That's exactly how coders use the index.

### F2. The biggest gains are on inputs Stage 1 will actually see
Typos gained 21 points of R@100 (64 → 85), shuffled words 15 (81 → 96), and note-style sentences reached 100%. Semantic matching against ~57k short index phrases gives many more close targets than 98k formal descriptions alone.

### F3. The hold-out was necessary
Loaded index terms score **100% R@100 / 98% R@10**, compared with 94% / 78% for held-out ones. The same pattern shows in the lay terms: verbatim index terms went 79% → **100%** R@10, while the other lay terms went 77% → 88%. Any future search evaluation must keep using held-out or independent queries.

### F4. The 94% is a fair estimate, not a pessimistic one
Hypothesis tested: *"The misses are codes whose only index entry happened to be held out, so production (0% held out) would do much better."* **Not supported.** Held-out queries whose gold code has *no* other loaded index route scored **97%** R@100 (n = 77). Those whose code *does* have other loaded routes scored **93%** (n = 523). Codes with many index routes tend to be vague "other specified" catch-alls, which are harder to reach. Loading the remaining 20% in production will add those terms, but these numbers don't suggest a large hidden gain.

### F5. A new bias: generic terms lose to more specific siblings
25 held-out queries fell out of the top 10, compared with 108 that entered it. Nearly all the losses follow one pattern: a **bare or short term** is outranked by a **longer loaded index term that contains it**:

| Held-out query | Gold | Rank baseline → now | Now ranked above it (via index term) |
|---|---|---|---|
| Chylothorax | J94.0 | 7 → 16 | B74.9 ← "Chylothorax filarial" |
| Intoxication caffeine | F15.929 | 1 → 24 | F15.229 ← "Intoxication caffeine with dependence" |
| Senile, senility | R41.81 | 8 → 25 | F03.90 ← "Senile, senility with mental changes" |
| Duplication, duplex stomach | Q40.2 | 3 → 19 | Q43.4 ← "Duplication, duplex anus" |
| Anomaly, anomalous urachus | Q64.4 | 1 → 20 | Q64.5 ← "Anomaly, anomalous urethra absence" |

Cause: text search scores index terms with `word_similarity(query, term)`, which is **1.0 whenever the query appears inside a longer term**. "Intoxication caffeine" therefore matches "Intoxication caffeine *with dependence*" perfectly, even though that term adds a qualifier the query doesn't have. This penalizes exactly the unqualified "unspecified" codes that a plain query should reach. The fix is cheap (R4 in §7). At @100 the effect is almost gone (3 losses vs 83 gains), so it affects ranking more than recall.

### F6. Text search still adds noise on abbreviations and full sentences
In the new default, **semantic alone beats hybrid** on abbreviations (R@10 87% vs 83%, R@1 70% vs 57%), and text still scores **0%** on note sentences. This is the same finding as Report 01 (F2/F3), still unaddressed. The index helped semantic more than text here.

### F7. Variant collapsing: small recall gain, worth keeping
Adding collapsing on top of index terms moved R@10 / R@100 by +1–2 points on most sets (held-out 92% → 94% R@100; 2+ sub-terms 96% → 98%). Its real value is the candidate list: Report 01 measured that 14% of slots, and over half in the worst 6% of queries, went to 7th-character siblings. The encounter character (A/D/S) is chosen later from encounter context, not from the diagnosis wording.

### F8. What's still missed (38 of 600 held-out queries at @100)
- **14 of 38** have the right 3-character category in the top 100: specificity near-misses.
- The rest are mostly **rare eponyms and archaic synonyms** whose meaning isn't in any loaded text or learned by a 0.6B embedding: *Gougerot-Carteaud disease → L83 Acanthosis nigricans*, *Griesinger's disease → B76.0 Ancylostomiasis*, *Cheadle's disease → E54 Scurvy*, *Mietens' syndrome → Q87.2*, *Onychophagia → F98.8 (nail biting)*, *Telescoped bowel → K56.1 Intussusception*.
- A few are artifacts of how index paths are joined into queries ("Ulcer, ulcerated, ulcerating, ulceration, ulcerative lower limb…"), the same limitation as in Report 01.

In production, loading 100% of the index gives search the exact eponyms above. A larger embedding model is the other lever (R6).

---

## 6. Limitations

- **Unnatural index-derived queries.** Same as Report 01: joined index paths ("Disease, diseased nails specified") aren't how clinicians type. That likely *understates* real performance somewhat.
- **The hand-labeled sets are small and author-labeled** (90 queries), with 16 overlapping loaded index terms. They're indicative only.
- **Index terms are still a proxy for Stage 0 output.** The eventual input is concepts extracted from SOAP notes. A note-derived test set (MIMIC-IV or coder-labeled) is still needed.
- **Single run, single embedding model** (Qwen3-0.6B). The numbers are deterministic given the data, but model-specific.
- **Latency was measured on one desktop GPU through LM Studio.** Query embedding dominates, and the extra index-term queries account for the p95 rise.

---

## 7. Recommendations

| # | Change | Targets | Effort |
|---|---|---|---|
| **R4a** | **Penalize extra words in index-term text matches.** Score with symmetric `similarity()` or a length-ratio factor instead of pure `word_similarity()`, so "Intoxication caffeine" prefers the term that *is* it over one that *contains* it | F5: most of the 25 top-10 regressions | Low |
| **R4b** | **Fix text search's failure modes:** match *any* word, ranked (OR), instead of *all* words (AND), so full sentences stop returning nothing; skip or down-weight text for bare abbreviations | F6: note sentences 0%, abbreviations | Low–Medium |
| **R4c** | **Weighted fusion.** Give semantic more weight than text in RRF, or tune weights on a dev split | F6 | Low |
| R5 | Evaluate Qwen3-4B (cut to 1024 dims, same schema) | F8 rare eponyms | Medium (~15 h to embed concepts + index terms at 4B speed) |
| R6 | Stage 0 normalization of lay terms and abbreviations | Remaining lay/abbreviation misses | Part of Stage 0 |
| — | **Production:** set `index_holdout_percent: 0` and reload the index | Adds the held-out 20% (incl. the exact F8 eponyms) | Trivial, but **evaluation then needs independent query sets** |

**Suggested next step:** R4a + R4b + R4c together (all small, all in the ranking layer, no re-embedding), then a short Report 03 with the same three datasets. After that, Stage 1 is ready for the decision layer to be evaluated on top of it.

---

## 8. Reproducing

From `backend/`, with Postgres and LM Studio (Qwen3-Embedding-0.6B) running:

```bash
just migrate
just terminology-index                    # 57,057 terms; 20% held out
just terminology-embeddings index-terms   # ~40 min on RX 6600 + LM Studio
just eval-build                           # held-out + contrast + hand-written sets
just eval-search                          # ~24 min: 3 configs x 1,190 queries x 3 modes
```

Report 01's outputs are frozen as `search-eval-results-report01.md` and `data/search_eval_results_report01.json`.
