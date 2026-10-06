"""Coding pipeline against a real PostgreSQL database.

Uses a throwaway database (TEST_DATABASE_URL, default jev_coding_test on the
dev container) that is dropped, re-created and migrated for this module —
the development database is never touched. Hybrid search is replaced by a
fake returning seeded concepts, so no embedding server is needed. Skipped
when PostgreSQL isn't reachable.
"""

import asyncio
import os
import subprocess
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5433/test")

import asyncpg
import pytest

from app.coding.engines.base import EngineResult
from app.coding.engines.search_rank import SearchRankEngine
from app.core.config import CodingConfig
from app.core.database import Database
from app.errors.domain import (
    BusinessRuleViolationError,
    NotFoundError,
    ResourceConflictError,
)
from app.models.terminology.terminology import TerminologyCodeSystem, TerminologyConcept
from app.repository.coding_repository import CodingRepository
from app.schemas.coding import (
    ClinicalItemIn,
    EncounterApprove,
    EncounterCreate,
    ItemReview,
)
from app.services.coding_service import CodingService
from app.services.search_ranking import RankedHit
from app.terminology.icd10cm import ICD10CM_URL

TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://jev:jev_dev_password@127.0.0.1:5433/jev_coding_test"
)
BACKEND = Path(__file__).resolve().parents[1]

SEED = [
    # code, display, billable
    ("K35.3", "Acute appendicitis with localized peritonitis", False),
    ("K35.30", "Acute appendicitis with localized peritonitis, without perforation or gangrene", True),
    ("K35.31", "Acute appendicitis with localized peritonitis and gangrene, without perforation", True),
    ("K35.80", "Unspecified acute appendicitis", True),
    ("I21.9", "Acute myocardial infarction, unspecified", True),
]


def _plain(url: str) -> str:
    return url.replace("postgresql+asyncpg://", "postgresql://")


async def _create_and_seed() -> None:
    db_name = TEST_DB_URL.rsplit("/", 1)[1]
    admin = await asyncpg.connect(_plain(TEST_DB_URL.rsplit("/", 1)[0] + "/postgres"), timeout=5)
    try:
        await admin.execute(f'DROP DATABASE IF EXISTS "{db_name}" WITH (FORCE)')
        await admin.execute(f'CREATE DATABASE "{db_name}"')
    finally:
        await admin.close()

    migrate = subprocess.run(  # noqa: ASYNC221 — one-off test setup, before any test runs
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        check=False,
        cwd=BACKEND,
        env={**os.environ, "DATABASE_URL": TEST_DB_URL},
        capture_output=True,
        text=True,
    )
    assert migrate.returncode == 0, migrate.stderr

    conn = await asyncpg.connect(_plain(TEST_DB_URL))
    try:
        cs_id = await conn.fetchval(
            "INSERT INTO terminology_code_system (canonical_url, version, name) VALUES ($1, '2027', 'ICD-10-CM') RETURNING id",
            ICD10CM_URL,
        )
        for order, (code, display, billable) in enumerate(SEED, 1):
            await conn.execute(
                "INSERT INTO terminology_concept (code_system_id, code, display, is_billable, sort_order) VALUES ($1,$2,$3,$4,$5)",
                cs_id, code, display, billable, order,
            )
    finally:
        await conn.close()


@pytest.fixture(scope="module")
def test_database():
    try:
        asyncio.run(_create_and_seed())
    except (OSError, asyncpg.PostgresError, TimeoutError) as exc:
        pytest.skip(f"PostgreSQL not reachable for integration tests: {exc}")
    return TEST_DB_URL


