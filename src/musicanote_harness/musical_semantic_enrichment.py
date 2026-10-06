"""Research-only musical semantics sidecars; no classifier or Core mutation.

SOURCE records preserve unaligned analyst prose. BOUND records independently
assert one versioned semantic axis on an immutable score/IR and rational span.
An imported statement is not a per-note fact, a human review, or training data.
The JSONL store is append-only and single-writer; callers provide genuine source,
alignment, model, and review references rather than this module inventing them.
"""

from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
from functools import lru_cache
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from jsonschema import Draft202012Validator


SCHEMA_NAME = "musicanote-musical-semantic-enrichment"
SCHEMA_VERSION = "0.1.0"
VERSION = "musical-semantic-enrichment-0.1.0"
SCHEMA_URI = "https://schemas.musicanote.com/musical-semantic-enrichment/0.1.0"
SCHEMA_PATH = Path(__file__).resolve().parents[2] / "docs" / "harmony" / "schemas" / "musical_semantic_enrichment.schema.json"
VOCABULARY_VERSION = "0.1.0"
AXES = (
    "voice_role", "harmonic_role", "texture", "motif", "form_role",
    "development", "placement", "performance",
)
TERMS = {
    "voice_role": ("melody", "countermelody", "bass", "accompaniment", "inner_voice", "pedal", "drone", "fill", "doubling", "response", "unknown"),
    "harmonic_role": ("chord_tone", "root", "third", "fifth", "seventh", "non_chord_tone", "passing", "neighbor", "double_neighbor", "changing_tone", "suspension", "retardation", "anticipation", "pedal", "structural_bass", "unknown"),
    "texture": ("homophonic", "polyphonic", "monophonic", "arpeggiated", "ostinato", "alberti_bass", "chordal", "heterophonic", "unknown"),
    "motif": ("occurrence", "variant", "fragment", "core", "complete_extent", "statement", "response", "unknown"),
    "form_role": ("opening", "continuation", "transition", "cadential", "closing", "contrast", "return", "unknown"),
    "development": ("repetition", "sequence", "augmentation", "diminution", "inversion", "retrograde", "fragmentation", "liquidation", "variation", "unknown"),
    "placement": ("foreground", "middleground", "background", "register_above", "register_below", "doubled", "distributed", "before", "after", "overlapping", "alternating", "unknown"),
    "performance": ("articulation", "dynamics", "phrasing", "timing", "ornamentation", "unknown"),
}
COVERAGE_STATES = ("not_assessed", "needs_alignment", "pending_review", "covered_partial", "covered")


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def _digest(value: Any) -> str:
    return sha256(_canonical(value).encode("utf-8")).hexdigest()


def record_ref(record: Mapping[str, Any]) -> dict[str, str]:
    """Return the immutable reference used for source, relation, and revision links."""
    validate_record(record)
    return {"record_id": record["record_id"], "record_sha256": record["record_sha256"]}


def _seal(record: dict[str, Any]) -> dict[str, Any]:
    digest = _digest(record)
    record["record_id"] = "mse_" + digest[:24]
    record["record_sha256"] = digest
    validate_record(record)
    return record


def _context(source_context: Mapping[str, Any]) -> dict[str, Any]:
    context = deepcopy(dict(source_context))
    context.setdefault("source_sha256", None)
    context.setdefault("rights", {
        "rights_status": "unknown", "rights_ref": None,
        "training_status": "unknown", "training_ref": None,
    })
    return context


def _provenance(provenance: Mapping[str, Any] | None) -> dict[str, Any]:
    if provenance is not None:
        return deepcopy(dict(provenance))
    return {
        "kind": "imported_source", "actor_id": None,
        "producer": {"name": "musical-semantic-source-intake", "version": SCHEMA_VERSION,
                     "config_sha256": None, "model_ref": None,
                     "schema_ref": {"name": SCHEMA_NAME, "version": SCHEMA_VERSION}},
    }


def _review(review: Mapping[str, Any] | None) -> dict[str, Any]:
    return deepcopy(dict(review)) if review is not None else {
        "status": "unreviewed", "reviewer_id": None, "review_ref": None,
    }


