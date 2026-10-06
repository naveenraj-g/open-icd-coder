from fastapi import APIRouter, Depends, Query

from app.di.dependencies.coding import get_coding_service
from app.schemas.coding import (
    CodingSettings,
    EncounterApprove,
    EncounterCreate,
    EncounterListResponse,
    EncounterOut,
    ItemCandidatesResponse,
    ItemReview,
)
from app.services.coding_service import CodingService

router = APIRouter()

_ENGINE = Query(
    None,
    description="Decision engine (default: coding.default_engine in configs/config.yaml)",
    examples=["search-rank"],
)


@router.get(
    "/settings",
    operation_id="get_coding_settings",
    summary="Decision engines and coding thresholds",
    description="Engines selectable with ?engine=, the default, and the thresholds that set flags.",
    response_model=CodingSettings,
)
async def get_settings(service: CodingService = Depends(get_coding_service)):
    return service.settings()


@router.post(
    "/encounters",
    operation_id="create_coding_encounter",
    summary="Submit a SOAP note and its findings for coding",
    description=(
        "Stores the encounter, then for every coded item (coding.coded_item_types — "
        "conditions in the prototype): hybrid search -> top candidates -> decision "
        "engine probabilities -> assigned code + flags. Other item types are stored "
        "as not_coded. Runs synchronously and returns the coded encounter."
    ),
    response_model=EncounterOut,
    status_code=201,
    responses={409: {"description": "Encounter already exists"}},
)
async def create_encounter(
    body: EncounterCreate,
    engine: str | None = _ENGINE,
    service: CodingService = Depends(get_coding_service),
):
    return await service.create_encounter(body, engine)


@router.get(
    "/encounters",
    operation_id="list_coding_encounters",
    summary="List encounters (review queue)",
    response_model=EncounterListResponse,
)
async def list_encounters(
    queue: str | None = Query(None, description="standard | close_review"),
    status: str | None = Query(None, description="processing | ready_for_review | reviewed | failed"),
    reviewed: bool | None = Query(None, description="Filter on isHumanReviewed"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    service: CodingService = Depends(get_coding_service),
):
    return await service.list_encounters(queue, status, reviewed, limit, offset)


@router.get(
    "/encounters/{encounter_id}",
    operation_id="get_coding_encounter",
    summary="Get a coded encounter",
    description="Each coded item's ai_classification (assigned code, probability, flags, "
    "ranked alternatives) beside its human review, plus the encounter audit_trail.",
    response_model=EncounterOut,
    responses={404: {"description": "Encounter not found"}},
)
async def get_encounter(encounter_id: str, service: CodingService = Depends(get_coding_service)):
    return await service.get_encounter(encounter_id)


@router.get(
    "/encounters/{encounter_id}/items/{item_id}/candidates",
    operation_id="get_coding_item_candidates",
    summary="All search candidates for one item, with probabilities",
    description="The full top-N the decision engine scored (not just the alternatives shown "
    "on the encounter), in search order: search rank/score, text and semantic ranks, "
    "matched index term, and the active decision's probability and rank.",
    response_model=ItemCandidatesResponse,
    responses={404: {"description": "Encounter or item not found"}},
)
async def get_item_candidates(
    encounter_id: str,
    item_id: int,
    service: CodingService = Depends(get_coding_service),
):
    return await service.get_item_candidates(encounter_id, item_id)


@router.post(
    "/encounters/{encounter_id}/items/{item_id}/review",
    operation_id="review_coding_item",
    summary="Approve, override or remove one item's code",
    description="approve = accept the assigned code · override = replace it with `code` "
    "(any billable ICD-10-CM code) · remove = don't bill this item. The AI's "
    "assignment is kept alongside; every action is audited.",
    response_model=EncounterOut,
    responses={404: {"description": "Encounter or item not found"}, 422: {"description": "Not allowed in the current state"}},
)
async def review_item(
    encounter_id: str,
    item_id: int,
    body: ItemReview,
    service: CodingService = Depends(get_coding_service),
):
    return await service.review_item(encounter_id, item_id, body)


@router.post(
    "/encounters/{encounter_id}/approve",
    operation_id="approve_coding_encounter",
    summary="Approve the encounter (isHumanReviewed = true)",
    description="Allowed once every coded item is approved, overridden or removed.",
    response_model=EncounterOut,
    responses={404: {"description": "Encounter not found"}, 422: {"description": "Items still unreviewed, or already approved"}},
)
async def approve_encounter(
    encounter_id: str,
    body: EncounterApprove,
    service: CodingService = Depends(get_coding_service),
):
    return await service.approve_encounter(encounter_id, body)


@router.post(
    "/encounters/{encounter_id}/rescore",
    operation_id="rescore_coding_encounter",
    summary="Re-run a decision engine over the stored candidates",
    description="No new search. Replaces each item's active decision and clears item "
    "reviews. Not allowed once the encounter is approved.",
    response_model=EncounterOut,
)
async def rescore(
    encounter_id: str,
    engine: str | None = _ENGINE,
    service: CodingService = Depends(get_coding_service),
):
    return await service.rescore(encounter_id, engine)
