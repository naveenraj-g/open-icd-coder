"""ICD-10-CM Alphabetic Index — parsing, cross-reference resolution and the
evaluation hold-out split.

The index is the coder's lookup book: every path of titles from a main term
down through its sub-terms names a condition, and most paths end in a code.

    Appendicitis > with > gangrene > with localized peritonitis  ->  K35.31

Each path becomes one searchable term, "Appendicitis with gangrene with
localized peritonitis", linked to its code. Paths that carry no code but a
"see" cross-reference are resolved to the code of the path they point at:

    Attack > heart   (see: Infarct, myocardium)   ->  I21.9

This module is shared by the index loader and eval/build_datasets.py so both
build term text the same way — the hold-out split depends on that.
"""

import hashlib
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass

from app.terminology.icd10cm import ICD10CM_URL
from app.terminology.import_.base import BaseLoader

_INDEX_MEMBER = re.compile(r"icd10cm-index-(\d{4})\.xml$", re.IGNORECASE)
# Cap on variant combinations per path — titles rarely list more than 3.
_MAX_ALIASES = 32


@dataclass(frozen=True)
class IndexEntry:
    term: str  # search text, e.g. "Appendicitis with gangrene"
    path: tuple[str, ...]  # ("Appendicitis", "with", "gangrene")
    code: str  # dotted code or category prefix, e.g. "K35.891", "S72.9"
    depth: int  # 0 = main term, 1 = first sub-term, ...
    via_see: bool  # resolved through a "see" cross-reference


def code_prefix(code: str) -> str:
    """'S72.9-' -> 'S72.9', 'A30.-' -> 'A30', 'K35.31' -> 'K35.31'.
    A trailing dash means "more characters required" — the code names a
    category, and any code beneath it is a valid completion."""
    return code.strip().rstrip("-").rstrip(".")


def title_text(title: ET.Element) -> str:
    """Title text without <nemod> (nonessential modifiers in parentheses) and
    without the NOS / NEC abbreviations."""
    parts = [title.text or ""]
    for child in title:
        parts.append(child.tail or "")
    text = " ".join("".join(parts).split())
    text = re.sub(r"\b(NOS|NEC)\b", "", text)
    return " ".join(text.replace(" ,", ",").split()).strip(" ,-")


def _norm(text: str) -> str:
    return " ".join(text.lower().replace(",", " ").split())


def parse_index_xml(data: bytes) -> tuple[str | None, list[IndexEntry]]:
    """Returns (release version, entries). Entries with codes come first;
    "see" cross-references are resolved against them afterwards."""
    root = ET.fromstring(data)
    version = (root.findtext("version") or "").strip() or None

    direct: list[IndexEntry] = []
    see_refs: list[tuple[tuple[str, ...], int, str]] = []
    code_by_path: dict[str, str] = {}

    def walk(
        node: ET.Element, path: tuple[str, ...], depth: int, aliases: list[tuple[str, ...]]
    ) -> None:
        title = node.find("title")
        text = title_text(title) if title is not None else ""
        here = (*path, text) if text else path
        if text:
            # Titles list word variants — "Infarct, infarction",
            # "myocardium, myocardial" — and cross-references use any one of
            # them ("see Infarct, myocardium"), so every combination is a key.
            variants = [text, *(v.strip() for v in text.split(",") if v.strip())]
            aliases = [(*a, v) for a in (aliases or [()]) for v in variants][:_MAX_ALIASES]
        code = node.findtext("code")
        see = node.findtext("see")
        if here:
            if code:
                prefix = code_prefix(code)
                direct.append(IndexEntry(" ".join(here), here, prefix, depth, False))
                for alias in aliases:
                    code_by_path.setdefault(_norm(" ".join(alias)), prefix)
            elif see:
                see_refs.append((here, depth, see))
        for child in node.findall("term"):
            walk(child, here, depth + 1, aliases)

    for letter in root.findall("letter"):
        for main in letter.findall("mainTerm"):
            walk(main, (), 0, [])

    resolved: list[IndexEntry] = []
    for here, depth, target in see_refs:
        # "Infarct, myocardium" names the path Infarct > myocardium. Targets
        # like "condition" or "Disease, by site" name no single path — skip.
        code = code_by_path.get(_norm(target))
        if code:
            resolved.append(IndexEntry(" ".join(here), here, code, depth, True))

    return version, direct + resolved


