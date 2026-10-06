"""ICD-10-CM loader — official CDC/NCHS release files, no account required.

Download (FY2027 shown; effective 2026-10-01):
  https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Publications/ICD10CM/2027/
    icd10cm-code-descriptions-2027.zip   (required — codes, billable flag, descriptions)
    icd10cm-table-and-index-2027.zip     (optional — inclusion terms + instructional notes)

Either the zip or the extracted file can be passed; zips are read in place.

1. Order file (icd10cm-order-YYYY.txt) — fixed width, one row per code:
     cols 1-5   order number
     cols 7-13  code, no dot (e.g. K3530)
     col  15    0 = category header (not billable), 1 = billable code
     cols 17-76 short description
     cols 78-   long description
   Includes the non-billable headers, which gives us the hierarchy.

2. Tabular XML (icd10cm-tabular-YYYY.xml) — per-code inclusion terms become
   synonyms (searchable); excludes / code-first / use-additional-code /
   7th-character notes are kept on the concept as JSON.

Run:
  just terminology-icd10cm
"""

import json
import re
import time
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from app.terminology.icd10cm import ICD10CM_URL, to_dotted
from app.terminology.import_.base import BaseLoader

_ORDER_MEMBER = re.compile(r"icd10cm-order-(\d{4})\.txt$", re.IGNORECASE)
_TABULAR_MEMBER = re.compile(r"icd10cm-tabular.*\.xml$", re.IGNORECASE)

# Tabular XML child tag -> key in TerminologyConcept.notes
_NOTE_TAGS = {
    "excludes1": "excludes1",
    "excludes2": "excludes2",
    "codeFirst": "code_first",
    "codeAlso": "code_also",
    "useAdditionalCode": "use_additional_code",
    "notes": "notes",
    "sevenChrNote": "seventh_character_note",
}
# Tabular XML child tags whose notes are alternate names for the code.
_SYNONYM_TAGS = {"inclusionTerm", "includes"}


@dataclass
class OrderRecord:
    sort_order: int
    code: str  # dotted, e.g. "K35.30"
    is_billable: bool
    short_display: str
    display: str


@dataclass
class TabularEntry:
    synonyms: list[str] = field(default_factory=list)
    notes: dict[str, list[str]] = field(default_factory=dict)


# ── Parsing (pure functions — unit-tested without a database) ─────────────────


def parse_order_line(line: str) -> OrderRecord | None:
    line = line.rstrip("\r\n")
    if len(line) < 17 or not line[:5].strip().isdigit():
        return None
    code = line[6:13].strip()
    if not code:
        return None
    short_display = line[16:76].strip()
    display = line[77:].strip() or short_display
    return OrderRecord(
        sort_order=int(line[:5]),
        code=to_dotted(code),
        is_billable=line[14] == "1",
        short_display=short_display,
        display=display,
    )


def parse_order_file(text: str) -> list[OrderRecord]:
    return [r for r in map(parse_order_line, text.splitlines()) if r is not None]


def derive_parent_code(code: str, known: set[str]) -> str | None:
    """Nearest existing ancestor by prefix: K35.30 -> K35.3 -> K35.
    Handles 7th-character placeholders too: S01.00XA -> S01.00 (no S01.00X)."""
    compact = code.replace(".", "")
    for end in range(len(compact) - 1, 2, -1):
        candidate = to_dotted(compact[:end])
        if candidate in known:
            return candidate
    return None


def _note_texts(el: ET.Element) -> list[str]:
    return [n.text.strip() for n in el.findall("note") if n.text and n.text.strip()]


def parse_tabular_xml(data: bytes) -> tuple[str | None, dict[str, TabularEntry]]:
    """Returns (release version, {dotted_code: TabularEntry}). Only a diag's
    direct children are read, so a category's notes aren't copied onto every
    descendant."""
    root = ET.fromstring(data)
    version = (root.findtext("version") or "").strip() or None
    entries: dict[str, TabularEntry] = {}

    for diag in root.iter("diag"):
        name = (diag.findtext("name") or "").strip()
        if not name:
            continue
        entry = TabularEntry()
        for child in diag:
            if child.tag in _SYNONYM_TAGS:
                entry.synonyms.extend(_note_texts(child))
            elif child.tag in _NOTE_TAGS:
                texts = _note_texts(child)
                if texts:
                    entry.notes.setdefault(_NOTE_TAGS[child.tag], []).extend(texts)
            elif child.tag == "sevenChrDef":
                exts = [
                    f"{ext.get('char')}: {ext.text.strip()}"
                    for ext in child.findall("extension")
                    if ext.text
                ]
                if exts:
                    entry.notes["seventh_character"] = exts
        if entry.synonyms or entry.notes:
            entries[to_dotted(name)] = entry

    return version, entries


