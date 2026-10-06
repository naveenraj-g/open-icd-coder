from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    true,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base

# Qwen3-Embedding-0.6B output size. Changing it needs a migration.
EMBEDDING_DIM = 1024


class TerminologyCodeSystem(Base):
    """One loaded release of a code system, e.g. ICD-10-CM FY2027.

    Several versions of the same system can coexist (canonical_url + version
    is unique), so a new annual release can be loaded before the old one is
    retired."""

    __tablename__ = "terminology_code_system"
    __table_args__ = (
        UniqueConstraint(
            "canonical_url", "version", name="uq_terminology_code_system_url_version"
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    canonical_url = Column(String, nullable=False, index=True)
    version = Column(String, nullable=False)
    name = Column(String, nullable=False)
    title = Column(String, nullable=True)
    publisher = Column(String, nullable=True)
    active = Column(Boolean, nullable=False, default=True, server_default=true())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    concepts = relationship(
        "TerminologyConcept",
        back_populates="code_system",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class TerminologyConcept(Base):
    """A single code within a code system release.

    For ICD-10-CM this holds both billable codes and the non-billable category
    headers above them (is_billable=False), linked by parent_concept_id so a
    retrieved category can be expanded into its specific child codes."""

    __tablename__ = "terminology_concept"
    __table_args__ = (
        UniqueConstraint(
            "code_system_id", "code", name="uq_terminology_concept_system_code"
        ),
        Index(
            "ix_terminology_concept_search_vector",
            "search_vector",
            postgresql_using="gin",
        ),
        Index(
            "ix_terminology_concept_display_trgm",
            "display",
            postgresql_using="gin",
            postgresql_ops={"display": "gin_trgm_ops"},
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    code_system_id = Column(
        Integer,
        ForeignKey("terminology_code_system.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Canonical dotted form, e.g. "K35.30" (as used in FHIR Coding.code).
    code = Column(String, nullable=False, index=True)
    display = Column(String, nullable=False)
    short_display = Column(String, nullable=True)
    definition = Column(Text, nullable=True)
    is_billable = Column(Boolean, nullable=False, default=False)
    # Position in the official tabular order — stable tie-breaker for sorting.
    sort_order = Column(Integer, nullable=True)
    parent_concept_id = Column(
        Integer,
        ForeignKey("terminology_concept.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    # Tabular-list instructional notes keyed by type, e.g.
    # {"excludes1": [...], "code_first": [...], "use_additional_code": [...]}.
    notes = Column(JSONB, nullable=True)
    active = Column(Boolean, nullable=False, default=True, server_default=true())
    # display (A) + synonyms (B) + short_display (D). Populated by the loader.
    search_vector = Column(TSVECTOR, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    code_system = relationship("TerminologyCodeSystem", back_populates="concepts")
    parent = relationship("TerminologyConcept", remote_side=[id])
    synonyms = relationship(
        "TerminologyConceptSynonym",
        back_populates="concept",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class TerminologyConceptEmbedding(Base):
    """Vector embedding of a concept's text (display + inclusion terms) for
    semantic search. One row per (concept, model), so models can be compared
    side by side; every model sharing this table must emit EMBEDDING_DIM."""

    __tablename__ = "terminology_concept_embedding"
    __table_args__ = (
        UniqueConstraint(
            "concept_id", "model", name="uq_terminology_concept_embedding_concept_model"
        ),
        Index(
            "ix_terminology_concept_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    concept_id = Column(
        Integer,
        ForeignKey("terminology_concept.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    model = Column(String, nullable=False)
    embedding = Column(Vector(EMBEDDING_DIM), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class TerminologyIndexTerm(Base):
    """One Alphabetic Index path, as searchable text, linked to the concept
    its code names — e.g. "Attack, attacks heart" -> I21.9. Kept separate from
    synonyms because some catch-all codes have hundreds of index terms; each
    term is matched (and embedded) on its own and grouped back to its concept
    at query time.

    concept_id may point at a non-billable category when the index gives a
    partial code ("S72.9-"); search expands those to billable descendants."""

    __tablename__ = "terminology_index_term"
    __table_args__ = (
        UniqueConstraint(
            "code_system_id", "term", "concept_id", name="uq_terminology_index_term"
        ),
        Index(
            "ix_terminology_index_term_search_vector",
            "search_vector",
            postgresql_using="gin",
        ),
        Index(
            "ix_terminology_index_term_term_trgm",
            "term",
            postgresql_using="gin",
            postgresql_ops={"term": "gin_trgm_ops"},
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    code_system_id = Column(
        Integer,
        ForeignKey("terminology_code_system.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    concept_id = Column(
        Integer,
        ForeignKey("terminology_concept.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    term = Column(String, nullable=False)
    depth = Column(Integer, nullable=False)
    # True when the index path had no code of its own but a "see" reference.
    via_see = Column(Boolean, nullable=False, default=False)
    search_vector = Column(TSVECTOR, nullable=True)

    concept = relationship("TerminologyConcept")


class TerminologyIndexTermEmbedding(Base):
    """Vector embedding of one index term, per model (see
    TerminologyConceptEmbedding)."""

    __tablename__ = "terminology_index_term_embedding"
    __table_args__ = (
        UniqueConstraint(
            "index_term_id", "model", name="uq_terminology_index_term_embedding_term_model"
        ),
        Index(
            "ix_terminology_index_term_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    index_term_id = Column(
        Integer,
        ForeignKey("terminology_index_term.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    model = Column(String, nullable=False)
    embedding = Column(Vector(EMBEDDING_DIM), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class TerminologyConceptSynonym(Base):
    """Alternate names for a concept (ICD-10-CM inclusion terms) — powers
    text search beyond the official description."""

    __tablename__ = "terminology_concept_synonym"
    __table_args__ = (
        UniqueConstraint(
            "concept_id", "synonym", name="uq_terminology_concept_synonym"
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    concept_id = Column(
        Integer,
        ForeignKey("terminology_concept.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    synonym = Column(String, nullable=False)

    concept = relationship("TerminologyConcept", back_populates="synonyms")
