"""Conservative cross-corpus taxonomy for imported harmony labels.

This does not rewrite source labels. It exposes comparable facets while
preserving unsupported syntax as modifiers and an explicit parse status.
"""

from __future__ import annotations

import re
from typing import Any


VERSION = "harmony-label-taxonomy-0.1.0"
_FIGURES = ("65", "64", "43", "42", "7", "6", "2")


def _degree_number(roman: str) -> int | None:
    table = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7}
    return table.get(roman.upper())


def classify_harmony_label(raw: str, components: dict[str, Any] | None = None) -> dict[str, Any]:
    components = components or {}
    source = str(raw or "").strip()
    compact = re.sub(r"\s+", "", source)
    if not compact or compact.casefold() in {"@none", "none", "n.c.", "nc"}:
        return {
            "taxonomy_version": VERSION, "parse_status": "no_chord", "family": "no_chord",
            "base_degree": None, "degree_number": None, "mode_case": None, "inversion_figure": None,
            "applied_to": None, "special_type": None, "alteration_prefix": "", "quality_marker": "",
            "continuation": False, "compound_path": [], "unparsed_modifiers": [],
        }

    continuation = compact.endswith("\\")
    compact = compact.rstrip("\\")
    compound_path = compact.split(".") if "." in compact else []
    core = compound_path[-1] if compound_path else compact
    applied_parts = core.split("/", 1)
    head, applied_to = applied_parts[0], applied_parts[1] if len(applied_parts) == 2 else None
    special_raw = str(components.get("special") or "")
    special_match = re.search(r"(Ger|Fr|It)(?:\+?6)?", f"{special_raw}|{head}", re.IGNORECASE)
    special_type = f"{special_match.group(1).title()}6" if special_match else None
    additions = re.findall(r"\([^)]*\)", head)
    head_without_additions = re.sub(r"\([^)]*\)", "", head)
    figure = str(components.get("figbass") or "") or next(
        (item for item in _FIGURES if head_without_additions.endswith(item)), ""
    )
    numeral_source = str(components.get("numeral") or "") or head_without_additions
    if figure and numeral_source.endswith(figure):
        numeral_source = numeral_source[:-len(figure)]
    match = re.search(r"^(?P<alter>[#b]*)(?P<roman>[ivIV]+)(?P<quality>[o%+]*)", numeral_source)
    if special_type:
        degree, alteration, quality, mode_case, parse_status = None, "", "", None, "parsed"
    elif match:
        degree = match.group("roman")
        alteration = match.group("alter")
        quality = match.group("quality")
        mode_case = "upper" if degree.isupper() else "lower"
        parse_status = "parsed" if match.end() == len(numeral_source) else "partial"
    else:
        degree, alteration, quality, mode_case, parse_status = None, "", "", None, "unsupported"
    degree_number = _degree_number(degree) if degree else None

    if special_type:
        family = "predominant_chromatic_augmented_sixth"
    elif alteration == "b" and degree_number == 2:
        family = "predominant_chromatic_neapolitan"
    elif applied_to and degree_number in {5, 7}:
        family = "applied_dominant_leading_tone"
    elif applied_to:
        family = "applied_other"
    elif degree_number == 1:
        family = "tonic"
    elif degree_number in {2, 4}:
        family = "predominant_diatonic"
    elif degree_number == 5 or degree_number == 7 and quality in {"o", "%"}:
        family = "dominant_leading_tone"
    elif degree_number in {3, 6}:
        family = "mediant_submediant"
    else:
        family = "other_or_unresolved"

    consumed = "".join(filter(None, [alteration, degree or "", quality, figure]))
    remaining = head_without_additions
    if consumed and remaining.startswith(consumed):
        remaining = remaining[len(consumed):]
    unparsed = [value for value in [remaining, *additions] if value]
    if compound_path:
        parse_status = "partial"
    return {
        "taxonomy_version": VERSION,
        "parse_status": parse_status,
        "family": family,
        "base_degree": degree,
        "degree_number": degree_number,
        "mode_case": mode_case,
        "inversion_figure": figure or None,
        "applied_to": applied_to,
        "special_type": special_type,
        "alteration_prefix": alteration,
        "quality_marker": quality,
        "continuation": continuation,
        "compound_path": compound_path,
        "unparsed_modifiers": unparsed,
    }
