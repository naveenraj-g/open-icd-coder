"""Search evaluation harness — runs every dataset query through each search
mode, under one or more pipeline configurations, and measures how highly the
gold code ranks.

Configurations (ablation) — see CONFIGS:
  baseline          concept text only, no variant collapsing (= Report 01 system)
  index             + Alphabetic Index terms
  index_collapse    + 7th-character variant collapsing          (= Report 02 system)
  r4a               + index-term length penalty
  r4ab              + any-word text matching
  r4abc             + weighted fusion (weight 0.4, tuned for "any")
  r4a_fb            r4a + any-word only as a fallback
  r4a_fb_c          + weighted fusion (hybrid_text_weight)      (= current default)
Default run: all of the above from index_collapse on.

Calls TerminologyService in-process with billable_only=True and limit=100 —
the realistic Stage 1 setting, where the decision layer later chooses among
the top 50-100 candidates. A hit counts as correct if its code or any of its
collapsed variants starts with a gold prefix.

Metrics per config x dataset x mode:
  R@k      share of queries whose gold code is in the top k (k = 1, 5, 10, 50, 100)
  Fam@10   share whose gold *category* (first 3 chars) is in the top 10
  MRR      mean of 1/rank of the gold code (0 when not in the top 100)
  p50/p95  per-query latency in ms (includes query embedding for semantic/hybrid)

Writes:
  ../docs/report/data/search_eval_results.json   summary + per-query ranks
  ../docs/report/search-eval-results.md          generated tables

Run (from backend/, with LM Studio's server up):
  uv run python -m eval.run_search_eval                      # all configs
  uv run python -m eval.run_search_eval --configs index_collapse --limit-per-set 5
"""

import argparse
import asyncio
import json
import statistics
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings
from app.di.container import Container
from app.services.terminology_service import TerminologyService
from app.terminology.icd10cm import ICD10CM_URL

DATASETS_DIR = Path(__file__).resolve().parent / "datasets"
REPORT_DIR = Path(__file__).resolve().parents[2] / "docs" / "report"

DATASETS = [
    ("index_terms", "Index terms (held out)"),
    ("index_typos", "Held-out + 1 typo"),
    ("index_shuffled", "Held-out, words shuffled"),
    ("lay_terms", "Lay terms ⚠"),
    ("abbreviations", "Abbreviations ⚠"),
    ("note_sentences", "Note sentences ⚠"),
    ("index_terms_seen", "Index terms (LOADED — contrast only)"),
]
CONFIGS = {
    # Report 02 systems
    "baseline": {"use_index_terms": False, "collapse_variants": False,
                 "text_match": "all", "index_length_penalty": False, "hybrid_text_weight": 1.0},
    "index": {"use_index_terms": True, "collapse_variants": False,
              "text_match": "all", "index_length_penalty": False, "hybrid_text_weight": 1.0},
    "index_collapse": {"use_index_terms": True, "collapse_variants": True,
                       "text_match": "all", "index_length_penalty": False, "hybrid_text_weight": 1.0},
    # Report 03 ranking fixes, added one at a time on top of index_collapse
    "r4a": {"use_index_terms": True, "collapse_variants": True,
            "text_match": "all", "index_length_penalty": True, "hybrid_text_weight": 1.0},
    "r4ab": {"use_index_terms": True, "collapse_variants": True,
             "text_match": "any", "index_length_penalty": True, "hybrid_text_weight": 1.0},
    "r4abc": {"use_index_terms": True, "collapse_variants": True,
              "text_match": "any", "index_length_penalty": True, "hybrid_text_weight": 0.4},
    # Report 03 revision: any-word only as a fallback, weight re-tuned for it
    "r4a_fb": {"use_index_terms": True, "collapse_variants": True,
               "text_match": "fallback", "index_length_penalty": True, "hybrid_text_weight": 1.0},
    "r4a_fb_c": {"use_index_terms": True, "collapse_variants": True,
                 "text_match": "fallback", "index_length_penalty": True,
                 "hybrid_text_weight": settings.search.hybrid_text_weight},
}
CONFIG_LABELS = {
    "baseline": "baseline",
    "index": "+index",
    "index_collapse": "+index +collapse",
    "r4a": "+R4a",
    "r4ab": "+R4a+b",
    "r4abc": "+R4a+b+c",
    "r4a_fb": "+R4a+fallback",
    "r4a_fb_c": "+R4a+fallback+c",
}
DEFAULT_CONFIGS = ["index_collapse", "r4a", "r4ab", "r4abc", "r4a_fb", "r4a_fb_c"]
MODES = ["text", "semantic", "hybrid"]
KS = [1, 5, 10, 50, 100]
LIMIT = 100


