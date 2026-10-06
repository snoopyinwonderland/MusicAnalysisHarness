"""Frozen source-voice diagnostics, never a voice repair or harmony promotion.

Canonical logical lanes are compared with fresh, conservative rendering-only
note mapping. Missing/ambiguous mappings remain visible. An explicit MusicXML
part+voice identity is NOT proof of an actual contrapuntal voice.
"""
import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path
from time import perf_counter
from xml.etree import ElementTree as ET

from .engraving import musicxml_with_canonical_ids, SOURCE_MAPPING_VERSION
from .harmony_progression_evidence_trial import write

VERSION = "source-locator-voice-audit-0.1.1"
XML_ID = "{http://www.w3.org/XML/1998/namespace}id"
SAME = "same_explicit_source_lane"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _load(path, hashes, expected=None, compressed=False):
    path = Path(path)
    payload = path.read_bytes()
    observed = hashlib.sha256(payload).hexdigest()
    key = str(path.resolve())
    if expected is not None and observed != expected:
        raise ValueError("input_hash_mismatch:" + key)
    if key in hashes and hashes[key] != observed:
        raise ValueError("input_changed_while_loading:" + key)
    hashes[key] = observed
    return json.loads(gzip.decompress(payload) if compressed else payload)


def _freeze_bytes(path, hashes, expected=None):
    key = str(Path(path).resolve())
    observed = digest(path)
    if expected is not None and observed != expected:
        raise ValueError("input_hash_mismatch:" + key)
    if key in hashes and hashes[key] != observed:
        raise ValueError("input_changed_while_loading:" + key)
    hashes[key] = observed


def _code_hashes():
    return {str(p.resolve()): digest(p) for p in sorted(Path(__file__).parent.glob("*.py"))}


def _local(element):
    return element.tag.rsplit("}", 1)[-1]


def _children(element, name):
    return [child for child in element if _local(child) == name]


def _raw_text(element, name):
    nodes = _children(element, name)
    # Element presence is distinct from absent/blank content. Explicit blank
    # voice/staff fields are malformed source data, never usable identities.
    value = ((nodes[0].text or "").strip() or None) if len(nodes) == 1 else None
    return value, len(nodes)


def mapped_note_sources(mapped_xml, ir, matched_note_ids):
    """Read fresh mapped locators; no stale source XPath or list-order fallback.

    Only IDs positively matched by the mapper are usable. Voice is never
    inherited, defaulted, or guessed. Staff absence defaults to MusicXML staff
    1, but empty/duplicate/invalid explicit staff remains unsupported.
    """
    ids = [note["note_id"] for note in ir["note_events"]]
    matched = set(matched_note_ids)
    if len(ids) != len(set(ids)) or len(matched) != len(matched_note_ids):
        raise ValueError("duplicate_canonical_or_matched_note_id")
    if not matched <= set(ids):
        raise ValueError("unknown_matched_note_id")
    root = ET.fromstring(mapped_xml)
    if _local(root) != "score-partwise":
        raise ValueError("unsupported_source_layout")
    parts = _children(root, "part")
    part_counts = Counter(part.get("id") for part in parts)
    result = {}
    for pi, part in enumerate(parts):
        source_part = part.get("id")
        for mi, measure in enumerate(_children(part, "measure")):
            for ni, note in enumerate(_children(measure, "note")):
                nid = note.get("id") or note.get(XML_ID)
                if nid not in matched:
                    continue
                if nid in result:
                    raise ValueError("duplicate_mapped_source_note_id")
                if len(_children(note, "pitch")) != 1 or _children(note, "rest"):
                    raise ValueError("mapped_id_not_single_pitched_note")
                voice, voice_count = _raw_text(note, "voice")
                raw_staff, staff_count = _raw_text(note, "staff")
                reasons = []
                if not source_part or part_counts[source_part] != 1:
                    reasons.append("missing_or_duplicate_source_part_id")
                if voice_count > 1:
                    reasons.append("duplicate_source_voice")
                elif voice_count == 1 and voice is None:
                    reasons.append("empty_explicit_source_voice")
                staff = 1 if staff_count == 0 else None
                if staff_count == 1:
                    try:
                        staff = int(raw_staff)
                        if staff < 1:
                            raise ValueError("nonpositive_staff")
                    except (ValueError, TypeError):
                        staff = None
                        reasons.append("empty_or_invalid_explicit_source_staff")
                elif staff_count > 1:
                    reasons.append("duplicate_source_staff")
                status = ("unsupported_source_fields" if reasons else
                          "missing_explicit_source_voice" if voice is None else
                          "explicit_source_voice_observed")
                result[nid] = {"note_id": nid, "source_part_id": source_part,
                    "source_part_index": pi, "source_voice": voice,
                    "source_voice_element_count": voice_count, "source_staff": staff,
                    "source_staff_raw": raw_staff, "source_staff_element_count": staff_count,
                    "staff_defaulted_from_absence": staff_count == 0,
                    "printed_measure_number": measure.get("number"), "sequential_measure_index": mi,
                    "source_element_index": ni,
                    "source_xpath": f"/score-partwise/part[{pi+1}]/measure[{mi+1}]/note[{ni+1}]",
                    "grace": bool(_children(note, "grace")),
                    "source_identity_status": status, "source_field_blockers": reasons}
    if set(result) != matched:
        raise ValueError("matched_source_note_coverage_mismatch")
    return result


