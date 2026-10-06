# Search evaluation — generated results

_Generated 2026-09-26T02:28:43+00:00 by `backend/eval/run_search_eval.py`. Do not edit by hand — re-run the script._

- Embedding model: `text-embedding-qwen3-embedding-0.6b`
- Coverage: 98,403 concepts (98,403 embedded) · 57,057 index terms (57,057 embedded) · 20% of index terms held out
- Settings: billable_only=true, limit=100, candidate pool 200 per source, hybrid = RRF k=60
- R@k: gold code (or a collapsed variant of it) in top k · Fam@10: gold 3-char category in top 10 · MRR: mean reciprocal rank · latency includes query embedding
- ⚠ = hand-labeled by the author, pending clinical review

## Configurations compared (hybrid mode)

| Dataset | n | +index +collapse R@10 | +index +collapse R@100 | +R4a R@10 | +R4a R@100 | +R4a+b R@10 | +R4a+b R@100 | +R4a+b+c R@10 | +R4a+b+c R@100 | +R4a+fallback R@10 | +R4a+fallback R@100 | +R4a+fallback+c R@10 | +R4a+fallback+c R@100 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Index terms (held out) | 600 | 78% | 94% | 78% | 94% | 77% | 92% | 79% | 92% | 77% | 92% | 78% | 91% |
| Held-out + 1 typo | 150 | 63% | 85% | 62% | 85% | 63% | 85% | 65% | 84% | 63% | 85% | 60% | 82% |
| Held-out, words shuffled | 150 | 87% | 96% | 86% | 96% | 85% | 95% | 90% | 95% | 87% | 96% | 88% | 95% |
| Lay terms ⚠ | 40 | 92% | 98% | 95% | 98% | 82% | 98% | 95% | 98% | 85% | 98% | 95% | 98% |
| Abbreviations ⚠ | 30 | 83% | 93% | 83% | 93% | 83% | 93% | 87% | 93% | 83% | 93% | 87% | 93% |
| Note sentences ⚠ | 20 | 75% | 100% | 75% | 100% | 80% | 100% | 80% | 100% | 80% | 100% | 80% | 100% |
| Index terms (LOADED — contrast only) | 200 | 98% | 100% | 100% | 100% | 98% | 100% | 99% | 100% | 100% | 100% | 98% | 100% |

| Dataset | n | +index +collapse R@10 | +index +collapse R@100 | +R4a R@10 | +R4a R@100 | +R4a+b R@10 | +R4a+b R@100 | +R4a+b+c R@10 | +R4a+b+c R@100 | +R4a+fallback R@10 | +R4a+fallback R@100 | +R4a+fallback+c R@10 | +R4a+fallback+c R@100 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Held-out · high word overlap | 155 | 94% | 100% | 94% | 100% | 95% | 100% | 94% | 99% | 94% | 100% | 94% | 99% |
| Held-out · partial overlap | 161 | 88% | 99% | 88% | 99% | 90% | 99% | 93% | 98% | 87% | 99% | 89% | 98% |
| Held-out · low overlap | 284 | 64% | 87% | 64% | 87% | 59% | 83% | 64% | 84% | 62% | 85% | 64% | 83% |
| Held-out · main term only | 200 | 68% | 86% | 68% | 86% | 66% | 82% | 64% | 82% | 67% | 84% | 62% | 79% |
| Held-out · 1 sub-term | 200 | 80% | 98% | 80% | 98% | 78% | 95% | 84% | 96% | 78% | 95% | 84% | 96% |
| Held-out · 2+ sub-terms | 200 | 86% | 98% | 87% | 98% | 87% | 99% | 90% | 98% | 86% | 98% | 88% | 98% |
| Lay · verbatim index term ⚠ | 14 | 100% | 100% | 100% | 100% | 100% | 100% | 100% | 100% | 100% | 100% | 100% | 100% |
| Lay · not an index term ⚠ | 26 | 88% | 96% | 92% | 96% | 73% | 96% | 92% | 96% | 77% | 96% | 92% | 96% |

## Full results — +index +collapse

`{'use_index_terms': True, 'collapse_variants': True, 'text_any_word': False, 'index_length_penalty': False, 'hybrid_text_weight': 1.0}` · **Bold** = best R@10 for that dataset

| Dataset | n | Mode | R@1 | R@5 | R@10 | R@50 | R@100 | Fam@10 | MRR | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Index terms (held out) | 600 | text | 43% | 60% | 66% | 72% | 74% | 77% | 0.51 | 51 | 132 |
| Index terms (held out) | 600 | semantic | 48% | 69% | 77% | 88% | 91% | 87% | 0.58 | 140 | 250 |
| Index terms (held out) | 600 | hybrid | 47% | 71% | **78%** | 90% | 94% | 88% | 0.58 | 179 | 347 |
| Held-out + 1 typo | 150 | text | 32% | 46% | 51% | 54% | 56% | 62% | 0.38 | 43 | 101 |
| Held-out + 1 typo | 150 | semantic | 37% | 54% | 61% | 76% | 81% | 72% | 0.45 | 141 | 244 |
| Held-out + 1 typo | 150 | hybrid | 42% | 59% | **63%** | 79% | 85% | 77% | 0.51 | 169 | 354 |
| Held-out, words shuffled | 150 | text | 46% | 66% | 73% | 79% | 80% | 84% | 0.55 | 63 | 124 |
| Held-out, words shuffled | 150 | semantic | 57% | 82% | **87%** | 95% | 95% | 91% | 0.68 | 144 | 280 |
| Held-out, words shuffled | 150 | hybrid | 51% | 77% | **87%** | 95% | 96% | 91% | 0.63 | 193 | 365 |
| Lay terms ⚠ | 40 | text | 48% | 57% | 62% | 68% | 70% | 62% | 0.52 | 43 | 113 |
| Lay terms ⚠ | 40 | semantic | 60% | 90% | **92%** | 98% | 98% | 92% | 0.73 | 138 | 322 |
| Lay terms ⚠ | 40 | hybrid | 62% | 80% | **92%** | 95% | 98% | 92% | 0.72 | 165 | 334 |
| Abbreviations ⚠ | 30 | text | 27% | 30% | 30% | 30% | 30% | 30% | 0.27 | 36 | 216 |
| Abbreviations ⚠ | 30 | semantic | 70% | 80% | **87%** | 93% | 93% | 87% | 0.75 | 136 | 195 |
| Abbreviations ⚠ | 30 | hybrid | 57% | 80% | 83% | 90% | 93% | 83% | 0.65 | 164 | 385 |
| Note sentences ⚠ | 20 | text | 0% | 0% | 0% | 0% | 0% | 0% | 0.00 | 83 | 108 |
| Note sentences ⚠ | 20 | semantic | 60% | 75% | **75%** | 100% | 100% | 85% | 0.67 | 146 | 230 |
| Note sentences ⚠ | 20 | hybrid | 60% | 75% | **75%** | 100% | 100% | 85% | 0.67 | 215 | 284 |
| Index terms (LOADED — contrast only) | 200 | text | 87% | 96% | **99%** | 100% | 100% | 100% | 0.91 | 64 | 149 |
| Index terms (LOADED — contrast only) | 200 | semantic | 86% | 96% | 98% | 100% | 100% | 99% | 0.91 | 144 | 253 |
| Index terms (LOADED — contrast only) | 200 | hybrid | 89% | 98% | 98% | 100% | 100% | 100% | 0.93 | 194 | 351 |

