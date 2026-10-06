"""Ranking pipeline steps — pure functions, no database."""

import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5433/test")

from app.models.terminology.terminology import TerminologyConcept
from app.services.search_ranking import (
    EXPAND_CAP,
    RRF_K,
    Candidate,
    RankedHit,
    collapse_variants,
    expand_to_billable,
    fuse,
    merge,
    variant_stem,
)


def C(id_, code, billable=True, order=None):
    return TerminologyConcept(id=id_, code=code, display=code, is_billable=billable, sort_order=order or id_)


def test_variant_stem():
    assert variant_stem("S72.92XA") == "S72.92X"
    assert variant_stem("K35.30") == "K35.30"
    assert variant_stem("I10") == "I10"


def test_merge_keeps_best_score_and_its_source():
    concepts = {1: C(1, "B03"), 2: C(2, "L41.0")}
    rows = [(1, 0.40, None), (1, 0.90, "Variola"), (2, 0.50, None), (99, 1.0, "unknown id")]
    out = merge(rows, concepts)
    assert [(c.concept.code, c.score, c.matched_on) for c in out] == [
        ("B03", 0.90, "Variola"),
        ("L41.0", 0.50, None),
    ]


def test_expand_replaces_category_with_billable_descendants():
    header = C(1, "S72.9", billable=False, order=100)
    kids = [C(10 + i, f"S72.9{i}XA", order=101 + i) for i in range(3)]
    out = expand_to_billable([Candidate(header, 0.8, "Fracture femur")], {"S72.9": kids})
    assert [c.concept.code for c in out] == ["S72.90XA", "S72.91XA", "S72.92XA"]
    assert all(c.matched_on == "Fracture femur" for c in out)
    assert out[0].score <= 0.8 and out[0].score > out[1].score


def test_expand_caps_distinct_stems_but_keeps_their_variants():
    header = C(1, "S72", billable=False)
    kids = []
    for stem in range(EXPAND_CAP + 5):
        for ext in "AD":
            kids.append(C(100 + stem * 2 + (ext == "D"), f"S72.{stem:02d}X{ext}", order=100 + stem * 2))
    out = expand_to_billable([Candidate(header, 0.5)], {"S72": kids})
    stems = {variant_stem(c.concept.code) for c in out}
    assert len(stems) == EXPAND_CAP
    assert len(out) == EXPAND_CAP * 2


def test_expand_keeps_a_descendants_own_better_score():
    header = C(1, "K35.3", billable=False)
    k3530 = C(2, "K35.30")
    out = expand_to_billable(
        [Candidate(k3530, 0.95), Candidate(header, 0.60, "Appendicitis")],
        {"K35.3": [k3530]},
    )
    assert [(c.concept.code, c.score, c.matched_on) for c in out] == [("K35.30", 0.95, None)]


def test_collapse_merges_seventh_character_siblings():
    cands = [
        Candidate(C(1, "S72.92XD", order=5), 0.9),
        Candidate(C(2, "K35.30"), 0.8),
        Candidate(C(3, "S72.92XA", order=4), 0.7),
    ]
    hits = collapse_variants(cands)
    assert [(h.concept.code, h.variants) for h in hits] == [
        ("S72.92XD", ["S72.92XA"]),
        ("K35.30", []),
    ]


def test_fuse_joins_on_stem_and_records_ranks():
    a = C(1, "S72.92XA")
    d = C(2, "S72.92XD")
    k = C(3, "K35.30")
    text_hits = [RankedHit(k, 1.0), RankedHit(a, 0.5)]
    sem_hits = [RankedHit(d, 0.9, "Fracture femur left", ["S72.92XS"])]
    fused = fuse(text_hits, sem_hits)
    by = {variant_stem(h.concept.code): h for h in fused}
    femur = by["S72.92X"]
    assert (femur.text_rank, femur.semantic_rank) == (2, 1)
    assert set(femur.variants) == {"S72.92XD", "S72.92XS"}
    assert femur.score == 1 / (RRF_K + 2) + 1 / (RRF_K + 1)
    # Found by both methods beats found by one.
    assert fused[0] is femur


def test_fuse_weights_shift_the_balance():
    t = RankedHit(C(1, "A00.0"), 1.0)
    s = RankedHit(C(2, "B00.0"), 1.0)
    # Each ranked first by one method: equal weights tie (broken by sort_order),
    # a lower text weight lets the semantic hit win.
    assert fuse([t], [s])[0].concept.code == "A00.0"
    lower = fuse([t], [s], text_weight=0.5)
    assert lower[0].concept.code == "B00.0"
    assert lower[0].score == 1 / (RRF_K + 1)
    assert lower[1].score == 0.5 / (RRF_K + 1)


def test_fuse_uncollapsed_does_not_reward_variant_count():
    # One stem with 3 variants per list vs one code ranked first in both.
    many = [RankedHit(C(i, f"S26.00X{e}"), 1.0) for i, e in ((1, "A"), (2, "D"), (3, "S"))]
    top = RankedHit(C(9, "I21.9"), 1.0)
    fused = fuse([top, *many], [top, *many], by_stem=False)
    assert fused[0].concept.code == "I21.9"
    assert all(not h.variants for h in fused)
    assert len(fused) == 4