class FakeTerminology:
    """Stands in for hybrid search: returns seeded concepts in a fixed order."""

    def __init__(self, concepts: dict[str, TerminologyConcept]):
        self.concepts = concepts

    async def retrieve(self, q, system, version, limit):
        cs = TerminologyCodeSystem(id=1, canonical_url=system, version="2027", name="ICD-10-CM")
        if q == "boom":
            raise RuntimeError("search exploded")
        if q == "nothing matches":
            return cs, []
        codes = ["I21.9", "K35.80"] if "infarction" in q else ["K35.30", "K35.80", "I21.9"]
        hits = [
            RankedHit(self.concepts[c], 1.0 / (60 + r), "Appendicitis localized" if c == "K35.30" else None)
            for r, c in enumerate(codes, 1)
        ]
        return cs, hits[:limit]


class ConfidentEngine:
    """Puts 0.95 on the second-ranked candidate — proves the engine, not
    search order, decides."""

    name = "confident"

    async def score(self, soap_note, item_text, candidates):
        second = sorted(candidates, key=lambda c: c.search_rank)[1]
        rest = [c for c in candidates if c.candidate_id != second.candidate_id]
        probs = {second.candidate_id: 0.95, **{c.candidate_id: 0.04 / len(rest) for c in rest}}
        return EngineResult(model="confident-v1", probabilities=probs, nota_probability=0.01)


class BrokenEngine:
    name = "broken"

    async def score(self, soap_note, item_text, candidates):
        raise TimeoutError("engine timed out")


@pytest.fixture
async def service(test_database):
    db = Database(test_database)
    async with db.session() as s:
        from sqlalchemy import select

        rows = (await s.execute(select(TerminologyConcept))).scalars().all()
    concepts = {c.code: c for c in rows}
    svc = CodingService(
        repository=CodingRepository(db.session),
        terminology=FakeTerminology(concepts),
        engines={e.name: e for e in (SearchRankEngine(), ConfidentEngine(), BrokenEngine())},
        config=CodingConfig(),
    )
    yield svc
    await db.disconnect()


def _encounter(encounter_id: str, conditions: list[str], **extra) -> EncounterCreate:
    return EncounterCreate(
        encounter_id=encounter_id,
        patient_id="pat_1",
        department="Emergency Medicine",
        soap_note="Acute inflammation of the appendix with localized peritonitis.",
        conditions=[ClinicalItemIn(text=t) for t in conditions],
        **extra,
    )


async def test_pipeline_scores_conditions_and_stores_the_rest(service):
    out = await service.create_encounter(
        _encounter(
            "enc-1",
            ["acute appendicitis with localized peritonitis", "boom"],
            medication_requests=[ClinicalItemIn(text="IV ceftriaxone 1 g", details={"route": "IV"})],
        )
    )
    assert out.status == "ready_for_review"
    assert out.review_queue == "close_review"  # a failed item + stand-in low confidence

    appendicitis, failed, medication = out.coded_concepts
    ai = appendicitis.ai_classification
    assert appendicitis.status == "scored"
    assert ai.engine == "search-rank"
    assert ai.assigned_code == "K35.30"  # search rank 1
    assert ai.candidates_scored == 3
    assert [a.code for a in ai.top_alternatives] == ["K35.80", "I21.9"]
    assert ai.top_alternatives[0].probability > ai.top_alternatives[1].probability
    assert "LOW_CONFIDENCE" in ai.flags  # stand-in top ≈ 0.67 < 0.75

    assert failed.status == "failed" and "search exploded" in failed.error
    assert failed.ai_classification is None
    assert medication.status == "not_coded" and medication.details == {"route": "IV"}

    assert out.audit_trail.isHumanReviewed is False
    assert out.audit_trail.final_billing_codes == ["K35.30"]  # preview


async def test_duplicate_encounter_is_rejected(service):
    await service.create_encounter(_encounter("enc-dup", ["acute appendicitis"]))
    with pytest.raises(ResourceConflictError):
        await service.create_encounter(_encounter("enc-dup", ["acute appendicitis"]))


