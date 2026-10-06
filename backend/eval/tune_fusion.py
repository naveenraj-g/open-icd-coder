"""Tune the hybrid text weight on the DEV split only.

For each dev query the text and semantic rankings are computed once (with
the current text-search settings), then re-fused offline for every candidate
weight — so the grid costs one search pass. Test sets are never touched here;
report results come from run_search_eval.py with the chosen weight.

Selection rule: highest MRR on dev; ties broken toward 1.0 (the untuned
default) so we only move off it when the data says to.

Run (from backend/, with LM Studio's server up):
  uv run python -m eval.tune_fusion
"""

import asyncio
import json
import logging
import time
from pathlib import Path

from app.core.config import settings
from app.di.container import Container
from app.services.search_ranking import fuse
from app.services.terminology_service import TerminologyService
from app.terminology.icd10cm import ICD10CM_URL

DEV = Path(__file__).resolve().parent / "datasets" / "index_dev.jsonl"
OUT = Path(__file__).resolve().parents[2] / "docs" / "report" / "data" / "fusion_tuning.json"
WEIGHTS = [1.5, 1.25, 1.0, 0.85, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.0]
LIMIT = 100


def rank_of(hits, prefixes) -> int | None:
    p = tuple(prefixes)
    for i, h in enumerate(hits[:LIMIT], 1):
        if any(c.startswith(p) for c in (h.concept.code, *h.variants)):
            return i
    return None


def metrics(ranks: list[int | None]) -> dict:
    n = len(ranks)
    return {
        "R@1": sum(1 for r in ranks if r and r <= 1) / n,
        "R@10": sum(1 for r in ranks if r and r <= 10) / n,
        "R@100": sum(1 for r in ranks if r) / n,
        "MRR": sum(1 / r for r in ranks if r) / n,
    }


async def main() -> None:
    logging.disable(logging.CRITICAL)
    items = [json.loads(line) for line in DEV.open(encoding="utf-8")]
    container = Container()
    service = TerminologyService(
        container.terminology.terminology_repository(),
        container.core.embedding_client(),
        use_index_terms=True,
        collapse_variants=True,
        candidate_pool=settings.search.candidate_pool,
        text_match=settings.search.text_match,
        index_length_penalty=True,
    )
    cs = await service._resolve_code_system(ICD10CM_URL, None)

    t0 = time.monotonic()
    pairs = []
    for i, item in enumerate(items, 1):
        vector = await service.embedding_client.embed_query(item["query"])
        text_ranked = await service._ranked(cs, item["query"], "text", None, True)
        sem_ranked = await service._ranked(cs, item["query"], "semantic", vector, True)
        pairs.append((item["gold"], text_ranked, sem_ranked))
        if i % 50 == 0:
            print(f"  {i}/{len(items)} dev queries ({time.monotonic() - t0:.0f}s)", flush=True)

    await service.embedding_client.close()
    await container.core.database().disconnect()

    rows = {
        "text only": metrics([rank_of(t, g) for g, t, _ in pairs]),
        "semantic only": metrics([rank_of(s, g) for g, _, s in pairs]),
    }
    for w in WEIGHTS:
        rows[f"hybrid w_text={w}"] = metrics(
            [rank_of(fuse(t, s, by_stem=True, text_weight=w), g) for g, t, s in pairs]
        )

    print(f"\nDEV split: {len(items)} held-out index terms\n")
    print(f"{'':22} {'R@1':>6} {'R@10':>6} {'R@100':>6} {'MRR':>6}")
    for name, m in rows.items():
        print(f"{name:22} {m['R@1']:6.1%} {m['R@10']:6.1%} {m['R@100']:6.1%} {m['MRR']:6.3f}")

    best = max(WEIGHTS, key=lambda w: (round(rows[f"hybrid w_text={w}"]["MRR"], 3), -abs(w - 1.0)))
    print(f"\nChosen hybrid_text_weight = {best} (max dev MRR, ties -> nearest 1.0)")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"dev_n": len(items), "results": rows, "chosen": best}, indent=1), encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    asyncio.run(main())
