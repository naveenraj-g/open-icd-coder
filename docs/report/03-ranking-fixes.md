# Report 03: Ranking Fixes (R4a / R4b / R4c)

| | |
|---|---|
| **Date** | 2026-09-26 |
| **Scope** | Stage 1 search ranking: the three fixes recommended in [Report 02](02-index-terms-and-variant-collapse.md) §7 |
| **Setup** | Same data, embeddings and test sets as Report 02 (the test sets are byte-identical) |
| **Raw results** | [`search-eval-results-report03.md`](search-eval-results-report03.md) (generated tables, 6 configurations) · [`data/search_eval_results_report03.json`](data/search_eval_results_report03.json) (frozen copies) · dev tuning: [`data/fusion_tuning.json`](data/fusion_tuning.json) (fallback), [`data/fusion_tuning_any.json`](data/fusion_tuning_any.json) (any-word) |

---

## 1. Summary

**Only one of the three fixes was adopted.** Two lowered recall and were rejected.

| Fix | What it does | Verdict |
|---|---|---|
| **R4a** Index-term length penalty | Stops an index term that merely *contains* the query from scoring as a perfect match | ✅ **Adopted.** R@1 47% → 49%, MRR 0.58 → 0.59, recall unchanged, no latency cost |
| **R4b** Any-word text matching | Text search matches *any* query word instead of *all* | ❌ **Rejected** (both variants). Held-out R@100 **94% → 92%** |
| **R4c** Weighted fusion | Text counts less than semantic in hybrid, with the weight tuned on a dev split | ❌ **Rejected.** Raised MRR on dev, but lowered R@100 on test |

**Production default after this report** (`configs/config.yaml`): `text_match: all`, `index_length_penalty: true`, `hybrid_text_weight: 1.0`.

Held-out index terms, hybrid: **R@10 78% · R@100 94% · R@1 49% · MRR 0.59**, which is Report 02's recall with a better first place. Stage 1 recall is still one point short of the ≥ 95% goal.

Two lessons for later work:
1. **Top-10 gains and top-100 recall pulled in opposite directions**, and Stage 1 is judged on recall.
2. **Report 02's diagnosis of its regressions was only partly right** (§4.3). R4a fixed the text side of the problem, but the same bias exists in semantic search.

---

## 2. What was tried

| Config | Index terms + collapse | R4a length penalty | Text matching | Hybrid text weight |
|---|---|---|---|---|
| Report 02 default | ✓ | ✗ | all words | 1.0 |
| +R4a | ✓ | ✓ | all words | 1.0 |
| +R4a +any | ✓ | ✓ | **any word** | 1.0 |
| +R4a +any +c | ✓ | ✓ | any word | **0.4** (tuned) |
| +R4a +fallback | ✓ | ✓ | **all, then any if < 10 hits** | 1.0 |
| +R4a +fallback +c | ✓ | ✓ | fallback | **0.2** (tuned) |

- **R4a:** index terms are scored with the mean of `word_similarity` ("query inside term") and symmetric `similarity` ("the two are about the same text"), and the full-text rank is length-normalized.
- **R4b "any":** `websearch_to_tsquery`'s AND becomes OR, with a +0.5 bonus when all words match.
- **R4b "fallback"** was added mid-study, after "any" failed: all-words matching first, and any-word only when that returns fewer than 10 candidates.
- **R4c:** weighted reciprocal rank fusion. The weight was tuned **only on a new dev split** of 300 held-out index terms, disjoint from the test sets, by maximizing dev MRR, a rule fixed before tuning. The test sets were never used for tuning.

---

## 3. Results (hybrid mode)

### 3.1 Held-out index terms (n = 600): the primary result

