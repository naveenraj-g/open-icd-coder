# Search evaluation — generated results

_Generated 2026-09-26T01:06:26+00:00 by `backend/eval/run_search_eval.py`. Do not edit by hand — re-run the script._

- Embedding model: `text-embedding-qwen3-embedding-0.6b`
- Coverage: 98,403 concepts (98,403 embedded) · 57,057 index terms (57,057 embedded) · 20% of index terms held out
- Settings: billable_only=true, limit=100, candidate pool 200 per source, hybrid = RRF k=60
- R@k: gold code (or a collapsed variant of it) in top k · Fam@10: gold 3-char category in top 10 · MRR: mean reciprocal rank · latency includes query embedding
- ⚠ = hand-labeled by the author, pending clinical review

## Configurations compared (hybrid mode)

| Dataset | n | baseline R@10 | baseline R@100 | +index R@10 | +index R@100 | +index +collapse R@10 | +index +collapse R@100 |
|---|---|---|---|---|---|---|---|
| Index terms (held out) | 600 | 64% | 80% | 77% | 92% | 78% | 94% |
| Held-out + 1 typo | 150 | 49% | 64% | 61% | 83% | 63% | 85% |
| Held-out, words shuffled | 150 | 69% | 81% | 85% | 96% | 87% | 96% |
| Lay terms ⚠ | 40 | 78% | 90% | 92% | 98% | 92% | 98% |
| Abbreviations ⚠ | 30 | 83% | 90% | 83% | 93% | 83% | 93% |
| Note sentences ⚠ | 20 | 70% | 80% | 75% | 100% | 75% | 100% |
| Index terms (LOADED — contrast only) | 200 | 68% | 88% | 98% | 100% | 98% | 100% |

| Dataset | n | baseline R@10 | baseline R@100 | +index R@10 | +index R@100 | +index +collapse R@10 | +index +collapse R@100 |
|---|---|---|---|---|---|---|---|
| Held-out · high word overlap | 155 | 95% | 100% | 92% | 100% | 94% | 100% |
| Held-out · partial overlap | 161 | 80% | 95% | 87% | 96% | 88% | 99% |
| Held-out · low overlap | 284 | 39% | 61% | 63% | 87% | 64% | 87% |
| Held-out · main term only | 200 | 54% | 68% | 68% | 86% | 68% | 86% |
| Held-out · 1 sub-term | 200 | 61% | 80% | 80% | 96% | 80% | 98% |
| Held-out · 2+ sub-terms | 200 | 78% | 93% | 83% | 96% | 86% | 98% |
| Lay · verbatim index term ⚠ | 14 | 79% | 93% | 100% | 100% | 100% | 100% |
| Lay · not an index term ⚠ | 26 | 77% | 88% | 88% | 96% | 88% | 96% |

## Full results — baseline

`{'use_index_terms': False, 'collapse_variants': False}` · **Bold** = best R@10 for that dataset

