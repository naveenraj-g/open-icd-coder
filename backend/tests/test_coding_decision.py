"""Decision logic and the stand-in engine — pure, no database."""

import pytest

from app.coding.decision import (
    LOW_CONFIDENCE,
    NO_CANDIDATES,
    NONE_OF_THE_ABOVE,
    assign,
    rank_scores,
    review_queue,
)
from app.coding.engines.base import EngineCandidate, EngineResult
from app.coding.engines.search_rank import SearchRankEngine


def test_rank_scores_orders_by_probability_and_fills_missing():
    result = EngineResult(model="m", probabilities={10: 0.2, 11: 0.7}, nota_probability=0.1)
    scores = rank_scores(result, [10, 11, 12])
    assert [(s.candidate_id, s.probability, s.rank) for s in scores] == [
        (11, 0.7, 1),
        (10, 0.2, 2),
        (None, 0.1, 3),
        (12, 0.0, 4),
    ]


def test_rank_scores_ties_keep_search_order_nota_last():
    result = EngineResult(model="m", probabilities={10: 0.5, 11: 0.5}, nota_probability=0.0)
    scores = rank_scores(result, [11, 10])
    assert [s.candidate_id for s in scores] == [11, 10, None]


def test_assign_confident_pick_has_no_flags():
    scores = rank_scores(EngineResult("m", {1: 0.94, 2: 0.05}, 0.01), [1, 2])
    a = assign(scores, low_confidence_threshold=0.75, nota_flag_threshold=0.2)
    assert (a.candidate_id, a.probability, a.flags) == (1, 0.94, [])


def test_assign_low_confidence():
    scores = rank_scores(EngineResult("m", {1: 0.6, 2: 0.4}), [1, 2])
    assert assign(scores, 0.75, 0.2).flags == [LOW_CONFIDENCE]


def test_assign_nota_ranked_first_still_suggests_best_real_candidate():
    scores = rank_scores(EngineResult("m", {1: 0.3, 2: 0.1}, nota_probability=0.6), [1, 2])
    a = assign(scores, 0.75, 0.2)
    assert a.candidate_id == 1
    assert a.nota_probability == 0.6
    assert a.flags == [LOW_CONFIDENCE, NONE_OF_THE_ABOVE]


def test_assign_nota_above_threshold_flags_even_when_not_first():
    scores = rank_scores(EngineResult("m", {1: 0.7}, nota_probability=0.25), [1])
    assert NONE_OF_THE_ABOVE in assign(scores, 0.5, 0.2).flags


def test_assign_without_candidates():
    scores = rank_scores(EngineResult("m", {}, nota_probability=0.0), [])
    a = assign(scores, 0.75, 0.2)
    assert (a.candidate_id, a.flags) == (None, [NO_CANDIDATES])


@pytest.mark.parametrize(
    ("items", "queue"),
    [
        ([("scored", []), ("scored", [])], "standard"),
        ([("scored", []), ("scored", [LOW_CONFIDENCE])], "close_review"),
        ([("scored", []), ("failed", [])], "close_review"),
        ([("no_candidates", [])], "close_review"),
        ([], "standard"),
    ],
)
def test_review_queue(items, queue):
    assert review_queue(items) == queue


async def test_search_rank_engine_is_monotone_in_rank_and_sums_to_one():
    cands = [EngineCandidate(100 + r, f"C{r}", "x", r) for r in (3, 1, 2)]
    result = await SearchRankEngine().score("note", "item", cands)
    p = result.probabilities
    assert abs(sum(p.values()) - 1.0) < 1e-9
    assert p[101] > p[102] > p[103]
    assert result.nota_probability == 0.0
    assert "uncalibrated" in result.model


def test_coding_settings_lists_engines_with_warnings():
    from app.coding.engines.jev import JevEngine
    from app.core.config import CodingConfig, JevConfig
    from app.services.coding_service import CodingService

    jev_free = JevEngine(JevConfig(routes={**JevConfig().routes, "opencode": JevConfig().routes["opencode"].model_copy(update={"model": "jev-1.13-free"})}), "opencode", "k")
    svc = CodingService(None, None, {"search-rank": SearchRankEngine(), "jev": jev_free}, CodingConfig(default_engine="jev"))
    s = svc.settings()
    by = {e.name: e for e in s.engines}
    assert by["jev"].is_default and by["jev"].engine == "jev-opencode" and by["jev"].route == "opencode"
    assert by["jev"].kind == "decision_model" and "synthetic data only" in by["jev"].warning
    assert by["search-rank"].kind == "stand_in" and "Uncalibrated" in by["search-rank"].warning
    assert s.low_confidence_threshold == 0.75