| Dataset | n | Mode | R@1 | R@5 | R@10 | R@50 | R@100 | Fam@10 | MRR | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Held-out · high word overlap | 155 | text | 69% | 87% | 92% | 99% | 100% | 98% | 0.77 | 60 | 132 |
| Held-out · high word overlap | 155 | semantic | 60% | 83% | 93% | 98% | 99% | 98% | 0.70 | 140 | 307 |
| Held-out · high word overlap | 155 | hybrid | 66% | 87% | **94%** | 100% | 100% | 99% | 0.76 | 186 | 396 |
| Held-out · partial overlap | 161 | text | 40% | 64% | 74% | 79% | 81% | 90% | 0.51 | 63 | 138 |
| Held-out · partial overlap | 161 | semantic | 58% | 81% | 87% | 97% | 98% | 99% | 0.67 | 142 | 309 |
| Held-out · partial overlap | 161 | hybrid | 50% | 80% | **88%** | 96% | 99% | 99% | 0.63 | 191 | 406 |
| Held-out · low overlap | 284 | text | 30% | 43% | 48% | 54% | 56% | 58% | 0.36 | 42 | 117 |
| Held-out · low overlap | 284 | semantic | 37% | 55% | 62% | 77% | 82% | 74% | 0.45 | 138 | 205 |
| Held-out · low overlap | 284 | hybrid | 35% | 57% | **64%** | 80% | 87% | 76% | 0.45 | 168 | 277 |
| Held-out · main term only | 200 | text | 44% | 55% | 58% | 64% | 66% | 65% | 0.49 | 35 | 116 |
| Held-out · main term only | 200 | semantic | 38% | 54% | 61% | 74% | 78% | 72% | 0.46 | 135 | 197 |
| Held-out · main term only | 200 | hybrid | 43% | 62% | **68%** | 82% | 86% | 78% | 0.52 | 157 | 247 |
| Held-out · 1 sub-term | 200 | text | 42% | 60% | 66% | 72% | 72% | 74% | 0.50 | 48 | 114 |
| Held-out · 1 sub-term | 200 | semantic | 50% | 74% | **83%** | 93% | 96% | 92% | 0.62 | 139 | 210 |
| Held-out · 1 sub-term | 200 | hybrid | 48% | 74% | 80% | 92% | 98% | 90% | 0.60 | 174 | 277 |
| Held-out · 2+ sub-terms | 200 | text | 42% | 66% | 74% | 82% | 84% | 91% | 0.53 | 72 | 151 |
| Held-out · 2+ sub-terms | 200 | semantic | 56% | 80% | **86%** | 96% | 98% | 97% | 0.66 | 147 | 309 |
| Held-out · 2+ sub-terms | 200 | hybrid | 50% | 77% | 86% | 95% | 98% | 97% | 0.62 | 201 | 412 |
| Lay · verbatim index term ⚠ | 14 | text | 86% | 86% | 93% | 100% | 100% | 93% | 0.87 | 38 | 48 |
| Lay · verbatim index term ⚠ | 14 | semantic | 79% | 93% | 93% | 100% | 100% | 93% | 0.85 | 134 | 186 |
| Lay · verbatim index term ⚠ | 14 | hybrid | 93% | 93% | **100%** | 100% | 100% | 100% | 0.94 | 159 | 184 |
| Lay · not an index term ⚠ | 26 | text | 27% | 42% | 46% | 50% | 54% | 46% | 0.33 | 43 | 119 |
| Lay · not an index term ⚠ | 26 | semantic | 50% | 88% | **92%** | 96% | 96% | 92% | 0.66 | 138 | 525 |
| Lay · not an index term ⚠ | 26 | hybrid | 46% | 73% | 88% | 92% | 96% | 88% | 0.60 | 172 | 484 |

## Full results — +R4a

`{'use_index_terms': True, 'collapse_variants': True, 'text_any_word': False, 'index_length_penalty': True, 'hybrid_text_weight': 1.0}` · **Bold** = best R@10 for that dataset