def _base(*, case_id: str, case_sha256: str | None, source_context: Mapping[str, Any],
          axis: str | None, term: str | None, provenance: Mapping[str, Any] | None,
          confidence: float | None, confidence_semantics: str | None,
          human_review: Mapping[str, Any] | None, lineage_id: str, revision: int,
          supersedes: Mapping[str, str] | None, rationale: str | None,
          relations: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "schema_name": SCHEMA_NAME, "schema_version": SCHEMA_VERSION, "schema_uri": SCHEMA_URI,
        "term_dictionary_version": VOCABULARY_VERSION, "case_id": case_id, "case_sha256": case_sha256,
        "lineage_id": lineage_id, "revision": revision,
        "supersedes": deepcopy(dict(supersedes)) if supersedes is not None else None,
        "source_context": _context(source_context),
        "claim": {"axis": axis, "term": term, "rationale": rationale,
                  "relations": deepcopy(list(relations))},
        "provenance": _provenance(provenance), "confidence": confidence,
        "confidence_semantics": confidence_semantics, "human_review": _review(human_review),
        "use_policy": {"research_only": True, "training_eligible": False, "gold_status": "not_established"},
    }


def build_source_claim(*, case_id: str, source_context: Mapping[str, Any],
                       axis: str | None = None, term: str | None = None,
                       provenance: Mapping[str, Any] | None = None,
                       confidence: float | None = None, confidence_semantics: str | None = None,
                       human_review: Mapping[str, Any] | None = None,
                       lineage_id: str | None = None, revision: int = 1,
                       supersedes: Mapping[str, str] | None = None,
                       case_sha256: str | None = None, rationale: str | None = None,
                       relations: Iterable[Mapping[str, Any]] = ()) -> dict[str, Any]:
    """Capture raw prose without alignment or any invented event/score target.

    A nullable axis/term preserves unclassified free prose. Known native tags may
    be routed to an axis without claiming a typed interpretation of the prose.
    """
    context = _context(source_context)
    lineage_id = lineage_id or "msel_" + _digest([case_id, context["source_ref"],
        context["source_revision"], context["location"], axis])[:24]
    record = _base(case_id=case_id, case_sha256=case_sha256, source_context=context,
                   axis=axis, term=term, provenance=provenance, confidence=confidence,
                   confidence_semantics=confidence_semantics, human_review=human_review,
                   lineage_id=lineage_id, revision=revision, supersedes=supersedes,
                   rationale=rationale, relations=relations)
    record.update(record_kind="SOURCE", coverage_state="needs_alignment", binding=None, source_claim_ref=None)
    return _seal(record)


def build_bound_claim(*, source_claim: Mapping[str, Any], binding: Mapping[str, Any],
                      axis: str, term: str, provenance: Mapping[str, Any],
                      confidence: float | None = None, confidence_semantics: str | None = None,
                      human_review: Mapping[str, Any] | None = None,
                      coverage_state: str = "pending_review", lineage_id: str | None = None,
                      revision: int = 1, supersedes: Mapping[str, str] | None = None,
                      rationale: str | None = None,
                      relations: Iterable[Mapping[str, Any]] = ()) -> dict[str, Any]:
    """Create a separate aligned assertion; alignment never upgrades its source.

    ``binding`` includes score_id, score_sha256, ir_sha256, ir_schema_version,
    alignment_ref, target {entity_refs, span}, and harmony_assumption_ref (nullable
    except for harmonic_role). Different assumptions remain different groups.
    A whole-case ``covered`` assertion needs an exact legacy span and human review
    in validate_records/append_record; default candidates remain pending review.
    """
    validate_record(source_claim)
    if source_claim["record_kind"] != "SOURCE":
        raise ValueError("A BOUND claim must refer to an independent SOURCE record")
    bound = deepcopy(dict(binding))
    lineage_id = lineage_id or "msel_" + _digest([source_claim["lineage_id"], bound, axis])[:24]
    record = _base(case_id=source_claim["case_id"], case_sha256=source_claim["case_sha256"],
                   source_context=source_claim["source_context"], axis=axis, term=term,
                   provenance=provenance, confidence=confidence, confidence_semantics=confidence_semantics,
                   human_review=human_review, lineage_id=lineage_id, revision=revision,
                   supersedes=supersedes, rationale=rationale, relations=relations)
    record.update(record_kind="BOUND", coverage_state=coverage_state, binding=bound,
                  source_claim_ref=record_ref(source_claim))
    return _seal(record)


