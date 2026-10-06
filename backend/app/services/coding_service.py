"""Coding pipeline orchestration (docs/goal.md §4):

  1. store the encounter and one item per finding
  2. per coded item: hybrid search -> top-N candidates (stored)
  3. decision engine scores the candidates (+ "none of the above")
  4. highest probability = assigned code; flags; encounter review queue
  5. human review per item, then encounter approval -> isHumanReviewed
"""

import time
from datetime import UTC, datetime

from app.coding.decision import SCORING_FAILED, assign, rank_scores, review_queue
from app.coding.engines.base import DecisionEngine, EngineCandidate
from app.core.config import CodingConfig
from app.core.logging import get_logger
from app.errors.domain import BusinessRuleViolationError, NotFoundError
from app.models.coding.coding import CodingEncounter, CodingItem
from app.repository.coding_repository import CodingRepository
from app.schemas.coding import (
    AIClassification,
    Alternative,
    AuditTrail,
    CandidateOut,
    ClinicalInput,
    CodedItemOut,
    CodingSettings,
    EncounterApprove,
    EncounterCreate,
    EncounterListResponse,
    EncounterOut,
    EncounterSummary,
    EngineInfo,
    ItemCandidatesResponse,
    ItemReview,
    ItemReviewState,
)
from app.services.terminology_service import TerminologyService
from app.terminology.icd10cm import ICD10CM_URL, to_dotted

logger = get_logger(__name__)

# Items in these states still need a reviewer before the encounter can be approved.
_UNRESOLVED = {"pending", "scored", "no_candidates", "failed"}
_RESOLVED = {"approved", "overridden", "removed"}