| Dataset | n | Mode | R@1 | R@5 | R@10 | R@50 | R@100 | Fam@10 | MRR | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Index terms (held out) | 600 | text | 46% | 62% | 67% | 73% | 74% | 78% | 0.53 | 50 | 126 |
| Index terms (held out) | 600 | semantic | 48% | 69% | 77% | 88% | 91% | 87% | 0.58 | 138 | 253 |
| Index terms (held out) | 600 | hybrid | 49% | 72% | **78%** | 89% | 94% | 88% | 0.59 | 178 | 352 |
| Held-out + 1 typo | 150 | text | 35% | 47% | 51% | 55% | 55% | 61% | 0.40 | 42 | 110 |
| Held-out + 1 typo | 150 | semantic | 37% | 54% | 61% | 76% | 81% | 72% | 0.45 | 140 | 225 |
| Held-out + 1 typo | 150 | hybrid | 41% | 58% | **62%** | 80% | 85% | 77% | 0.50 | 170 | 362 |
| Held-out, words shuffled | 150 | text | 51% | 69% | 75% | 79% | 81% | 85% | 0.58 | 63 | 121 |
| Held-out, words shuffled | 150 | semantic | 57% | 82% | **87%** | 95% | 95% | 91% | 0.68 | 148 | 272 |
| Held-out, words shuffled | 150 | hybrid | 55% | 81% | 86% | 95% | 96% | 91% | 0.66 | 195 | 365 |
| Lay terms ⚠ | 40 | text | 52% | 55% | 62% | 65% | 70% | 62% | 0.55 | 43 | 125 |
| Lay terms ⚠ | 40 | semantic | 60% | 90% | 92% | 98% | 98% | 92% | 0.73 | 139 | 296 |
| Lay terms ⚠ | 40 | hybrid | 60% | 78% | **95%** | 98% | 98% | 95% | 0.70 | 168 | 324 |
| Abbreviations ⚠ | 30 | text | 27% | 30% | 30% | 30% | 30% | 30% | 0.28 | 37 | 239 |
| Abbreviations ⚠ | 30 | semantic | 70% | 80% | **87%** | 93% | 93% | 87% | 0.75 | 134 | 188 |
| Abbreviations ⚠ | 30 | hybrid | 60% | 80% | 83% | 90% | 93% | 83% | 0.69 | 162 | 407 |
| Note sentences ⚠ | 20 | text | 0% | 0% | 0% | 0% | 0% | 0% | 0.00 | 80 | 104 |
| Note sentences ⚠ | 20 | semantic | 60% | 75% | **75%** | 100% | 100% | 85% | 0.67 | 152 | 226 |
| Note sentences ⚠ | 20 | hybrid | 60% | 75% | **75%** | 100% | 100% | 85% | 0.67 | 211 | 284 |
| Index terms (LOADED — contrast only) | 200 | text | 93% | 96% | 99% | 100% | 100% | 100% | 0.95 | 65 | 153 |
| Index terms (LOADED — contrast only) | 200 | semantic | 86% | 96% | 98% | 100% | 100% | 99% | 0.91 | 140 | 241 |
| Index terms (LOADED — contrast only) | 200 | hybrid | 91% | 98% | **100%** | 100% | 100% | 100% | 0.94 | 194 | 351 |

| Dataset | n | Mode | R@1 | R@5 | R@10 | R@50 | R@100 | Fam@10 | MRR | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Held-out · high word overlap | 155 | text | 72% | 88% | 92% | 99% | 100% | 98% | 0.79 | 58 | 133 |
| Held-out · high word overlap | 155 | semantic | 60% | 83% | 93% | 98% | 99% | 98% | 0.70 | 138 | 286 |
| Held-out · high word overlap | 155 | hybrid | 67% | 89% | **94%** | 100% | 100% | 99% | 0.77 | 184 | 450 |
| Held-out · partial overlap | 161 | text | 46% | 67% | 75% | 80% | 82% | 91% | 0.55 | 62 | 138 |
| Held-out · partial overlap | 161 | semantic | 58% | 81% | 87% | 97% | 98% | 99% | 0.67 | 143 | 306 |
| Held-out · partial overlap | 161 | hybrid | 53% | 82% | **88%** | 95% | 99% | 99% | 0.65 | 189 | 407 |
| Held-out · low overlap | 284 | text | 33% | 45% | 49% | 55% | 55% | 59% | 0.39 | 42 | 118 |
| Held-out · low overlap | 284 | semantic | 37% | 55% | 62% | 77% | 82% | 74% | 0.45 | 136 | 195 |
| Held-out · low overlap | 284 | hybrid | 37% | 57% | **64%** | 80% | 87% | 76% | 0.47 | 169 | 270 |
| Held-out · main term only | 200 | text | 46% | 56% | 60% | 64% | 66% | 67% | 0.51 | 35 | 118 |
| Held-out · main term only | 200 | semantic | 38% | 54% | 61% | 74% | 78% | 72% | 0.46 | 134 | 204 |
| Held-out · main term only | 200 | hybrid | 45% | 62% | **68%** | 81% | 86% | 78% | 0.53 | 157 | 261 |
| Held-out · 1 sub-term | 200 | text | 48% | 62% | 66% | 72% | 73% | 75% | 0.54 | 47 | 110 |
| Held-out · 1 sub-term | 200 | semantic | 50% | 74% | **83%** | 93% | 96% | 92% | 0.62 | 138 | 200 |
| Held-out · 1 sub-term | 200 | hybrid | 50% | 74% | 80% | 92% | 98% | 90% | 0.61 | 174 | 328 |
| Held-out · 2+ sub-terms | 200 | text | 44% | 68% | 76% | 82% | 84% | 91% | 0.55 | 71 | 147 |
| Held-out · 2+ sub-terms | 200 | semantic | 56% | 80% | 86% | 96% | 98% | 97% | 0.66 | 148 | 307 |
| Held-out · 2+ sub-terms | 200 | hybrid | 52% | 79% | **87%** | 95% | 98% | 97% | 0.64 | 199 | 428 |
| Lay · verbatim index term ⚠ | 14 | text | 86% | 86% | 93% | 100% | 100% | 93% | 0.87 | 39 | 51 |
| Lay · verbatim index term ⚠ | 14 | semantic | 79% | 93% | 93% | 100% | 100% | 93% | 0.85 | 132 | 166 |
| Lay · verbatim index term ⚠ | 14 | hybrid | 93% | 93% | **100%** | 100% | 100% | 100% | 0.94 | 161 | 207 |
| Lay · not an index term ⚠ | 26 | text | 35% | 38% | 46% | 46% | 54% | 46% | 0.38 | 44 | 138 |
| Lay · not an index term ⚠ | 26 | semantic | 50% | 88% | **92%** | 96% | 96% | 92% | 0.66 | 143 | 487 |
| Lay · not an index term ⚠ | 26 | hybrid | 42% | 69% | **92%** | 96% | 96% | 92% | 0.57 | 178 | 555 |

