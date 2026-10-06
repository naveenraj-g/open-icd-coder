# Reports

Evaluation reports for the AI-augmented medical coding prototype (see [`../goal.md`](../goal.md)).

| # | Report | Stage | Headline |
|---|---|---|---|
| 01 | [Search evaluation: text vs semantic vs hybrid](01-search-evaluation.md) | Stage 1 retrieval | Hybrid is best everywhere, but hits only 75% Recall@100 on official index terms (goal ≥ 95%); the gap is vocabulary |
| 02 | [Alphabetic Index terms + variant collapsing](02-index-terms-and-variant-collapse.md) | Stage 1 retrieval | On held-out index terms, hybrid Recall@100 80% → 94% and low-overlap terms 61% → 87%; new bias found: generic terms lose to longer index siblings |
| 03 | [Ranking fixes R4a / R4b / R4c](03-ranking-fixes.md) | Stage 1 retrieval | Only the index-term length penalty adopted (R@1 47% → 49%, recall unchanged); any-word matching and weighted fusion rejected: both lowered R@100 94% → 91–92% |

Generated result tables ([`search-eval-results.md`](search-eval-results.md)) and raw per-query data ([`data/`](data/)) are rewritten by the evaluation scripts. Don't edit them by hand.
