"""JevEngine against a mocked AI Gateway /v1/evaluate endpoint — request
shape and response handling follow the documented evaluation API."""

import json
import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5433/test")

import httpx
import pytest

from app.coding.engines.base import EngineCandidate
from app.coding.engines.jev import NOTA_OPTION, JevEngine, JevError
from app.core.config import JevConfig

CANDS = [
    EngineCandidate(11, "K35.30", "Acute appendicitis with localized peritonitis, without perforation or gangrene", 1),
    EngineCandidate(12, "K35.31", "Acute appendicitis with localized peritonitis and gangrene, without perforation", 2),
    EngineCandidate(13, "K35.80", "Unspecified acute appendicitis", 3),
]
NOTE = "Acute inflammation of the appendix with localized peritonitis."


def ok_response(probabilities: dict, choice: str = "K35.30") -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "model": "typesafe-ai/jev",
            "answers": {"icd10cm": {"type": "choice", "choice": choice, "probabilities": probabilities}},
            "usage": {"inputTokens": 512, "outputTokens": 20},
            "providerMetadata": {"gateway": {"cost": "0.0000215", "generationId": "gen_abc"}},
        },
    )


def engine(handler, api_key="test-key", route="vercel", **cfg) -> JevEngine:
    e = JevEngine(JevConfig(retry_backoff_seconds=0, **cfg), route, api_key)
    e._http = httpx.AsyncClient(base_url="https://gw.test/v1", transport=httpx.MockTransport(handler))
    return e


async def test_request_shape_and_probability_mapping():
    seen = {}

    def handler(request: httpx.Request):
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["authorization"]
        seen["body"] = json.loads(request.content)
        return ok_response({"K35.30": 0.94, "K35.31": 0.03, "K35.80": 0.02, NOTA_OPTION: 0.01})

    result = await engine(handler).score(NOTE, "acute appendicitis, localized peritonitis", CANDS)

    body = seen["body"]
    assert seen["url"] == "https://gw.test/v1/evaluate"
    assert seen["auth"] == "Bearer test-key"
    assert body["model"] == "typesafe-ai/jev"
    assert body["state"] == {"soap_note": NOTE, "condition_to_code": "acute appendicitis, localized peritonitis"}
    q = body["questions"]["icd10cm"]
    assert q["type"] == "choice"
    assert list(q["criteria"]) == ["K35.30", "K35.31", "K35.80", NOTA_OPTION]
    assert q["criteria"]["K35.80"] == "Unspecified acute appendicitis"
    assert "providerOptions" not in body

    assert result.probabilities == {11: 0.94, 12: 0.03, 13: 0.02}
    assert result.nota_probability == 0.01
    assert result.cost == pytest.approx(0.0000215)
    assert result.model == "typesafe-ai/jev"
    assert result.raw_response["choice"] == "K35.30"
    assert result.raw_response["generation_id"] == "gen_abc"
    assert result.raw_response["options_offered"] == 4
    assert result.raw_response["route"] == "vercel"


async def test_opencode_route_shape_confidence_and_computed_cost():
    seen = {}

    def handler(request: httpx.Request):
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content)
        # Shape observed from OpenCode Zen: confidence, snake_case usage, no cost.
        return httpx.Response(
            200,
            json={
                "model": "jev-1.13",
                "answers": {"icd10cm": {"type": "choice", "choice": "K35.30", "confidence": 0.97,
                                        "probabilities": {"K35.30": 0.98, "K35.31": 0, "NONE_OF_THE_ABOVE": 0.02}}},
                "usage": {"input_tokens": 1_000_000, "output_tokens": 73},
            },
        )

    e = engine(handler, route="opencode")
    assert e.name == "jev-opencode"
    result = await e.score(NOTE, "x", CANDS)
    assert seen["url"] == "https://gw.test/v1/systemone"
    assert seen["body"]["model"] == "jev-1.13"
    assert result.probabilities == {11: 0.98, 12: 0.0}
    assert result.nota_probability == 0.02
    assert result.raw_response["confidence"] == 0.97
    assert result.cost == pytest.approx(0.042)  # 1M input tokens at $0.042/M


async def test_free_tier_cost_is_zero():
    free = httpx.Response(200, json={"model": "jev-1.13-free", "usage": {"input_tokens": 500},
                                     "answers": {"icd10cm": {"type": "choice", "probabilities": {"K35.30": 1.0}}}})
    result = await engine(lambda r: free, route="opencode").score(NOTE, "x", CANDS)
    assert result.cost == 0.0


async def test_zdr_option_only_sent_on_routes_that_support_it():
    seen = {}

    def handler(request):
        seen["body"] = json.loads(request.content)
        return ok_response({"K35.30": 1.0})

    await engine(handler, route="opencode", zero_data_retention=True).score(NOTE, "x", CANDS)
    assert "providerOptions" not in seen["body"]


def test_unknown_route_is_rejected():
    with pytest.raises(ValueError, match="Unknown Jev route"):
        JevEngine(JevConfig(), "nope", "k")


async def test_options_not_offered_are_ignored():
    result = await engine(lambda r: ok_response({"K35.30": 0.5, "Z99.99": 0.5})).score(NOTE, "x", CANDS)
    assert result.probabilities == {11: 0.5}


async def test_zero_data_retention_and_no_nota_options():
    seen = {}

    def handler(request):
        seen["body"] = json.loads(request.content)
        return ok_response({"K35.30": 1.0})

    await engine(handler, zero_data_retention=True, include_none_of_the_above=False).score(NOTE, "x", CANDS)
    assert seen["body"]["providerOptions"] == {"gateway": {"zeroDataRetention": True}}
    assert NOTA_OPTION not in seen["body"]["questions"]["icd10cm"]["criteria"]


async def test_missing_api_key_fails_before_calling():
    calls = []
    e = engine(lambda r: calls.append(r) or ok_response({}), api_key=None)
    with pytest.raises(JevError, match="AI_GATEWAY_API_KEY is not set"):
        await e.score(NOTE, "x", CANDS)
    assert calls == []


async def test_account_errors_are_not_retried_and_message_is_surfaced():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(
            403,
            json={"error": {"message": "AI Gateway requires a valid credit card on file", "type": "customer_verification_required"}},
        )

    with pytest.raises(JevError, match=r"\(vercel\) HTTP 403: AI Gateway requires a valid credit card on file \(customer_verification_required\)"):
        await engine(handler, max_retries=3).score(NOTE, "x", CANDS)
    assert calls["n"] == 1


async def test_rate_limits_and_server_errors_are_retried():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429, json={"error": {"message": "slow down"}})
        if calls["n"] == 2:
            return httpx.Response(503, text="unavailable")
        return ok_response({"K35.30": 0.9, "K35.31": 0.1})

    result = await engine(handler, max_retries=2).score(NOTE, "x", CANDS)
    assert calls["n"] == 3
    assert result.probabilities[11] == 0.9


async def test_response_without_probabilities_is_an_error():
    bad = httpx.Response(200, json={"answers": {"icd10cm": {"type": "choice", "choice": "K35.30"}}})
    with pytest.raises(JevError, match="no probabilities"):
        await engine(lambda r: bad).score(NOTE, "x", CANDS)
