from collections import Counter
from datetime import datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from app.coding.decision import RankedScore
from app.errors.domain import ResourceConflictError
from app.models.coding.coding import (
    CodingAuditEvent,
    CodingCandidate,
    CodingCandidateScore,
    CodingDecision,
    CodingEncounter,
    CodingItem,
)
from app.models.terminology.terminology import TerminologyCodeSystem, TerminologyConcept
from app.schemas.coding import EncounterCreate

SYSTEM = "system"


def _full_encounter():
    return (
        select(CodingEncounter)
        .options(
            selectinload(CodingEncounter.items).selectinload(CodingItem.candidates),
            selectinload(CodingEncounter.items)
            .selectinload(CodingItem.decisions)
            .selectinload(CodingDecision.scores),
        )
    )


class CodingRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory

    # ── Encounter lifecycle ───────────────────────────────────────────────────

    async def create_encounter(self, data: EncounterCreate, coded_types: set[str]) -> CodingEncounter:
        """Encounter + one item per entry. Coded types start pending; the rest
        are stored as not_coded."""
        async with self.session_factory() as session:
            encounter = CodingEncounter(
                encounter_id=data.encounter_id,
                patient_id=data.patient_id,
                department=data.department,
                soap_note=data.soap_note,
                status="processing",
            )
            for seq, (item_type, item) in enumerate(data.items(), start=1):
                encounter.items.append(
                    CodingItem(
                        item_type=item_type,
                        sequence=seq,
                        text=item.text,
                        details=item.details,
                        status="pending" if item_type in coded_types else "not_coded",
                        flags=[],
                    )
                )
            session.add(encounter)
            try:
                await session.flush()
            except IntegrityError as exc:
                raise ResourceConflictError(
                    f"Encounter {data.encounter_id} already exists",
                    metadata={"encounter_id": data.encounter_id},
                ) from exc
            session.add(
                CodingAuditEvent(
                    encounter_pk=encounter.id,
                    action="encounter.received",
                    actor=SYSTEM,
                    after={
                        "items": dict(Counter(i.item_type for i in encounter.items)),
                        "coded_item_types": sorted(coded_types),
                    },
                )
            )
            await session.commit()
            return encounter

    async def get_encounter(self, encounter_id: str) -> CodingEncounter | None:
        async with self.session_factory() as session:
            row = await session.execute(_full_encounter().where(CodingEncounter.encounter_id == encounter_id))
            return row.scalar_one_or_none()

    async def list_encounters(
        self,
        queue: str | None,
        status: str | None,
        reviewed: bool | None,
        limit: int,
        offset: int,
    ) -> tuple[int, list[tuple[CodingEncounter, int, int]]]:
        async with self.session_factory() as session:
            stmt = select(CodingEncounter)
            if queue:
                stmt = stmt.where(CodingEncounter.review_queue == queue)
            if status:
                stmt = stmt.where(CodingEncounter.status == status)
            if reviewed is not None:
                stmt = stmt.where(CodingEncounter.is_human_reviewed.is_(reviewed))
            total = await session.scalar(select(func.count()).select_from(stmt.subquery()))

            counts = (
                select(
                    CodingItem.encounter_pk,
                    func.count().label("n_items"),
                    func.count().filter(func.jsonb_array_length(CodingItem.flags) > 0).label("flagged"),
                )
                .group_by(CodingItem.encounter_pk)
                .subquery()
            )
            rows = await session.execute(
                stmt.add_columns(func.coalesce(counts.c.n_items, 0), func.coalesce(counts.c.flagged, 0))
                .outerjoin(counts, counts.c.encounter_pk == CodingEncounter.id)
                .order_by(CodingEncounter.created_at.desc(), CodingEncounter.id.desc())
                .limit(limit)
                .offset(offset)
            )
            return total or 0, [(e, n, f) for e, n, f in rows.all()]

    async def finalize_encounter(self, encounter_pk: int, status: str, queue: str | None) -> None:
        async with self.session_factory() as session:
            await session.execute(
                update(CodingEncounter)
                .where(CodingEncounter.id == encounter_pk)
                .values(status=status, review_queue=queue)
            )
            session.add(
                CodingAuditEvent(
                    encounter_pk=encounter_pk,
                    action="encounter.processed",
                    actor=SYSTEM,
                    after={"status": status, "review_queue": queue},
                )
            )
            await session.commit()

    # ── Pipeline writes ───────────────────────────────────────────────────────

    async def save_candidates(
        self, item_id: int, search_query: str, rows: list[dict[str, Any]]
    ) -> list[CodingCandidate]:
        async with self.session_factory() as session:
            await session.execute(
                update(CodingItem).where(CodingItem.id == item_id).values(search_query=search_query)
            )
            candidates = [CodingCandidate(item_id=item_id, **row) for row in rows]
            session.add_all(candidates)
            await session.commit()
            return candidates

    async def record_decision(
        self,
        encounter_pk: int,
        item_id: int,
        decision: dict[str, Any],
        scores: list[RankedScore],
        item_values: dict[str, Any],
        audit_after: dict[str, Any],
    ) -> None:
        """New decision becomes the active one; the item's assignment is
        replaced and any earlier human review of it is cleared."""
        async with self.session_factory() as session:
            await session.execute(
                update(CodingDecision)
                .where(CodingDecision.item_id == item_id, CodingDecision.is_active.is_(True))
                .values(is_active=False)
            )
            row = CodingDecision(item_id=item_id, is_active=True, **decision)
            row.scores = [
                CodingCandidateScore(candidate_id=s.candidate_id, probability=s.probability, rank=s.rank)
                for s in scores
            ]
            session.add(row)
            await session.execute(
                update(CodingItem)
                .where(CodingItem.id == item_id)
                .values(
                    **item_values,
                    final_concept_id=None,
                    final_code=None,
                    final_display=None,
                    review_action=None,
                    reviewed_by=None,
                    reviewed_at=None,
                )
            )
            session.add(
                CodingAuditEvent(
                    encounter_pk=encounter_pk,
                    item_id=item_id,
                    action="item.scored" if decision.get("status") == "succeeded" else "item.scoring_failed",
                    actor=SYSTEM,
                    after=audit_after,
                )
            )
            await session.commit()

    async def mark_item(
        self, encounter_pk: int, item_id: int, values: dict[str, Any], action: str
    ) -> None:
        async with self.session_factory() as session:
            await session.execute(update(CodingItem).where(CodingItem.id == item_id).values(**values))
            session.add(
                CodingAuditEvent(
                    encounter_pk=encounter_pk,
                    item_id=item_id,
                    action=action,
                    actor=SYSTEM,
                    after={k: v for k, v in values.items() if k in ("status", "flags", "error")},
                )
            )
            await session.commit()

    # ── Review ────────────────────────────────────────────────────────────────

    async def find_billable_concept(self, system: str, code: str) -> TerminologyConcept | None:
        """A billable code in the latest active release of `system`."""
        async with self.session_factory() as session:
            cs_id = (
                select(TerminologyCodeSystem.id)
                .where(TerminologyCodeSystem.canonical_url == system, TerminologyCodeSystem.active.is_(True))
                .order_by(TerminologyCodeSystem.version.desc())
                .limit(1)
                .scalar_subquery()
            )
            row = await session.execute(
                select(TerminologyConcept).where(
                    TerminologyConcept.code_system_id == cs_id,
                    TerminologyConcept.code == code,
                )
            )
            return row.scalar_one_or_none()

    async def apply_item_review(
        self,
        encounter_pk: int,
        item_id: int,
        values: dict[str, Any],
        actor: str,
        before: dict[str, Any],
        after: dict[str, Any],
    ) -> None:
        async with self.session_factory() as session:
            await session.execute(update(CodingItem).where(CodingItem.id == item_id).values(**values))
            session.add(
                CodingAuditEvent(
                    encounter_pk=encounter_pk,
                    item_id=item_id,
                    action=f"item.{values['review_action']}",
                    actor=actor,
                    before=before,
                    after=after,
                )
            )
            await session.commit()

    async def approve_encounter(
        self, encounter_pk: int, reviewer: str, reviewed_at: datetime, final_codes: list[str]
    ) -> None:
        async with self.session_factory() as session:
            await session.execute(
                update(CodingEncounter)
                .where(CodingEncounter.id == encounter_pk)
                .values(
                    is_human_reviewed=True,
                    reviewed_by=reviewer,
                    reviewed_at=reviewed_at,
                    status="reviewed",
                )
            )
            session.add(
                CodingAuditEvent(
                    encounter_pk=encounter_pk,
                    action="encounter.approved",
                    actor=reviewer,
                    after={"final_billing_codes": final_codes},
                )
            )
            await session.commit()

    async def list_audit(self, encounter_pk: int) -> list[CodingAuditEvent]:
        async with self.session_factory() as session:
            rows = await session.execute(
                select(CodingAuditEvent)
                .where(CodingAuditEvent.encounter_pk == encounter_pk)
                .order_by(CodingAuditEvent.id)
            )
            return list(rows.scalars().all())