| Config | R@1 | R@10 | **R@100** | MRR | p50 ms | p95 ms |
|---|---|---|---|---|---|---|
| Report 02 default | 47% | 78% | **94%** | 0.58 | 179 | 347 |
| **+R4a (new default)** | **49%** | 78% | **94%** | **0.59** | 178 | 352 |
| +R4a +any | 44% | 77% | 92% | 0.55 | 237 | 717 |
| +R4a +any +c (w = 0.4) | 45% | 79% | 92% | 0.56 | 239 | 735 |
| +R4a +fallback | 46% | 77% | 92% | 0.56 | 213 | 489 |
| +R4a +fallback +c (w = 0.2) | 48% | 78% | 91% | 0.58 | 215 | 483 |

### 3.2 All test sets: R@10 / R@100

| Test set | Report 02 | **+R4a** | +any | +any +c | +fallback | +fallback +c |
|---|---|---|---|---|---|---|
| Index terms (held out), 600 | 78 / 94 | **78 / 94** | 77 / 92 | 79 / 92 | 77 / 92 | 78 / 91 |
| + 1 typo, 150 | 63 / 85 | 62 / 85 | 63 / 85 | 65 / 84 | 63 / 85 | 60 / 82 |
| Words shuffled, 150 | 87 / 96 | 86 / 96 | 85 / 95 | 90 / 95 | 87 / 96 | 88 / 95 |
| Low word overlap, 284 | 64 / 87 | 64 / 87 | 59 / 83 | 64 / 84 | 62 / 85 | 64 / 83 |
| Main term only, 200 | 68 / 86 | 68 / 86 | 66 / 82 | 64 / 82 | 67 / 84 | 62 / 79 |
| Lay terms ⚠, 40 | 92 / 98 | **95** / 98 | 82 / 98 | 95 / 98 | 85 / 98 | 95 / 98 |
| Lay, not an index term ⚠, 26 | 88 / 96 | **92** / 96 | 73 / 96 | 92 / 96 | 77 / 96 | 92 / 96 |
| Abbreviations ⚠, 30 | 83 / 93 | 83 / 93 | 83 / 93 | 87 / 93 | 83 / 93 | 87 / 93 |
| Note sentences ⚠, 20 | 75 / 100 | 75 / 100 | 80 / 100 | 80 / 100 | 80 / 100 | 80 / 100 |

⚠ Hand-labeled by the author; small; pending clinical review.

### 3.3 Dev-split tuning (300 held-out terms, never reported as results)

| Text matching | Weight chosen | Dev MRR at w = 1.0 → chosen | Dev R@100 at w = 1.0 → chosen |
|---|---|---|---|
| any word | 0.4 | 0.540 → 0.563 | 96.7% → 96.0% |
| fallback | 0.2 | 0.534 → 0.573 | 95.7% → 95.3% |

Dev already showed the trade-off: **lower text weight improves ranking at the top (MRR) and loses a little at depth (R@100).** The test set confirmed it: MRR stayed flat or rose, and R@100 fell by 1 point.

---

## 4. Findings

### F1. R4a is a clean, modest win
Compared with the Report 02 default, **18 held-out queries moved into rank 1 and 7 moved out.** R@10 and R@100 are unchanged, latency is unchanged, and lay terms that aren't index terms improved (R@10 88% → 92%). It's the only change adopted.

### F2. Any-word matching floods hybrid search with generic hits
For eponym queries, OR matching returns **every code containing the common word**. "Devic's disease" pulls in every "… disease" code.

- Text-only recall actually *rose* (444 → 464 of 600 in the top 100), and the number of queries where text found *anything* went from 556 to 590.
- **Hybrid** recall fell (562 → 552). Fusion rewards whatever text ranks highly, so a full-length list of loosely related codes pushes correct semantic hits down.

13 held-out queries fell out of the top 100 and 3 came in. Examples that fell out: *Devic's disease → G36.0* (rank 6 → gone), *Degos' disease*, *Leser-Trélat disease*, *Mibelli's disease*, *Schilder disease*. All were previously found by semantic search and precise all-words text.

It also made search slower: p95 went from 352 to **717 ms**.

