from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ItemType = Literal["condition", "observation", "service_request", "medication_request"]
ReviewAction = Literal["approve", "override", "remove"]


# ── Request ───────────────────────────────────────────────────────────────────


class ClinicalItemIn(BaseModel):
    """One finding from the note — already extracted upstream (Stage 0 is
    out of scope here). `text` is what gets searched; `details` keeps the
    rest of the source record (status, value, dose, dates …) untouched."""

    model_config = ConfigDict(extra="forbid")
    text: str = Field(..., min_length=1, max_length=500, examples=["acute appendicitis with localized peritonitis"])
    details: dict[str, Any] | None = None


class EncounterCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    encounter_id: str = Field(..., min_length=1, max_length=100, examples=["enc_2026_98312A"])
    patient_id: str = Field(..., min_length=1, max_length=100, examples=["pat_4412"])
    department: str | None = Field(None, max_length=200, examples=["Emergency Medicine"])
    soap_note: str = Field(..., min_length=1, max_length=50_000)
    conditions: list[ClinicalItemIn] = Field(default_factory=list)
    observations: list[ClinicalItemIn] = Field(default_factory=list)
    service_requests: list[ClinicalItemIn] = Field(default_factory=list)
    medication_requests: list[ClinicalItemIn] = Field(default_factory=list)

    @model_validator(mode="after")
    def _at_least_one_item(self) -> "EncounterCreate":
        if not (self.conditions or self.observations or self.service_requests or self.medication_requests):
            raise ValueError("at least one condition, observation, service request or medication request is required")
        return self

    def items(self) -> list[tuple[str, ClinicalItemIn]]:
        """(item_type, item) in a stable order: conditions first."""
        return [
            *(("condition", i) for i in self.conditions),
            *(("observation", i) for i in self.observations),
            *(("service_request", i) for i in self.service_requests),
            *(("medication_request", i) for i in self.medication_requests),
        ]


class ItemReview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: ReviewAction
    reviewer: str = Field(..., min_length=1, max_length=100)
    # Required for override: the code the reviewer chose (dotted or not).
    code: str | None = Field(None, max_length=10)

    @model_validator(mode="after")
    def _code_for_override(self) -> "ItemReview":
        if self.action == "override" and not self.code:
            raise ValueError("override requires `code`")
        if self.action != "override" and self.code:
            raise ValueError("`code` is only used with action=override")
        return self


class EncounterApprove(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reviewer: str = Field(..., min_length=1, max_length=100)


# ── Response (shape follows the proposal's JSON: clinical_input / ai_classification / audit_trail) ──


class ClinicalInput(BaseModel):
    soap_note: str
    department: str | None = None


class Alternative(BaseModel):
    code: str
    description: str
    probability: float
    search_rank: int
    matched_on: str | None = None


class AIClassification(BaseModel):
    engine: str
    model: str | None = None
    assigned_code: str | None
    assigned_description: str | None
    # Named `probability`, not `jev_probability`, because the engine varies —
    # see `engine` (e.g. the search-rank stand-in is not Jev).
    probability: float | None
    none_of_the_above_probability: float
    flags: list[str]
    top_alternatives: list[Alternative]
    candidates_scored: int
    latency_ms: float | None = None


class ItemReviewState(BaseModel):
    action: str | None = None
    final_code: str | None = None
    final_description: str | None = None
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None


class CodedItemOut(BaseModel):
    item_id: int
    item_type: str
    sequence: int
    text: str
    details: dict[str, Any] | None = None
    # pending | not_coded | no_candidates | scored | failed | approved | overridden | removed
    status: str
    error: str | None = None
    ai_classification: AIClassification | None = None
    review: ItemReviewState


class AuditTrail(BaseModel):
    isHumanReviewed: bool
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    # Final codes of approved/overridden items, in item order. Before review
    # this previews what would be billed: each scored item's assigned code.
    final_billing_codes: list[str]


class EncounterOut(BaseModel):
    encounter_id: str
    patient_id: str
    status: str
    review_queue: str | None = None
    clinical_input: ClinicalInput
    coded_concepts: list[CodedItemOut]
    audit_trail: AuditTrail
    created_at: datetime | None = None


class EncounterSummary(BaseModel):
    encounter_id: str
    patient_id: str
    department: str | None = None
    status: str
    review_queue: str | None = None
    is_human_reviewed: bool
    items: int
    flagged_items: int
    created_at: datetime | None = None


class EncounterListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    data: list[EncounterSummary]


class EngineInfo(BaseModel):
    name: str  # what to pass as ?engine=
    engine: str  # the engine it resolves to (e.g. "jev" -> "jev-opencode")
    kind: Literal["decision_model", "stand_in"]
    route: str | None = None
    model: str | None = None
    is_default: bool
    warning: str | None = None


class CodingSettings(BaseModel):
    default_engine: str
    engines: list[EngineInfo]
    coded_item_types: list[str]
    candidates_per_item: int
    alternatives_shown: int
    low_confidence_threshold: float
    nota_flag_threshold: float


class CandidateOut(BaseModel):
    """One stored search candidate for an item, with the active decision's
    probability for it."""

    code: str
    description: str
    # Stage 1 — hybrid search
    search_rank: int
    search_score: float | None = None
    text_rank: int | None = None
    semantic_rank: int | None = None
    matched_on: str | None = None
    variants: list[str] = []
    # Stage 2 — decision engine (None if the item was never scored)
    probability: float | None = None
    probability_rank: int | None = None
    is_assigned: bool
    is_final: bool


class ItemCandidatesResponse(BaseModel):
    encounter_id: str
    item_id: int
    text: str
    search_query: str | None = None
    engine: str | None = None
    model: str | None = None
    none_of_the_above_probability: float | None = None
    # Final code chosen by the reviewer that search never offered, if any.
    final_code_not_in_candidates: str | None = None
    total: int
    candidates: list[CandidateOut]
