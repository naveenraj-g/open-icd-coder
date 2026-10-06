from typing import Literal

from pydantic import BaseModel


class CodeSystemResponse(BaseModel):
    id: int
    canonical_url: str
    version: str
    name: str
    title: str | None = None
    publisher: str | None = None
    active: bool
    concept_count: int
    # Concepts embedded with the configured embedding model (semantic search
    # covers only these).
    embedded_count: int
    # Alphabetic Index terms loaded as searchable text (excludes the
    # evaluation hold-out), and how many are embedded.
    index_term_count: int
    index_terms_embedded: int
    embedding_model: str


class CodeSystemListResponse(BaseModel):
    total: int
    data: list[CodeSystemResponse]


class ConceptSummary(BaseModel):
    code: str
    display: str
    short_display: str | None = None
    is_billable: bool


SearchMode = Literal["text", "semantic", "hybrid"]


class SearchHit(ConceptSummary):
    # Meaning depends on match_type:
    #   text     — full-text rank + trigram word similarity
    #   semantic — cosine similarity (0..1)
    #   hybrid   — reciprocal rank fusion of the text and semantic rankings
    #   code     — None (ordered by tabular position)
    score: float | None = None
    # 1-based position in each underlying ranking (hybrid only) — shows which
    # method found the code, and how highly.
    text_rank: int | None = None
    semantic_rank: int | None = None
    # The Alphabetic Index term that matched, when the hit came from the index
    # rather than the code's own description — e.g. "Variola" for B03.
    matched_on: str | None = None
    # Codes differing only in the 7th character (encounter/episode), merged
    # into this hit — e.g. S72.92XD, S72.92XS under S72.92XA.
    variants: list[str] = []


class SearchResponse(BaseModel):
    system: str
    version: str
    query: str
    match_type: Literal["code", "text", "semantic", "hybrid"]
    # Exact match count for code-prefix queries; None for ranked retrieval
    # (text/semantic/hybrid), which has no natural cut-off.
    total: int | None
    limit: int
    offset: int
    data: list[SearchHit]


class InheritedNotes(BaseModel):
    """Notes declared on an ancestor category, which apply to this code too."""

    code: str
    display: str
    notes: dict[str, list[str]]


class ConceptDetailResponse(ConceptSummary):
    system: str
    version: str
    parent: ConceptSummary | None = None
    children: list[ConceptSummary]
    synonyms: list[str]
    # Tabular-list instructional notes keyed by type, e.g. "excludes1",
    # "code_first", "use_additional_code", "seventh_character".
    notes: dict[str, list[str]]
    # Notes from ancestor categories, nearest first — per ICD-10-CM
    # conventions, a category's instructional notes apply to every code
    # beneath it.
    inherited_notes: list[InheritedNotes]
