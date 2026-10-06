from fastapi import APIRouter, Depends, Query

from app.core.config import settings
from app.di.dependencies.terminology import get_terminology_service
from app.schemas.terminology import (
    CodeSystemListResponse,
    ConceptDetailResponse,
    SearchMode,
    SearchResponse,
)
from app.services.terminology_service import TerminologyService
from app.terminology.icd10cm import ICD10CM_URL

router = APIRouter()

_SYSTEM = Query(ICD10CM_URL, description="Code system canonical URL")
_VERSION = Query(None, description="Release, e.g. '2027'. Default: latest loaded")


@router.get(
    "/code-systems",
    operation_id="list_terminology_code_systems",
    summary="List loaded code systems",
    description="Every loaded code system release with its concept count.",
    response_model=CodeSystemListResponse,
)
async def list_code_systems(
    service: TerminologyService = Depends(get_terminology_service),
):
    return await service.list_code_systems()


@router.get(
    "/search",
    operation_id="search_terminology_concepts",
    summary="Search codes by code or text",
    description=(
        "Code-shaped queries ('K35', 'k3530', 'K35.3') always return codes with "
        "that prefix in tabular order. Otherwise `mode` picks the method:\n\n"
        "- **text** — PostgreSQL full-text search (word stems, any order) + "
        "trigram similarity (typos) over the description and inclusion terms.\n"
        "- **semantic** — nearest codes by embedding similarity (pgvector); "
        "finds lay wording like 'heart attack'. Needs the embedding server.\n"
        "- **hybrid** — both rankings merged with reciprocal rank fusion; each "
        "hit reports its `text_rank` and `semantic_rank`."
    ),
    response_model=SearchResponse,
    responses={503: {"description": "Embedding server unreachable (semantic/hybrid)"}},
)
async def search_concepts(
    q: str = Query(
        ...,
        min_length=1,
        max_length=200,
        description="e.g. 'acute appendicitis with localized peritonitis', 'heart attack' or 'K35.3'",
    ),
    mode: SearchMode = Query(
        settings.search.default_mode,
        description="text | semantic | hybrid (default from configs/config.yaml)",
    ),
    system: str = _SYSTEM,
    version: str | None = _VERSION,
    billable_only: bool = Query(False, description="Exclude non-billable category headers"),
    limit: int = Query(settings.search.default_limit, ge=1, le=settings.search.max_limit),
    offset: int = Query(0, ge=0),
    service: TerminologyService = Depends(get_terminology_service),
):
    return await service.search(q, system, version, mode, billable_only, limit, offset)


@router.get(
    "/concepts/{code}",
    operation_id="get_terminology_concept",
    summary="Get one code with its hierarchy and notes",
    description=(
        "Accepts dotted or undotted ICD-10-CM codes ('K35.30' or 'K3530'). "
        "Returns the parent, direct children, inclusion terms and tabular notes "
        "(excludes1/2, code first, use additional code, 7th character), plus "
        "`inherited_notes` from ancestor categories, which apply to this code too."
    ),
    response_model=ConceptDetailResponse,
    responses={404: {"description": "Code or code system not found"}},
)
async def get_concept(
    code: str,
    system: str = _SYSTEM,
    version: str | None = _VERSION,
    service: TerminologyService = Depends(get_terminology_service),
):
    return await service.get_concept(code, system, version)