| Dataset | n | Mode | R@1 | R@5 | R@10 | R@50 | R@100 | Fam@10 | MRR | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Index terms (held out) | 600 | text | 37% | 45% | 48% | 53% | 54% | 54% | 0.41 | 35 | 96 |
| Index terms (held out) | 600 | semantic | 38% | 52% | 60% | 72% | 76% | 70% | 0.45 | 128 | 231 |
| Index terms (held out) | 600 | hybrid | 42% | 57% | **64%** | 75% | 80% | 74% | 0.49 | 148 | 214 |
| Held-out + 1 typo | 150 | text | 17% | 23% | 25% | 27% | 27% | 28% | 0.19 | 26 | 75 |
| Held-out + 1 typo | 150 | semantic | 25% | 43% | 49% | 58% | 62% | 58% | 0.33 | 121 | 156 |
| Held-out + 1 typo | 150 | hybrid | 27% | 44% | **49%** | 59% | 64% | 60% | 0.34 | 139 | 197 |
| Held-out, words shuffled | 150 | text | 39% | 47% | 51% | 54% | 57% | 59% | 0.43 | 43 | 94 |
| Held-out, words shuffled | 150 | semantic | 44% | 60% | **69%** | 73% | 78% | 76% | 0.51 | 124 | 150 |
| Held-out, words shuffled | 150 | hybrid | 47% | 64% | **69%** | 75% | 81% | 80% | 0.54 | 157 | 219 |
| Lay terms ⚠ | 40 | text | 32% | 38% | 42% | 50% | 52% | 42% | 0.35 | 30 | 82 |
| Lay terms ⚠ | 40 | semantic | 40% | 65% | 72% | 85% | 88% | 72% | 0.51 | 116 | 165 |
| Lay terms ⚠ | 40 | hybrid | 48% | 68% | **78%** | 88% | 90% | 78% | 0.57 | 142 | 182 |
| Abbreviations ⚠ | 30 | text | 23% | 27% | 27% | 27% | 27% | 27% | 0.24 | 31 | 180 |
| Abbreviations ⚠ | 30 | semantic | 63% | 73% | 77% | 87% | 87% | 77% | 0.68 | 116 | 149 |
| Abbreviations ⚠ | 30 | hybrid | 57% | 80% | **83%** | 90% | 90% | 83% | 0.66 | 141 | 280 |
| Note sentences ⚠ | 20 | text | 0% | 0% | 0% | 0% | 0% | 0% | 0.00 | 52 | 69 |
| Note sentences ⚠ | 20 | semantic | 45% | 70% | **70%** | 75% | 80% | 75% | 0.54 | 129 | 161 |
| Note sentences ⚠ | 20 | hybrid | 45% | 70% | **70%** | 75% | 80% | 75% | 0.54 | 176 | 195 |
| Index terms (LOADED — contrast only) | 200 | text | 36% | 40% | 44% | 48% | 50% | 51% | 0.39 | 45 | 109 |
| Index terms (LOADED — contrast only) | 200 | semantic | 40% | 58% | 63% | 78% | 84% | 73% | 0.49 | 122 | 155 |
| Index terms (LOADED — contrast only) | 200 | hybrid | 46% | 60% | **68%** | 82% | 88% | 79% | 0.53 | 156 | 232 |

| Dataset | n | Mode | R@1 | R@5 | R@10 | R@50 | R@100 | Fam@10 | MRR | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Held-out · high word overlap | 155 | text | 75% | 88% | 92% | 99% | 100% | 97% | 0.81 | 48 | 109 |
| Held-out · high word overlap | 155 | semantic | 65% | 82% | 86% | 92% | 93% | 93% | 0.73 | 130 | 227 |
| Held-out · high word overlap | 155 | hybrid | 69% | 89% | **95%** | 100% | 100% | 99% | 0.78 | 155 | 233 |
| Held-out · partial overlap | 161 | text | 40% | 52% | 57% | 63% | 64% | 70% | 0.45 | 43 | 98 |
| Held-out · partial overlap | 161 | semantic | 49% | 70% | **81%** | 93% | 94% | 92% | 0.59 | 126 | 220 |
| Held-out · partial overlap | 161 | hybrid | 53% | 71% | 80% | 92% | 95% | 93% | 0.61 | 160 | 221 |
| Held-out · low overlap | 284 | text | 14% | 18% | 19% | 21% | 23% | 22% | 0.16 | 27 | 81 |
| Held-out · low overlap | 284 | semantic | 16% | 26% | 33% | 48% | 58% | 45% | 0.22 | 129 | 240 |
| Held-out · low overlap | 284 | hybrid | 20% | 33% | **39%** | 52% | 61% | 50% | 0.27 | 140 | 193 |
| Held-out · main term only | 200 | text | 34% | 40% | 42% | 46% | 47% | 46% | 0.37 | 25 | 86 |
| Held-out · main term only | 200 | semantic | 30% | 40% | 46% | 55% | 62% | 54% | 0.35 | 136 | 290 |
| Held-out · main term only | 200 | hybrid | 36% | 49% | **54%** | 62% | 68% | 62% | 0.42 | 134 | 189 |
| Held-out · 1 sub-term | 200 | text | 40% | 46% | 48% | 50% | 52% | 52% | 0.43 | 29 | 77 |
| Held-out · 1 sub-term | 200 | semantic | 38% | 52% | 58% | 72% | 77% | 70% | 0.45 | 126 | 185 |
| Held-out · 1 sub-term | 200 | hybrid | 42% | 57% | **61%** | 75% | 80% | 72% | 0.49 | 144 | 189 |
| Held-out · 2+ sub-terms | 200 | text | 37% | 48% | 54% | 62% | 62% | 64% | 0.42 | 50 | 108 |
| Held-out · 2+ sub-terms | 200 | semantic | 46% | 64% | 76% | 88% | 91% | 86% | 0.55 | 127 | 188 |
| Held-out · 2+ sub-terms | 200 | hybrid | 48% | 66% | **78%** | 89% | 93% | 88% | 0.57 | 164 | 237 |
| Lay · verbatim index term ⚠ | 14 | text | 43% | 57% | 57% | 71% | 79% | 57% | 0.49 | 27 | 42 |
| Lay · verbatim index term ⚠ | 14 | semantic | 64% | 79% | **86%** | 86% | 86% | 86% | 0.71 | 115 | 127 |
| Lay · verbatim index term ⚠ | 14 | hybrid | 79% | 79% | 79% | 93% | 93% | 79% | 0.79 | 136 | 159 |
| Lay · not an index term ⚠ | 26 | text | 27% | 27% | 35% | 38% | 38% | 35% | 0.28 | 32 | 86 |
| Lay · not an index term ⚠ | 26 | semantic | 27% | 58% | 65% | 85% | 88% | 65% | 0.41 | 116 | 170 |
| Lay · not an index term ⚠ | 26 | hybrid | 31% | 62% | **77%** | 85% | 88% | 77% | 0.45 | 145 | 218 |

