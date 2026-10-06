"""ICD-10-CM code-format helpers shared by the loader and the search service."""

import re

ICD10CM_URL = "http://hl7.org/fhir/sid/icd-10-cm"

# A full or partial ICD-10-CM code as a user might type it: letter, digit,
# alphanumeric, then up to four more characters with an optional dot.
# Matches "K35", "k353", "K35.3", "K35.30", "S01.00XA".
_CODE_LIKE = re.compile(r"^[A-Za-z]\d[0-9A-Za-z](\.?[0-9A-Za-z]{0,4})?$")


def to_dotted(code: str) -> str:
    """"K3530" -> "K35.30". ICD-10-CM always places the dot after the 3rd
    character; 3-character categories have no dot."""
    compact = code.replace(".", "").strip().upper()
    return compact if len(compact) <= 3 else f"{compact[:3]}.{compact[3:]}"


def is_code_like(query: str) -> bool:
    return bool(_CODE_LIKE.match(query.strip()))
