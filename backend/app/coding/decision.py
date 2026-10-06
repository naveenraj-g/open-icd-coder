"""Pure decision logic — no I/O, unit-tested directly.

Turns an engine's probabilities into what gets stored and shown:
ranked scores, the assigned code, confidence flags, and the encounter's
review queue (docs/goal.md §6).
"""

from dataclasses import dataclass

from app.coding.engines.base import EngineResult

LOW_CONFIDENCE = "LOW_CONFIDENCE"
NONE_OF_THE_ABOVE = "NONE_OF_THE_ABOVE"
NO_CANDIDATES = "NO_CANDIDATES"
SCORING_FAILED = "SCORING_FAILED"

# Item statuses that need a human's close attention.
_ATTENTION_STATUSES = {"no_candidates", "failed"}


@dataclass(frozen=True)
class RankedScore:
    candidate_id: int | None  # None = "none of the above"
    probability: float
    rank: int


@dataclass(frozen=True)
class Assignment:
    candidate_id: int | None
    probability: float | None
    nota_probability: float
    flags: list[str]


def rank_scores(result: EngineResult, candidate_ids: list[int]) -> list[RankedScore]:
    """Every candidate (missing ones at 0) plus NOTA, most probable first.
    Ties keep search order, NOTA last among equals."""
    order = {cid: i for i, cid in enumerate(candidate_ids)}
    entries: list[tuple[int | None, float]] = [
        (cid, float(result.probabilities.get(cid, 0.0))) for cid in candidate_ids
    ]
    entries.append((None, float(result.nota_probability)))
    entries.sort(key=lambda e: (-e[1], order.get(e[0], len(order))))
    return [RankedScore(cid, p, i) for i, (cid, p) in enumerate(entries, start=1)]


def assign(
    scores: list[RankedScore], low_confidence_threshold: float, nota_flag_threshold: float
) -> Assignment:
    """The assigned code is the most probable real candidate — even when NOTA
    ranks higher, so the reviewer still sees the best available suggestion;
    the NOTA flag tells them the engine doubts all of them."""
    nota = next((s for s in scores if s.candidate_id is None), None)
    nota_p = nota.probability if nota else 0.0
    best = next((s for s in scores if s.candidate_id is not None), None)

    flags: list[str] = []
    if best is None:
        return Assignment(None, None, nota_p, [NO_CANDIDATES])
    if best.probability < low_confidence_threshold:
        flags.append(LOW_CONFIDENCE)
    if nota_p >= nota_flag_threshold or (nota is not None and nota.rank == 1 and nota_p > 0):
        flags.append(NONE_OF_THE_ABOVE)
    return Assignment(best.candidate_id, best.probability, nota_p, flags)


def review_queue(items: list[tuple[str, list[str]]]) -> str:
    """items: (status, flags) for every coded item. Any flag or failure
    sends the whole encounter to close review."""
    for status, flags in items:
        if flags or status in _ATTENTION_STATUSES:
            return "close_review"
    return "standard"