@lru_cache(maxsize=1)
def _validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _span(span: Mapping[str, Any]) -> tuple[Fraction, Fraction]:
    for point in (span["start"], span["end"]):
        if (type(point["numerator"]) is not int or type(point["denominator"]) is not int
                or point["denominator"] <= 0):
            raise ValueError("Time bounds must use integer rational coordinates with positive denominator")
    start = Fraction(span["start"]["numerator"], span["start"]["denominator"])
    end = Fraction(span["end"]["numerator"], span["end"]["denominator"])
    if start < 0 or end <= start:
        raise ValueError("Targets require a nonnegative, nonempty rational [start,end) span")
    return start, end


def validate_record(record: Mapping[str, Any]) -> None:
    """Check schema, typed vocabulary, local invariants, and content integrity."""
    errors = sorted(_validator().iter_errors(record), key=lambda error: str(list(error.path)))
    if errors:
        raise ValueError("Invalid musical semantic record: " + errors[0].message)
    payload = {key: value for key, value in record.items() if key not in {"record_id", "record_sha256"}}
    digest = _digest(payload)
    if record["record_sha256"] != digest or record["record_id"] != "mse_" + digest[:24]:
        raise ValueError("Tampered musical semantic record content/hash")
    axis, term = record["claim"]["axis"], record["claim"]["term"]
    if term is not None and (axis is None or term not in TERMS[axis]):
        raise ValueError("Term is not registered for this independent semantic axis")
    if (record["confidence"] is None) != (record["confidence_semantics"] is None):
        raise ValueError("Numeric confidence needs explicit semantics; missing confidence stays null")
    if record["confidence"] is not None:
        kinds = {"imported_source": {"source_reported"}, "human": {"human_reported"},
                 "rule": {"uncalibrated_score", "calibrated_probability"},
                 "ai": {"uncalibrated_score", "calibrated_probability"}}
        if record["confidence_semantics"] not in kinds[record["provenance"]["kind"]]:
            raise ValueError("Confidence semantics must match source/rule/AI/human provenance")
    review = record["human_review"]
    if review["status"] in {"validated", "rejected"} and not (review["reviewer_id"] and review["review_ref"]):
        raise ValueError("Human validation/rejection needs a separate reviewer and review reference")
    if review["status"] == "unreviewed" and (review["reviewer_id"] is not None or review["review_ref"] is not None):
        raise ValueError("Unreviewed source provenance must not impersonate a reviewer")
    if record["revision"] == 1 and record["supersedes"] is not None:
        raise ValueError("Initial revisions must not supersede another record")
    if record["revision"] > 1 and record["supersedes"] is None:
        raise ValueError("Later revisions require an immutable supersedes link")
    if record["record_kind"] == "BOUND":
        _span(record["binding"]["target"]["span"])
        if axis in {"voice_role", "harmonic_role"} and not record["binding"]["target"]["entity_refs"]:
            raise ValueError("Note/group role claims need explicit event references")
        if axis == "harmonic_role" and record["binding"]["harmony_assumption_ref"] is None:
            raise ValueError("Harmonic roles require an explicit immutable harmony assumption")
        if record["coverage_state"] in {"covered_partial", "covered"} and review["status"] != "validated":
            raise ValueError("Covered states require separate validated human review")
    rights = record["source_context"]["rights"]
    context = record["source_context"]
    if context["source_revision"].startswith("sha256:") and context["source_revision"] != "sha256:" + str(context["source_sha256"]):
        raise ValueError("Source revision hash does not match preserved source content hash")
    for prefix in ("rights", "training"):
        if rights[prefix + "_status"] == "inherited" and not rights[prefix + "_ref"]:
            raise ValueError("Inherited policies require a traceable policy reference")
        if rights[prefix + "_status"] == "unknown" and rights[prefix + "_ref"] is not None:
            raise ValueError("Unknown policies cannot claim an inherited policy reference")


def _legacy_hash(value: Any, field: str) -> None:
    if value is not None and (not isinstance(value, str) or len(value) != 64
            or any(character not in "0123456789abcdef" for character in value)):
        raise ValueError("Invalid immutable legacy hash: " + field)


def _legacy_inventory(value: Any, field: str) -> None:
    if (not isinstance(value, list) or any(not isinstance(entity_id, str) or not entity_id.strip()
            for entity_id in value) or len(value) != len(set(value))):
        raise ValueError("Legacy " + field + " must be a list of unique nonempty event IDs")


