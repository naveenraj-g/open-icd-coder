"""Jev (TypeSafe AI) decision engine — one connector, two routes:

  opencode  POST https://opencode.ai/zen/v1/systemone   (TypeSafe-native; model jev-1.13)
  vercel    POST https://ai-gateway.vercel.sh/v1/evaluate (model typesafe-ai/jev)

Both take the same request:
  {
    "model": ...,
    "state": {"soap_note": ..., "condition_to_code": ...},
    "questions": {"icd10cm": {"type": "choice", "instructions": ...,
                              "criteria": {"K35.30": "<description>", ...,
                                           "NONE_OF_THE_ABOVE": "..."}}}
  }
and answer with a probability for every option:
  {"answers": {"icd10cm": {"type": "choice", "choice": "K35.30",
                           "confidence": 0.97,                 # opencode
                           "probabilities": {"K35.30": 0.98, ...}}},
   "usage": {"input_tokens" | "inputTokens": ...},
   "providerMetadata": {"gateway": {"cost": "..."}}}           # vercel

The candidate codes ARE the answer options, so Jev can only return a code
that search supplied — the closed-set guarantee.

Docs: https://opencode.ai/docs/zen/ ·
      https://vercel.com/docs/ai-gateway/modalities/evaluation
"""

import asyncio

import httpx

from app.coding.engines.base import EngineCandidate, EngineResult
from app.core.config import JevConfig
from app.core.logging import get_logger

logger = get_logger(__name__)

QUESTION_KEY = "icd10cm"
NOTA_OPTION = "NONE_OF_THE_ABOVE"
NOTA_DESCRIPTION = "None of the listed ICD-10-CM codes fits the documented condition"
_RETRYABLE = {408, 409, 425, 429, 500, 502, 503, 504}


class JevError(Exception):
    """Jev call failed — recorded on the decision, the item is flagged."""


class JevEngine:
    def __init__(self, config: JevConfig, route: str, api_key: str | None):
        if route not in config.routes:
            raise ValueError(f"Unknown Jev route {route!r}; configured: {sorted(config.routes)}")
        self.config = config
        self.route_name = route
        self.route = config.routes[route]
        self.api_key = api_key
        self.name = f"jev-{route}"
        self._http = httpx.AsyncClient(base_url=self.route.base_url.rstrip("/"), timeout=config.timeout_seconds)

    def build_request(self, soap_note: str, item_text: str, candidates: list[EngineCandidate]) -> dict:
        criteria = {c.code: c.display for c in candidates}
        if self.config.include_none_of_the_above:
            criteria[NOTA_OPTION] = NOTA_DESCRIPTION
        body: dict = {
            "model": self.route.model,
            "state": {"soap_note": soap_note, "condition_to_code": item_text},
            "questions": {
                QUESTION_KEY: {
                    "type": "choice",
                    "instructions": self.config.instructions,
                    "criteria": criteria,
                }
            },
        }
        if self.config.zero_data_retention and self.route.supports_zdr_option:
            body["providerOptions"] = {"gateway": {"zeroDataRetention": True}}
        return body

    async def score(
        self, soap_note: str, item_text: str, candidates: list[EngineCandidate]
    ) -> EngineResult:
        if not self.api_key:
            raise JevError(f"{self.route.api_key_setting} is not set in backend/.env (Jev route '{self.route_name}')")
        body = self.build_request(soap_note, item_text, candidates)
        data = await self._post(body)

        answer = (data.get("answers") or {}).get(QUESTION_KEY) or {}
        probabilities = answer.get("probabilities")
        if not isinstance(probabilities, dict) or not probabilities:
            raise JevError(f"Jev response has no probabilities for '{QUESTION_KEY}': {str(data)[:300]}")

        by_code = {c.code: c.candidate_id for c in candidates}
        mapped = {by_code[code]: float(p) for code, p in probabilities.items() if code in by_code}
        unknown = sorted(set(probabilities) - set(by_code) - {NOTA_OPTION})
        if unknown:
            logger.warning(
                "Jev returned options that were not offered",
                extra={"event": "jev.unknown_options", "unknown": unknown[:10]},
            )

        usage = data.get("usage") or {}
        gateway = (data.get("providerMetadata") or data.get("provider_metadata") or {}).get("gateway") or {}
        return EngineResult(
            model=data.get("model") or self.route.model,
            probabilities=mapped,
            nota_probability=float(probabilities.get(NOTA_OPTION, 0.0)),
            raw_response={
                "route": self.route_name,
                "choice": answer.get("choice"),
                "confidence": answer.get("confidence"),
                "probabilities": probabilities,
                "usage": usage,
                "generation_id": gateway.get("generationId"),
                "options_offered": len(body["questions"][QUESTION_KEY]["criteria"]),
            },
            cost=self._cost(data.get("model") or self.route.model, gateway, usage),
        )

    def _cost(self, model: str, gateway: dict, usage: dict) -> float | None:
        """Reported cost when the route gives one (Vercel); otherwise input
        tokens x the route's list price. Free-tier models cost nothing."""
        if gateway.get("cost") is not None:
            return float(gateway["cost"])
        if model.endswith("-free"):
            return 0.0
        tokens = usage.get("input_tokens", usage.get("inputTokens"))
        if tokens is None or self.route.input_price_per_million is None:
            return None
        return tokens * self.route.input_price_per_million / 1_000_000

    async def _post(self, body: dict) -> dict:
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        attempts = self.config.max_retries + 1
        for attempt in range(1, attempts + 1):
            try:
                r = await self._http.post(self.route.path, json=body, headers=headers)
            except httpx.TransportError as exc:
                if attempt < attempts:
                    await self._backoff(attempt, str(exc))
                    continue
                raise JevError(f"Jev ({self.route_name}) unreachable after {attempts} attempts: {exc}") from exc

            if r.status_code == 200:
                return r.json()
            if r.status_code in _RETRYABLE and attempt < attempts:
                await self._backoff(attempt, f"HTTP {r.status_code}")
                continue
            raise JevError(f"Jev ({self.route_name}) HTTP {r.status_code}: {_error_message(r)}")
        raise JevError("unreachable")  # pragma: no cover

    async def _backoff(self, attempt: int, reason: str) -> None:
        logger.warning(
            "Jev request failed, retrying",
            extra={"event": "jev.retry", "route": self.route_name, "attempt": attempt, "reason": reason[:200]},
        )
        await asyncio.sleep(self.config.retry_backoff_seconds * attempt)

    async def close(self) -> None:
        await self._http.aclose()


def _error_message(r: httpx.Response) -> str:
    """Errors come as {"error": {"message", "type"}} (gateways) or
    {"message", "error_type"} (TypeSafe). Never includes request data."""
    try:
        d = r.json()
    except ValueError:
        return r.text[:300]
    err = d.get("error") if isinstance(d.get("error"), dict) else d
    msg = err.get("message") or str(d)[:300]
    kind = err.get("type") or err.get("error_type")
    return f"{msg} ({kind})" if kind else msg