## Full results — +R4a+b

`{'use_index_terms': True, 'collapse_variants': True, 'text_any_word': True, 'index_length_penalty': True, 'hybrid_text_weight': 1.0}` · **Bold** = best R@10 for that dataset

| Dataset | n | Mode | R@1 | R@5 | R@10 | R@50 | R@100 | Fam@10 | MRR | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Index terms (held out) | 600 | text | 37% | 51% | 57% | 72% | 77% | 67% | 0.44 | 116 | 525 |
| Index terms (held out) | 600 | semantic | 48% | 69% | 77% | 88% | 91% | 87% | 0.58 | 140 | 245 |
| Index terms (held out) | 600 | hybrid | 44% | 67% | **77%** | 89% | 92% | 85% | 0.55 | 237 | 717 |
| Held-out + 1 typo | 150 | text | 31% | 42% | 47% | 59% | 66% | 52% | 0.37 | 89 | 600 |
| Held-out + 1 typo | 150 | semantic | 37% | 54% | 61% | 76% | 81% | 72% | 0.45 | 143 | 244 |
| Held-out + 1 typo | 150 | hybrid | 37% | 55% | **63%** | 79% | 85% | 73% | 0.46 | 219 | 741 |
| Held-out, words shuffled | 150 | text | 44% | 54% | 62% | 79% | 85% | 71% | 0.50 | 175 | 676 |
| Held-out, words shuffled | 150 | semantic | 57% | 82% | **87%** | 95% | 95% | 91% | 0.68 | 147 | 294 |
| Held-out, words shuffled | 150 | hybrid | 49% | 79% | 85% | 94% | 95% | 89% | 0.61 | 299 | 914 |
| Lay terms ⚠ | 40 | text | 35% | 38% | 45% | 65% | 70% | 45% | 0.38 | 74 | 262 |
| Lay terms ⚠ | 40 | semantic | 60% | 90% | **92%** | 98% | 98% | 92% | 0.73 | 136 | 301 |
| Lay terms ⚠ | 40 | hybrid | 52% | 65% | 82% | 98% | 98% | 82% | 0.61 | 202 | 540 |
| Abbreviations ⚠ | 30 | text | 27% | 30% | 30% | 33% | 33% | 30% | 0.28 | 36 | 231 |
| Abbreviations ⚠ | 30 | semantic | 70% | 80% | **87%** | 93% | 93% | 87% | 0.75 | 134 | 187 |
| Abbreviations ⚠ | 30 | hybrid | 63% | 80% | 83% | 90% | 93% | 83% | 0.70 | 160 | 392 |
| Note sentences ⚠ | 20 | text | 40% | 45% | 50% | 65% | 70% | 55% | 0.42 | 255 | 755 |
| Note sentences ⚠ | 20 | semantic | 60% | 75% | 75% | 100% | 100% | 85% | 0.67 | 153 | 298 |
| Note sentences ⚠ | 20 | hybrid | 60% | 75% | **80%** | 100% | 100% | 85% | 0.66 | 399 | 876 |
| Index terms (LOADED — contrast only) | 200 | text | 55% | 77% | 82% | 96% | 98% | 90% | 0.65 | 182 | 939 |
| Index terms (LOADED — contrast only) | 200 | semantic | 86% | 96% | 98% | 100% | 100% | 99% | 0.91 | 145 | 260 |
| Index terms (LOADED — contrast only) | 200 | hybrid | 76% | 96% | **98%** | 100% | 100% | 100% | 0.84 | 315 | 1119 |