## Full results — +index

`{'use_index_terms': True, 'collapse_variants': False}` · **Bold** = best R@10 for that dataset

| Dataset | n | Mode | R@1 | R@5 | R@10 | R@50 | R@100 | Fam@10 | MRR | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Index terms (held out) | 600 | text | 43% | 59% | 65% | 72% | 73% | 76% | 0.50 | 51 | 132 |
| Index terms (held out) | 600 | semantic | 48% | 68% | 76% | 86% | 90% | 86% | 0.57 | 144 | 248 |
| Index terms (held out) | 600 | hybrid | 47% | 70% | **77%** | 88% | 92% | 88% | 0.57 | 181 | 370 |
| Held-out + 1 typo | 150 | text | 32% | 46% | 49% | 54% | 56% | 61% | 0.38 | 42 | 102 |
| Held-out + 1 typo | 150 | semantic | 37% | 54% | 60% | 73% | 79% | 71% | 0.45 | 141 | 239 |
| Held-out + 1 typo | 150 | hybrid | 43% | 58% | **61%** | 76% | 83% | 77% | 0.51 | 170 | 341 |
| Held-out, words shuffled | 150 | text | 46% | 64% | 71% | 79% | 80% | 83% | 0.54 | 63 | 126 |
| Held-out, words shuffled | 150 | semantic | 57% | 78% | **85%** | 93% | 95% | 90% | 0.67 | 144 | 274 |
| Held-out, words shuffled | 150 | hybrid | 53% | 76% | **85%** | 94% | 96% | 90% | 0.63 | 193 | 362 |
| Lay terms ⚠ | 40 | text | 48% | 57% | 60% | 68% | 70% | 60% | 0.52 | 44 | 120 |
| Lay terms ⚠ | 40 | semantic | 60% | 90% | **92%** | 98% | 98% | 92% | 0.73 | 137 | 311 |
| Lay terms ⚠ | 40 | hybrid | 62% | 78% | **92%** | 98% | 98% | 92% | 0.72 | 171 | 329 |
| Abbreviations ⚠ | 30 | text | 27% | 30% | 30% | 30% | 30% | 30% | 0.27 | 38 | 224 |
| Abbreviations ⚠ | 30 | semantic | 70% | 80% | **87%** | 93% | 93% | 87% | 0.75 | 138 | 184 |
| Abbreviations ⚠ | 30 | hybrid | 57% | 80% | 83% | 90% | 93% | 83% | 0.66 | 159 | 427 |
| Note sentences ⚠ | 20 | text | 0% | 0% | 0% | 0% | 0% | 0% | 0.00 | 79 | 100 |
| Note sentences ⚠ | 20 | semantic | 60% | 75% | **75%** | 95% | 100% | 85% | 0.67 | 146 | 224 |
| Note sentences ⚠ | 20 | hybrid | 60% | 75% | **75%** | 95% | 100% | 85% | 0.67 | 215 | 297 |
| Index terms (LOADED — contrast only) | 200 | text | 87% | 96% | **99%** | 100% | 100% | 100% | 0.91 | 65 | 150 |
| Index terms (LOADED — contrast only) | 200 | semantic | 86% | 96% | 97% | 100% | 100% | 98% | 0.91 | 142 | 253 |
| Index terms (LOADED — contrast only) | 200 | hybrid | 90% | 97% | 98% | 100% | 100% | 100% | 0.93 | 194 | 365 |

