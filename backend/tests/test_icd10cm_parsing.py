"""ICD-10-CM parsing — pure functions, no database needed.

Sample lines are copied verbatim from the FY2027 release files.
"""

import pytest

from app.terminology.icd10cm import is_code_like, to_dotted
from app.terminology.import_.loaders.embeddings import build_embedding_text
from app.terminology.import_.loaders.icd10cm import (
    derive_parent_code,
    parse_order_file,
    parse_order_line,
    parse_tabular_xml,
)

ORDER_SAMPLE = (
    "14218 K35     0 Acute appendicitis                                           Acute appendicitis\n"
    "14228 K353    0 Acute appendicitis with localized peritonitis                Acute appendicitis with localized peritonitis\n"
    "14229 K3530   1 Acute appendicitis with loc peritonitis, w/o perf or gangr   Acute appendicitis with localized peritonitis, without perforation or gangrene\n"
)


def test_parse_order_line_billable():
    r = parse_order_line(ORDER_SAMPLE.splitlines()[2])
    assert r is not None
    assert r.sort_order == 14229
    assert r.code == "K35.30"
    assert r.is_billable is True
    assert r.short_display == "Acute appendicitis with loc peritonitis, w/o perf or gangr"
    assert r.display == "Acute appendicitis with localized peritonitis, without perforation or gangrene"


def test_parse_order_line_header():
    r = parse_order_line(ORDER_SAMPLE.splitlines()[0])
    assert r is not None
    assert r.code == "K35"
    assert r.is_billable is False


def test_parse_order_file_skips_blank_and_junk_lines():
    records = parse_order_file(ORDER_SAMPLE + "\n\nnot a record\n")
    assert [r.code for r in records] == ["K35", "K35.3", "K35.30"]


@pytest.mark.parametrize(
    ("raw", "dotted"),
    [("K35", "K35"), ("K3530", "K35.30"), ("k35.30", "K35.30"), ("S0100XA", "S01.00XA")],
)
def test_to_dotted(raw, dotted):
    assert to_dotted(raw) == dotted


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("K35", True),
        ("k3530", True),
        ("K35.3", True),
        ("K35.", True),
        ("S01.00XA", True),
        ("appendicitis", False),
        ("acute K35", False),
        ("35", False),
    ],
)
def test_is_code_like(query, expected):
    assert is_code_like(query) is expected


def test_derive_parent_code_walks_up_to_nearest_existing_ancestor():
    known = {"K35", "K35.3", "K35.30", "S01", "S01.0", "S01.00", "S01.00XA"}
    assert derive_parent_code("K35.30", known) == "K35.3"
    assert derive_parent_code("K35.3", known) == "K35"
    assert derive_parent_code("K35", known) is None
    # 7th-character code with an "X" placeholder: S01.00X doesn't exist.
    assert derive_parent_code("S01.00XA", known) == "S01.00"


def test_build_embedding_text():
    assert build_embedding_text("Fever, unspecified", []) == "Fever, unspecified"
    assert (
        build_embedding_text(
            "Acute appendicitis with perforation, localized peritonitis, and gangrene, without abscess",
            ["Perforated appendix NOS", "Ruptured appendix (with localized peritonitis) NOS"],
        )
        == "Acute appendicitis with perforation, localized peritonitis, and gangrene, without abscess. "
        "Includes: Perforated appendix NOS; Ruptured appendix (with localized peritonitis) NOS"
    )
    # A synonym identical to the display adds nothing.
    assert build_embedding_text("Cholera", ["cholera"]) == "Cholera"


TABULAR_SAMPLE = b"""<?xml version="1.0" encoding="utf-8"?>
<ICD10CM.tabular>
  <version>2027</version>
  <chapter>
    <diag>
      <name>K35.3</name>
      <desc>Acute appendicitis with localized peritonitis</desc>
      <excludes1><note>acute appendicitis with generalized peritonitis (K35.2-)</note></excludes1>
      <diag>
        <name>K35.30</name>
        <desc>Acute appendicitis with localized peritonitis, without perforation or gangrene</desc>
        <inclusionTerm>
          <note>Acute appendicitis with localized peritonitis NOS</note>
        </inclusionTerm>
      </diag>
    </diag>
    <diag>
      <name>S01.00</name>
      <desc>Unspecified open wound of scalp</desc>
      <sevenChrDef>
        <extension char="A">initial encounter</extension>
        <extension char="D">subsequent encounter</extension>
      </sevenChrDef>
    </diag>
  </chapter>
</ICD10CM.tabular>
"""


def test_parse_tabular_xml():
    version, entries = parse_tabular_xml(TABULAR_SAMPLE)
    assert version == "2027"

    assert entries["K35.30"].synonyms == ["Acute appendicitis with localized peritonitis NOS"]
    assert entries["K35.30"].notes == {}

    # A category's notes stay on the category — not copied to its children.
    assert entries["K35.3"].notes == {
        "excludes1": ["acute appendicitis with generalized peritonitis (K35.2-)"]
    }
    assert entries["K35.3"].synonyms == []

    assert entries["S01.00"].notes["seventh_character"] == [
        "A: initial encounter",
        "D: subsequent encounter",
    ]
