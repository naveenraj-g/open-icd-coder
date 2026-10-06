"""concept embeddings: pgvector table + HNSW cosine index

Revision ID: 8b2e4d6f1a3c
Revises: 3f9c1a7b2d4e
Create Date: 2026-09-26 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = "8b2e4d6f1a3c"
down_revision: Union[str, None] = "3f9c1a7b2d4e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "terminology_concept_embedding",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("concept_id", sa.Integer(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("embedding", Vector(1024), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["concept_id"], ["terminology_concept.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("concept_id", "model", name="uq_terminology_concept_embedding_concept_model"),
    )
    op.create_index(
        "ix_terminology_concept_embedding_concept_id",
        "terminology_concept_embedding",
        ["concept_id"],
    )
    op.create_index(
        "ix_terminology_concept_embedding_hnsw",
        "terminology_concept_embedding",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )


def downgrade() -> None:
    op.drop_index("ix_terminology_concept_embedding_hnsw", table_name="terminology_concept_embedding")
    op.drop_index("ix_terminology_concept_embedding_concept_id", table_name="terminology_concept_embedding")
    op.drop_table("terminology_concept_embedding")
