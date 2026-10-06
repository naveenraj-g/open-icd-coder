"""Live smoke test of every Jev route — SYNTHETIC note only.

For each route/model: can the account call Jev, does the answer carry a
probability per option, are 100 candidates + NONE_OF_THE_ABOVE accepted,
latency and cost. The free OpenCode tier may use prompts for training, which
is acceptable here only because the note is synthetic.

Run (from backend/, Postgres + LM Studio up for the candidate search):
  just jev-check
"""

import asyncio
import logging
import time

from app.coding.engines.base import EngineCandidate
from app.coding.engines.jev import JevEngine, JevError
from app.core.config import settings
from app.di.container import Container
from app.terminology.icd10cm import ICD10CM_URL

NOTE = (
    "Patient presents with acute inflammation of the appendix, showing signs of localized "
    "peritonitis. Recommending emergency laparoscopic appendectomy. Prescribed IV antibiotics."
)
CONDITION = "acute appendicitis with localized peritonitis"

# (route, model override or None, label)
TARGETS = [
    ("opencode", None, "OpenCode Zen · jev-1.13 (paid)"),
    ("opencode", "jev-1.13-free", "OpenCode Zen · jev-1.13-free (synthetic data only)"),
    ("vercel", None, "Vercel AI Gateway · typesafe-ai/jev"),
]


def engine_for(route: str, model: str | None) -> JevEngine:
    config = settings.jev
    if model:
        routes = dict(config.routes)
        routes[route] = routes[route].model_copy(update={"model": model})
        config = config.model_copy(update={"routes": routes})
    key = getattr(settings, config.routes[route].api_key_setting)
    return JevEngine(config, route, key)


async def check(label: str, engine: JevEngine, candidates: list[EngineCandidate]) -> bool:
    by_id = {c.candidate_id: c for c in candidates}
    t0 = time.perf_counter()
    try:
        result = await engine.score(NOTE, CONDITION, candidates)
    except JevError as exc:
        print(f"  ✗ {len(candidates):3} candidates: {exc}")
        return False
    ms = (time.perf_counter() - t0) * 1000
    raw = result.raw_response
    cost = f"${result.cost:.7f}" if result.cost is not None else "n/a"
    print(
        f"  ✓ {len(candidates):3} candidates: {ms:5.0f} ms · cost {cost} · "
        f"probabilities for {len(raw['probabilities'])}/{raw['options_offered']} options "
        f"(sum {sum(raw['probabilities'].values()):.3f}) · confidence {raw.get('confidence')} · "
        f"NOTA {result.nota_probability:.3f}"
    )
    for cid, p in sorted(result.probabilities.items(), key=lambda kv: -kv[1])[:3]:
        print(f"      {p:6.3f}  {by_id[cid].code:8} {by_id[cid].display[:70]}")
    return True


async def main() -> None:
    logging.disable(logging.WARNING)
    container = Container()
    terminology = container.terminology.terminology_service()
    _, hits = await terminology.retrieve(CONDITION, ICD10CM_URL, None, 100)
    await terminology.embedding_client.close()
    await container.core.database().disconnect()
    candidates = [EngineCandidate(i, h.concept.code, h.concept.display, i) for i, h in enumerate(hits, 1)]

    for route, model, label in TARGETS:
        print(f"\n{label}")
        engine = engine_for(route, model)
        try:
            if await check(label, engine, candidates[:5]):
                await check(label, engine, candidates)
        finally:
            await engine.close()


if __name__ == "__main__":
    asyncio.run(main())