| Dataset | n | Mode | R@1 | R@5 | R@10 | R@50 | R@100 | Fam@10 | MRR | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Held-out · high word overlap | 155 | text | 75% | 88% | 92% | 99% | 100% | 96% | 0.81 | 127 | 503 |
| Held-out · high word overlap | 155 | semantic | 60% | 83% | 93% | 98% | 99% | 98% | 0.70 | 140 | 290 |
| Held-out · high word overlap | 155 | hybrid | 68% | 92% | **95%** | 100% | 100% | 99% | 0.78 | 247 | 694 |
| Held-out · partial overlap | 161 | text | 40% | 61% | 69% | 93% | 94% | 82% | 0.50 | 132 | 718 |
| Held-out · partial overlap | 161 | semantic | 58% | 81% | 87% | 97% | 98% | 99% | 0.67 | 144 | 301 |
| Held-out · partial overlap | 161 | hybrid | 52% | 79% | **90%** | 98% | 99% | 98% | 0.65 | 271 | 919 |
| Held-out · low overlap | 284 | text | 15% | 25% | 32% | 46% | 55% | 43% | 0.21 | 98 | 452 |
| Held-out · low overlap | 284 | semantic | 37% | 55% | **62%** | 77% | 82% | 74% | 0.45 | 137 | 191 |
| Held-out · low overlap | 284 | hybrid | 26% | 46% | 59% | 78% | 83% | 71% | 0.36 | 222 | 572 |
| Held-out · main term only | 200 | text | 36% | 48% | 52% | 60% | 62% | 59% | 0.42 | 47 | 188 |
| Held-out · main term only | 200 | semantic | 38% | 54% | 61% | 74% | 78% | 72% | 0.46 | 133 | 189 |
| Held-out · main term only | 200 | hybrid | 39% | 58% | **66%** | 79% | 82% | 73% | 0.48 | 171 | 340 |
| Held-out · 1 sub-term | 200 | text | 33% | 46% | 52% | 70% | 80% | 63% | 0.40 | 106 | 330 |
| Held-out · 1 sub-term | 200 | semantic | 50% | 74% | **83%** | 93% | 96% | 92% | 0.62 | 140 | 204 |
| Held-out · 1 sub-term | 200 | hybrid | 43% | 67% | 78% | 91% | 95% | 86% | 0.55 | 232 | 498 |
| Held-out · 2+ sub-terms | 200 | text | 42% | 59% | 66% | 87% | 90% | 79% | 0.51 | 231 | 782 |
| Held-out · 2+ sub-terms | 200 | semantic | 56% | 80% | 86% | 96% | 98% | 97% | 0.66 | 149 | 301 |
| Held-out · 2+ sub-terms | 200 | hybrid | 49% | 76% | **87%** | 97% | 99% | 96% | 0.62 | 373 | 960 |
| Lay · verbatim index term ⚠ | 14 | text | 79% | 86% | 86% | 100% | 100% | 86% | 0.83 | 43 | 62 |
| Lay · verbatim index term ⚠ | 14 | semantic | 79% | 93% | 93% | 100% | 100% | 93% | 0.85 | 131 | 153 |
| Lay · verbatim index term ⚠ | 14 | hybrid | 93% | 93% | **100%** | 100% | 100% | 100% | 0.94 | 169 | 202 |
| Lay · not an index term ⚠ | 26 | text | 12% | 12% | 23% | 46% | 54% | 23% | 0.14 | 116 | 430 |
| Lay · not an index term ⚠ | 26 | semantic | 50% | 88% | **92%** | 96% | 96% | 92% | 0.66 | 144 | 482 |
| Lay · not an index term ⚠ | 26 | hybrid | 31% | 50% | 73% | 96% | 96% | 73% | 0.44 | 230 | 964 |

## Full results — +R4a+b+c

`{'use_index_terms': True, 'collapse_variants': True, 'text_any_word': True, 'index_length_penalty': True, 'hybrid_text_weight': 0.4}` · **Bold** = best R@10 for that dataset

| Dataset | n | Mode | R@1 | R@5 | R@10 | R@50 | R@100 | Fam@10 | MRR | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Index terms (held out) | 600 | text | 37% | 51% | 57% | 72% | 77% | 67% | 0.44 | 118 | 496 |
| Index terms (held out) | 600 | semantic | 48% | 69% | 77% | 88% | 91% | 87% | 0.58 | 142 | 290 |
| Index terms (held out) | 600 | hybrid | 45% | 71% | **79%** | 88% | 92% | 87% | 0.56 | 239 | 735 |
| Held-out + 1 typo | 150 | text | 31% | 42% | 47% | 59% | 66% | 52% | 0.37 | 91 | 575 |
| Held-out + 1 typo | 150 | semantic | 37% | 54% | 61% | 76% | 81% | 72% | 0.45 | 144 | 242 |
| Held-out + 1 typo | 150 | hybrid | 40% | 59% | **65%** | 78% | 84% | 73% | 0.48 | 231 | 738 |
| Held-out, words shuffled | 150 | text | 44% | 54% | 62% | 79% | 85% | 71% | 0.50 | 178 | 751 |
| Held-out, words shuffled | 150 | semantic | 57% | 82% | 87% | 95% | 95% | 91% | 0.68 | 150 | 289 |
| Held-out, words shuffled | 150 | hybrid | 55% | 84% | **90%** | 94% | 95% | 91% | 0.67 | 299 | 895 |
| Lay terms ⚠ | 40 | text | 35% | 38% | 45% | 65% | 70% | 45% | 0.38 | 77 | 254 |
| Lay terms ⚠ | 40 | semantic | 60% | 90% | 92% | 98% | 98% | 92% | 0.73 | 141 | 332 |
| Lay terms ⚠ | 40 | hybrid | 52% | 80% | **95%** | 98% | 98% | 95% | 0.66 | 206 | 584 |
| Abbreviations ⚠ | 30 | text | 27% | 30% | 30% | 33% | 33% | 30% | 0.28 | 38 | 234 |
| Abbreviations ⚠ | 30 | semantic | 70% | 80% | **87%** | 93% | 93% | 87% | 0.75 | 138 | 183 |
| Abbreviations ⚠ | 30 | hybrid | 70% | 83% | **87%** | 93% | 93% | 87% | 0.76 | 161 | 391 |
| Note sentences ⚠ | 20 | text | 40% | 45% | 50% | 65% | 70% | 55% | 0.42 | 257 | 798 |
| Note sentences ⚠ | 20 | semantic | 60% | 75% | 75% | 100% | 100% | 85% | 0.67 | 155 | 307 |
| Note sentences ⚠ | 20 | hybrid | 65% | 75% | **80%** | 100% | 100% | 85% | 0.70 | 392 | 866 |
| Index terms (LOADED — contrast only) | 200 | text | 55% | 77% | 82% | 96% | 98% | 90% | 0.65 | 178 | 914 |
| Index terms (LOADED — contrast only) | 200 | semantic | 86% | 96% | 98% | 100% | 100% | 99% | 0.91 | 145 | 246 |
| Index terms (LOADED — contrast only) | 200 | hybrid | 84% | 96% | **99%** | 100% | 100% | 100% | 0.90 | 313 | 1062 |

