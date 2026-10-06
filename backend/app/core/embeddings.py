"""Client for any OpenAI-compatible /embeddings endpoint (LM Studio locally)."""

import asyncio

import httpx

from app.core.config import EmbeddingConfig
from app.core.logging import get_logger
from app.errors.base import ApplicationError

logger = get_logger(__name__)


class EmbeddingUnavailableError(ApplicationError):
    def __init__(self, message: str, cause: Exception | None = None):
        super().__init__(
            name="EmbeddingUnavailableError",
            message=message,
            status_code=503,
            code="EMBEDDING_UNAVAILABLE",
            cause=cause,
        )


class EmbeddingClient:
    def __init__(self, config: EmbeddingConfig, api_key: str | None = None):
        self.config = config
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._http = httpx.AsyncClient(
            base_url=config.base_url.rstrip("/"),
            headers=headers,
            timeout=config.timeout_seconds,
        )

    @property
    def model(self) -> str:
        return self.config.model

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed texts to be searched (code descriptions) — no instruction."""
        return await self._embed(texts)

    async def embed_query(self, query: str) -> list[float]:
        """Embed a search query, with the model's retrieval instruction."""
        return (await self._embed([self.config.query_instruction + query]))[0]

    async def _embed(self, texts: list[str]) -> list[list[float]]:
        # LM Studio occasionally answers 400/5xx while it loads or swaps
        # models; a short backoff rides that out instead of failing a long job.
        attempts = self.config.max_retries + 1
        for attempt in range(1, attempts + 1):
            try:
                r = await self._http.post(
                    "/embeddings", json={"model": self.config.model, "input": texts}
                )
                r.raise_for_status()
                break
            except httpx.HTTPError as exc:
                if attempt < attempts:
                    logger.warning(
                        "Embedding request failed, retrying",
                        extra={
                            "event": "embedding.retry",
                            "attempt": attempt,
                            "error": str(exc)[:200],
                        },
                    )
                    await asyncio.sleep(self.config.retry_backoff_seconds * attempt)
                    continue
                raise EmbeddingUnavailableError(
                    f"Embedding service unavailable at {self.config.base_url} "
                    f"(model {self.config.model}) after {attempts} attempts. "
                    "Is LM Studio's server running with that model?",
                    cause=exc,
                ) from exc

        data = sorted(r.json()["data"], key=lambda d: d["index"])
        vectors = [d["embedding"] for d in data]
        if len(vectors) != len(texts):
            raise EmbeddingUnavailableError(
                f"Embedding service returned {len(vectors)} vectors for {len(texts)} inputs"
            )
        if vectors and len(vectors[0]) != self.config.dimensions:
            raise EmbeddingUnavailableError(
                f"Model {self.config.model} returned {len(vectors[0])}-dim vectors; "
                f"embedding.dimensions is {self.config.dimensions}"
            )
        return vectors

    async def close(self) -> None:
        await self._http.aclose()
