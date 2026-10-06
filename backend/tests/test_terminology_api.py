"""Router → DI → service wiring, with the repository swapped for an in-memory
fake so no database is needed."""

import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5433/test")

import pytest
from dependency_injector import providers
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.main import app
from app.models.terminology.terminology import TerminologyCodeSystem, TerminologyConcept
from app.terminology.icd10cm import ICD10CM_URL

CS = TerminologyCodeSystem(id=1, canonical_url=ICD10CM_URL, version="2027", name="ICD-10-CM", active=True)
K353 = TerminologyConcept(
    id=10,
    code="K35.3",
    display="Acute appendicitis with localized peritonitis",
    is_billable=False,
    notes={"excludes1": ["acute appendicitis with generalized peritonitis (K35.2-)"]},
    synonyms=[],
)
K3530 = TerminologyConcept(
    id=11,
    code="K35.30",
    display="Acute appendicitis with localized peritonitis, without perforation or gangrene",
    short_display="Acute appendicitis with loc peritonitis, w/o perf or gangr",
    is_billable=True,
    notes={"excludes1": ["something (X00)"]},
    synonyms=[],
)
K3530.parent = K353
I219 = TerminologyConcept(id=12, code="I21.9", display="Acute myocardial infarction, unspecified", is_billable=True, sort_order=5, synonyms=[])
K3530.sort_order = 9


class FakeEmbeddingClient:
    model = "fake-embed"

    def __init__(self):
        self.queries: list[str] = []

    async def embed_query(self, query):
        self.queries.append(query)
        return [0.1] * 1024

    async def close(self):
        pass


B03 = TerminologyConcept(id=13, code="B03", display="Smallpox", is_billable=True, sort_order=1, synonyms=[])
CONCEPTS = {c.id: c for c in (K353, K3530, I219, B03)}


class FakeRepository:
    def __init__(self):
        self.calls: list[tuple] = []

    async def list_code_systems(self, embedding_model):
        return [
            (CS, {"concepts": 2, "concepts_embedded": 1, "index_terms": 5, "index_terms_embedded": 4})
        ]

    async def get_code_system(self, canonical_url, version):
        return CS if canonical_url == ICD10CM_URL and version in (None, "2027") else None

    async def search_by_code_prefix(self, cs_id, prefix, billable_only, limit, offset):
        self.calls.append(("code", prefix, billable_only))
        if not prefix.startswith("K35"):
            return 0, []
        return 1, [K3530]

    async def text_candidates(
        self, cs_id, q, pool, include_index_terms, match="all", index_length_penalty=False
    ):
        self.calls.append(("text", q, include_index_terms))
        self.text_flags = (match, index_length_penalty)
        if q == "variola":
            return [(13, 0.9, "Variola")]
        return [(11, 1.2345678, None)]

    async def semantic_candidates(self, cs_id, model, vector, pool, include_index_terms):
        self.calls.append(("semantic", model, include_index_terms))
        # Semantic ranks the MI code first; text ranked K35.30 first. The
        # category K35.3 is matched through an index term.
        return [(12, 0.81, None), (11, 0.52, None), (10, 0.50, "Appendicitis localized")]

    async def load_concepts(self, ids):
        return {i: CONCEPTS[i] for i in ids if i in CONCEPTS}

    async def billable_descendants(self, cs_id, codes):
        return {c: [K3530] if c == "K35.3" else [] for c in codes}

    async def get_concept(self, cs_id, code):
        return (K3530, [], [K353]) if code == "K35.30" else None