| Dataset | n | Mode | R@1 | R@5 | R@10 | R@50 | R@100 | Fam@10 | MRR | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Held-out · high word overlap | 155 | text | 75% | 88% | 92% | 99% | 100% | 96% | 0.81 | 126 | 422 |
| Held-out · high word overlap | 155 | semantic | 60% | 83% | 93% | 98% | 99% | 98% | 0.70 | 144 | 299 |
| Held-out · high word overlap | 155 | hybrid | 64% | 88% | **94%** | 99% | 99% | 99% | 0.74 | 250 | 678 |
| Held-out · partial overlap | 161 | text | 40% | 61% | 69% | 93% | 94% | 82% | 0.50 | 132 | 733 |
| Held-out · partial overlap | 161 | semantic | 58% | 81% | 87% | 97% | 98% | 99% | 0.67 | 144 | 310 |
| Held-out · partial overlap | 161 | hybrid | 55% | 85% | **93%** | 98% | 98% | 99% | 0.68 | 267 | 895 |
| Held-out · low overlap | 284 | text | 15% | 25% | 32% | 46% | 55% | 43% | 0.21 | 98 | 418 |
| Held-out · low overlap | 284 | semantic | 37% | 55% | 62% | 77% | 82% | 74% | 0.45 | 139 | 205 |
| Held-out · low overlap | 284 | hybrid | 29% | 54% | **64%** | 77% | 84% | 74% | 0.40 | 224 | 572 |
| Held-out · main term only | 200 | text | 36% | 48% | 52% | 60% | 62% | 59% | 0.42 | 48 | 184 |
| Held-out · main term only | 200 | semantic | 38% | 54% | 61% | 74% | 78% | 72% | 0.46 | 134 | 196 |
| Held-out · main term only | 200 | hybrid | 40% | 57% | **64%** | 76% | 82% | 72% | 0.47 | 173 | 316 |
| Held-out · 1 sub-term | 200 | text | 33% | 46% | 52% | 70% | 80% | 63% | 0.40 | 108 | 319 |
| Held-out · 1 sub-term | 200 | semantic | 50% | 74% | 83% | 93% | 96% | 92% | 0.62 | 142 | 268 |
| Held-out · 1 sub-term | 200 | hybrid | 46% | 76% | **84%** | 92% | 96% | 92% | 0.59 | 232 | 522 |
| Held-out · 2+ sub-terms | 200 | text | 42% | 59% | 66% | 87% | 90% | 79% | 0.51 | 234 | 776 |
| Held-out · 2+ sub-terms | 200 | semantic | 56% | 80% | 86% | 96% | 98% | 97% | 0.66 | 151 | 310 |
| Held-out · 2+ sub-terms | 200 | hybrid | 48% | 80% | **90%** | 97% | 98% | 98% | 0.62 | 367 | 946 |
| Lay · verbatim index term ⚠ | 14 | text | 79% | 86% | 86% | 100% | 100% | 86% | 0.83 | 41 | 65 |
| Lay · verbatim index term ⚠ | 14 | semantic | 79% | 93% | 93% | 100% | 100% | 93% | 0.85 | 134 | 163 |
| Lay · verbatim index term ⚠ | 14 | hybrid | 93% | 100% | **100%** | 100% | 100% | 100% | 0.95 | 163 | 197 |
| Lay · not an index term ⚠ | 26 | text | 12% | 12% | 23% | 46% | 54% | 23% | 0.14 | 118 | 444 |
| Lay · not an index term ⚠ | 26 | semantic | 50% | 88% | **92%** | 96% | 96% | 92% | 0.66 | 150 | 495 |
| Lay · not an index term ⚠ | 26 | hybrid | 31% | 69% | **92%** | 96% | 96% | 92% | 0.50 | 234 | 1134 |

## Full results — +R4a+fallback

`{'use_index_terms': True, 'collapse_variants': True, 'text_match': 'fallback', 'index_length_penalty': True, 'hybrid_text_weight': 1.0}` · **Bold** = best R@10 for that dataset

| Dataset | n | Mode | R@1 | R@5 | R@10 | R@50 | R@100 | Fam@10 | MRR | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Index terms (held out) | 600 | text | 40% | 56% | 63% | 75% | 78% | 73% | 0.48 | 81 | 314 |
| Index terms (held out) | 600 | semantic | 48% | 69% | 77% | 88% | 91% | 87% | 0.58 | 140 | 258 |
| Index terms (held out) | 600 | hybrid | 46% | 68% | **77%** | 89% | 92% | 86% | 0.56 | 213 | 489 |
| Held-out + 1 typo | 150 | text | 32% | 45% | 49% | 59% | 64% | 57% | 0.38 | 84 | 502 |
| Held-out + 1 typo | 150 | semantic | 37% | 54% | 61% | 76% | 81% | 72% | 0.45 | 142 | 238 |
| Held-out + 1 typo | 150 | hybrid | 40% | 56% | **63%** | 80% | 85% | 74% | 0.48 | 218 | 671 |
| Held-out, words shuffled | 150 | text | 45% | 63% | 71% | 84% | 88% | 79% | 0.53 | 109 | 393 |
| Held-out, words shuffled | 150 | semantic | 57% | 82% | 87% | 95% | 95% | 91% | 0.68 | 149 | 280 |
| Held-out, words shuffled | 150 | hybrid | 51% | 81% | **87%** | 95% | 96% | 90% | 0.63 | 247 | 588 |
| Lay terms ⚠ | 40 | text | 45% | 45% | 57% | 65% | 72% | 57% | 0.47 | 64 | 290 |
| Lay terms ⚠ | 40 | semantic | 60% | 90% | **92%** | 98% | 98% | 92% | 0.73 | 139 | 299 |
| Lay terms ⚠ | 40 | hybrid | 52% | 65% | 85% | 98% | 98% | 85% | 0.61 | 197 | 549 |
| Abbreviations ⚠ | 30 | text | 27% | 30% | 30% | 30% | 30% | 30% | 0.28 | 38 | 227 |
| Abbreviations ⚠ | 30 | semantic | 70% | 80% | **87%** | 93% | 93% | 87% | 0.75 | 134 | 185 |
| Abbreviations ⚠ | 30 | hybrid | 60% | 80% | 83% | 90% | 93% | 83% | 0.69 | 166 | 399 |
| Note sentences ⚠ | 20 | text | 40% | 45% | 50% | 65% | 70% | 55% | 0.42 | 349 | 854 |
| Note sentences ⚠ | 20 | semantic | 60% | 75% | 75% | 100% | 100% | 85% | 0.67 | 154 | 236 |
| Note sentences ⚠ | 20 | hybrid | 60% | 75% | **80%** | 100% | 100% | 85% | 0.66 | 496 | 1098 |
| Index terms (LOADED — contrast only) | 200 | text | 82% | 92% | 94% | 100% | 100% | 96% | 0.87 | 100 | 302 |
| Index terms (LOADED — contrast only) | 200 | semantic | 86% | 96% | 98% | 100% | 100% | 99% | 0.91 | 144 | 241 |
| Index terms (LOADED — contrast only) | 200 | hybrid | 90% | 98% | **100%** | 100% | 100% | 100% | 0.94 | 240 | 462 |

