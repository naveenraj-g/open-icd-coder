"""terminology schema: code systems, concepts, synonyms

Revision ID: 3f9c1a7b2d4e
Revises:
Create Date: 2026-09-26 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "3f9c1a7b2d4e"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Also created by db/init on a fresh container; kept here so the schema
    # doesn't depend on how the database was provisioned.
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "terminology_code_system",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("canonical_url", sa.String(), nullable=False),
        sa.Column("version", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("publisher", sa.String(), nullable=True),
        sa.Column("active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("canonical_url", "version", name="uq_terminology_code_system_url_version"),
    )
    op.create_index(
        "ix_terminology_code_system_canonical_url",
        "terminology_code_system",
        ["canonical_url"],
    )

    op.create_table(
        "terminology_concept",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code_system_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("display", sa.String(), nullable=False),
        sa.Column("short_display", sa.String(), nullable=True),
        sa.Column("definition", sa.Text(), nullable=True),
        sa.Column("is_billable", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=True),
        sa.Column("parent_concept_id", sa.Integer(), nullable=True),
        sa.Column("notes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("search_vector", postgresql.TSVECTOR(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["code_system_id"], ["terminology_code_system.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["parent_concept_id"], ["terminology_concept.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code_system_id", "code", name="uq_terminology_concept_system_code"),
    )
    op.create_index("ix_terminology_concept_code_system_id", "terminology_concept", ["code_system_id"])
    op.create_index("ix_terminology_concept_code", "terminology_concept", ["code"])
    op.create_index("ix_terminology_concept_parent_concept_id", "terminology_concept", ["parent_concept_id"])
    op.create_index(
        "ix_terminology_concept_search_vector",
        "terminology_concept",
        ["search_vector"],
        postgresql_using="gin",
    )
    op.create_index(
        "ix_terminology_concept_display_trgm",
        "terminology_concept",
        ["display"],
        postgresql_using="gin",
        postgresql_ops={"display": "gin_trgm_ops"},
    )

    op.create_table(
        "terminology_concept_synonym",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("concept_id", sa.Integer(), nullable=False),
        sa.Column("synonym", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["concept_id"], ["terminology_concept.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("concept_id", "synonym", name="uq_terminology_concept_synonym"),
    )
    op.create_index(
        "ix_terminology_concept_synonym_concept_id",
        "terminology_concept_synonym",
        ["concept_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_terminology_concept_synonym_concept_id", table_name="terminology_concept_synonym")
    op.drop_table("terminology_concept_synonym")
    op.drop_index("ix_terminology_concept_display_trgm", table_name="terminology_concept")
    op.drop_index("ix_terminology_concept_search_vector", table_name="terminology_concept")
    op.drop_index("ix_terminology_concept_parent_concept_id", table_name="terminology_concept")
    op.drop_index("ix_terminology_concept_code", table_name="terminology_concept")
    op.drop_index("ix_terminology_concept_code_system_id", table_name="terminology_concept")
    op.drop_table("terminology_concept")
    op.drop_index("ix_terminology_code_system_canonical_url", table_name="terminology_code_system")
    op.drop_table("terminology_code_system")