| Dataset | n | Mode | R@1 | R@5 | R@10 | R@50 | R@100 | Fam@10 | MRR | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Held-out · high word overlap | 155 | text | 69% | 85% | 90% | 97% | 99% | 97% | 0.76 | 58 | 134 |
| Held-out · high word overlap | 155 | semantic | 60% | 83% | 91% | 97% | 98% | 97% | 0.70 | 144 | 278 |
| Held-out · high word overlap | 155 | hybrid | 66% | 86% | **92%** | 99% | 100% | 99% | 0.75 | 186 | 401 |
| Held-out · partial overlap | 161 | text | 40% | 63% | 73% | 78% | 80% | 88% | 0.50 | 62 | 144 |
| Held-out · partial overlap | 161 | semantic | 58% | 81% | 86% | 93% | 96% | 98% | 0.67 | 148 | 311 |
| Held-out · partial overlap | 161 | hybrid | 51% | 78% | **87%** | 94% | 96% | 98% | 0.62 | 196 | 410 |
| Held-out · low overlap | 284 | text | 30% | 43% | 46% | 54% | 56% | 57% | 0.36 | 43 | 117 |
| Held-out · low overlap | 284 | semantic | 37% | 54% | 61% | 76% | 82% | 74% | 0.45 | 141 | 203 |
| Held-out · low overlap | 284 | hybrid | 35% | 55% | **63%** | 80% | 87% | 76% | 0.45 | 170 | 278 |
| Held-out · main term only | 200 | text | 44% | 55% | 58% | 64% | 66% | 64% | 0.49 | 36 | 117 |
| Held-out · main term only | 200 | semantic | 38% | 53% | 60% | 74% | 78% | 70% | 0.45 | 142 | 211 |
| Held-out · main term only | 200 | hybrid | 43% | 62% | **68%** | 81% | 86% | 78% | 0.51 | 163 | 260 |
| Held-out · 1 sub-term | 200 | text | 42% | 58% | 65% | 70% | 72% | 74% | 0.50 | 47 | 111 |
| Held-out · 1 sub-term | 200 | semantic | 50% | 74% | **82%** | 91% | 94% | 92% | 0.62 | 140 | 203 |
| Held-out · 1 sub-term | 200 | hybrid | 48% | 73% | 80% | 91% | 96% | 89% | 0.60 | 174 | 323 |
| Held-out · 2+ sub-terms | 200 | text | 42% | 64% | 72% | 80% | 82% | 90% | 0.52 | 72 | 149 |
| Held-out · 2+ sub-terms | 200 | semantic | 56% | 78% | **84%** | 94% | 97% | 96% | 0.65 | 149 | 311 |
| Held-out · 2+ sub-terms | 200 | hybrid | 50% | 74% | 83% | 94% | 96% | 97% | 0.61 | 207 | 466 |
| Lay · verbatim index term ⚠ | 14 | text | 86% | 86% | 86% | 100% | 100% | 86% | 0.87 | 38 | 50 |
| Lay · verbatim index term ⚠ | 14 | semantic | 79% | 93% | 93% | 100% | 100% | 93% | 0.85 | 130 | 154 |
| Lay · verbatim index term ⚠ | 14 | hybrid | 93% | 93% | **100%** | 100% | 100% | 100% | 0.94 | 155 | 191 |
| Lay · not an index term ⚠ | 26 | text | 27% | 42% | 46% | 50% | 54% | 46% | 0.33 | 45 | 137 |
| Lay · not an index term ⚠ | 26 | semantic | 50% | 88% | **92%** | 96% | 96% | 92% | 0.66 | 143 | 495 |
| Lay · not an index term ⚠ | 26 | hybrid | 46% | 69% | 88% | 96% | 96% | 88% | 0.60 | 183 | 563 |