| Dataset | n | Mode | R@1 | R@5 | R@10 | R@50 | R@100 | Fam@10 | MRR | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Held-out · high word overlap | 155 | text | 74% | 88% | 92% | 99% | 100% | 98% | 0.80 | 76 | 289 |
| Held-out · high word overlap | 155 | semantic | 60% | 83% | 93% | 98% | 99% | 98% | 0.70 | 140 | 285 |
| Held-out · high word overlap | 155 | hybrid | 66% | 90% | **94%** | 100% | 100% | 99% | 0.77 | 203 | 479 |
| Held-out · partial overlap | 161 | text | 42% | 64% | 76% | 89% | 92% | 90% | 0.52 | 95 | 370 |
| Held-out · partial overlap | 161 | semantic | 58% | 81% | **87%** | 97% | 98% | 99% | 0.67 | 144 | 297 |
| Held-out · partial overlap | 161 | hybrid | 53% | 80% | **87%** | 95% | 99% | 98% | 0.65 | 234 | 572 |
| Held-out · low overlap | 284 | text | 21% | 33% | 40% | 54% | 58% | 50% | 0.27 | 73 | 251 |
| Held-out · low overlap | 284 | semantic | 37% | 55% | **62%** | 77% | 82% | 74% | 0.45 | 138 | 212 |
| Held-out · low overlap | 284 | hybrid | 30% | 49% | **62%** | 79% | 85% | 73% | 0.40 | 204 | 411 |
| Held-out · main term only | 200 | text | 40% | 50% | 56% | 64% | 66% | 62% | 0.45 | 50 | 182 |
| Held-out · main term only | 200 | semantic | 38% | 54% | 61% | 74% | 78% | 72% | 0.46 | 135 | 207 |
| Held-out · main term only | 200 | hybrid | 40% | 60% | **67%** | 80% | 84% | 76% | 0.49 | 176 | 315 |
| Held-out · 1 sub-term | 200 | text | 38% | 55% | 62% | 75% | 80% | 71% | 0.46 | 83 | 254 |
| Held-out · 1 sub-term | 200 | semantic | 50% | 74% | **83%** | 93% | 96% | 92% | 0.62 | 139 | 215 |
| Held-out · 1 sub-term | 200 | hybrid | 45% | 68% | 78% | 90% | 95% | 86% | 0.56 | 211 | 408 |
| Held-out · 2+ sub-terms | 200 | text | 44% | 62% | 72% | 86% | 88% | 86% | 0.53 | 112 | 450 |
| Held-out · 2+ sub-terms | 200 | semantic | 56% | 80% | 86% | 96% | 98% | 97% | 0.66 | 148 | 311 |
| Held-out · 2+ sub-terms | 200 | hybrid | 52% | 76% | **86%** | 96% | 98% | 97% | 0.63 | 270 | 635 |
| Lay · verbatim index term ⚠ | 14 | text | 86% | 86% | 93% | 100% | 100% | 93% | 0.87 | 44 | 64 |
| Lay · verbatim index term ⚠ | 14 | semantic | 79% | 93% | 93% | 100% | 100% | 93% | 0.85 | 142 | 166 |
| Lay · verbatim index term ⚠ | 14 | hybrid | 93% | 93% | **100%** | 100% | 100% | 100% | 0.94 | 167 | 202 |
| Lay · not an index term ⚠ | 26 | text | 23% | 23% | 38% | 46% | 58% | 38% | 0.26 | 113 | 448 |
| Lay · not an index term ⚠ | 26 | semantic | 50% | 88% | **92%** | 96% | 96% | 92% | 0.66 | 136 | 497 |
| Lay · not an index term ⚠ | 26 | hybrid | 31% | 50% | 77% | 96% | 96% | 77% | 0.44 | 229 | 960 |

## Full results — +R4a+fallback+c

`{'use_index_terms': True, 'collapse_variants': True, 'text_match': 'fallback', 'index_length_penalty': True, 'hybrid_text_weight': 0.2}` · **Bold** = best R@10 for that dataset

