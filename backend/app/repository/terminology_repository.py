from sqlalchemy import func, literal, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import joinedload, selectinload

from app.models.terminology.terminology import TerminologyCodeSystem, TerminologyConcept

# (concept_id, score, matched_on) — matched_on is the index term that
# produced the score, or None when it came from the concept's own text.
CandidateRow = tuple[int, float, str | None]

# Any-word matching: added when the text matches ALL query words, so exact
# multi-word matches outrank partial ones (scores otherwise top out near 2).
ALL_WORDS_BONUS = 0.5
# "fallback" matching switches from all-words to any-word below this many
# candidates (concept + index rows) — i.e. when all-words found ~nothing.
ANY_WORD_FALLBACK_MIN = 10


def _vector_literal(v: list[float]) -> str:
    return "[" + ",".join(f"{x:.7g}" for x in v) + "]"


class TerminologyRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory

    async def list_code_systems(self, embedding_model: str) -> list[tuple[TerminologyCodeSystem, dict]]:
        """Every loaded release with coverage counts: concepts, index terms,
        and how many of each have an embedding from `embedding_model`."""
        async with self.session_factory() as session:
            systems = (
                await session.execute(
                    select(TerminologyCodeSystem).order_by(
                        TerminologyCodeSystem.name, TerminologyCodeSystem.version.desc()
                    )
                )
            ).scalars().all()
            out = []
            for cs in systems:
                stats = (
                    await session.execute(
                        text(
                            """
                            SELECT
                              (SELECT count(*) FROM terminology_concept WHERE code_system_id = :cs) AS concepts,
                              (SELECT count(*) FROM terminology_concept_embedding e
                                 JOIN terminology_concept c ON c.id = e.concept_id
                                WHERE c.code_system_id = :cs AND e.model = :m) AS concepts_embedded,
                              (SELECT count(*) FROM terminology_index_term WHERE code_system_id = :cs) AS index_terms,
                              (SELECT count(*) FROM terminology_index_term_embedding e
                                 JOIN terminology_index_term t ON t.id = e.index_term_id
                                WHERE t.code_system_id = :cs AND e.model = :m) AS index_terms_embedded
                            """
                        ),
                        {"cs": cs.id, "m": embedding_model},
                    )
                ).mappings().one()
                out.append((cs, dict(stats)))
            return out

    async def get_code_system(
        self, canonical_url: str, version: str | None
    ) -> TerminologyCodeSystem | None:
        """A specific release, or the latest active one when version is None."""
        async with self.session_factory() as session:
            stmt = select(TerminologyCodeSystem).where(
                TerminologyCodeSystem.canonical_url == canonical_url
            )
            if version is not None:
                stmt = stmt.where(TerminologyCodeSystem.version == version)
            else:
                stmt = stmt.where(TerminologyCodeSystem.active.is_(True))
            row = await session.execute(
                stmt.order_by(TerminologyCodeSystem.version.desc()).limit(1)
            )
            return row.scalar_one_or_none()

    async def search_by_code_prefix(
        self,
        code_system_id: int,
        prefix: str,
        billable_only: bool,
        limit: int,
        offset: int,
    ) -> tuple[int, list[TerminologyConcept]]:
        """Codes starting with `prefix` (dotted), in official tabular order."""
        async with self.session_factory() as session:
            stmt = (
                select(TerminologyConcept)
                .where(TerminologyConcept.code_system_id == code_system_id)
                .where(TerminologyConcept.code.startswith(prefix))
            )
            if billable_only:
                stmt = stmt.where(TerminologyConcept.is_billable.is_(True))

            total = await session.scalar(select(func.count()).select_from(stmt.subquery()))
            rows = await session.execute(
                stmt.order_by(TerminologyConcept.sort_order).limit(limit).offset(offset)
            )
            return total or 0, list(rows.scalars().all())

    async def text_candidates(
        self,
        code_system_id: int,
        q: str,
        pool: int,
        include_index_terms: bool,
        match: str = "all",
        index_length_penalty: bool = False,
    ) -> list[CandidateRow]:
        """Lexical matches from concept text (description + inclusion terms)
        and, optionally, Alphabetic Index terms — top `pool` from each.

        A row matches when EITHER full-text search matches (stemmed words) OR
        the query is trigram word-similar to the text (typos).
        Score = ts_rank_cd (0..1) + trigram similarity (0..1) [+ all-words bonus].

        match — how full-text treats the query's words:
          "all"       every word must match (PostgreSQL websearch default)
          "any"       any word may match, +ALL_WORDS_BONUS when all do. Lets
                      long note sentences match at all, but floods the list
                      for queries with common words ("Devic's disease" pulls
                      every "... disease"), which hurts hybrid (Report 03).
          "fallback"  "all" first; "any" only when that finds fewer than
                      ANY_WORD_FALLBACK_MIN candidates.

        index_length_penalty (Report 02 F5): score index terms with the mean of
        word_similarity (query inside term) and symmetric similarity (term
        about as long as the query), and length-normalise the full-text rank,
        so "Intoxication caffeine" prefers the term that IS it over
        "Intoxication caffeine with dependence", which merely contains it."""
        async with self.session_factory() as session:
            if match == "fallback":
                rows = await self._text_rows(
                    session, code_system_id, q, pool, include_index_terms, False, index_length_penalty
                )
                if len(rows) >= ANY_WORD_FALLBACK_MIN:
                    return rows
                any_word = True
            else:
                any_word = match == "any"
            return await self._text_rows(
                session, code_system_id, q, pool, include_index_terms, any_word, index_length_penalty
            )

    async def _text_rows(
        self,
        session: AsyncSession,
        code_system_id: int,
        q: str,
        pool: int,
        include_index_terms: bool,
        any_word: bool,
        index_length_penalty: bool,
    ) -> list[CandidateRow]:
        params = {"q": q, "cs": code_system_id, "pool": pool, "bonus": ALL_WORDS_BONUS}
        # SQL fragments below are fixed strings chosen by flags, never user input.
        if any_word:
            tsq_sql = (
                "SELECT websearch_to_tsquery('english', :q) AS tsq_all, "
                "replace(websearch_to_tsquery('english', :q)::text, '&', '|')::tsquery AS tsq"
            )
        else:
            tsq_sql = (
                "SELECT websearch_to_tsquery('english', :q) AS tsq_all, "
                "websearch_to_tsquery('english', :q) AS tsq"
            )

        def bonus(col: str) -> str:
            return f" + CASE WHEN {col} @@ q.tsq_all THEN :bonus ELSE 0 END" if any_word else ""

        rows = (
            await session.execute(
                text(
                    f"""
                    SELECT c.id,
                           coalesce(ts_rank_cd(c.search_vector, q.tsq, 32), 0)
                             + word_similarity(:q, c.display){bonus("c.search_vector")} AS score
                      FROM terminology_concept c, ({tsq_sql}) q
                     WHERE c.code_system_id = :cs
                       AND (c.search_vector @@ q.tsq OR :q <% c.display)
                     ORDER BY score DESC
                     LIMIT :pool
                    """
                ),
                params,
            )
        ).all()
        out: list[CandidateRow] = [(r[0], float(r[1]), None) for r in rows]
        if include_index_terms:
            if index_length_penalty:
                # 33 = 1 | 32: divide rank by 1 + log(term length), then scale to 0..1
                rank_sql = "coalesce(ts_rank_cd(t.search_vector, q.tsq, 33), 0)"
                sim_sql = "(word_similarity(:q, t.term) + similarity(:q, t.term)) / 2"
            else:
                rank_sql = "coalesce(ts_rank_cd(t.search_vector, q.tsq, 32), 0)"
                sim_sql = "word_similarity(:q, t.term)"
            rows = (
                await session.execute(
                    text(
                        f"""
                        SELECT t.concept_id, t.term,
                               {rank_sql} + {sim_sql}{bonus("t.search_vector")} AS score
                          FROM terminology_index_term t, ({tsq_sql}) q
                         WHERE t.code_system_id = :cs
                           AND (t.search_vector @@ q.tsq OR :q <% t.term)
                         ORDER BY score DESC
                         LIMIT :pool
                        """
                    ),
                    params,
                )
            ).all()
            out.extend((r[0], float(r[2]), r[1]) for r in rows)
        return out

    async def semantic_candidates(
        self,
        code_system_id: int,
        model: str,
        query_vector: list[float],
        pool: int,
        include_index_terms: bool,
    ) -> list[CandidateRow]:
        """Nearest concepts and (optionally) index terms by cosine similarity
        on the HNSW indexes — top `pool` from each. Score = cosine similarity."""
        params = {
            "v": _vector_literal(query_vector),
            "m": model,
            "cs": code_system_id,
            "pool": pool,
        }
        async with self.session_factory() as session:
            # HNSW returns at most ef_search candidates per scan and the code
            # system filter is applied after it — widen the pool and let
            # pgvector keep scanning, in exact distance order, until enough
            # rows survive.
            await session.execute(text(f"SET LOCAL hnsw.ef_search = {min(max(pool, 40), 1000)}"))
            await session.execute(text("SET LOCAL hnsw.iterative_scan = strict_order"))
            rows = (
                await session.execute(
                    text(
                        """
                        SELECT e.concept_id,
                               1 - (e.embedding <=> CAST(:v AS vector)) AS similarity
                          FROM terminology_concept_embedding e
                          JOIN terminology_concept c ON c.id = e.concept_id
                         WHERE e.model = :m AND c.code_system_id = :cs
                         ORDER BY e.embedding <=> CAST(:v AS vector)
                         LIMIT :pool
                        """
                    ),
                    params,
                )
            ).all()
            out: list[CandidateRow] = [(r[0], float(r[1]), None) for r in rows]
            if include_index_terms:
                rows = (
                    await session.execute(
                        text(
                            """
                            SELECT t.concept_id, t.term,
                                   1 - (e.embedding <=> CAST(:v AS vector)) AS similarity
                              FROM terminology_index_term_embedding e
                              JOIN terminology_index_term t ON t.id = e.index_term_id
                             WHERE e.model = :m AND t.code_system_id = :cs
                             ORDER BY e.embedding <=> CAST(:v AS vector)
                             LIMIT :pool
                            """
                        ),
                        params,
                    )
                ).all()
                out.extend((r[0], float(r[2]), r[1]) for r in rows)
            return out

    async def load_concepts(self, concept_ids: list[int]) -> dict[int, TerminologyConcept]:
        if not concept_ids:
            return {}
        async with self.session_factory() as session:
            rows = await session.execute(
                select(TerminologyConcept).where(TerminologyConcept.id.in_(concept_ids))
            )
            return {c.id: c for c in rows.scalars().all()}

    async def billable_descendants(
        self, code_system_id: int, category_codes: list[str]
    ) -> dict[str, list[TerminologyConcept]]:
        """{category code: its billable descendants in tabular order}. ICD-10-CM
        codes are hierarchical by prefix, so descendants of "S72.9" are the
        billable codes starting with "S72.9"."""
        if not category_codes:
            return {}
        async with self.session_factory() as session:
            rows = await session.execute(
                select(TerminologyConcept)
                .where(TerminologyConcept.code_system_id == code_system_id)
                .where(TerminologyConcept.is_billable.is_(True))
                .where(or_(*(TerminologyConcept.code.startswith(c) for c in category_codes)))
                .order_by(TerminologyConcept.sort_order)
            )
            concepts = rows.scalars().all()
        out: dict[str, list[TerminologyConcept]] = {c: [] for c in category_codes}
        for concept in concepts:
            for category in category_codes:
                if concept.code.startswith(category):
                    out[category].append(concept)
        return out

    async def get_concept(
        self, code_system_id: int, code: str
    ) -> tuple[TerminologyConcept, list[TerminologyConcept], list[TerminologyConcept]] | None:
        """(concept with parent + synonyms loaded, its direct children,
        its ancestors that carry notes — nearest first)."""
        async with self.session_factory() as session:
            row = await session.execute(
                select(TerminologyConcept)
                .options(
                    joinedload(TerminologyConcept.parent),
                    selectinload(TerminologyConcept.synonyms),
                )
                .where(TerminologyConcept.code_system_id == code_system_id)
                .where(TerminologyConcept.code == code)
            )
            concept = row.scalar_one_or_none()
            if concept is None:
                return None
            children = await session.execute(
                select(TerminologyConcept)
                .where(TerminologyConcept.parent_concept_id == concept.id)
                .order_by(TerminologyConcept.sort_order)
            )
            ancestors = await self._ancestors_with_notes(session, concept)
            return concept, list(children.scalars().all()), ancestors

    async def _ancestors_with_notes(
        self, session: AsyncSession, concept: TerminologyConcept
    ) -> list[TerminologyConcept]:
        """Every ancestor that carries tabular notes, nearest first. ICD-10-CM
        notes on a category apply to all codes beneath it."""
        if concept.parent_concept_id is None:
            return []
        anc = (
            select(
                TerminologyConcept.id,
                TerminologyConcept.parent_concept_id,
                literal(1).label("depth"),
            )
            .where(TerminologyConcept.id == concept.parent_concept_id)
            .cte("ancestors", recursive=True)
        )
        anc = anc.union_all(
            select(
                TerminologyConcept.id,
                TerminologyConcept.parent_concept_id,
                anc.c.depth + 1,
            ).where(TerminologyConcept.id == anc.c.parent_concept_id)
        )
        rows = await session.execute(
            select(TerminologyConcept)
            .join(anc, anc.c.id == TerminologyConcept.id)
            .where(TerminologyConcept.notes.is_not(None))
            .order_by(anc.c.depth)
        )
        return list(rows.scalars().all())