## Full results — +index +collapse

`{'use_index_terms': True, 'collapse_variants': True}` · **Bold** = best R@10 for that dataset

| Dataset | n | Mode | R@1 | R@5 | R@10 | R@50 | R@100 | Fam@10 | MRR | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Index terms (held out) | 600 | text | 43% | 60% | 66% | 72% | 74% | 77% | 0.51 | 50 | 134 |
| Index terms (held out) | 600 | semantic | 48% | 69% | 77% | 88% | 91% | 87% | 0.58 | 140 | 242 |
| Index terms (held out) | 600 | hybrid | 47% | 71% | **78%** | 90% | 94% | 88% | 0.58 | 177 | 350 |
| Held-out + 1 typo | 150 | text | 32% | 46% | 51% | 54% | 56% | 62% | 0.38 | 42 | 102 |
| Held-out + 1 typo | 150 | semantic | 37% | 54% | 61% | 76% | 81% | 72% | 0.45 | 140 | 234 |
| Held-out + 1 typo | 150 | hybrid | 42% | 59% | **63%** | 79% | 85% | 77% | 0.51 | 169 | 351 |
| Held-out, words shuffled | 150 | text | 46% | 66% | 73% | 79% | 80% | 84% | 0.55 | 62 | 125 |
| Held-out, words shuffled | 150 | semantic | 57% | 82% | **87%** | 95% | 95% | 91% | 0.68 | 144 | 288 |
| Held-out, words shuffled | 150 | hybrid | 51% | 77% | **87%** | 95% | 96% | 91% | 0.63 | 194 | 364 |
| Lay terms ⚠ | 40 | text | 48% | 57% | 62% | 68% | 70% | 62% | 0.52 | 42 | 114 |
| Lay terms ⚠ | 40 | semantic | 60% | 90% | **92%** | 98% | 98% | 92% | 0.73 | 138 | 303 |
| Lay terms ⚠ | 40 | hybrid | 62% | 80% | **92%** | 95% | 98% | 92% | 0.72 | 168 | 342 |
| Abbreviations ⚠ | 30 | text | 27% | 30% | 30% | 30% | 30% | 30% | 0.27 | 36 | 219 |
| Abbreviations ⚠ | 30 | semantic | 70% | 80% | **87%** | 93% | 93% | 87% | 0.75 | 136 | 208 |
| Abbreviations ⚠ | 30 | hybrid | 57% | 80% | 83% | 90% | 93% | 83% | 0.65 | 162 | 403 |
| Note sentences ⚠ | 20 | text | 0% | 0% | 0% | 0% | 0% | 0% | 0.00 | 77 | 102 |
| Note sentences ⚠ | 20 | semantic | 60% | 75% | **75%** | 100% | 100% | 85% | 0.67 | 145 | 213 |
| Note sentences ⚠ | 20 | hybrid | 60% | 75% | **75%** | 100% | 100% | 85% | 0.67 | 212 | 284 |
| Index terms (LOADED — contrast only) | 200 | text | 87% | 96% | **99%** | 100% | 100% | 100% | 0.91 | 66 | 153 |
| Index terms (LOADED — contrast only) | 200 | semantic | 86% | 96% | 98% | 100% | 100% | 99% | 0.91 | 142 | 250 |
| Index terms (LOADED — contrast only) | 200 | hybrid | 89% | 98% | 98% | 100% | 100% | 100% | 0.93 | 196 | 377 |

