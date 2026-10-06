"""EmbeddingClient against a mocked OpenAI-compatible endpoint."""

import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5433/test")

import httpx
import pytest

from app.core.config import EmbeddingConfig
from app.core.embeddings import EmbeddingClient, EmbeddingUnavailableError


def _client(handler, **overrides) -> EmbeddingClient:
    config = EmbeddingConfig(dimensions=3, retry_backoff_seconds=0, **overrides)
    client = EmbeddingClient(config)
    client._http = httpx.AsyncClient(
        base_url="http://embed.test/v1", transport=httpx.MockTransport(handler)
    )
    return client


def _ok(request: httpx.Request) -> httpx.Response:
    inputs = __import__("json").loads(request.content)["input"]
    # Deliberately out of order — the client must sort by index.
    data = [{"index": i, "embedding": [float(i), 0.0, 1.0]} for i in range(len(inputs))][::-1]
    return httpx.Response(200, json={"data": data})


async def test_query_gets_instruction_and_documents_do_not():
    seen: list[list[str]] = []

    def handler(request):
        seen.append(__import__("json").loads(request.content)["input"])
        return _ok(request)

    client = _client(handler, query_instruction="Q: ")
    vectors = await client.embed_documents(["a", "b"])
    await client.embed_query("heart attack")
    assert vectors == [[0.0, 0.0, 1.0], [1.0, 0.0, 1.0]]
    assert seen == [["a", "b"], ["Q: heart attack"]]


async def test_transient_errors_are_retried():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(400, text="model loading") if calls["n"] <= 2 else _ok(request)

    client = _client(handler, max_retries=3)
    assert await client.embed_documents(["a"]) == [[0.0, 0.0, 1.0]]
    assert calls["n"] == 3


async def test_gives_up_after_max_retries():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(503)

    client = _client(handler, max_retries=2)
    with pytest.raises(EmbeddingUnavailableError):
        await client.embed_documents(["a"])
    assert calls["n"] == 3


async def test_wrong_dimension_is_rejected():
    client = _client(lambda r: httpx.Response(200, json={"data": [{"index": 0, "embedding": [1.0, 2.0]}]}))
    with pytest.raises(EmbeddingUnavailableError, match="2-dim"):
        await client.embed_documents(["a"])