class CodingService:
    def __init__(
        self,
        repository: CodingRepository,
        terminology: TerminologyService,
        engines: dict[str, DecisionEngine],
        config: CodingConfig,
    ):
        self.repository = repository
        self.terminology = terminology
        self.engines = engines
        self.config = config

    def _engine(self, name: str | None) -> DecisionEngine:
        name = name or self.config.default_engine
        engine = self.engines.get(name)
        if engine is None:
            raise BusinessRuleViolationError(
                f"Unknown decision engine {name!r}. Available: {sorted(self.engines)}",
                metadata={"engine": name},
            )
        return engine

    # ── Pipeline ──────────────────────────────────────────────────────────────

    async def create_encounter(self, data: EncounterCreate, engine_name: str | None = None) -> EncounterOut:
        engine = self._engine(engine_name)
        encounter = await self.repository.create_encounter(data, set(self.config.coded_item_types))
        coded = [i for i in encounter.items if i.status == "pending"]

        for item in coded:
            try:
                await self._search_and_score(encounter, item, engine)
            except Exception as exc:  # one bad item must not sink the encounter
                logger.exception(
                    "Coding item failed",
                    extra={"event": "coding.item_failed", "encounter_id": encounter.encounter_id, "item_id": item.id},
                )
                await self.repository.mark_item(
                    encounter.id,
                    item.id,
                    {"status": "failed", "flags": [SCORING_FAILED], "error": f"{type(exc).__name__}: {exc}"[:500]},
                    "item.failed",
                )

        await self._finalize(encounter.encounter_id)
        return await self.get_encounter(encounter.encounter_id)

    async def _search_and_score(self, encounter: CodingEncounter, item: CodingItem, engine: DecisionEngine) -> None:
        query = item.text
        _, hits = await self.terminology.retrieve(query, ICD10CM_URL, None, self.config.candidates_per_item)
        if not hits:
            await self.repository.mark_item(
                encounter.id, item.id, {"status": "no_candidates", "flags": ["NO_CANDIDATES"]}, "item.no_candidates"
            )
            return
        candidates = await self.repository.save_candidates(
            item.id,
            query,
            [
                {
                    "concept_id": h.concept.id,
                    "code": h.concept.code,
                    "display": h.concept.display,
                    "search_rank": rank,
                    "search_score": h.score,
                    "text_rank": h.text_rank,
                    "semantic_rank": h.semantic_rank,
                    "matched_on": h.matched_on,
                    "variants": h.variants,
                }
                for rank, h in enumerate(hits, start=1)
            ],
        )
        await self._score(encounter, item, candidates, engine)

    async def _score(self, encounter, item, candidates, engine: DecisionEngine) -> None:
        by_id = {c.id: c for c in candidates}
        engine_input = [
            EngineCandidate(c.id, c.code, c.display, c.search_rank)
            for c in sorted(candidates, key=lambda c: c.search_rank)
        ]
        t0 = time.perf_counter()
        try:
            result = await engine.score(encounter.soap_note, item.text, engine_input)
        except Exception as exc:  # noqa: BLE001 — any engine failure is recorded, not raised
            latency = (time.perf_counter() - t0) * 1000
            await self.repository.record_decision(
                encounter.id,
                item.id,
                {"engine": engine.name, "status": "failed", "latency_ms": latency, "error": str(exc)[:1000]},
                [],
                {"status": "failed", "flags": [SCORING_FAILED], "error": f"{engine.name}: {exc}"[:500],
                 "assigned_concept_id": None, "assigned_code": None, "assigned_display": None,
                 "probability": None, "nota_probability": None},
                {"engine": engine.name, "error": str(exc)[:200]},
            )
            return
        latency = (time.perf_counter() - t0) * 1000

        # Closed set: ignore anything the engine scored that wasn't offered.
        result.probabilities = {cid: p for cid, p in result.probabilities.items() if cid in by_id}
        scores = rank_scores(result, [c.candidate_id for c in engine_input])
        a = assign(scores, self.config.low_confidence_threshold, self.config.nota_flag_threshold)
        chosen = by_id.get(a.candidate_id) if a.candidate_id is not None else None

        await self.repository.record_decision(
            encounter.id,
            item.id,
            {
                "engine": engine.name,
                "model": result.model,
                "status": "succeeded",
                "latency_ms": latency,
                "cost": result.cost,
                "raw_response": result.raw_response,
            },
            scores,
            {
                "status": "scored",
                "error": None,
                "assigned_concept_id": chosen.concept_id if chosen else None,
                "assigned_code": chosen.code if chosen else None,
                "assigned_display": chosen.display if chosen else None,
                "probability": a.probability,
                "nota_probability": a.nota_probability,
                "flags": a.flags,
            },
            {
                "engine": engine.name,
                "model": result.model,
                "assigned_code": chosen.code if chosen else None,
                "probability": a.probability,
                "flags": a.flags,
                "candidates": len(candidates),
            },
        )

    async def _finalize(self, encounter_id: str) -> None:
        encounter = await self.repository.get_encounter(encounter_id)
        coded = [i for i in encounter.items if i.status != "not_coded"]
        if coded and all(i.status == "failed" for i in coded):
            status = "failed"
        else:
            status = "ready_for_review"
        queue = review_queue([(i.status, list(i.flags or [])) for i in coded])
        await self.repository.finalize_encounter(encounter.id, status, queue)

    async def rescore(self, encounter_id: str, engine_name: str | None) -> EncounterOut:
        """Re-run a decision engine over the stored candidates (no new search).
        Clears item reviews; not allowed once the encounter is approved."""
        engine = self._engine(engine_name)
        encounter = await self._require(encounter_id)
        if encounter.is_human_reviewed:
            raise BusinessRuleViolationError(f"Encounter {encounter_id} is already approved")
        for item in encounter.items:
            if item.status == "not_coded" or not item.candidates:
                continue
            await self._score(encounter, item, item.candidates, engine)
        await self._finalize(encounter_id)
        return await self.get_encounter(encounter_id)

    # ── Read ──────────────────────────────────────────────────────────────────

    def settings(self) -> CodingSettings:
        engines = []
        for name, engine in self.engines.items():
            route = getattr(engine, "route", None)
            model = route.model if route is not None else "search-rank-v1"
            if route is None:
                warning = "Uncalibrated stand-in: probabilities come from search rank, not a decision model"
            elif model.endswith("-free"):
                warning = "Free tier: prompts may be used for training - synthetic data only"
            else:
                warning = None
            engines.append(
                EngineInfo(
                    name=name,
                    engine=engine.name,
                    kind="stand_in" if route is None else "decision_model",
                    route=getattr(engine, "route_name", None),
                    model=model,
                    is_default=name == self.config.default_engine,
                    warning=warning,
                )
            )
        return CodingSettings(
            default_engine=self.config.default_engine,
            engines=engines,
            coded_item_types=list(self.config.coded_item_types),
            candidates_per_item=self.config.candidates_per_item,
            alternatives_shown=self.config.alternatives_shown,
            low_confidence_threshold=self.config.low_confidence_threshold,
            nota_flag_threshold=self.config.nota_flag_threshold,
        )


    async def _require(self, encounter_id: str) -> CodingEncounter:
        encounter = await self.repository.get_encounter(encounter_id)
        if encounter is None:
            raise NotFoundError(f"Encounter {encounter_id} not found", metadata={"encounter_id": encounter_id})
        return encounter

    async def get_encounter(self, encounter_id: str) -> EncounterOut:
        return self._to_out(await self._require(encounter_id))

    async def list_encounters(
        self, queue: str | None, status: str | None, reviewed: bool | None, limit: int, offset: int
    ) -> EncounterListResponse:
        total, rows = await self.repository.list_encounters(queue, status, reviewed, limit, offset)
        return EncounterListResponse(
            total=total,
            limit=limit,
            offset=offset,
            data=[
                EncounterSummary(
                    encounter_id=e.encounter_id,
                    patient_id=e.patient_id,
                    department=e.department,
                    status=e.status,
                    review_queue=e.review_queue,
                    is_human_reviewed=e.is_human_reviewed,
                    items=n,
                    flagged_items=flagged,
                    created_at=e.created_at,
                )
                for e, n, flagged in rows
            ],
        )

    def _to_out(self, e: CodingEncounter) -> EncounterOut:
        items = [self._item_out(i) for i in e.items]
        if e.is_human_reviewed:
            billing = [i.final_code for i in e.items if i.status in ("approved", "overridden") and i.final_code]
        else:
            billing = [
                i.final_code or i.assigned_code
                for i in e.items
                if i.status in ("scored", "approved", "overridden") and (i.final_code or i.assigned_code)
            ]
        return EncounterOut(
            encounter_id=e.encounter_id,
            patient_id=e.patient_id,
            status=e.status,
            review_queue=e.review_queue,
            clinical_input=ClinicalInput(soap_note=e.soap_note, department=e.department),
            coded_concepts=items,
            audit_trail=AuditTrail(
                isHumanReviewed=e.is_human_reviewed,
                reviewed_by=e.reviewed_by,
                reviewed_at=e.reviewed_at,
                final_billing_codes=billing,
            ),
            created_at=e.created_at,
        )

    def _item_out(self, i: CodingItem) -> CodedItemOut:
        ai = None
        decision = next((d for d in reversed(i.decisions) if d.is_active), None)
        if decision is not None and decision.status == "succeeded":
            cands = {c.id: c for c in i.candidates}
            alternatives = [
                Alternative(
                    code=cands[s.candidate_id].code,
                    description=cands[s.candidate_id].display,
                    probability=round(s.probability, 6),
                    search_rank=cands[s.candidate_id].search_rank,
                    matched_on=cands[s.candidate_id].matched_on,
                )
                for s in decision.scores
                if s.candidate_id is not None
                and s.candidate_id in cands
                and cands[s.candidate_id].code != i.assigned_code
            ][: self.config.alternatives_shown]
            ai = AIClassification(
                engine=decision.engine,
                model=decision.model,
                assigned_code=i.assigned_code,
                assigned_description=i.assigned_display,
                probability=round(i.probability, 6) if i.probability is not None else None,
                none_of_the_above_probability=round(i.nota_probability or 0.0, 6),
                flags=list(i.flags or []),
                top_alternatives=alternatives,
                candidates_scored=len(cands),
                latency_ms=round(decision.latency_ms, 1) if decision.latency_ms is not None else None,
            )
        return CodedItemOut(
            item_id=i.id,
            item_type=i.item_type,
            sequence=i.sequence,
            text=i.text,
            details=i.details,
            status=i.status,
            error=i.error,
            ai_classification=ai,
            review=ItemReviewState(
                action=i.review_action,
                final_code=i.final_code,
                final_description=i.final_display,
                reviewed_by=i.reviewed_by,
                reviewed_at=i.reviewed_at,
            ),
        )

    async def get_item_candidates(self, encounter_id: str, item_id: int) -> ItemCandidatesResponse:
        """Every stored search candidate for an item (the full top-N, not just
        the alternatives shown), in search order, with the active decision's
        probability and rank for each."""
        encounter = await self._require(encounter_id)
        item = next((i for i in encounter.items if i.id == item_id), None)
        if item is None:
            raise NotFoundError(f"Item {item_id} not found in encounter {encounter_id}")

        decision = next((d for d in reversed(item.decisions) if d.is_active), None)
        scored = decision is not None and decision.status == "succeeded"
        by_candidate = {s.candidate_id: s for s in decision.scores} if scored else {}
        codes = {c.code for c in item.candidates}
        return ItemCandidatesResponse(
            encounter_id=encounter.encounter_id,
            item_id=item.id,
            text=item.text,
            search_query=item.search_query,
            engine=decision.engine if decision else None,
            model=decision.model if decision else None,
            none_of_the_above_probability=item.nota_probability if scored else None,
            final_code_not_in_candidates=(
                item.final_code if item.final_code and item.final_code not in codes else None
            ),
            total=len(item.candidates),
            candidates=[
                CandidateOut(
                    code=c.code,
                    description=c.display,
                    search_rank=c.search_rank,
                    search_score=round(c.search_score, 6) if c.search_score is not None else None,
                    text_rank=c.text_rank,
                    semantic_rank=c.semantic_rank,
                    matched_on=c.matched_on,
                    variants=list(c.variants or []),
                    probability=round(by_candidate[c.id].probability, 6) if c.id in by_candidate else None,
                    probability_rank=by_candidate[c.id].rank if c.id in by_candidate else None,
                    is_assigned=c.code == item.assigned_code,
                    is_final=c.code == item.final_code,
                )
                for c in sorted(item.candidates, key=lambda c: c.search_rank)
            ],
        )

    # ── Review ────────────────────────────────────────────────────────────────

    async def review_item(self, encounter_id: str, item_id: int, review: ItemReview) -> EncounterOut:
        encounter = await self._require(encounter_id)
        if encounter.is_human_reviewed:
            raise BusinessRuleViolationError(f"Encounter {encounter_id} is already approved")
        item = next((i for i in encounter.items if i.id == item_id), None)
        if item is None:
            raise NotFoundError(f"Item {item_id} not found in encounter {encounter_id}")
        if item.status in ("not_coded", "pending"):
            raise BusinessRuleViolationError(f"Item {item_id} is {item.status} and can't be reviewed")

        now = datetime.now(UTC)
        before = {"status": item.status, "final_code": item.final_code, "assigned_code": item.assigned_code}

        if review.action == "approve":
            if not item.assigned_code:
                raise BusinessRuleViolationError(
                    f"Item {item_id} has no suggested code to approve — override with a code or remove it"
                )
            values = {
                "status": "approved",
                "final_concept_id": item.assigned_concept_id,
                "final_code": item.assigned_code,
                "final_display": item.assigned_display,
            }
            after = {"final_code": item.assigned_code}
        elif review.action == "override":
            code = to_dotted(review.code)
            concept = await self.repository.find_billable_concept(ICD10CM_URL, code)
            if concept is None or not concept.is_billable:
                raise BusinessRuleViolationError(
                    f"{code} is not a billable ICD-10-CM code in the loaded release",
                    metadata={"code": code},
                )
            values = {
                "status": "overridden",
                "final_concept_id": concept.id,
                "final_code": concept.code,
                "final_display": concept.display,
            }
            after = {
                "final_code": concept.code,
                # Was the reviewer's code among the search candidates? A miss
                # here is a retrieval failure worth measuring (goal.md §9).
                "in_candidates": any(c.code == concept.code for c in item.candidates),
            }
        else:  # remove
            values = {"status": "removed", "final_concept_id": None, "final_code": None, "final_display": None}
            after = {"final_code": None}

        values |= {"review_action": review.action, "reviewed_by": review.reviewer, "reviewed_at": now}
        await self.repository.apply_item_review(encounter.id, item.id, values, review.reviewer, before, after)
        return await self.get_encounter(encounter_id)

    async def approve_encounter(self, encounter_id: str, body: EncounterApprove) -> EncounterOut:
        encounter = await self._require(encounter_id)
        if encounter.is_human_reviewed:
            raise BusinessRuleViolationError(f"Encounter {encounter_id} is already approved")
        unresolved = [i.id for i in encounter.items if i.status in _UNRESOLVED]
        if unresolved:
            raise BusinessRuleViolationError(
                f"{len(unresolved)} item(s) still need review (approve, override or remove) before the encounter can be approved",
                metadata={"unresolved_item_ids": unresolved},
            )
        final_codes = [i.final_code for i in encounter.items if i.status in ("approved", "overridden") and i.final_code]
        await self.repository.approve_encounter(
            encounter.id, body.reviewer, datetime.now(UTC), final_codes
        )
        return await self.get_encounter(encounter_id)