async def test_engine_decides_not_search_order_and_high_confidence_is_standard_queue(service):
    out = await service.create_encounter(_encounter("enc-conf", ["acute appendicitis"]), engine_name="confident")
    ai = out.coded_concepts[0].ai_classification
    assert (ai.assigned_code, ai.probability, ai.flags) == ("K35.80", 0.95, [])
    assert ai.none_of_the_above_probability == 0.01
    assert out.review_queue == "standard"


async def test_engine_failure_and_empty_search_are_flagged(service):
    out = await service.create_encounter(
        _encounter("enc-fail", ["acute appendicitis", "nothing matches"]), engine_name="broken"
    )
    scored, empty = out.coded_concepts
    assert scored.status == "failed" and "SCORING_FAILED" in (await service.repository.get_encounter("enc-fail")).items[0].flags
    assert empty.status == "no_candidates"
    assert out.status == "ready_for_review"  # not every item failed
    assert out.review_queue == "close_review"


async def test_review_flow_to_approval(service):
    out = await service.create_encounter(_encounter("enc-rev", ["acute appendicitis", "myocardial infarction", "boom"]))
    first, second, failed = (i.item_id for i in out.coded_concepts)

    with pytest.raises(BusinessRuleViolationError, match="still need review"):
        await service.approve_encounter("enc-rev", EncounterApprove(reviewer="coder1"))

    out = await service.review_item("enc-rev", first, ItemReview(action="approve", reviewer="coder1"))
    assert out.coded_concepts[0].status == "approved"
    assert out.coded_concepts[0].review.final_code == "K35.30"
    assert out.coded_concepts[0].ai_classification.assigned_code == "K35.30"  # AI output kept

    # Override the failed item with a real code the search never offered.
    out = await service.review_item("enc-rev", failed, ItemReview(action="override", reviewer="coder1", code="k3531"))
    assert out.coded_concepts[2].status == "overridden"
    assert out.coded_concepts[2].review.final_code == "K35.31"

    out = await service.review_item("enc-rev", second, ItemReview(action="remove", reviewer="coder1"))
    assert out.coded_concepts[1].status == "removed"

    out = await service.approve_encounter("enc-rev", EncounterApprove(reviewer="coder1"))
    assert out.status == "reviewed"
    assert out.audit_trail.isHumanReviewed is True
    assert out.audit_trail.reviewed_by == "coder1"
    assert out.audit_trail.final_billing_codes == ["K35.30", "K35.31"]

    with pytest.raises(BusinessRuleViolationError, match="already approved"):
        await service.review_item("enc-rev", first, ItemReview(action="remove", reviewer="coder2"))

    enc = await service.repository.get_encounter("enc-rev")
    actions = [e.action for e in await service.repository.list_audit(enc.id)]
    assert actions[0] == "encounter.received"
    assert actions[-4:] == ["item.approve", "item.override", "item.remove", "encounter.approved"]
    override = next(e for e in await service.repository.list_audit(enc.id) if e.action == "item.override")
    assert override.after == {"final_code": "K35.31", "in_candidates": False}
    assert override.actor == "coder1"


async def test_override_rejects_unknown_and_non_billable_codes(service):
    out = await service.create_encounter(_encounter("enc-bad", ["acute appendicitis"]))
    item = out.coded_concepts[0].item_id
    with pytest.raises(BusinessRuleViolationError, match="not a billable"):
        await service.review_item("enc-bad", item, ItemReview(action="override", reviewer="c", code="Z99.999"))
    with pytest.raises(BusinessRuleViolationError, match="not a billable"):
        await service.review_item("enc-bad", item, ItemReview(action="override", reviewer="c", code="K35.3"))


async def test_not_coded_items_cannot_be_reviewed_and_unknown_items_404(service):
    out = await service.create_encounter(
        _encounter("enc-nc", ["acute appendicitis"], service_requests=[ClinicalItemIn(text="CBC")])
    )
    cbc = out.coded_concepts[1].item_id
    with pytest.raises(BusinessRuleViolationError, match="not_coded"):
        await service.review_item("enc-nc", cbc, ItemReview(action="remove", reviewer="c"))
    with pytest.raises(NotFoundError):
        await service.review_item("enc-nc", 999_999, ItemReview(action="remove", reviewer="c"))