def load(name: str) -> list[dict]:
    with open(DATASETS_DIR / f"{name}.jsonl", encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def first_rank(hits: list[list[str]], prefixes: list[str]) -> int | None:
    """hits: per result, [code, *variants]."""
    p = tuple(prefixes)
    return next((i for i, codes in enumerate(hits, 1) if any(c.startswith(p) for c in codes)), None)


def summarise(rows: list[dict]) -> dict:
    n = len(rows)
    ranks = [r["rank"] for r in rows]
    lat = sorted(r["latency_ms"] for r in rows)
    return {
        "n": n,
        **{f"R@{k}": sum(1 for x in ranks if x and x <= k) / n for k in KS},
        "Fam@10": sum(1 for r in rows if r["family_rank"] and r["family_rank"] <= 10) / n,
        "MRR": sum(1 / x for x in ranks if x) / n,
        "p50_ms": statistics.median(lat),
        "p95_ms": lat[min(n - 1, int(round(0.95 * (n - 1))))],
    }


def build_summary(per_query: list[dict]) -> dict:
    grouped: dict[tuple, list[dict]] = defaultdict(list)
    for r in per_query:
        grouped[(r["config"], r["dataset"], r["mode"])].append(r)
        meta = r["meta"]
        if r["dataset"] == "index_terms":
            grouped[(r["config"], f"index_terms · overlap={meta['overlap_bucket']}", r["mode"])].append(r)
            grouped[(r["config"], f"index_terms · depth={meta['depth']}", r["mode"])].append(r)
        if "is_loaded_index_term" in meta:
            side = "verbatim index term" if meta["is_loaded_index_term"] else "not an index term"
            grouped[(r["config"], f"{r['dataset']} · {side}", r["mode"])].append(r)
    return {f"{c} | {d} | {m}": summarise(rows) for (c, d, m), rows in grouped.items()}


async def coverage(service: TerminologyService) -> dict:
    systems = await service.list_code_systems()
    cs = next(s for s in systems.data if s.canonical_url == ICD10CM_URL)
    return cs.model_dump(include={"version", "concept_count", "embedded_count", "index_term_count", "index_terms_embedded"})


async def evaluate(config_names: list[str], limit_per_set: int | None) -> dict:
    container = Container()
    repo = container.terminology.terminology_repository()
    embedder = container.core.embedding_client()
    per_query: list[dict] = []

    try:
        cov = await coverage(TerminologyService(repo, embedder))
        print(f"Coverage: {cov}")
        if any(CONFIGS[c]["use_index_terms"] for c in config_names):
            if not cov["index_term_count"]:
                raise SystemExit("Index terms not loaded — run `just terminology-index` first.")
            if cov["index_terms_embedded"] < cov["index_term_count"]:
                print(
                    f"WARNING: only {cov['index_terms_embedded']:,}/{cov['index_term_count']:,} "
                    "index terms embedded — semantic results will under-report."
                )

        for config in config_names:
            service = TerminologyService(
                repo, embedder, candidate_pool=settings.search.candidate_pool, **CONFIGS[config]
            )
            print(f"\n[{config}] {CONFIGS[config]}")
            for name, _ in DATASETS:
                items = load(name)[:limit_per_set] if limit_per_set else load(name)
                t_set = time.monotonic()
                for item in items:
                    for mode in MODES:
                        t0 = time.perf_counter()
                        res = await service.search(
                            q=item["query"],
                            system=ICD10CM_URL,
                            version=None,
                            mode=mode,
                            billable_only=True,
                            limit=LIMIT,
                            offset=0,
                        )
                        ms = (time.perf_counter() - t0) * 1000
                        hits = [[h.code, *h.variants] for h in res.data]
                        per_query.append(
                            {
                                "config": config,
                                "dataset": name,
                                "id": item["id"],
                                "query": item["query"],
                                "gold": item["gold"],
                                "mode": mode,
                                "match_type": res.match_type,
                                "rank": first_rank(hits, item["gold"]),
                                "family_rank": first_rank(hits, [g[:3] for g in item["gold"]]),
                                "latency_ms": round(ms, 1),
                                "top3": [h.code for h in res.data[:3]],
                                "top1_matched_on": res.data[0].matched_on if res.data else None,
                                "meta": item.get("meta", {}),
                            }
                        )
                print(f"  {name:18} {len(items):4} queries  ({time.monotonic() - t_set:.0f}s)", flush=True)
    finally:
        await embedder.close()
        await container.core.database().disconnect()

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "embedding_model": embedder.model,
        "coverage": cov,
        "settings": {
            "billable_only": True,
            "limit": LIMIT,
            "candidate_pool": settings.search.candidate_pool,
            "index_holdout_percent": settings.terminology.index_holdout_percent,
            "hybrid": "RRF k=60",
            "configs": {c: CONFIGS[c] for c in config_names},
        },
        "summary": build_summary(per_query),
        "per_query": per_query,
    }


