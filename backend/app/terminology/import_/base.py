"""Shared async base class for terminology loaders.

Uses asyncpg directly (not SQLAlchemy) for bulk-load performance: COPY for
the big inserts, one transaction per release so a failed load leaves the
previous data untouched.
"""

import time

import asyncpg


class BaseLoader:
    source_name: str = "unknown"

    def __init__(self, db_url: str):
        # SQLAlchemy uses postgresql+asyncpg:// — asyncpg needs plain postgresql://
        self.db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
        self._conn: asyncpg.Connection | None = None
        self._t0 = time.monotonic()

    async def __aenter__(self) -> "BaseLoader":
        self._log("Connecting to database...")
        self._conn = await asyncpg.connect(self.db_url)
        return self

    async def __aexit__(self, *_) -> None:
        if self._conn:
            await self._conn.close()

    @property
    def conn(self) -> asyncpg.Connection:
        assert self._conn is not None, "Not connected — use async with loader"
        return self._conn

    def _log(self, msg: str) -> None:
        print(f"[{self.source_name.upper()} +{time.monotonic() - self._t0:5.1f}s] {msg}")

    async def upsert_code_system(
        self,
        canonical_url: str,
        version: str,
        name: str,
        title: str | None = None,
        publisher: str | None = None,
    ) -> int:
        row = await self.conn.fetchrow(
            """
            INSERT INTO terminology_code_system
                (canonical_url, version, name, title, publisher)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (canonical_url, version) DO UPDATE SET
                name       = EXCLUDED.name,
                title      = EXCLUDED.title,
                publisher  = EXCLUDED.publisher,
                active     = TRUE,
                updated_at = NOW()
            RETURNING id
            """,
            canonical_url, version, name, title, publisher,
        )
        return row["id"]

    async def clear_concepts(self, code_system_id: int) -> int:
        """Remove every concept of a release (synonyms cascade) so a re-run
        reloads cleanly instead of leaving stale rows behind."""
        status = await self.conn.execute(
            "DELETE FROM terminology_concept WHERE code_system_id = $1",
            code_system_id,
        )
        return int(status.split()[-1])

    async def fetch_concept_id_map(self, code_system_id: int) -> dict[str, int]:
        """Returns {code: db_id} for all concepts under a code system."""
        rows = await self.conn.fetch(
            "SELECT code, id FROM terminology_concept WHERE code_system_id = $1",
            code_system_id,
        )
        return {r["code"]: r["id"] for r in rows}

    async def set_parents(self, pairs: list[tuple[int, int]]) -> None:
        """pairs: (child_db_id, parent_db_id). One COPY into a temp table, then
        a single UPDATE — far faster than ~100k individual UPDATEs."""
        await self.conn.execute(
            "CREATE TEMP TABLE tmp_concept_parent (child_id int, parent_id int) ON COMMIT DROP"
        )
        await self.conn.copy_records_to_table(
            "tmp_concept_parent", records=pairs, columns=["child_id", "parent_id"]
        )
        await self.conn.execute(
            """
            UPDATE terminology_concept c
               SET parent_concept_id = t.parent_id
              FROM tmp_concept_parent t
             WHERE c.id = t.child_id
            """
        )

    async def build_search_vectors(self, code_system_id: int) -> None:
        """display (A) + synonyms (B) + short_display (D)."""
        await self.conn.execute(
            """
            UPDATE terminology_concept c
               SET search_vector =
                     setweight(to_tsvector('english', c.display), 'A')
                  || setweight(to_tsvector('english', coalesce(
                         (SELECT string_agg(s.synonym, ' ')
                            FROM terminology_concept_synonym s
                           WHERE s.concept_id = c.id), '')), 'B')
                  || setweight(to_tsvector('english', coalesce(c.short_display, '')), 'D')
             WHERE c.code_system_id = $1
            """,
            code_system_id,
        )
