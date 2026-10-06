"""Build the search-evaluation datasets from the official ICD-10-CM release.

Gold labels come from the ICD-10-CM Alphabetic Index (the coder's lookup book
published by CDC/NCHS), not from us — each index path such as

    Appendicitis > with > gangrene > with localized peritonitis  ->  K35.31

becomes a query ("Appendicitis with gangrene with localized peritonitis")
with that gold code. Term text is built by the same parser the index loader
uses (app/terminology/import_/loaders/icd10cm_index.py).

Hold-out: search also loads index terms, so evaluating on them would test
lookup, not search. The primary sets are drawn ONLY from the held-out share
(terminology.index_holdout_percent) that the loader never loads.
index_terms_seen.jsonl is drawn from the loaded share on purpose — the gap
between it and index_terms.jsonl shows how much testing on loaded text
would inflate the numbers.

Hand-written sets (lay terms, abbreviations, note-style sentences) come from
eval/handwritten.py.

Run (from backend/):
  uv run python -m eval.build_datasets
"""

import bisect
import json
import random
import re
import zipfile
from collections import defaultdict
from pathlib import Path

from app.core.config import settings
from app.terminology.import_.loaders.icd10cm import parse_order_file
from app.terminology.import_.loaders.icd10cm_index import is_holdout, parse_index_xml
from eval import handwritten

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
OUT_DIR = Path(__file__).resolve().parent / "datasets"
ORDER_ZIP = DATA_DIR / "icd10cm-code-descriptions-2027.zip"
INDEX_ZIP = DATA_DIR / "icd10cm-table-and-index-2027.zip"

SEED = 20260926
PER_DEPTH_BUCKET = 200  # held-out sample: 200 each for depth 0, 1, 2+ -> 600
SEEN_N = 200  # sample from the loaded share, for the contamination contrast
PERTURB_N = 150
DEV_N = 300  # held-out tuning split, disjoint from the test sample

_STOP = {
    "a", "an", "and", "as", "at", "by", "for", "from", "in", "of", "on", "or",
    "the", "to", "with", "without", "due", "nos", "nec", "other", "unspecified",
}
_WORD = re.compile(r"[a-z0-9]+")


def content_words(text: str) -> list[str]:
    return [w for w in _WORD.findall(text.lower()) if w not in _STOP]


def lexical_overlap(query: str, target: str) -> float:
    """Share of the query's content words that appear in the target text."""
    q = content_words(query)
    if not q:
        return 0.0
    t = set(content_words(target))
    return sum(w in t for w in q) / len(q)


def overlap_bucket(overlap: float) -> str:
    if overlap >= 0.67:
        return "high"
    if overlap >= 0.34:
        return "partial"
    return "low"


def typo(query: str, rng: random.Random) -> str | None:
    words = query.split()
    candidates = [i for i, w in enumerate(words) if len(w) >= 5 and w.isalpha()]
    if not candidates:
        return None
    i = rng.choice(candidates)
    w = words[i]
    j = rng.randrange(1, len(w) - 1)
    op = rng.choice(["delete", "swap", "substitute"])
    if op == "delete":
        w = w[:j] + w[j + 1 :]
    elif op == "swap":
        w = w[: j - 1] + w[j] + w[j - 1] + w[j + 1 :]
    else:
        w = w[:j] + rng.choice("abcdefghijklmnopqrstuvwxyz") + w[j + 1 :]
    words[i] = w
    return " ".join(words)


def shuffled(query: str, rng: random.Random) -> str | None:
    words = [w for w in query.split() if w.lower() not in {"with", "without", "and", "of", "in", "due", "to"}]
    if len(words) < 3:
        return None
    for _ in range(10):
        out = words[:]
        rng.shuffle(out)
        if out != words:
            return " ".join(out)
    return None


def _write(name: str, rows: list[dict], note: str = "") -> None:
    with open(OUT_DIR / name, "w", encoding="utf-8") as f:
        f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
    print(f"{name:26} {len(rows):5} queries {note}")


