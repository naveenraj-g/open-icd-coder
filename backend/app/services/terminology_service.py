from app.core.embeddings import EmbeddingClient
from app.core.logging import get_logger
from app.errors.domain import NotFoundError
from app.models.terminology.terminology import TerminologyCodeSystem, TerminologyConcept
from app.repository.terminology_repository import TerminologyRepository
from app.schemas.terminology import (
    CodeSystemListResponse,
    CodeSystemResponse,
    ConceptDetailResponse,
    ConceptSummary,
    InheritedNotes,
    SearchHit,
    SearchMode,
    SearchResponse,
)
from app.services.search_ranking import (
    RankedHit,
    as_hits,
    collapse_variants,
    expand_to_billable,
    fuse,
    merge,
)
from app.terminology.icd10cm import ICD10CM_URL, is_code_like, to_dotted

logger = get_logger(__name__)


def _summary(concept: TerminologyConcept) -> ConceptSummary:
    return ConceptSummary(
        code=concept.code,
        display=concept.display,
        short_display=concept.short_display,
        is_billable=concept.is_billable,
    )


def _to_hit(hit: RankedHit, score: float | None) -> SearchHit:
    return SearchHit(
        **_summary(hit.concept).model_dump(),
        score=score,
        text_rank=hit.text_rank,
        semantic_rank=hit.semantic_rank,
        matched_on=hit.matched_on,
        variants=hit.variants,
    )