# ── Evaluation hold-out ───────────────────────────────────────────────────────


def is_holdout(term: str, percent: int) -> bool:
    """Deterministic split on the term text: the same term is always on the
    same side, across runs and machines. Held-out terms are never loaded into
    search, so evaluation queries drawn from them measure generalisation
    rather than lookup of text search already contains."""
    if percent <= 0:
        return False
    digest = hashlib.sha1(_norm(term).encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") % 100 < percent


# ── Loader ────────────────────────────────────────────────────────────────────


class Icd10cmIndexLoader(BaseLoader):
    """Loads Alphabetic Index terms into terminology_index_term for an
    already-loaded ICD-10-CM release, skipping the evaluation hold-out.

    Run:
      just terminology-index
    """

    source_name = "icd10cm-index"

    async def load(self, index_path: str, version: str | None, holdout_percent: int) -> None:
        # Imported here to avoid a cycle: icd10cm.py is the code-set loader.
        from app.terminology.import_.loaders.icd10cm import _read_member

        t0 = time.monotonic()
        member, raw = _read_member(index_path, _INDEX_MEMBER)
        self._log(f"Reading {member}")
        xml_version, entries = parse_index_xml(raw)
        direct = sum(not e.via_see for e in entries)
        self._log(f"{len(entries):,} index terms parsed ({direct:,} with codes, {len(entries) - direct:,} via 'see')")

        version = version or xml_version
        cs = await self.conn.fetchrow(
            """
            SELECT id, version FROM terminology_code_system
             WHERE canonical_url = $1 AND ($2::text IS NULL OR version = $2) AND active
             ORDER BY version DESC LIMIT 1
            """,
            ICD10CM_URL, version,
        )
        if cs is None:
            raise ValueError(f"ICD-10-CM {version or ''} is not loaded — run `just terminology-icd10cm` first")
        if xml_version and xml_version != cs["version"]:
            raise ValueError(f"Release mismatch: index is {xml_version}, loaded code set is {cs['version']}")

        ids = await self.fetch_concept_id_map(cs["id"])
        held_out = unknown = 0
        rows: set[tuple[int, str, int, bool]] = set()
        for e in entries:
            if is_holdout(e.term, holdout_percent):
                held_out += 1
                continue
            concept_id = ids.get(e.code)
            if concept_id is None:
                unknown += 1
                continue
            rows.add((concept_id, e.term, e.depth, e.via_see))
        self._log(
            f"Held out {held_out:,} terms for evaluation ({holdout_percent}%) · "
            f"{unknown} with codes not in the code set · {len(rows):,} to load"
        )

        async with self.conn.transaction():
            status = await self.conn.execute(
                "DELETE FROM terminology_index_term WHERE code_system_id = $1", cs["id"]
            )
            if (removed := int(status.split()[-1])):
                self._log(f"Removed {removed:,} index terms from a previous load")

            # (term, concept) is unique; a term reached both directly and via
            # "see" keeps the direct entry.
            best: dict[tuple[int, str], tuple[int, bool]] = {}
            for concept_id, term, depth, via_see in rows:
                key = (concept_id, term)
                if key not in best or (best[key][1] and not via_see):
                    best[key] = (depth, via_see)
            await self.conn.copy_records_to_table(
                "terminology_index_term",
                records=[
                    (cs["id"], concept_id, term, depth, via_see)
                    for (concept_id, term), (depth, via_see) in sorted(best.items())
                ],
                columns=["code_system_id", "concept_id", "term", "depth", "via_see"],
            )
            await self.conn.execute(
                """
                UPDATE terminology_index_term
                   SET search_vector = to_tsvector('english', term)
                 WHERE code_system_id = $1
                """,
                cs["id"],
            )
            self._log(f"Inserted {len(best):,} index terms with search vectors")

        await self.conn.execute("ANALYZE terminology_index_term")
        self._log(f"Done in {time.monotonic() - t0:.1f}s")
