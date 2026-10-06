"""Embedding job — embeds a loaded release's concepts and Alphabetic Index
terms via the configured OpenAI-compatible endpoint (LM Studio) and stores
the vectors for semantic search.

Targets:
  concepts     terminology_concept -> terminology_concept_embedding
               text = description + inclusion terms
  index-terms  terminology_index_term -> terminology_index_term_embedding
               text = the index term itself ("Attack, attacks heart")

Resumable: only rows without an embedding for the configured model are
selected, and each batch is written as soon as it's embedded, so Ctrl+C and a
re-run picks up where it stopped.

Run:
  just terminology-embeddings                    # both targets
  just terminology-embeddings index-terms        # one target
  just terminology-embeddings concepts 2000      # first 2,000, to try it out
"""

import asyncio
import time
from dataclasses import dataclass

from app.core.embeddings import EmbeddingClient
from app.terminology.import_.base import BaseLoader


def build_embedding_text(display: str, synonyms: list[str]) -> str:
    """The text a concept is embedded from: its official description plus its
    inclusion terms, which carry the alternate wordings clinicians use."""
    synonyms = [s for s in synonyms if s and s.lower() != display.lower()]
    if not synonyms:
        return display
    return f"{display}. Includes: {'; '.join(synonyms)}"


def _vector_literal(v: list[float]) -> str:
    return "[" + ",".join(f"{x:.7g}" for x in v) + "]"


@dataclass(frozen=True)
class _Target:
    label: str
    # Rows still to embed: (id, text) — $1 code_system_id, $2 model, $3 limit
    pending_sql: str
    # How many are already embedded — $1 code_system_id, $2 model
    done_sql: str
    insert_sql: str


TARGETS = {
    "concepts": _Target(
        label="concepts",
        pending_sql="""
            SELECT c.id, c.display,
                   coalesce(array_agg(s.synonym ORDER BY s.synonym)
                            FILTER (WHERE s.synonym IS NOT NULL), '{}') AS synonyms
              FROM terminology_concept c
              LEFT JOIN terminology_concept_synonym s ON s.concept_id = c.id
             WHERE c.code_system_id = $1
               AND NOT EXISTS (
                     SELECT 1 FROM terminology_concept_embedding e
                      WHERE e.concept_id = c.id AND e.model = $2)
             GROUP BY c.id
             ORDER BY c.sort_order
             LIMIT $3
        """,
        done_sql="""
            SELECT count(*) FROM terminology_concept_embedding e
              JOIN terminology_concept c ON c.id = e.concept_id
             WHERE c.code_system_id = $1 AND e.model = $2
        """,
        insert_sql="""
            INSERT INTO terminology_concept_embedding (concept_id, model, embedding)
            VALUES ($1, $2, $3::vector)
            ON CONFLICT (concept_id, model) DO NOTHING
        """,
    ),
    "index-terms": _Target(
        label="index terms",
        pending_sql="""
            SELECT t.id, t.term
              FROM terminology_index_term t
             WHERE t.code_system_id = $1
               AND NOT EXISTS (
                     SELECT 1 FROM terminology_index_term_embedding e
                      WHERE e.index_term_id = t.id AND e.model = $2)
             ORDER BY t.id
             LIMIT $3
        """,
        done_sql="""
            SELECT count(*) FROM terminology_index_term_embedding e
              JOIN terminology_index_term t ON t.id = e.index_term_id
             WHERE t.code_system_id = $1 AND e.model = $2
        """,
        insert_sql="""
            INSERT INTO terminology_index_term_embedding (index_term_id, model, embedding)
            VALUES ($1, $2, $3::vector)
            ON CONFLICT (index_term_id, model) DO NOTHING
        """,
    ),
}


class EmbeddingLoader(BaseLoader):
    source_name = "embeddings"

    def __init__(self, db_url: str, client: EmbeddingClient):
        super().__init__(db_url)
        self.client = client

    async def load(
        self,
        canonical_url: str,
        version: str | None,
        targets: list[str],
        limit: int | None,
    ) -> None:
        cs = await self.conn.fetchrow(
            """
            SELECT id, name, version FROM terminology_code_system
             WHERE canonical_url = $1 AND ($2::text IS NULL OR version = $2) AND active
             ORDER BY version DESC LIMIT 1
            """,
            canonical_url, version,
        )
        if cs is None:
            raise ValueError(f"Code system not loaded: {canonical_url} {version or ''}".strip())
        for name in targets:
            await self._embed_target(cs, TARGETS[name], limit)

    async def _embed_target(self, cs, target: _Target, limit: int | None) -> None:
        cfg = self.client.config
        rows = await self.conn.fetch(target.pending_sql, cs["id"], cfg.model, limit)
        done_before = await self.conn.fetchval(target.done_sql, cs["id"], cfg.model)
        self._log(
            f"{cs['name']} {cs['version']} {target.label} · model {cfg.model} · "
            f"{done_before:,} already embedded · {len(rows):,} to do"
        )
        if not rows:
            return

        if "synonyms" in rows[0].keys():
            items = [(r["id"], build_embedding_text(r["display"], list(r["synonyms"]))) for r in rows]
        else:
            items = [(r["id"], r["term"]) for r in rows]
        batches = [items[i : i + cfg.batch_size] for i in range(0, len(items), cfg.batch_size)]

        # One asyncpg connection can't run statements concurrently — requests to
        # the embedding server run in parallel, writes are serialised.
        sem = asyncio.Semaphore(cfg.concurrency)
        write_lock = asyncio.Lock()
        progress = {"done": 0}
        t0 = time.monotonic()

        async def run_batch(batch: list[tuple[int, str]]) -> None:
            async with sem:
                vectors = await self.client.embed_documents([text for _, text in batch])
            async with write_lock:
                await self.conn.executemany(
                    target.insert_sql,
                    [(row_id, cfg.model, _vector_literal(v)) for (row_id, _), v in zip(batch, vectors)],
                )
                progress["done"] += len(batch)
                done = progress["done"]
                rate = done / (time.monotonic() - t0)
                eta_min = (len(items) - done) / rate / 60 if rate else 0
                if done == len(items) or (done // cfg.batch_size) % 10 == 0:
                    self._log(
                        f"  {target.label}: {done:,} / {len(items):,} ({done / len(items):.0%}) · "
                        f"{rate:.0f} texts/s · ETA {eta_min:.0f} min"
                    )

        await asyncio.gather(*(run_batch(b) for b in batches))
        self._log(f"Embedded {len(items):,} {target.label} in {time.monotonic() - t0:.0f}s")
        await self.conn.execute("ANALYZE terminology_concept_embedding")
        await self.conn.execute("ANALYZE terminology_index_term_embedding")