def main() -> None:
    rng = random.Random(SEED)
    holdout_pct = settings.terminology.index_holdout_percent
    if holdout_pct <= 0:
        raise SystemExit(
            "terminology.index_holdout_percent is 0 — every index term is loaded, "
            "so there is nothing clean to evaluate on. Set it > 0 (prototype: 20)."
        )

    with zipfile.ZipFile(ORDER_ZIP) as zf:
        name = next(n for n in zf.namelist() if re.search(r"icd10cm-order-\d{4}\.txt$", n))
        records = parse_order_file(zf.read(name).decode("utf-8-sig"))
    display = {r.code: r.display for r in records}
    billable = sorted(r.code for r in records if r.is_billable)

    def has_billable(prefix: str) -> bool:
        i = bisect.bisect_left(billable, prefix)
        return i < len(billable) and billable[i].startswith(prefix)

    with zipfile.ZipFile(INDEX_ZIP) as zf:
        name = next(n for n in zf.namelist() if re.search(r"icd10cm-index-\d{4}\.xml$", n))
        _, entries = parse_index_xml(zf.read(name))

    # Direct index entries only (a code printed on the path itself); drop terms
    # the index maps to more than one code.
    by_term: dict[str, set[str]] = defaultdict(set)
    depth_of: dict[str, int] = {}
    for e in entries:
        if e.via_see or len(e.term) < 4:
            continue
        by_term[e.term].add(e.code)
        depth_of.setdefault(e.term, e.depth)

    pools: dict[bool, dict[str, list[dict]]] = {True: defaultdict(list), False: defaultdict(list)}
    for term, codes in by_term.items():
        if len(codes) != 1:
            continue
        code = next(iter(codes))
        if not has_billable(code) or code not in display:
            continue
        depth = depth_of[term]
        overlap = lexical_overlap(term, display[code])
        bucket = "0" if depth == 0 else "1" if depth == 1 else "2+"
        pools[is_holdout(term, holdout_pct)][bucket].append(
            {
                "query": term,
                "gold": [code],
                "meta": {
                    "depth": bucket,
                    "chapter": code[0],
                    "overlap": round(overlap, 2),
                    "overlap_bucket": overlap_bucket(overlap),
                    "gold_display": display[code],
                },
            }
        )

    held_out = pools[True]
    sample: list[dict] = []
    for bucket in ("0", "1", "2+"):
        items = sorted(held_out[bucket], key=lambda r: r["query"])
        sample.extend(rng.sample(items, min(PER_DEPTH_BUCKET, len(items))))
    for i, rec in enumerate(sample, 1):
        rec["id"] = f"idx-{i:04d}"
        rec["source"] = f"ICD-10-CM FY2027 Alphabetic Index — held out ({holdout_pct}%), not loaded into search"

    seen_items = sorted((r for b in pools[False].values() for r in b), key=lambda r: r["query"])
    seen = rng.sample(seen_items, min(SEEN_N, len(seen_items)))
    for i, rec in enumerate(seen, 1):
        rec["id"] = f"seen-{i:04d}"
        rec["source"] = "ICD-10-CM FY2027 Alphabetic Index — LOADED into search (contamination contrast)"

    typos, shuffles = [], []
    for rec in rng.sample(sample, len(sample)):
        if len(typos) < PERTURB_N and (q := typo(rec["query"], rng)):
            typos.append({**rec, "id": rec["id"] + "-typo", "query": q, "meta": {**rec["meta"], "original": rec["query"]}})
        if len(shuffles) < PERTURB_N and (q := shuffled(rec["query"], rng)):
            shuffles.append({**rec, "id": rec["id"] + "-shuf", "query": q, "meta": {**rec["meta"], "original": rec["query"]}})

    # Dev split for tuning (e.g. fusion weights) — held out like the test set,
    # disjoint from it. Drawn last so adding it left every earlier sample, and
    # therefore every test set, unchanged.
    test_queries = {r["query"] for r in sample}
    dev_pool = sorted(
        (r for b in held_out.values() for r in b if r["query"] not in test_queries),
        key=lambda r: r["query"],
    )
    dev = [dict(r) for r in rng.sample(dev_pool, min(DEV_N, len(dev_pool)))]
    for i, rec in enumerate(dev, 1):
        rec["id"] = f"dev-{i:04d}"
        rec["source"] = "ICD-10-CM FY2027 Alphabetic Index — held out; DEV split (tuning only)"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    n_held = sum(len(v) for v in held_out.values())
    n_seen = len(seen_items)
    _write("index_terms.jsonl", sample, f"(held out; from {n_held:,} eligible)")
    _write("index_typos.jsonl", typos, "(held out)")
    _write("index_shuffled.jsonl", shuffles, "(held out)")
    _write("index_terms_seen.jsonl", seen, f"(LOADED; from {n_seen:,} eligible)")
    _write("index_dev.jsonl", dev, "(held out; DEV — for tuning, never reported as a result)")

    # Hand-written queries that happen to BE a loaded index term (e.g.
    # "lockjaw") are answered by lookup — flag them so results can be split.
    def _norm(t: str) -> str:
        return " ".join(t.lower().replace(",", " ").split())

    loaded_terms = {_norm(e.term) for e in entries if not is_holdout(e.term, holdout_pct)}

    # Hand-written sets — validate every gold prefix against the code set so
    # a typo in a label can't silently make a query unanswerable.
    for set_name, items in handwritten.SETS.items():
        rows = []
        for i, (query, golds) in enumerate(items, 1):
            for g in golds:
                if not has_billable(g):
                    raise SystemExit(f"{set_name}: gold {g!r} for {query!r} matches no billable code")
            rows.append(
                {
                    "id": f"{set_name}-{i:03d}",
                    "query": query,
                    "gold": golds,
                    "source": "hand-written",
                    "meta": {
                        "labeled_by": handwritten.LABELED_BY,
                        "is_loaded_index_term": _norm(query) in loaded_terms,
                    },
                }
            )
        n_hit = sum(r["meta"]["is_loaded_index_term"] for r in rows)
        _write(f"{set_name}.jsonl", rows, f"(hand-labeled; {n_hit} are verbatim loaded index terms)")


if __name__ == "__main__":
    main()