def lane_inventory(note_events, source_notes):
    """Cardinalities use mapped notes only; exclusions are explicitly retained."""
    ids = [note["note_id"] for note in note_events]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate_lane_inventory_note_id")
    groups = defaultdict(list)
    for note in note_events:
        groups[(note.get("part_id"), note.get("voice_id"))].append(note["note_id"])
    rows = []
    counts = Counter()
    cardinalities = Counter()
    staff_cardinalities = Counter()
    for (part, voice), note_ids in sorted(groups.items(), key=lambda item: str(item[0])):
        by_source = defaultdict(list)
        staff_scopes = set()
        missing = []
        unsupported = []
        unmapped = []
        for nid in note_ids:
            source = source_notes.get(nid)
            if source is None:
                unmapped.append(nid)
                continue
            if source["source_staff"] is not None:
                staff_scopes.add((source["source_part_id"], source["source_staff"]))
            if source["source_identity_status"] == "explicit_source_voice_observed":
                by_source[(source["source_part_id"], source["source_voice"])].append(nid)
            elif source["source_identity_status"] == "missing_explicit_source_voice":
                missing.append(nid)
            else:
                unsupported.append(nid)
        cardinality = len(by_source)
        cardinalities[str(cardinality)] += 1
        staff_cardinalities[str(len(staff_scopes))] += 1
        counts.update({"logical_lanes": 1, "single_explicit_source_lane": cardinality == 1,
            "multiple_explicit_source_lanes": cardinality > 1,
            "no_explicit_source_lane": cardinality == 0,
            "missing_source_voice_lanes": bool(missing), "unsupported_source_field_lanes": bool(unsupported),
            "unmapped_note_lanes": bool(unmapped), "notes": len(note_ids),
            "mapped_notes": len(note_ids) - len(unmapped), "unmapped_notes": len(unmapped)})
        rows.append({"logical_part_id": part, "logical_voice_id": voice,
            "note_ids": note_ids, "explicit_source_lane_cardinality": cardinality,
            "mixed_explicit_source_lane": cardinality > 1,
            "actual_source_lanes": [{"source_part_id": p, "source_voice": v, "note_ids": ns}
                                    for (p, v), ns in sorted(by_source.items())],
            "staff_scopes": [{"source_part_id": p, "source_staff": s}
                             for p, s in sorted(staff_scopes, key=str)],
            "missing_source_voice_note_ids": missing, "unsupported_source_field_note_ids": unsupported,
            "unmapped_note_ids": unmapped, "contrapuntal_identity_certified": False})
    return {"counts": dict(counts), "explicit_source_lane_cardinality_counts": dict(cardinalities),
            "staff_cardinality_counts": dict(staff_cardinalities), "lanes": rows}


def _sound_source(sid, sounds, source_notes):
    sound = sounds.get(sid)
    if sound is None or not sound.get("source_note_ids"):
        return {"status": "unknown_sounding_event", "sounding_event_id": sid, "source_note_ids": []}
    ids = sound["source_note_ids"]
    rows = [source_notes.get(nid) for nid in ids]
    scopes = {(r["source_part_id"], r["source_voice"]) for r in rows
              if r and r["source_identity_status"] == "explicit_source_voice_observed"}
    status = ("unmapped_source_note" if any(r is None for r in rows) else
              "unsupported_source_fields" if any(r["source_identity_status"] == "unsupported_source_fields" for r in rows) else
              "missing_explicit_source_voice" if any(r["source_identity_status"] != "explicit_source_voice_observed" for r in rows) else
              "ambiguous_sound_source_voice" if len(scopes) != 1 else "single_explicit_source_lane")
    return {"status": status, "sounding_event_id": sid, "source_note_ids": list(ids),
            "actual_source_lanes": [{"source_part_id": p, "source_voice": v} for p, v in sorted(scopes)]}


