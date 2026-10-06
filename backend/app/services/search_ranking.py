"""Pure ranking steps for terminology search — no I/O, unit-tested directly.

Pipeline, per retrieval method (text or semantic):

  1. merge      candidates from concept descriptions and from Alphabetic Index
                terms are grouped per concept, keeping the best score and the
                index term that produced it (matched_on)
  2. expand     with billable_only, a hit on a non-billable category (the index
                often gives "S72.9-") is replaced by its billable descendants,
                which inherit the category's score
  3. collapse   codes that differ only in the 7th character (encounter / episode:
                S72.92XA vs S72.92XD) become one hit listing the others as
                variants — the 7th character comes from encounter context, not
                from the diagnosis wording, so they shouldn't crowd the list

Hybrid mode then fuses the two methods' final lists with reciprocal rank fusion.
"""

from dataclasses import dataclass, field

from app.models.terminology.terminology import TerminologyConcept

# Reciprocal rank fusion constant — the standard value from Cormack et al.;
# damps the gap between rank 1 and rank 2 so neither method dominates.
RRF_K = 60
# Distinct billable stems a single category hit may expand into.
EXPAND_CAP = 10
# Tiny per-position decay so expanded descendants keep tabular order below
# their category's score instead of tying.
_EXPAND_DECAY = 1e-4


@dataclass
class Candidate:
    concept: TerminologyConcept
    score: float
    matched_on: str | None = None  # index term text, or None for the description


@dataclass
class RankedHit:
    concept: TerminologyConcept
    score: float
    matched_on: str | None = None
    variants: list[str] = field(default_factory=list)
    # Filled by fuse(): 1-based position in each method's list.
    text_rank: int | None = None
    semantic_rank: int | None = None


def variant_stem(code: str) -> str:
    """'S72.92XA' -> 'S72.92X'. Codes with 7 significant characters carry a
    7th-character extension; everything else is its own stem."""
    return code[:-1] if len(code.replace(".", "")) == 7 else code


def _order(c: Candidate) -> tuple:
    return (-c.score, c.concept.sort_order or 0)


def merge(
    rows: list[tuple[int, float, str | None]], concepts: dict[int, TerminologyConcept]
) -> list[Candidate]:
    """rows: (concept_id, score, matched_on) from any source. One Candidate per
    concept with its best score, best first."""
    best: dict[int, Candidate] = {}
    for concept_id, score, matched_on in rows:
        concept = concepts.get(concept_id)
        if concept is None:
            continue
        current = best.get(concept_id)
        if current is None or score > current.score:
            best[concept_id] = Candidate(concept, score, matched_on)
    return sorted(best.values(), key=_order)


def expand_to_billable(
    candidates: list[Candidate], descendants: dict[str, list[TerminologyConcept]]
) -> list[Candidate]:
    """Replace each non-billable candidate with up to EXPAND_CAP of its
    billable descendants' stems (tabular order). A descendant that is also a
    candidate in its own right keeps the better of the two scores."""
    out: dict[int, Candidate] = {c.concept.id: c for c in candidates if c.concept.is_billable}
    for cand in candidates:
        if cand.concept.is_billable:
            continue
        stems: list[str] = []
        for i, child in enumerate(descendants.get(cand.concept.code, [])):
            stem = variant_stem(child.code)
            if stem not in stems:
                if len(stems) >= EXPAND_CAP:
                    break
                stems.append(stem)
            inherited = Candidate(child, cand.score - _EXPAND_DECAY * i, cand.matched_on)
            current = out.get(child.id)
            if current is None or inherited.score > current.score:
                out[child.id] = inherited
    return sorted(out.values(), key=_order)


def collapse_variants(candidates: list[Candidate]) -> list[RankedHit]:
    """One hit per 7th-character stem, represented by its best-scoring code;
    the other codes are listed as variants. Input must be best-first."""
    hits: list[RankedHit] = []
    by_stem: dict[str, RankedHit] = {}
    for cand in candidates:
        stem = variant_stem(cand.concept.code)
        hit = by_stem.get(stem)
        if hit is None:
            hit = RankedHit(cand.concept, cand.score, cand.matched_on)
            by_stem[stem] = hit
            hits.append(hit)
        elif cand.concept.code != hit.concept.code:
            hit.variants.append(cand.concept.code)
    return hits


def as_hits(candidates: list[Candidate]) -> list[RankedHit]:
    return [RankedHit(c.concept, c.score, c.matched_on) for c in candidates]


def fuse(
    text_hits: list[RankedHit],
    semantic_hits: list[RankedHit],
    by_stem: bool = True,
    text_weight: float = 1.0,
    semantic_weight: float = 1.0,
) -> list[RankedHit]:
    """Weighted reciprocal rank fusion: score = sum of weight / (RRF_K + rank).
    Uses only positions, so the methods' incomparable score scales don't
    matter; the weights set how much each method's ranking counts.

    by_stem=True (lists already collapsed): a hit in one list meets its
    7th-character sibling in the other. by_stem=False (uncollapsed lists):
    key by exact code — keying by stem there would let one stem collect a
    contribution per variant, and families with many variants would win."""
    fused: dict[str, RankedHit] = {}
    order: list[str] = []
    for method, hits, weight in (
        ("text", text_hits, text_weight),
        ("semantic", semantic_hits, semantic_weight),
    ):
        for rank, hit in enumerate(hits, start=1):
            key = variant_stem(hit.concept.code) if by_stem else hit.concept.code
            entry = fused.get(key)
            if entry is None:
                entry = RankedHit(hit.concept, 0.0, hit.matched_on, list(hit.variants))
                fused[key] = entry
                order.append(key)
            else:
                known = {entry.concept.code, *entry.variants}
                entry.variants.extend(
                    c for c in (hit.concept.code, *hit.variants) if c not in known
                )
            entry.score += weight / (RRF_K + rank)
            if method == "text":
                entry.text_rank = rank
            else:
                entry.semantic_rank = rank
    return sorted(
        (fused[k] for k in order),
        key=lambda h: (-h.score, h.concept.sort_order or 0),
    )