def _legacy_sources(value: Any) -> None:
    if not isinstance(value, list):
        raise ValueError("Legacy source_refs must be a list of source-reference strings or revision objects")
    seen = set()
    for ref in value:
        if isinstance(ref, str):
            if not ref.strip():
                raise ValueError("Legacy source_refs strings must be nonempty")
            key = (ref, None)
        elif isinstance(ref, Mapping):
            if (not set(ref).issubset({"source_ref", "source_revision", "source_sha256"})
                    or any(not isinstance(ref.get(field), str) or not ref[field].strip()
                           for field in ("source_ref", "source_revision"))):
                raise ValueError("Legacy source_refs revision objects require typed source_ref/source_revision")
            _legacy_hash(ref.get("source_sha256"), "source_refs.source_sha256")
            if (ref["source_revision"].startswith("sha256:") and ref.get("source_sha256") is not None
                    and ref["source_revision"] != "sha256:" + ref["source_sha256"]):
                raise ValueError("Legacy source_refs revision/hash mismatch")
            key = (ref["source_ref"], ref["source_revision"])
        else:
            raise ValueError("Legacy source_refs entries must be strings or typed revision objects")
        if key in seen:
            raise ValueError("Duplicate legacy source_refs entry")
        seen.add(key)


def _case_index(legacy_cases: Iterable[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    result = {}
    for case in legacy_cases:
        if not isinstance(case, Mapping) or not isinstance(case.get("case_id"), str) or not case["case_id"].strip():
            raise ValueError("Legacy descriptors require a nonempty case_id")
        if case["case_id"] in result:
            raise ValueError("Duplicate legacy case_id")
        for field in ("case_sha256", "score_sha256", "ir_sha256"):
            _legacy_hash(case.get(field), field)
        if case.get("source_refs") is not None:
            _legacy_sources(case["source_refs"])
        if case.get("entity_ids") is not None:
            _legacy_inventory(case["entity_ids"], "entity_ids")
        required = case.get("required_entity_ids")
        if required is not None:
            if not isinstance(required, Mapping) or not set(required).issubset(AXES):
                raise ValueError("Legacy required_entity_ids must be an object keyed by registered semantic axes")
            for axis, inventory in required.items():
                _legacy_inventory(inventory, "required_entity_ids." + axis)
                if case.get("entity_ids") is not None and not set(inventory).issubset(case["entity_ids"]):
                    raise ValueError("Legacy required_entity_ids must belong to the independently registered event inventory")
        if case.get("span") is not None:
            _span(case["span"])
        result[case["case_id"]] = case
    return result


def _stale_reason(record: Mapping[str, Any], case: Mapping[str, Any]) -> str | None:
    if case.get("case_sha256") is not None and record["case_sha256"] != case["case_sha256"]:
        return "case_revision_mismatch"
    context = record["source_context"]
    refs = case.get("source_refs", ())
    if refs:
        matches = [ref for ref in refs if (ref if isinstance(ref, str) else ref.get("source_ref")) == context["source_ref"]]
        if not matches:
            return "source_reference_mismatch"
        exact = any(isinstance(ref, str) or (ref.get("source_revision") == context["source_revision"]
                    and (ref.get("source_sha256") is None or ref["source_sha256"] == context["source_sha256"])) for ref in matches)
        if not exact:
            return "source_revision_mismatch"
    if record["record_kind"] == "BOUND":
        binding = record["binding"]
        for field in ("score_id", "score_sha256", "ir_sha256", "ir_schema_version"):
            if case.get(field) is None:
                if field in {"score_sha256", "ir_sha256"}:
                    return "legacy_immutable_binding_not_registered"
            elif binding[field] != case[field]:
                return field + "_mismatch"
        entity_refs = binding["target"]["entity_refs"]
        if entity_refs and case.get("entity_ids") is None:
            return "legacy_event_registry_not_registered"
        if case.get("entity_ids") is not None and not set(entity_refs).issubset(set(case["entity_ids"])):
            return "unregistered_event_reference"
        if case.get("span") is not None:
            start, end = _span(binding["target"]["span"])
            case_start, case_end = _span(case["span"])
            if start < case_start or end > case_end:
                return "target_outside_legacy_case"
    return None


def _complete_reason(record: Mapping[str, Any], case: Mapping[str, Any] | None) -> str | None:
    if case is None or case.get("span") is None:
        return "complete_scope_not_registered"
    if _span(case["span"]) != _span(record["binding"]["target"]["span"]):
        return "complete_scope_mismatch"
    axis = record["claim"]["axis"]
    inventory = (case.get("required_entity_ids") or {}).get(axis, case.get("entity_ids"))
    if inventory is None:
        return "complete_inventory_not_registered"
    if set(inventory) != set(record["binding"]["target"]["entity_refs"]):
        return "complete_inventory_mismatch"
    return None


def validate_records(records: Iterable[Mapping[str, Any]], *,
                     legacy_cases: Iterable[Mapping[str, Any]] = (),
                     require_complete_scope: bool = True) -> None:
    """Validate append order and references, optionally rejecting stale bindings.

    Event membership can be checked only when a descriptor explicitly supplies
    entity_ids. No score parsing or musical accuracy/authentication is performed.
    """
    records = list(records)
    cases = _case_index(legacy_cases)
    seen: dict[str, Mapping[str, Any]] = {}
    tips: dict[str, Mapping[str, Any]] = {}
    for record in records:
        validate_record(record)
        if record["record_id"] in seen:
            raise ValueError("Duplicate record ID in append-only history")
        links = [ref for ref in (record["supersedes"], record["source_claim_ref"]) if ref is not None]
        links += [relation["target_ref"] for relation in record["claim"]["relations"]]
        for ref in links:
            target = seen.get(ref["record_id"])
            if target is None or target["record_sha256"] != ref["record_sha256"]:
                raise ValueError("Missing, forward, or tampered immutable record reference")
        previous = tips.get(record["lineage_id"])
        if previous is None:
            if record["revision"] != 1:
                raise ValueError("Revision history must start at one")
        else:
            if record["supersedes"] != record_ref(previous) or record["revision"] != previous["revision"] + 1:
                raise ValueError("Revision must supersede the current lineage tip exactly once")
            for field in ("case_id", "case_sha256", "record_kind", "source_context", "binding", "source_claim_ref"):
                if record[field] != previous[field]:
                    raise ValueError("Revision cannot retarget immutable case/source/binding; start a new lineage")
            if record["claim"]["axis"] != previous["claim"]["axis"]:
                raise ValueError("Independent axes cannot be merged by superseding another axis")
        if record["record_kind"] == "BOUND":
            source = seen[record["source_claim_ref"]["record_id"]]
            if source["record_kind"] != "SOURCE" or any(source[field] != record[field] for field in ("case_id", "case_sha256", "source_context")):
                raise ValueError("BOUND source revision/context must exactly match its SOURCE claim")
        for relation in record["claim"]["relations"]:
            target = seen[relation["target_ref"]["record_id"]]
            if record["case_id"] != target["case_id"]:
                raise ValueError("Relations cannot silently combine different cases")
            if record["record_kind"] == "BOUND" and target["record_kind"] == "BOUND":
                for field in ("score_sha256", "ir_sha256", "harmony_assumption_ref"):
                    if record["binding"][field] != target["binding"][field]:
                        raise ValueError("Relations cannot pool assertions under changed score/IR/harmony assumptions")
                start, end = _span(record["binding"]["target"]["span"])
                target_start, target_end = _span(target["binding"]["target"]["span"])
                kind = relation["relation_type"]
                if kind == "before" and end > target_start:
                    raise ValueError("Before relation contradicts half-open target chronology")
                if kind == "after" and start < target_end:
                    raise ValueError("After relation contradicts half-open target chronology")
                if kind == "overlaps" and max(start, target_start) >= min(end, target_end):
                    raise ValueError("Overlaps relation requires positive rational-span intersection")
        if cases:
            case = cases.get(record["case_id"])
            if case is None:
                raise ValueError("Record case_id is not registered")
            reason = _stale_reason(record, case)
            if reason is not None:
                raise ValueError("Stale or unregistered target: " + reason)
        if record["coverage_state"] == "covered" and require_complete_scope:
            case = cases.get(record["case_id"])
            reason = _complete_reason(record, case)
            if reason is not None:
                raise ValueError("Whole-case covered state needs independently registered scope/inventory: " + reason)
        seen[record["record_id"]] = record
        tips[record["lineage_id"]] = record


def load_records(path: str | Path) -> list[dict[str, Any]]:
    """Read and validate a complete sidecar; absent optional legacy sidecars are empty."""
    path = Path(path)
    if not path.exists():
        return []
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    # Full coverage is case-relative; validate integrity without claiming it here.
    _validate_history_without_complete_scope(records)
    return records


def _validate_history_without_complete_scope(records: list[Mapping[str, Any]]) -> None:
    # A reader may check integrity without independently registered case scope.
    # This never upgrades a record's case-relative coverage in the planner.
    validate_records(records, require_complete_scope=False)


def append_record(path: str | Path, record: Mapping[str, Any], *,
                  legacy_cases: Iterable[Mapping[str, Any]] = ()) -> bool:
    """Append one valid revision. Identical retry is a no-op, never a duplicate row."""
    path = Path(path)
    legacy_cases = list(legacy_cases)
    existing = load_records(path)
    validate_record(record)
    if record["record_kind"] == "BOUND" and not legacy_cases:
        raise ValueError("Appending BOUND claims requires independent registered legacy scope/hashes/events")
    for previous in existing:
        if previous["record_id"] == record["record_id"]:
            if _canonical(previous) != _canonical(record):
                raise ValueError("Duplicate record ID with different content")
            # Retrying against changed registration must not reuse stale status.
            validate_records(existing, legacy_cases=legacy_cases)
            return False
    validate_records([*existing, record], legacy_cases=legacy_cases)
    path.parent.mkdir(parents=True, exist_ok=True)
    separator = "" if not path.exists() or path.stat().st_size == 0 or path.read_bytes().endswith(b"\n") else "\n"
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(separator + _canonical(record) + "\n")
    return True


def plan_coverage(legacy_cases: Iterable[Mapping[str, Any]],
                  records: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Deterministically plan missing axes without modifying legacy descriptors.

    Missing means not assessed/aligned/reviewed completely, never a negative
    musical assertion. Assumption groups are not pooled to manufacture coverage.
    Legacy descriptors need only case_id; artifact/IR references without actual
    immutable score/IR hashes cannot make a BOUND record current.
    """
    cases = _case_index(legacy_cases)
    records = list(records)
    _validate_history_without_complete_scope(records)
    tips = {record["lineage_id"]: record for record in records}
    result = []
    for case_id, case in sorted(cases.items()):
        source_states = {axis: "not_assessed" for axis in AXES}
        groups: dict[str, dict[str, Any]] = {}
        stale = []
        for record in tips.values():
            if record["case_id"] != case_id:
                continue
            reason = _stale_reason(record, case)
            if reason:
                stale.append({"record_id": record["record_id"], "reason": reason})
                continue
            axis = record["claim"]["axis"]
            if axis is None:
                continue
            if record["record_kind"] == "SOURCE":
                source_states[axis] = "needs_alignment"
                continue
            binding = record["binding"]
            key_data = {field: binding[field] for field in ("score_sha256", "ir_sha256", "harmony_assumption_ref")}
            key = _digest(key_data)
            group = groups.setdefault(key, {"group_id": key, **deepcopy(key_data),
                "axis_states": {a: "not_assessed" for a in AXES}, "record_ids": []})
            state = record["coverage_state"]
            if record["human_review"]["status"] == "rejected":
                state = "pending_review"
            if state == "covered":
                reason = _complete_reason(record, case)
                if reason is not None:
                    stale.append({"record_id": record["record_id"], "reason": reason})
                    continue
            rank = {state_name: index for index, state_name in enumerate(COVERAGE_STATES)}
            if rank[state] > rank[group["axis_states"][axis]]:
                group["axis_states"][axis] = state
            group["record_ids"].append(record["record_id"])
        axis_states = dict(source_states)
        for axis in AXES:
            states = [group["axis_states"][axis] for group in groups.values() if group["axis_states"][axis] != "not_assessed"]
            if states:
                # A case-wide summary never pools multiple harmony assumptions.
                axis_states[axis] = states[0] if len(groups) == 1 else (
                    "covered_partial" if any(s in {"covered", "covered_partial"} for s in states) else "pending_review")
        ordered_groups = []
        for _, group in sorted(groups.items()):
            group["record_ids"].sort()
            group["missing_axes"] = [axis for axis in AXES if group["axis_states"][axis] != "covered"]
            ordered_groups.append(group)
        result.append({"case_id": case_id, "axis_states": axis_states,
            "missing_axes": [axis for axis in AXES if axis_states[axis] != "covered"],
            "assumption_groups": ordered_groups, "stale_record_ids": sorted(stale, key=lambda row: row["record_id"]),
            "missing_semantics": "not assessed/aligned/reviewed completely; not negative musical evidence"})
    return result