async def test_rescore_replaces_decision_and_clears_review(service):
    out = await service.create_encounter(_encounter("enc-rs", ["acute appendicitis"]))
    item = out.coded_concepts[0].item_id
    await service.review_item("enc-rs", item, ItemReview(action="approve", reviewer="c"))

    out = await service.rescore("enc-rs", "confident")
    concept = out.coded_concepts[0]
    assert concept.ai_classification.engine == "confident"
    assert concept.ai_classification.assigned_code == "K35.80"
    assert concept.status == "scored" and concept.review.action is None
    assert out.review_queue == "standard"

    enc = await service.repository.get_encounter("enc-rs")
    decisions = enc.items[0].decisions
    assert [(d.engine, d.is_active) for d in decisions] == [("search-rank", False), ("confident", True)]
    assert len(enc.items[0].candidates) == 3  # no new search


async def test_list_encounters_filters(service):
    await service.create_encounter(_encounter("enc-list-a", ["acute appendicitis"]), engine_name="confident")
    _, rows = await service.repository.list_encounters("standard", None, False, 100, 0)
    ids = [e.encounter_id for e, _, _ in rows]
    assert "enc-list-a" in ids
    listed = await service.list_encounters("close_review", None, None, 100, 0)
    assert "enc-list-a" not in [e.encounter_id for e in listed.data]
    assert all(e.review_queue == "close_review" for e in listed.data)


async def test_unknown_engine_is_rejected(service):
    with pytest.raises(BusinessRuleViolationError, match="Unknown decision engine"):
        await service.create_encounter(_encounter("enc-eng", ["x"]), engine_name="gpt-99")


async def test_item_candidates_lists_every_candidate_with_probabilities(service):
    out = await service.create_encounter(_encounter("enc-cands", ["acute appendicitis"]), engine_name="confident")
    item = out.coded_concepts[0].item_id

    res = await service.get_item_candidates("enc-cands", item)
    assert res.total == 3 and len(res.candidates) == 3
    assert [c.code for c in res.candidates] == ["K35.30", "K35.80", "I21.9"]  # search order
    assert [c.search_rank for c in res.candidates] == [1, 2, 3]
    by = {c.code: c for c in res.candidates}
    # ConfidentEngine puts 0.95 on the second search result.
    assert by["K35.80"].probability == 0.95 and by["K35.80"].probability_rank == 1
    assert by["K35.80"].is_assigned and not by["K35.30"].is_assigned
    assert by["K35.30"].matched_on == "Appendicitis localized"
    assert res.engine == "confident" and res.none_of_the_above_probability == 0.01
    assert res.final_code_not_in_candidates is None

    # Reviewer picks a code search never offered -> reported separately.
    await service.review_item("enc-cands", item, ItemReview(action="override", reviewer="c", code="K35.31"))
    res = await service.get_item_candidates("enc-cands", item)
    assert res.final_code_not_in_candidates == "K35.31"
    assert not any(c.is_final for c in res.candidates)


async def test_item_candidates_for_unscored_and_unknown_items(service):
    out = await service.create_encounter(
        _encounter("enc-cands-2", ["nothing matches"], medication_requests=[ClinicalItemIn(text="aspirin")])
    )
    empty, med = out.coded_concepts
    res = await service.get_item_candidates("enc-cands-2", empty.item_id)
    assert res.total == 0 and res.engine is None and res.none_of_the_above_probability is None
    assert (await service.get_item_candidates("enc-cands-2", med.item_id)).total == 0
    with pytest.raises(NotFoundError):
        await service.get_item_candidates("enc-cands-2", 999_999)