def classify_link(link, sounds, source_notes):
    if len(link) != 2:
        raise ValueError("invalid_saved_link_shape")
    ends = [_sound_source(sid, sounds, source_notes) for sid in link]
    blockers = [end["status"] for end in ends if end["status"] != "single_explicit_source_lane"]
    status = blockers[0] if blockers else SAME if ends[0]["actual_source_lanes"] == ends[1]["actual_source_lanes"] else "different_explicit_source_lane"
    return {"link": list(link), "status": status, "endpoints": ends,
            "contrapuntal_identity_certified": False}


def classify_temporal_path(path, sounds, source_notes):
    chain = path["carried_event_refs"]
    if not chain or chain[0] != path["source_ref"]:
        raise ValueError("invalid_saved_temporal_chain")
    expected = [list(edge) for edge in zip(chain, chain[1:] + [path["target_ref"]])]
    if path["links"] != expected:
        raise ValueError("saved_temporal_link_chain_mismatch")
    links = [classify_link(edge, sounds, source_notes) for edge in expected]
    return {"relation": path["relation"], "source_ref": path["source_ref"], "target_ref": path["target_ref"],
            "carried_event_refs": list(chain), "link_audits": links,
            "source_lane_statuses": sorted({row["status"] for row in links}),
            "contrapuntal_identity_certified": False}


def validate_policy(entry):
    if entry.get("split") not in ("train", "dev"):
        raise ValueError("protected_or_unassigned_split")
    if entry.get("rights", {}).get("internal_research_use") is not True:
        raise ValueError("internal_research_not_approved")
    if not entry.get("work_family_id") or not entry.get("score_sha256"):
        raise ValueError("missing_frozen_policy_identity")


def _compressed_write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(gzip.compress(json.dumps(value, ensure_ascii=False, allow_nan=False,
                                             separators=(",", ":")).encode("utf-8"), mtime=0))


def _sum_counts(values, field):
    total = Counter()
    for value in values:
        total.update(value[field])
    return dict(total)