| Dataset | n | Mode | R@1 | R@5 | R@10 | R@50 | R@100 | Fam@10 | MRR | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Held-out · high word overlap | 155 | text | 69% | 87% | 92% | 99% | 100% | 98% | 0.77 | 58 | 133 |
| Held-out · high word overlap | 155 | semantic | 60% | 83% | 93% | 98% | 99% | 98% | 0.70 | 141 | 268 |
| Held-out · high word overlap | 155 | hybrid | 66% | 87% | **94%** | 100% | 100% | 99% | 0.76 | 186 | 398 |
| Held-out · partial overlap | 161 | text | 40% | 64% | 74% | 79% | 81% | 90% | 0.51 | 62 | 143 |
| Held-out · partial overlap | 161 | semantic | 58% | 81% | 87% | 97% | 98% | 99% | 0.67 | 144 | 339 |
| Held-out · partial overlap | 161 | hybrid | 50% | 80% | **88%** | 96% | 99% | 99% | 0.63 | 189 | 413 |
| Held-out · low overlap | 284 | text | 30% | 43% | 48% | 54% | 56% | 58% | 0.36 | 42 | 117 |
| Held-out · low overlap | 284 | semantic | 37% | 55% | 62% | 77% | 82% | 74% | 0.45 | 138 | 190 |
| Held-out · low overlap | 284 | hybrid | 35% | 57% | **64%** | 80% | 87% | 76% | 0.45 | 168 | 280 |
| Held-out · main term only | 200 | text | 44% | 55% | 58% | 64% | 66% | 65% | 0.49 | 35 | 117 |
| Held-out · main term only | 200 | semantic | 38% | 54% | 61% | 74% | 78% | 72% | 0.46 | 134 | 199 |
| Held-out · main term only | 200 | hybrid | 43% | 62% | **68%** | 82% | 86% | 78% | 0.52 | 157 | 248 |
| Held-out · 1 sub-term | 200 | text | 42% | 60% | 66% | 72% | 72% | 74% | 0.50 | 49 | 104 |
| Held-out · 1 sub-term | 200 | semantic | 50% | 74% | **83%** | 93% | 96% | 92% | 0.62 | 141 | 202 |
| Held-out · 1 sub-term | 200 | hybrid | 48% | 74% | 80% | 92% | 98% | 90% | 0.60 | 175 | 323 |
| Held-out · 2+ sub-terms | 200 | text | 42% | 66% | 74% | 82% | 84% | 91% | 0.53 | 71 | 150 |
| Held-out · 2+ sub-terms | 200 | semantic | 56% | 80% | **86%** | 96% | 98% | 97% | 0.66 | 148 | 294 |
| Held-out · 2+ sub-terms | 200 | hybrid | 50% | 77% | 86% | 95% | 98% | 97% | 0.62 | 203 | 430 |
| Lay · verbatim index term ⚠ | 14 | text | 86% | 86% | 93% | 100% | 100% | 93% | 0.87 | 38 | 47 |
| Lay · verbatim index term ⚠ | 14 | semantic | 79% | 93% | 93% | 100% | 100% | 93% | 0.85 | 131 | 155 |
| Lay · verbatim index term ⚠ | 14 | hybrid | 93% | 93% | **100%** | 100% | 100% | 100% | 0.94 | 157 | 198 |
| Lay · not an index term ⚠ | 26 | text | 27% | 42% | 46% | 50% | 54% | 46% | 0.33 | 44 | 117 |
| Lay · not an index term ⚠ | 26 | semantic | 50% | 88% | **92%** | 96% | 96% | 92% | 0.66 | 143 | 477 |
| Lay · not an index term ⚠ | 26 | hybrid | 46% | 73% | 88% | 92% | 96% | 88% | 0.60 | 173 | 557 |