class TerminologyService:
    def __init__(
        self,
        repository: TerminologyRepository,
        embedding_client: EmbeddingClient,
        use_index_terms: bool = True,
        collapse_variants: bool = True,
        candidate_pool: int = 200,
        text_match: str = "all",
        index_length_penalty: bool = True,
        hybrid_text_weight: float = 1.0,
    ):
        self.repository = repository
        self.embedding_client = embedding_client
        self.use_index_terms = use_index_terms
        self.collapse_variants = collapse_variants
        self.candidate_pool = candidate_pool
        self.text_match = text_match
        self.index_length_penalty = index_length_penalty
        self.hybrid_text_weight = hybrid_text_weight

    async def list_code_systems(self) -> CodeSystemListResponse:
        model = self.embedding_client.model
        rows = await self.repository.list_code_systems(model)
        return CodeSystemListResponse(
            total=len(rows),
            data=[
                CodeSystemResponse(
                    id=cs.id,
                    canonical_url=cs.canonical_url,
                    version=cs.version,
                    name=cs.name,
                    title=cs.title,
                    publisher=cs.publisher,
                    active=cs.active,
                    concept_count=stats["concepts"],
                    embedded_count=stats["concepts_embedded"],
                    index_term_count=stats["index_terms"],
                    index_terms_embedded=stats["index_terms_embedded"],
                    embedding_model=model,
                )
                for cs, stats in rows
            ],
        )

    async def _resolve_code_system(self, system: str, version: str | None) -> TerminologyCodeSystem:
        cs = await self.repository.get_code_system(system, version)
        if cs is None:
            label = f"{system} (version {version})" if version else system
            raise NotFoundError(
                f"Code system not loaded: {label}. Run the terminology loader first.",
                metadata={"system": system, "version": version},
            )
        return cs

    async def _ranked(
        self,
        cs: TerminologyCodeSystem,
        q: str,
        method: str,
        query_vector: list[float] | None,
        billable_only: bool,
    ) -> list[RankedHit]:
        """One method's final ranking: candidates -> merge -> expand -> collapse."""
        if method == "text":
            rows = await self.repository.text_candidates(
                cs.id,
                q,
                self.candidate_pool,
                self.use_index_terms,
                match=self.text_match,
                index_length_penalty=self.index_length_penalty,
            )
        else:
            rows = await self.repository.semantic_candidates(
                cs.id,
                self.embedding_client.model,
                query_vector,
                self.candidate_pool,
                self.use_index_terms,
            )
        concepts = await self.repository.load_concepts(list({r[0] for r in rows}))
        candidates = merge(rows, concepts)

        if billable_only:
            categories = [c.concept.code for c in candidates if not c.concept.is_billable]
            descendants = await self.repository.billable_descendants(cs.id, categories)
            candidates = expand_to_billable(candidates, descendants)

        return collapse_variants(candidates) if self.collapse_variants else as_hits(candidates)

    async def _hybrid(self, cs: TerminologyCodeSystem, q: str, billable_only: bool) -> list[RankedHit]:
        vector = await self.embedding_client.embed_query(q)
        text_ranked = await self._ranked(cs, q, "text", None, billable_only)
        semantic_ranked = await self._ranked(cs, q, "semantic", vector, billable_only)
        return fuse(
            text_ranked,
            semantic_ranked,
            by_stem=self.collapse_variants,
            text_weight=self.hybrid_text_weight,
        )

    async def retrieve(
        self, q: str, system: str, version: str | None, limit: int
    ) -> tuple[TerminologyCodeSystem, list[RankedHit]]:
        """Stage 1 for the coding pipeline: the top `limit` billable
        candidates for a clinical phrase, by hybrid search, with their
        concept records — so callers can store foreign keys, not just codes."""
        cs = await self._resolve_code_system(system, version)
        return cs, (await self._hybrid(cs, q.strip(), billable_only=True))[:limit]

    async def search(
        self,
        q: str,
        system: str,
        version: str | None,
        mode: SearchMode,
        billable_only: bool,
        limit: int,
        offset: int,
    ) -> SearchResponse:
        cs = await self._resolve_code_system(system, version)
        q = q.strip()
        total: int | None = None

        # Code-shaped input ("K35", "k3530", "K35.3") is a prefix lookup on the
        # code itself, whatever the mode. Some abbreviations are code-shaped
        # too ("T2DM" looks like T2D.M) — if no code matches, fall through to
        # a normal search.
        code_hits = None
        if system == ICD10CM_URL and is_code_like(q):
            count, concepts = await self.repository.search_by_code_prefix(
                cs.id, to_dotted(q), billable_only, limit, offset
            )
            if count:
                total = count
                code_hits = [SearchHit(**_summary(c).model_dump()) for c in concepts]

        if code_hits is not None:
            match_type = "code"
            hits = code_hits

        elif mode == "text":
            match_type = "text"
            ranked = await self._ranked(cs, q, "text", None, billable_only)
            hits = [_to_hit(h, round(h.score, 4)) for h in ranked[offset : offset + limit]]

        elif mode == "semantic":
            match_type = "semantic"
            vector = await self.embedding_client.embed_query(q)
            ranked = await self._ranked(cs, q, "semantic", vector, billable_only)
            hits = [_to_hit(h, round(h.score, 4)) for h in ranked[offset : offset + limit]]

        else:
            match_type = "hybrid"
            fused = await self._hybrid(cs, q, billable_only)
            hits = [_to_hit(h, round(h.score, 5)) for h in fused[offset : offset + limit]]

        logger.info(
            "Terminology search",
            extra={
                "event": "terminology.search",
                "system": system,
                "version": cs.version,
                "match_type": match_type,
                "returned": len(hits),
            },
        )
        return SearchResponse(
            system=system,
            version=cs.version,
            query=q,
            match_type=match_type,
            total=total,
            limit=limit,
            offset=offset,
            data=hits,
        )

    async def get_concept(self, code: str, system: str, version: str | None) -> ConceptDetailResponse:
        cs = await self._resolve_code_system(system, version)
        lookup = to_dotted(code) if system == ICD10CM_URL else code
        result = await self.repository.get_concept(cs.id, lookup)
        if result is None:
            raise NotFoundError(
                f"Code {lookup} not found in {cs.name} {cs.version}",
                metadata={"code": lookup, "system": system, "version": cs.version},
            )
        concept, children, ancestors = result
        return ConceptDetailResponse(
            **_summary(concept).model_dump(),
            system=system,
            version=cs.version,
            parent=_summary(concept.parent) if concept.parent else None,
            children=[_summary(c) for c in children],
            synonyms=sorted(s.synonym for s in concept.synonyms),
            notes=concept.notes or {},
            inherited_notes=[
                InheritedNotes(code=a.code, display=a.display, notes=a.notes)
                for a in ancestors
            ],
        )