def run(plan_path, case_dir, output_dir):
    output = Path(output_dir)
    case_dir = Path(case_dir)
    if output.exists():
        raise ValueError("output_exists_no_overwrite")
    started = perf_counter()
    hashes = {}
    plan = _load(plan_path, hashes)
    previous = _load(case_dir / "report.json", hashes)
    _load(case_dir / "run-contract.json", hashes)
    if (previous.get("complete") is not True or previous.get("inputs_unchanged") is not True or
            previous.get("snapshots_unchanged") is not True or previous.get("failed_rechecks") or
            previous.get("source_labels_used") is not False or previous.get("accuracy_measured") is not False):
        raise ValueError("invalid_previous_case_audit")
    packages = {p["pair_id"]: p for p in plan["packages"]}
    if len(packages) != len(plan["packages"]) or len(packages) != previous["frozen_packages"]:
        raise ValueError("frozen_package_coverage_mismatch")
    parents = {}
    for pair, package in packages.items():
        source = package["source"]
        entry = source["manifest_entry"]
        validate_policy(entry)
        path = entry["score_source_path"]
        if source["source_files"].get(path) != entry["score_sha256"]:
            raise ValueError("score_path_not_frozen_in_source_files")
        for name, expected in source["source_files"].items():
            _freeze_bytes(name, hashes, expected)
        ir = _load(source["frozen_ir_path"], hashes, source["ir_sha256"])
        if ir["score"]["score_id"] != entry["score_id"] or ir["ir_document_id"] != entry["ir_document_id"]:
            raise ValueError("manifest_parent_identity_mismatch")
        if source.get("original_ir_path"):
            _freeze_bytes(source["original_ir_path"], hashes, source["ir_sha256"])
        if source.get("preparation_path"):
            _load(source["preparation_path"], hashes, source["preparation_sha256"])
        parents[pair] = ir
    cases = []
    sample_keys = set()
    for record in previous["records"]:
        identity = (record["pair_id"], record["sample_id"], record["plan_index"])
        if identity in sample_keys:
            raise ValueError("duplicate_case_sample_identity")
        sample_keys.add(identity)
        pair = record["pair_id"]
        case = _load(record["artifact"], hashes, record["sha256"], compressed=True)
        if pair not in packages or case["sample"]["sample_id"] != record["sample_id"]:
            raise ValueError("case_identity_mismatch")
        snapshot = case["source_snapshot"]
        source = packages[pair]["source"]
        if (snapshot["manifest_entry"] != source["manifest_entry"] or
                snapshot["canonical_ir_sha256"] != source["ir_sha256"] or
                snapshot["source_xml_sha256"] != source["manifest_entry"]["score_sha256"] or
                snapshot.get("pitch_policy") != source.get("pitch_policy")):
            raise ValueError("case_snapshot_policy_mismatch")
        for field in ("source_xml", "canonical_ir"):
            _freeze_bytes(snapshot[field], hashes, snapshot[field + "_sha256"])
        if len(case["groups"]) != len(case["group_contexts"]):
            raise ValueError("case_context_group_count_mismatch")
        cases.append((record, case))
    if len(cases) != previous["supported_samples"]:
        raise ValueError("case_sample_coverage_mismatch")
    code = _code_hashes()
    contract = {"version": VERSION, "mapping_version": SOURCE_MAPPING_VERSION,
        "frozen_plan": str(Path(plan_path).resolve()), "parent_case_dir": str(case_dir.resolve()),
        "input_hashes": hashes, "code_hashes": code,
        "scope": "all frozen packages; all saved supported contexts and witnesses, no source-lane repair",
        "internal_only": True, "source_labels_used": False, "accuracy_measured": False,
        "source_contrapuntal_identity_certified": False, "split_rights_changed": False,
        "production_modified": False, "core_modified": False, "engine_recomputed": False,
        "gate_changed": False, "annotation_retargeted": False, "gold_promoted": False,
        "training_promoted": False, "external_transmission": False}
    output.mkdir(parents=True, exist_ok=False)
    write(output / "run-contract.json", contract)
    records = []
    source_notes = {}
    artifacts = {}
    mapping_counts = Counter()
    hint_counts = Counter()
    global_inventories = []
    for pair, package in packages.items():
        ir = parents[pair]
        frozen_memory = json.dumps(ir, sort_keys=True, separators=(",", ":"))
        mapped_xml, mapping = musicxml_with_canonical_ids(package["source"]["manifest_entry"]["score_source_path"], ir)
        if frozen_memory != json.dumps(ir, sort_keys=True, separators=(",", ":")):
            raise ValueError("mapper_mutated_parent_ir")
        mapped = mapped_note_sources(mapped_xml, ir, mapping["matched_note_ids_in_source_order"])
        if mapping["matched_count"] != len(mapped) or mapping["ir_note_count"] != len(ir["note_events"]):
            raise ValueError("mapping_count_mismatch")
        if set(mapping["unmatched_ir_note_ids"]) != {n["note_id"] for n in ir["note_events"]} - set(mapped):
            raise ValueError("mapping_exclusion_mismatch")
        source_notes[pair] = mapped
        inventory = lane_inventory(ir["note_events"], mapped)
        global_inventories.append(inventory)
        by_lane = {(row["logical_part_id"], row["logical_voice_id"]): row for row in inventory["lanes"]}
        notes = {n["note_id"]: n for n in ir["note_events"]}
        for hint in mapping["voice_hint_disagreements"]:
            note = notes[hint["note_id"]]
            lane = by_lane[(note["part_id"], note["voice_id"])]
            key = ("mixed_explicit_lane" if lane["explicit_source_lane_cardinality"] > 1 else
                   "constant_explicit_lane" if lane["explicit_source_lane_cardinality"] == 1 else "no_explicit_lane")
            hint_counts[key] += 1
        mapping_counts.update({"packages": 1, "complete_packages": mapping["complete"],
            "notes": len(ir["note_events"]), "matched": len(mapped),
            "unmatched_ir": len(mapping["unmatched_ir_note_ids"]),
            "unmatched_xml": len(mapping["unmatched_xml_notes"]),
            "voice_hint_disagreements": len(mapping["voice_hint_disagreements"])})
        destination = output / "packages" / (hashlib.sha256(pair.encode()).hexdigest()[:20] + ".json.gz")
        value = {"version": VERSION, "pair_id": pair, "manifest_entry": deepcopy(package["source"]["manifest_entry"]),
            "pitch_policy": deepcopy(package["source"].get("pitch_policy")),
            "source_path": package["source"]["manifest_entry"]["score_source_path"],
            "source_sha256": package["source"]["manifest_entry"]["score_sha256"],
            "parent_ir_path": package["source"]["frozen_ir_path"], "parent_ir_sha256": package["source"]["ir_sha256"],
            "mapping": mapping, "note_sources": mapped, "logical_lane_inventory": inventory,
            "internal_only": True, "source_contrapuntal_identity_certified": False}
        _compressed_write(destination, value)
        artifacts[str(destination.resolve())] = digest(destination)
        records.append({"pair_id": pair, "artifact": str(destination.resolve()), "sha256": digest(destination),
                        "mapping_complete": mapping["complete"], "counts": inventory["counts"]})
    case_records = []
    context_inventories = []
    context_counts = Counter()
    relation_counts = {kind: {"records": Counter(), "links": Counter(), "paths": Counter()}
                       for kind in ("direct", "temporal")}
    unique_links = {kind: {} for kind in ("direct", "temporal")}
    unique_context_lanes = set()
    for record, case in cases:
        pair = record["pair_id"]
        ir = parents[pair]
        notes = {n["note_id"]: n for n in ir["note_events"]}
        sounds = {s["sounding_event_id"]: s for s in ir["sounding_events"]}
        if len(sounds) != len(ir["sounding_events"]):
            raise ValueError("duplicate_sounding_event_id")
        groups = []
        for index, (group, context) in enumerate(zip(case["groups"], case["group_contexts"])):
            if any(notes.get(n["note_id"]) != n for n in context["note_events"]):
                raise ValueError("parent_context_note_identity_mismatch")
            if any(sounds.get(s["sounding_event_id"]) != s for s in context["sounding_events"]):
                raise ValueError("parent_context_sound_identity_mismatch")
            inventory = lane_inventory(context["note_events"], source_notes[pair])
            context_inventories.append(inventory)
            context_counts["contexts"] += 1
            context_counts["mixed_contexts"] += inventory["counts"]["multiple_explicit_source_lanes"] > 0
            context_counts["missing_source_voice_contexts"] += inventory["counts"]["missing_source_voice_lanes"] > 0
            context_counts["unmapped_note_contexts"] += inventory["counts"]["unmapped_note_lanes"] > 0
            unique_context_lanes.update((pair, row["logical_part_id"], row["logical_voice_id"])
                                        for row in inventory["lanes"])
            witness_rows = []
            for audit in group.get("audits", []):
                direct = audit.get("direct", {}).get("status") == "conditional_witness_rechecked"
                temporal = audit.get("temporal", {}).get("status") == "conditional_witness_rechecked"
                if not direct and not temporal:
                    continue
                entry = {"query_index": audit["query_index"], "pair": deepcopy(audit["pair"]),
                         "direct_link_audits": [], "temporal_path_audits": [],
                         "function_confirmed": False, "source_contrapuntal_identity_certified": False}
                for kind, selected in (("direct", direct), ("temporal", temporal)):
                    if not selected:
                        continue
                    if kind == "direct":
                        links = [classify_link(link, sounds, source_notes[pair]) for link in audit["direct"]["selected_links"]]
                        entry["direct_link_audits"] = links
                    else:
                        paths = [classify_temporal_path(path, sounds, source_notes[pair])
                                 for path in audit["temporal"]["selected_paths"]]
                        entry["temporal_path_audits"] = paths
                        links = [link for path in paths for link in path["link_audits"]]
                        relation_counts[kind]["paths"].update(",".join(path["source_lane_statuses"]) for path in paths)
                    label = ",".join(sorted({link["status"] for link in links})) if links else "empty_saved_witness"
                    relation_counts[kind]["records"][label] += 1
                    for link in links:
                        relation_counts[kind]["links"][link["status"]] += 1
                        key = (pair, tuple(link["link"]))
                        if key in unique_links[kind] and unique_links[kind][key] != link["status"]:
                            raise ValueError("repeated_link_classification_changed")
                        unique_links[kind][key] = link["status"]
                witness_rows.append(entry)
            groups.append({"group_index": index, "group_span": deepcopy(group["span"]),
                           "context_span": deepcopy(context["span"]), "logical_lane_inventory": inventory,
                           "witness_records": witness_rows})
        destination = output / "contexts" / (hashlib.sha256(repr((pair, record["sample_id"], record["plan_index"])).encode()).hexdigest()[:20] + ".json.gz")
        value = {"version": VERSION, "pair_id": pair, "sample_id": record["sample_id"],
            "plan_index": record["plan_index"], "parent_artifact": record["artifact"], "parent_sha256": record["sha256"],
            "parent_ir_document_id": ir["ir_document_id"], "groups": groups,
            "source_contrapuntal_identity_certified": False, "engine_recomputed": False, "gate_changed": False}
        _compressed_write(destination, value)
        artifacts[str(destination.resolve())] = digest(destination)
        case_records.append({"pair_id": pair, "sample_id": record["sample_id"], "plan_index": record["plan_index"],
                             "artifact": str(destination.resolve()), "sha256": digest(destination), "contexts": len(groups)})
    changed_inputs = [p for p, h in hashes.items() if digest(p) != h]
    current_code = _code_hashes()
    changed_code = sorted(p for p in set(code) | set(current_code) if code.get(p) != current_code.get(p))
    changed_artifacts = [p for p, h in artifacts.items() if digest(p) != h]
    summary = {"packages": len(records), "work_families": len({p["source"]["manifest_entry"]["work_family_id"] for p in packages.values()}),
        "mapping": dict(mapping_counts), "global_logical_lanes": _sum_counts(global_inventories, "counts"),
        "global_source_lane_cardinalities": _sum_counts(global_inventories, "explicit_source_lane_cardinality_counts"),
        "global_staff_cardinalities": _sum_counts(global_inventories, "staff_cardinality_counts"),
        "hint_disagreement_lane_membership": dict(hint_counts), "case_samples": len(case_records),
        "context_counts": dict(context_counts), "context_logical_lane_instances": _sum_counts(context_inventories, "counts"),
        "context_source_lane_cardinalities": _sum_counts(context_inventories, "explicit_source_lane_cardinality_counts"),
        "context_staff_cardinalities": _sum_counts(context_inventories, "staff_cardinality_counts"),
        "unique_context_logical_lanes": len(unique_context_lanes),
        "positive_witnesses": {kind: {**{name: dict(values) for name, values in counts.items()},
                                      "unique_links": dict(Counter(unique_links[kind].values()))}
                               for kind, counts in relation_counts.items()}}
    if (mapping_counts["matched"] + mapping_counts["unmatched_ir"] != mapping_counts["notes"] or
            sum(hint_counts.values()) != mapping_counts["voice_hint_disagreements"]):
        raise ValueError("diagnostic_coverage_partition_mismatch")
    result = {"version": VERSION, "complete": not (changed_inputs or changed_code or changed_artifacts),
        "summary": summary, "records": records, "contexts": case_records,
        "input_hashes_unchanged": not changed_inputs, "code_hashes_unchanged": not changed_code,
        "artifacts_unchanged": not changed_artifacts, "changed_inputs": changed_inputs,
        "changed_code": changed_code, "changed_artifacts": changed_artifacts, "artifact_hashes": artifacts,
        "contract_sha256": digest(output / "run-contract.json"), "source_labels_used": False,
        "accuracy_measured": False, "source_contrapuntal_identity_certified": False,
        "core_modified": False, "production_modified": False, "engine_recomputed": False,
        "gate_changed": False, "split_rights_changed": False, "gold_promoted": False,
        "training_promoted": False, "external_transmission": False,
        "elapsed_seconds": perf_counter() - started,
        "limits": ["Mapped XML part+voice is explicit source notation, not actual contrapuntal identity.",
                   "Logical lanes, voices, Core, annotations, engines, gates, rights and splits remain unchanged.",
                   "Single-source-lane cardinalities apply to known mapped notes only; all exclusions remain visible.",
                   "Padded-context mixtures may occur outside a selected witness; they do not invalidate it automatically.",
                   "No harmonic accuracy, source pitch/concert normalization, rhythm or contrapuntal assessment."]}
    write(output / "report.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.plan, args.cases, args.output)
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
    if not result["complete"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
