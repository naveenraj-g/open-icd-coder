"""Decision engine interface — Stage 2 of the pipeline (docs/goal.md §4.3).

An engine sees the whole SOAP note (context), one codable item, and that
item's search candidates, and returns a probability for each candidate plus
an optional "none of the above" (NOTA) probability. It may only score the
candidates it was given — that closed-set contract is what rules out
hallucinated codes.

Jev plugs in here as one more implementation; so do baselines for comparison.
"""

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class EngineCandidate:
    candidate_id: int
    code: str
    display: str
    search_rank: int


@dataclass
class EngineResult:
    model: str
    # candidate_id -> probability. Any candidate left out gets 0.
    probabilities: dict[int, float]
    # Probability that no candidate fits (NOTA); 0 when the engine has none.
    nota_probability: float = 0.0
    raw_response: dict[str, Any] = field(default_factory=dict)
    cost: float | None = None


class DecisionEngine(Protocol):
    name: str

    async def score(
        self, soap_note: str, item_text: str, candidates: list[EngineCandidate]
    ) -> EngineResult: ...
