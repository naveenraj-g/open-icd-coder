"""Coding pipeline: encounter -> items -> search candidates -> decision
engine scores -> human review. See docs/goal.md §4-§5.

Design rules:
  - The AI's output is never overwritten. Assignment fields on CodingItem
    describe the active decision; the human's choice lives in final_* /
    review_* fields beside it, and every change is appended to
    CodingAuditEvent.
  - Candidates are engine-independent (what search returned). Probabilities
    belong to a CodingDecision, so the same candidates can be scored by Jev
    and by a baseline and compared.
  - Code and display are snapshotted onto candidates and items, so a later
    terminology reload doesn't rewrite what a reviewer saw.
"""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    false,
    true,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class CodingEncounter(Base):
    """One SOAP note submitted for coding."""

    __tablename__ = "coding_encounter"

    id = Column(Integer, primary_key=True, autoincrement=True)
    encounter_id = Column(String, nullable=False, unique=True, index=True)
    patient_id = Column(String, nullable=False, index=True)
    department = Column(String, nullable=True)
    soap_note = Column(Text, nullable=False)
    # processing -> ready_for_review -> reviewed; failed if every item failed
    status = Column(String, nullable=False, index=True)
    # standard | close_review — from item flags
    review_queue = Column(String, nullable=True, index=True)
    is_human_reviewed = Column(Boolean, nullable=False, default=False, server_default=false())
    reviewed_by = Column(String, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    items = relationship(
        "CodingItem",
        back_populates="encounter",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="CodingItem.sequence",
    )


class CodingItem(Base):
    """One condition / observation / service request / medication request
    from the note. Only configured item types (coding.coded_item_types) are
    searched and scored; the rest are stored with status not_coded."""

    __tablename__ = "coding_item"
    __table_args__ = (
        UniqueConstraint("encounter_pk", "sequence", name="uq_coding_item_encounter_sequence"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    encounter_pk = Column(
        Integer, ForeignKey("coding_encounter.id", ondelete="CASCADE"), nullable=False, index=True
    )
    item_type = Column(String, nullable=False)
    sequence = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    details = Column(JSONB, nullable=True)
    # Exact text sent to search — kept for reproducibility.
    search_query = Column(Text, nullable=True)
    # pending | not_coded | no_candidates | scored | failed | approved | overridden | removed
    status = Column(String, nullable=False, index=True)
    error = Column(Text, nullable=True)

    # Active decision's pick (AI output — never edited by review).
    assigned_concept_id = Column(
        Integer, ForeignKey("terminology_concept.id", ondelete="SET NULL"), nullable=True
    )
    assigned_code = Column(String, nullable=True)
    assigned_display = Column(String, nullable=True)
    probability = Column(Float, nullable=True)
    nota_probability = Column(Float, nullable=True)
    # e.g. ["LOW_CONFIDENCE", "NONE_OF_THE_ABOVE", "NO_CANDIDATES"]
    flags = Column(JSONB, nullable=False, default=list, server_default="[]")

    # Human decision.
    final_concept_id = Column(
        Integer, ForeignKey("terminology_concept.id", ondelete="SET NULL"), nullable=True
    )
    final_code = Column(String, nullable=True)
    final_display = Column(String, nullable=True)
    review_action = Column(String, nullable=True)  # approve | override | remove
    reviewed_by = Column(String, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    encounter = relationship("CodingEncounter", back_populates="items")
    candidates = relationship(
        "CodingCandidate",
        back_populates="item",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="CodingCandidate.search_rank",
    )
    decisions = relationship(
        "CodingDecision",
        back_populates="item",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="CodingDecision.id",
    )


class CodingCandidate(Base):
    """One hybrid-search result for an item (the top-N handed to the engine)."""

    __tablename__ = "coding_candidate"
    __table_args__ = (UniqueConstraint("item_id", "code", name="uq_coding_candidate_item_code"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(Integer, ForeignKey("coding_item.id", ondelete="CASCADE"), nullable=False, index=True)
    concept_id = Column(
        Integer, ForeignKey("terminology_concept.id", ondelete="SET NULL"), nullable=True
    )
    code = Column(String, nullable=False)
    display = Column(String, nullable=False)
    search_rank = Column(Integer, nullable=False)
    search_score = Column(Float, nullable=True)
    text_rank = Column(Integer, nullable=True)
    semantic_rank = Column(Integer, nullable=True)
    matched_on = Column(String, nullable=True)
    variants = Column(JSONB, nullable=False, default=list, server_default="[]")

    item = relationship("CodingItem", back_populates="candidates")


class CodingDecision(Base):
    """One scoring run of a decision engine over an item's candidates."""

    __tablename__ = "coding_decision"
    __table_args__ = (Index("ix_coding_decision_item_active", "item_id", "is_active"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(Integer, ForeignKey("coding_item.id", ondelete="CASCADE"), nullable=False, index=True)
    engine = Column(String, nullable=False)  # "jev", "search-rank", ...
    model = Column(String, nullable=True)
    status = Column(String, nullable=False)  # succeeded | failed
    # The decision the item's assignment currently comes from.
    is_active = Column(Boolean, nullable=False, default=True, server_default=true())
    latency_ms = Column(Float, nullable=True)
    cost = Column(Float, nullable=True)
    error = Column(Text, nullable=True)
    raw_response = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    item = relationship("CodingItem", back_populates="decisions")
    scores = relationship(
        "CodingCandidateScore",
        back_populates="decision",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="CodingCandidateScore.rank",
    )


class CodingCandidateScore(Base):
    """A decision's probability for one candidate. candidate_id NULL is the
    "none of the above" option."""

    __tablename__ = "coding_candidate_score"

    id = Column(Integer, primary_key=True, autoincrement=True)
    decision_id = Column(
        Integer, ForeignKey("coding_decision.id", ondelete="CASCADE"), nullable=False, index=True
    )
    candidate_id = Column(
        Integer, ForeignKey("coding_candidate.id", ondelete="CASCADE"), nullable=True
    )
    probability = Column(Float, nullable=False)
    rank = Column(Integer, nullable=False)  # 1 = most probable

    decision = relationship("CodingDecision", back_populates="scores")
    candidate = relationship("CodingCandidate")


class CodingAuditEvent(Base):
    """Append-only trail of everything that happened to an encounter."""

    __tablename__ = "coding_audit_event"

    id = Column(Integer, primary_key=True, autoincrement=True)
    encounter_pk = Column(
        Integer, ForeignKey("coding_encounter.id", ondelete="CASCADE"), nullable=False, index=True
    )
    item_id = Column(Integer, ForeignKey("coding_item.id", ondelete="CASCADE"), nullable=True, index=True)
    # encounter.received | item.scored | item.approve | item.override | ...
    action = Column(String, nullable=False)
    actor = Column(String, nullable=True)  # reviewer, or "system"
    before = Column(JSONB, nullable=True)
    after = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