### F3. The fallback didn't fix it
Switching to any-word only when all-words finds fewer than 10 candidates still lost recall (94% → 92%). The queries where all-words finds little are **rare eponyms and short terms**: the same queries that any-word hurts. Note-style sentences, which motivated R4b, were already at **100% R@100** through semantic search; any-word only moved them 75% → 80% R@10, which is **one query out of 20**.

### F4. Weighted fusion trades recall for precision at the top
Lower text weights raised MRR on dev (by 0.02–0.04) and on test (flat to +0.02), and gave the best R@10 on several small sets (abbreviations 83% → 87%, shuffled 87% → 90%). But every tuned weight **lowered held-out R@100 by 1–3 points**. Stage 1 hands the top 50–100 to the decision layer, which re-ranks them, so losing recall to gain top-10 order is the wrong trade here. It might be the right trade for a *human-facing* list; see §6.

### F5. Correction to Report 02 F5: the "longer sibling" bias isn't only in text search
Report 02 attributed its 25 top-10 regressions to text scoring (`word_similarity` treats "contained in" as a perfect match). R4a fixed that in text: for "Intoxication caffeine", **text-only** search now ranks the correct F15.929 first, where before it lost to "…caffeine *with dependence*". But **only 3 of the 25 returned to the hybrid top 10.** "Intoxication caffeine" is still at hybrid rank 24, because the semantic side makes the same mistake: the embedding of the longer, more specific index term sits closer to the query than the correct code's formal description ("Other stimulant use, unspecified with intoxication, unspecified"). Fixing this needs a semantic-side or post-fusion remedy (§6), not more text scoring.

### F6. The dev split was worth building
Both tuned weights looked like improvements on the metric they were tuned for, and both reduced recall. Without a separate dev split, we'd have tuned on the test set and probably shipped a regression that looked like a gain.

---

## 5. Limitations

- **Same caveats as Reports 01–02:** index-derived queries are sometimes unnatural, the hand-labeled sets are small and author-labeled, and there's a single embedding model.
- **Differences of 1–2 points on the 600-query set are 6–12 queries.** The R4a gain (MRR +0.01, R@1 +2 points) is small. It's adopted because it has no measured cost, not because it's large.
- **Only the pre-registered weight grid and selection rule were tried** (max dev MRR). A recall-oriented rule (max dev R@100) would have picked w ≈ 1.0, i.e. no change. That's consistent with the decision taken here.

---

## 6. Recommendations

| # | Change | Why |
|---|---|---|
| **R7** | **Accept Stage 1 at R@100 ≈ 94% and move on to the decision layer.** | Per-fix gains are now 0–2 points. Stage 2 results will show whether the missing ~6% matters (e.g. whether Jev's "none of the above" catches them) |
| R8 | For the *human* review screen, consider a separate precision-oriented ordering (e.g. weighted fusion w ≈ 0.2–0.4) of the same candidates | F4: better top-10 order, and the recall cost doesn't matter for display |
| R9 | Semantic-side fix for "longer sibling" bias: penalize index-term hits whose term has qualifiers ("with …", "due to …") absent from the query, or re-rank candidates with a cross-encoder | F5: text-only fixes can't reach it |
| R5 | (from Report 02) Qwen3-4B embeddings | Rare eponyms (Report 02 F8) remain the main residual |

---

## 7. Reproducing

From `backend/`, with Postgres and LM Studio running:

```bash
just eval-build                 # identical test sets + the new dev split
just eval-tune                  # dev-only weight tuning -> docs/report/data/fusion_tuning.json
uv run python -m eval.run_search_eval --configs index_collapse,r4a,r4ab,r4abc,r4a_fb,r4a_fb_c
```

The last command takes about 65 minutes: 6 configurations × 1,190 queries × 3 modes. The `--append` flag adds configurations to an existing results file without re-running the others.

The switches are all in `configs/config.yaml` under `search:`: `text_match` (`all` | `any` | `fallback`), `index_length_penalty` and `hybrid_text_weight`. Rejected options stay in the code so these results can be reproduced.