@pytest.fixture
async def client():
    fake = FakeRepository()
    embedder = FakeEmbeddingClient()
    with (
        app.container.terminology.terminology_repository.override(providers.Object(fake)),
        app.container.core.embedding_client.override(providers.Object(embedder)),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            c.fake = fake
            c.embedder = embedder
            yield c


async def test_code_shaped_query_uses_prefix_search(client):
    r = await client.get("/api/v1/terminology/search", params={"q": "k353"})
    assert r.status_code == 200
    body = r.json()
    assert body["match_type"] == "code"
    assert body["version"] == "2027"
    assert body["data"][0]["code"] == "K35.30"
    assert body["data"][0]["score"] is None
    assert client.fake.calls == [("code", "K35.3", False)]


async def test_text_query_uses_text_search(client):
    r = await client.get(
        "/api/v1/terminology/search",
        params={"q": "  appendicitis localized ", "mode": "text", "billable_only": "true"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["match_type"] == "text"
    assert body["query"] == "appendicitis localized"
    assert body["data"][0]["score"] == 1.2346
    assert body["data"][0]["matched_on"] is None
    assert client.fake.calls == [("text", "appendicitis localized", True)]
    assert client.embedder.queries == []


async def test_text_search_flags_come_from_config(client):
    await client.get("/api/v1/terminology/search", params={"q": "fever", "mode": "text"})
    # configs/config.yaml defaults (Report 03): all-words matching, length penalty on.
    assert client.fake.text_flags == ("all", True)


async def test_index_term_match_is_reported(client):
    r = await client.get("/api/v1/terminology/search", params={"q": "variola", "mode": "text"})
    hit = r.json()["data"][0]
    assert (hit["code"], hit["matched_on"]) == ("B03", "Variola")


async def test_default_mode_is_hybrid(client):
    r = await client.get("/api/v1/terminology/search", params={"q": "appendicitis"})
    assert r.status_code == 200
    assert r.json()["match_type"] == "hybrid"
    assert [c[0] for c in client.fake.calls] == ["text", "semantic"]


async def test_semantic_mode_embeds_query_and_returns_similarity(client):
    r = await client.get("/api/v1/terminology/search", params={"q": "heart attack", "mode": "semantic"})
    assert r.status_code == 200
    body = r.json()
    assert body["match_type"] == "semantic"
    assert body["total"] is None
    # Without billable_only the matched category K35.3 is returned as-is.
    assert [h["code"] for h in body["data"]] == ["I21.9", "K35.30", "K35.3"]
    assert body["data"][0]["score"] == 0.81
    assert client.embedder.queries == ["heart attack"]
    assert client.fake.calls == [("semantic", "fake-embed", True)]


async def test_billable_only_expands_matched_category(client):
    r = await client.get(
        "/api/v1/terminology/search",
        params={"q": "heart attack", "mode": "semantic", "billable_only": "true"},
    )
    codes = [h["code"] for h in r.json()["data"]]
    # K35.3 is replaced by its billable descendant K35.30, already present with
    # a better score of its own — so it appears once.
    assert codes == ["I21.9", "K35.30"]


async def test_hybrid_mode_fuses_both_rankings(client):
    r = await client.get("/api/v1/terminology/search", params={"q": "appendicitis", "mode": "hybrid"})
    assert r.status_code == 200
    body = r.json()
    assert body["match_type"] == "hybrid"
    by_code = {h["code"]: h for h in body["data"]}
    # K35.30: text rank 1 + semantic rank 2 beats I21.9: semantic rank 1 only.
    assert [h["code"] for h in body["data"]][:2] == ["K35.30", "I21.9"]
    assert by_code["K35.30"]["text_rank"] == 1 and by_code["K35.30"]["semantic_rank"] == 2
    assert by_code["I21.9"]["text_rank"] is None and by_code["I21.9"]["semantic_rank"] == 1
    w = settings.search.hybrid_text_weight
    assert by_code["K35.30"]["score"] == round(w / 61 + 1 / 62, 5)


async def test_code_shaped_abbreviation_with_no_code_falls_back_to_search(client):
    # "T2DM" is code-shaped (T2D.M) but no such code exists.
    r = await client.get("/api/v1/terminology/search", params={"q": "T2DM", "mode": "text"})
    assert r.status_code == 200
    assert r.json()["match_type"] == "text"
    assert client.fake.calls == [("code", "T2D.M", False), ("text", "T2DM", True)]


async def test_code_shaped_query_ignores_mode(client):
    r = await client.get("/api/v1/terminology/search", params={"q": "K35.3", "mode": "semantic"})
    assert r.json()["match_type"] == "code"
    assert client.embedder.queries == []


async def test_code_systems_reports_embedding_coverage(client):
    body = (await client.get("/api/v1/terminology/code-systems")).json()
    assert body["data"][0]["concept_count"] == 2
    assert body["data"][0]["embedded_count"] == 1
    assert body["data"][0]["index_term_count"] == 5
    assert body["data"][0]["index_terms_embedded"] == 4
    assert body["data"][0]["embedding_model"] == "fake-embed"


async def test_concept_detail_accepts_undotted_code(client):
    r = await client.get("/api/v1/terminology/concepts/K3530")
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == "K35.30"
    assert body["parent"]["code"] == "K35.3"
    assert body["notes"] == {"excludes1": ["something (X00)"]}
    assert body["inherited_notes"] == [
        {
            "code": "K35.3",
            "display": "Acute appendicitis with localized peritonitis",
            "notes": {"excludes1": ["acute appendicitis with generalized peritonitis (K35.2-)"]},
        }
    ]


async def test_unknown_code_is_404(client):
    r = await client.get("/api/v1/terminology/concepts/Z99.999")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "NOT_FOUND"


async def test_unloaded_version_is_404(client):
    r = await client.get("/api/v1/terminology/search", params={"q": "fever", "version": "2019"})
    assert r.status_code == 404
    assert "not loaded" in r.json()["error"]["message"]


async def test_empty_query_is_422(client):
    r = await client.get("/api/v1/terminology/search", params={"q": ""})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"
