"""alphabetic index terms + their embeddings

Revision ID: c4d7a9e2b5f1
Revises: 8b2e4d6f1a3c
Create Date: 2026-09-26 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "c4d7a9e2b5f1"
down_revision: Union[str, None] = "8b2e4d6f1a3c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "terminology_index_term",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code_system_id", sa.Integer(), nullable=False),
        sa.Column("concept_id", sa.Integer(), nullable=False),
        sa.Column("term", sa.String(), nullable=False),
        sa.Column("depth", sa.Integer(), nullable=False),
        sa.Column("via_see", sa.Boolean(), nullable=False),
        sa.Column("search_vector", postgresql.TSVECTOR(), nullable=True),
        sa.ForeignKeyConstraint(["code_system_id"], ["terminology_code_system.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["concept_id"], ["terminology_concept.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code_system_id", "term", "concept_id", name="uq_terminology_index_term"),
    )
    op.create_index("ix_terminology_index_term_code_system_id", "terminology_index_term", ["code_system_id"])
    op.create_index("ix_terminology_index_term_concept_id", "terminology_index_term", ["concept_id"])
    op.create_index(
        "ix_terminology_index_term_search_vector",
        "terminology_index_term",
        ["search_vector"],
        postgresql_using="gin",
    )
    op.create_index(
        "ix_terminology_index_term_term_trgm",
        "terminology_index_term",
        ["term"],
        postgresql_using="gin",
        postgresql_ops={"term": "gin_trgm_ops"},
    )

    op.create_table(
        "terminology_index_term_embedding",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("index_term_id", sa.Integer(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("embedding", Vector(1024), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["index_term_id"], ["terminology_index_term.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("index_term_id", "model", name="uq_terminology_index_term_embedding_term_model"),
    )
    op.create_index(
        "ix_terminology_index_term_embedding_index_term_id",
        "terminology_index_term_embedding",
        ["index_term_id"],
    )
    op.create_index(
        "ix_terminology_index_term_embedding_hnsw",
        "terminology_index_term_embedding",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )


def downgrade() -> None:
    op.drop_index("ix_terminology_index_term_embedding_hnsw", table_name="terminology_index_term_embedding")
    op.drop_index("ix_terminology_index_term_embedding_index_term_id", table_name="terminology_index_term_embedding")
    op.drop_table("terminology_index_term_embedding")
    op.drop_index("ix_terminology_index_term_term_trgm", table_name="terminology_index_term")
    op.drop_index("ix_terminology_index_term_search_vector", table_name="terminology_index_term")
    op.drop_index("ix_terminology_index_term_concept_id", table_name="terminology_index_term")
    op.drop_index("ix_terminology_index_term_code_system_id", table_name="terminology_index_term")
    op.drop_table("terminology_index_term")