def _read_member(path: str, pattern: re.Pattern[str]) -> tuple[str, bytes]:
    """Returns (member_name, bytes) from a zip, or (file_name, bytes) for a plain file."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(path)
    if zipfile.is_zipfile(p):
        with zipfile.ZipFile(p) as zf:
            matches = [n for n in zf.namelist() if pattern.search(n)]
            if not matches:
                raise FileNotFoundError(f"No file matching {pattern.pattern} inside {path}")
            return matches[0], zf.read(matches[0])
    return p.name, p.read_bytes()


# ── Loader ────────────────────────────────────────────────────────────────────


class Icd10cmLoader(BaseLoader):
    source_name = "icd10cm"

    async def load(
        self,
        order_path: str,
        tabular_path: str | None = None,
        version: str | None = None,
    ) -> None:
        t0 = time.monotonic()

        member, raw = _read_member(order_path, _ORDER_MEMBER)
        self._log(f"Reading {member}")
        records = parse_order_file(raw.decode("utf-8-sig"))
        billable = sum(r.is_billable for r in records)
        self._log(f"{len(records):,} codes parsed ({billable:,} billable, {len(records) - billable:,} headers)")

        file_version = m.group(1) if (m := _ORDER_MEMBER.search(member)) else None

        tabular: dict[str, TabularEntry] = {}
        if tabular_path:
            t_member, t_raw = _read_member(tabular_path, _TABULAR_MEMBER)
            self._log(f"Reading {t_member}")
            xml_version, tabular = parse_tabular_xml(t_raw)
            if file_version and xml_version and xml_version != file_version:
                raise ValueError(
                    f"Release mismatch: order file is {file_version}, tabular XML is {xml_version}"
                )
            file_version = file_version or xml_version
            n_syn = sum(len(e.synonyms) for e in tabular.values())
            self._log(f"{len(tabular):,} codes with tabular notes, {n_syn:,} inclusion terms")

        version = version or file_version
        if not version:
            raise ValueError("Could not detect the release year — pass --version")

        known = {r.code for r in records}
        missing = [c for c in tabular if c not in known]
        if missing:
            self._log(f"WARNING: {len(missing)} tabular codes not in order file (ignored), e.g. {missing[:5]}")

        async with self.conn.transaction():
            cs_id = await self.upsert_code_system(
                canonical_url=ICD10CM_URL,
                version=version,
                name="ICD-10-CM",
                title="International Classification of Diseases, 10th Revision, Clinical Modification",
                publisher="National Center for Health Statistics (NCHS)",
            )
            self._log(f"CodeSystem ICD-10-CM {version} id={cs_id}")

            removed = await self.clear_concepts(cs_id)
            if removed:
                self._log(f"Removed {removed:,} concepts from a previous load of this release")

            await self.conn.copy_records_to_table(
                "terminology_concept",
                records=[
                    (
                        cs_id,
                        r.code,
                        r.display,
                        r.short_display,
                        r.is_billable,
                        r.sort_order,
                        _notes_json(tabular.get(r.code)),
                    )
                    for r in records
                ],
                columns=[
                    "code_system_id",
                    "code",
                    "display",
                    "short_display",
                    "is_billable",
                    "sort_order",
                    "notes",
                ],
            )
            self._log(f"Inserted {len(records):,} concepts")

            ids = await self.fetch_concept_id_map(cs_id)

            pairs = [
                (ids[r.code], ids[parent])
                for r in records
                if (parent := derive_parent_code(r.code, known)) is not None
            ]
            await self.set_parents(pairs)
            self._log(f"Linked {len(pairs):,} parent → child relationships")

            synonyms = sorted(
                {
                    (ids[code], syn)
                    for code, entry in tabular.items()
                    if code in ids
                    for syn in entry.synonyms
                }
            )
            await self.conn.copy_records_to_table(
                "terminology_concept_synonym",
                records=synonyms,
                columns=["concept_id", "synonym"],
            )
            self._log(f"Inserted {len(synonyms):,} synonyms")

            await self.build_search_vectors(cs_id)
            self._log("Built full-text search vectors")

        await self.conn.execute("ANALYZE terminology_concept")
        await self.conn.execute("ANALYZE terminology_concept_synonym")
        self._log(f"Done in {time.monotonic() - t0:.1f}s")


def _notes_json(entry: TabularEntry | None) -> str | None:
    if entry is None or not entry.notes:
        return None
    return json.dumps(entry.notes)