| Dataset | n | Mode | R@1 | R@5 | R@10 | R@50 | R@100 | Fam@10 | MRR | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Index terms (held out) | 600 | text | 40% | 56% | 63% | 75% | 78% | 73% | 0.48 | 81 | 304 |
| Index terms (held out) | 600 | semantic | 48% | 69% | 77% | 88% | 91% | 87% | 0.58 | 140 | 256 |
| Index terms (held out) | 600 | hybrid | 48% | 71% | **78%** | 88% | 91% | 87% | 0.58 | 215 | 483 |
| Held-out + 1 typo | 150 | text | 32% | 45% | 49% | 59% | 64% | 57% | 0.38 | 85 | 502 |
| Held-out + 1 typo | 150 | semantic | 37% | 54% | **61%** | 76% | 81% | 72% | 0.45 | 143 | 264 |
| Held-out + 1 typo | 150 | hybrid | 38% | 56% | 60% | 77% | 82% | 72% | 0.46 | 213 | 743 |
| Held-out, words shuffled | 150 | text | 45% | 63% | 71% | 84% | 88% | 79% | 0.53 | 108 | 372 |
| Held-out, words shuffled | 150 | semantic | 57% | 82% | 87% | 95% | 95% | 91% | 0.68 | 147 | 292 |
| Held-out, words shuffled | 150 | hybrid | 58% | 82% | **88%** | 94% | 95% | 91% | 0.69 | 251 | 603 |
| Lay terms ⚠ | 40 | text | 45% | 45% | 57% | 65% | 72% | 57% | 0.47 | 63 | 272 |
| Lay terms ⚠ | 40 | semantic | 60% | 90% | 92% | 98% | 98% | 92% | 0.73 | 139 | 308 |
| Lay terms ⚠ | 40 | hybrid | 57% | 92% | **95%** | 98% | 98% | 95% | 0.72 | 193 | 572 |
| Abbreviations ⚠ | 30 | text | 27% | 30% | 30% | 30% | 30% | 30% | 0.28 | 39 | 229 |
| Abbreviations ⚠ | 30 | semantic | 70% | 80% | **87%** | 93% | 93% | 87% | 0.75 | 136 | 194 |
| Abbreviations ⚠ | 30 | hybrid | 70% | 83% | **87%** | 93% | 93% | 87% | 0.77 | 166 | 415 |
| Note sentences ⚠ | 20 | text | 40% | 45% | 50% | 65% | 70% | 55% | 0.42 | 348 | 863 |
| Note sentences ⚠ | 20 | semantic | 60% | 75% | 75% | 100% | 100% | 85% | 0.67 | 157 | 241 |
| Note sentences ⚠ | 20 | hybrid | 65% | 75% | **80%** | 100% | 100% | 85% | 0.71 | 485 | 1000 |
| Index terms (LOADED — contrast only) | 200 | text | 82% | 92% | 94% | 100% | 100% | 96% | 0.87 | 100 | 294 |
| Index terms (LOADED — contrast only) | 200 | semantic | 86% | 96% | 98% | 100% | 100% | 99% | 0.91 | 143 | 248 |
| Index terms (LOADED — contrast only) | 200 | hybrid | 90% | 97% | **98%** | 100% | 100% | 100% | 0.93 | 236 | 449 |

| Dataset | n | Mode | R@1 | R@5 | R@10 | R@50 | R@100 | Fam@10 | MRR | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Held-out · high word overlap | 155 | text | 74% | 88% | 92% | 99% | 100% | 98% | 0.80 | 75 | 283 |
| Held-out · high word overlap | 155 | semantic | 60% | 83% | 93% | 98% | 99% | 98% | 0.70 | 141 | 274 |
| Held-out · high word overlap | 155 | hybrid | 63% | 86% | **94%** | 99% | 99% | 98% | 0.72 | 204 | 473 |
| Held-out · partial overlap | 161 | text | 42% | 64% | 76% | 89% | 92% | 90% | 0.52 | 96 | 389 |
| Held-out · partial overlap | 161 | semantic | 58% | 81% | 87% | 97% | 98% | 99% | 0.67 | 143 | 318 |
| Held-out · partial overlap | 161 | hybrid | 59% | 83% | **89%** | 97% | 98% | 98% | 0.69 | 234 | 589 |
| Held-out · low overlap | 284 | text | 21% | 33% | 40% | 54% | 58% | 50% | 0.27 | 73 | 256 |
| Held-out · low overlap | 284 | semantic | 37% | 55% | 62% | 77% | 82% | 74% | 0.45 | 138 | 200 |
| Held-out · low overlap | 284 | hybrid | 33% | 56% | **64%** | 77% | 83% | 74% | 0.44 | 208 | 428 |
| Held-out · main term only | 200 | text | 40% | 50% | 56% | 64% | 66% | 62% | 0.45 | 48 | 184 |
| Held-out · main term only | 200 | semantic | 38% | 54% | 61% | 74% | 78% | 72% | 0.46 | 134 | 200 |
| Held-out · main term only | 200 | hybrid | 40% | 56% | **62%** | 74% | 79% | 72% | 0.48 | 182 | 322 |
| Held-out · 1 sub-term | 200 | text | 38% | 55% | 62% | 75% | 80% | 71% | 0.46 | 84 | 248 |
| Held-out · 1 sub-term | 200 | semantic | 50% | 74% | 83% | 93% | 96% | 92% | 0.62 | 140 | 209 |
| Held-out · 1 sub-term | 200 | hybrid | 49% | 78% | **84%** | 92% | 96% | 92% | 0.61 | 213 | 416 |
| Held-out · 2+ sub-terms | 200 | text | 44% | 62% | 72% | 86% | 88% | 86% | 0.53 | 112 | 471 |
| Held-out · 2+ sub-terms | 200 | semantic | 56% | 80% | 86% | 96% | 98% | 97% | 0.66 | 148 | 298 |
| Held-out · 2+ sub-terms | 200 | hybrid | 54% | 80% | **88%** | 97% | 98% | 98% | 0.65 | 267 | 628 |
| Lay · verbatim index term ⚠ | 14 | text | 86% | 86% | 93% | 100% | 100% | 93% | 0.87 | 42 | 66 |
| Lay · verbatim index term ⚠ | 14 | semantic | 79% | 93% | 93% | 100% | 100% | 93% | 0.85 | 138 | 170 |
| Lay · verbatim index term ⚠ | 14 | hybrid | 86% | 100% | **100%** | 100% | 100% | 100% | 0.92 | 165 | 209 |
| Lay · not an index term ⚠ | 26 | text | 23% | 23% | 38% | 46% | 58% | 38% | 0.26 | 121 | 449 |
| Lay · not an index term ⚠ | 26 | semantic | 50% | 88% | **92%** | 96% | 96% | 92% | 0.66 | 144 | 482 |
| Lay · not an index term ⚠ | 26 | hybrid | 42% | 88% | **92%** | 96% | 96% | 92% | 0.62 | 232 | 975 |
