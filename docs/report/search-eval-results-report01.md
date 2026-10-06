# Search evaluation — generated results

_Generated 2026-09-25T23:55:43+00:00 by `backend/eval/run_search_eval.py`. Do not edit by hand — re-run the script._

- Embedding model: `text-embedding-qwen3-embedding-0.6b`
- Settings: billable_only=true, limit=100, hybrid = RRF k=60, pool 100 per method
- R@k: gold code in top k · Fam@10: gold 3-char category in top 10 · MRR: mean reciprocal rank · latency includes query embedding
- **Bold** = best R@10 for that dataset

## By dataset

| Dataset | n | Mode | R@1 | R@5 | R@10 | R@50 | R@100 | Fam@10 | MRR | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Official index terms | 600 | text | 35% | 41% | 43% | 46% | 47% | 49% | 0.38 | 44 | 101 |
| Official index terms | 600 | semantic | 34% | 50% | 56% | 65% | 69% | 67% | 0.41 | 71 | 128 |
| Official index terms | 600 | hybrid | 39% | 56% | **61%** | 72% | 75% | 73% | 0.47 | 100 | 169 |
| Index terms + 1 typo | 150 | text | 21% | 26% | 26% | 27% | 27% | 29% | 0.23 | 45 | 111 |
| Index terms + 1 typo | 150 | semantic | 33% | 52% | 56% | 63% | 65% | 64% | 0.41 | 64 | 81 |
| Index terms + 1 typo | 150 | hybrid | 35% | 53% | **58%** | 65% | 67% | 66% | 0.43 | 104 | 173 |
| Index terms, words shuffled | 150 | text | 34% | 39% | 41% | 45% | 45% | 51% | 0.37 | 59 | 106 |
| Index terms, words shuffled | 150 | semantic | 37% | 55% | 65% | 72% | 75% | 73% | 0.45 | 62 | 78 |
| Index terms, words shuffled | 150 | hybrid | 41% | 61% | **68%** | 77% | 81% | 78% | 0.49 | 120 | 176 |
| Lay terms (hand-labeled) | 40 | text | 22% | 25% | 30% | 38% | 40% | 30% | 0.25 | 26 | 56 |
| Lay terms (hand-labeled) | 40 | semantic | 32% | 57% | 68% | 78% | 78% | 68% | 0.45 | 58 | 71 |
| Lay terms (hand-labeled) | 40 | hybrid | 35% | 70% | **75%** | 85% | 85% | 75% | 0.51 | 79 | 109 |
| Abbreviations (hand-labeled) | 30 | text | 7% | 10% | 10% | 10% | 13% | 10% | 0.08 | 16 | 148 |
| Abbreviations (hand-labeled) | 30 | semantic | 60% | 77% | 77% | 83% | 90% | 77% | 0.66 | 58 | 90 |
| Abbreviations (hand-labeled) | 30 | hybrid | 47% | 73% | **80%** | 80% | 83% | 80% | 0.57 | 70 | 194 |
| Note-style sentences (hand-labeled) | 20 | text | 0% | 0% | 0% | 0% | 0% | 0% | 0.00 | 104 | 129 |
| Note-style sentences (hand-labeled) | 20 | semantic | 40% | 65% | **70%** | 80% | 80% | 75% | 0.51 | 76 | 82 |
| Note-style sentences (hand-labeled) | 20 | hybrid | 40% | 65% | **70%** | 80% | 80% | 75% | 0.51 | 172 | 197 |

## Official index terms — sliced

Word overlap = share of the query's content words found in the gold code's official description. Depth = how many sub-terms below the index main term (deeper = more specific).

| Dataset | n | Mode | R@1 | R@5 | R@10 | R@50 | R@100 | Fam@10 | MRR | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Index · high word overlap | 141 | text | 76% | 88% | 91% | 96% | 97% | 96% | 0.81 | 51 | 120 |
| Index · high word overlap | 141 | semantic | 65% | 85% | 88% | 89% | 89% | 90% | 0.73 | 70 | 114 |
| Index · high word overlap | 141 | hybrid | 74% | 91% | **94%** | 100% | 100% | 98% | 0.81 | 107 | 182 |
| Index · partial overlap | 152 | text | 39% | 47% | 51% | 55% | 55% | 60% | 0.43 | 53 | 103 |
| Index · partial overlap | 152 | semantic | 43% | 63% | 71% | 80% | 84% | 82% | 0.53 | 72 | 128 |
| Index · partial overlap | 152 | hybrid | 47% | 68% | **74%** | 85% | 88% | 87% | 0.56 | 111 | 173 |
| Index · low overlap | 307 | text | 14% | 16% | 17% | 19% | 19% | 21% | 0.15 | 39 | 88 |
| Index · low overlap | 307 | semantic | 15% | 27% | 35% | 46% | 52% | 50% | 0.21 | 70 | 128 |
| Index · low overlap | 307 | hybrid | 20% | 33% | **39%** | 53% | 57% | 55% | 0.26 | 96 | 152 |
| Index · main term only | 200 | text | 36% | 44% | 44% | 46% | 48% | 48% | 0.39 | 28 | 62 |
| Index · main term only | 200 | semantic | 24% | 38% | 45% | 51% | 55% | 55% | 0.30 | 72 | 172 |
| Index · main term only | 200 | hybrid | 35% | 48% | **52%** | 61% | 64% | 64% | 0.41 | 83 | 123 |
| Index · 1 sub-term | 200 | text | 30% | 33% | 37% | 40% | 40% | 40% | 0.32 | 41 | 69 |
| Index · 1 sub-term | 200 | semantic | 30% | 46% | 52% | 64% | 70% | 64% | 0.38 | 65 | 96 |
| Index · 1 sub-term | 200 | hybrid | 34% | 50% | **57%** | 71% | 75% | 68% | 0.42 | 97 | 133 |
| Index · 2+ sub-terms | 200 | text | 38% | 46% | 48% | 52% | 52% | 57% | 0.42 | 72 | 125 |
| Index · 2+ sub-terms | 200 | semantic | 47% | 66% | 72% | 80% | 82% | 82% | 0.56 | 75 | 101 |
| Index · 2+ sub-terms | 200 | hybrid | 50% | 68% | **74%** | 84% | 86% | 88% | 0.57 | 134 | 193 |
