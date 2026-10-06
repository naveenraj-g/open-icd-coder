"""Stand-in decision engine: turns search rank into pseudo-probabilities.

⚠ NOT a decision model and NOT calibrated. It exists so the pipeline, API,
storage and review flow can be built and tested end to end before Jev is
connected. Its "probabilities" are exp(-(rank - 1) / TEMPERATURE),
normalised — a monotone function of search rank and nothing more. Confidence
flags derived from them carry no meaning.
"""

import math

from app.coding.engines.base import EngineCandidate, EngineResult

TEMPERATURE = 1.0


class SearchRankEngine:
    name = "search-rank"

    async def score(
        self, soap_note: str, item_text: str, candidates: list[EngineCandidate]
    ) -> EngineResult:
        weights = {c.candidate_id: math.exp(-(c.search_rank - 1) / TEMPERATURE) for c in candidates}
        total = sum(weights.values()) or 1.0
        return EngineResult(
            model="search-rank-v1 (uncalibrated stand-in)",
            probabilities={cid: w / total for cid, w in weights.items()},
            nota_probability=0.0,
            raw_response={"note": "pseudo-probabilities from search rank; not a decision model"},
        )