# ── Markdown ──────────────────────────────────────────────────────────────────


def _pct(x: float) -> str:
    return f"{x * 100:.0f}%"


def _config_comparison(summary: dict, configs: list[str], datasets: list[tuple[str, str]]) -> list[str]:
    """Hybrid mode only: each config side by side on R@10 and R@100."""
    head = " | ".join(f"{CONFIG_LABELS[c]} R@10 | {CONFIG_LABELS[c]} R@100" for c in configs)
    lines = [f"| Dataset | n | {head} |", "|---|---|" + "---|" * (2 * len(configs))]
    for key, label in datasets:
        cells, n = [], None
        for c in configs:
            s = summary.get(f"{c} | {key} | hybrid")
            if not s:
                cells += ["–", "–"]
                continue
            n = s["n"]
            cells += [_pct(s["R@10"]), _pct(s["R@100"])]
        if n is not None:
            lines.append(f"| {label} | {n} | " + " | ".join(cells) + " |")
    return lines


def _full_table(summary: dict, config: str, datasets: list[tuple[str, str]]) -> list[str]:
    lines = [
        "| Dataset | n | Mode | R@1 | R@5 | R@10 | R@50 | R@100 | Fam@10 | MRR | p50 ms | p95 ms |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for key, label in datasets:
        present = [m for m in MODES if f"{config} | {key} | {m}" in summary]
        if not present:
            continue
        best = max(summary[f"{config} | {key} | {m}"]["R@10"] for m in present)
        for mode in present:
            s = summary[f"{config} | {key} | {mode}"]
            r10 = _pct(s["R@10"])
            r10 = f"**{r10}**" if s["R@10"] == best else r10
            lines.append(
                f"| {label} | {s['n']} | {mode} | {_pct(s['R@1'])} | {_pct(s['R@5'])} | {r10} | "
                f"{_pct(s['R@50'])} | {_pct(s['R@100'])} | {_pct(s['Fam@10'])} | {s['MRR']:.2f} | "
                f"{s['p50_ms']:.0f} | {s['p95_ms']:.0f} |"
            )
    return lines


SLICES = [
    ("index_terms · overlap=high", "Held-out · high word overlap"),
    ("index_terms · overlap=partial", "Held-out · partial overlap"),
    ("index_terms · overlap=low", "Held-out · low overlap"),
    ("index_terms · depth=0", "Held-out · main term only"),
    ("index_terms · depth=1", "Held-out · 1 sub-term"),
    ("index_terms · depth=2+", "Held-out · 2+ sub-terms"),
    ("lay_terms · verbatim index term", "Lay · verbatim index term ⚠"),
    ("lay_terms · not an index term", "Lay · not an index term ⚠"),
]


def write_markdown(results: dict, path: Path) -> None:
    s = results["summary"]
    configs = list(results["settings"]["configs"])
    cov = results["coverage"]
    lines = [
        "# Search evaluation — generated results",
        "",
        f"_Generated {results['generated_at']} by `backend/eval/run_search_eval.py`. "
        "Do not edit by hand — re-run the script._",
        "",
        f"- Embedding model: `{results['embedding_model']}`",
        f"- Coverage: {cov['concept_count']:,} concepts ({cov['embedded_count']:,} embedded) · "
        f"{cov['index_term_count']:,} index terms ({cov['index_terms_embedded']:,} embedded) · "
        f"{results['settings']['index_holdout_percent']}% of index terms held out",
        f"- Settings: billable_only=true, limit={LIMIT}, candidate pool "
        f"{results['settings']['candidate_pool']} per source, hybrid = RRF k=60",
        "- R@k: gold code (or a collapsed variant of it) in top k · Fam@10: gold 3-char "
        "category in top 10 · MRR: mean reciprocal rank · latency includes query embedding",
        "- ⚠ = hand-labeled by the author, pending clinical review",
        "",
        "## Configurations compared (hybrid mode)",
        "",
        *_config_comparison(s, configs, DATASETS),
        "",
        *_config_comparison(s, configs, SLICES),
        "",
    ]
    for c in configs:
        lines += [
            f"## Full results — {CONFIG_LABELS[c]}",
            "",
            f"`{results['settings']['configs'][c]}` · **Bold** = best R@10 for that dataset",
            "",
            *_full_table(s, c, DATASETS),
            "",
            *_full_table(s, c, SLICES),
            "",
        ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--configs", default=",".join(DEFAULT_CONFIGS), help=f"Comma-separated subset of {list(CONFIGS)}")
    p.add_argument("--limit-per-set", type=int, help="Only the first N queries of each dataset (smoke test)")
    p.add_argument(
        "--append",
        action="store_true",
        help="Keep other configs' rows from the existing results file and add these (re-runs replace)",
    )
    args = p.parse_args()
    configs = [c.strip() for c in args.configs.split(",") if c.strip()]
    unknown = [c for c in configs if c not in CONFIGS]
    if unknown:
        raise SystemExit(f"Unknown config(s): {unknown}")

    t0 = time.monotonic()
    results = asyncio.run(evaluate(configs, args.limit_per_set))

    (REPORT_DIR / "data").mkdir(parents=True, exist_ok=True)
    json_path = REPORT_DIR / "data" / "search_eval_results.json"
    md_path = REPORT_DIR / "search-eval-results.md"
    if args.append and json_path.exists():
        previous = json.loads(json_path.read_text(encoding="utf-8"))
        kept = [r for r in previous["per_query"] if r["config"] not in configs]
        kept_configs = {c: v for c, v in previous["settings"]["configs"].items() if c not in configs}
        results["per_query"] = kept + results["per_query"]
        results["settings"]["configs"] = {**kept_configs, **results["settings"]["configs"]}
        results["summary"] = build_summary(results["per_query"])
    json_path.write_text(json.dumps(results, indent=1, ensure_ascii=False), encoding="utf-8")
    write_markdown(results, md_path)
    print(f"\nWrote {md_path}\nWrote {json_path}\nTotal {time.monotonic() - t0:.0f}s")


if __name__ == "__main__":
    main()
