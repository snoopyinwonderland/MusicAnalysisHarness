"""Reference-only DAG reachability over frozen spelled harmony inventories.

No search expansion, pruning change, training, or inference from gold labels.
The witness is an evaluator oracle, not a selected/validated musical analysis.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from fractions import Fraction
import gzip
import hashlib
import json
from pathlib import Path
from time import perf_counter

from .harmony_candidate_recall import evaluate, fraction, paths_from_search, rational, spelling
from .harmony_progression_search import _hash
from .source_locator_revision_trial import validate_policy

VERSION = "harmony-lattice-recall-0.1.0"


def signature(value):
    if value is None:
        return None
    root, members = value
    return None if root is None else spelling(root), tuple(sorted({spelling(m) for m in members}))


def cells_from_record(record):
    start, end = fraction(record["sample_span"]["start"]), fraction(record["sample_span"]["end"])
    if start < 0 or start >= end:
        raise ValueError("invalid_context_span")
    cells, cursor = [], start
    for cell in record["reference_cells"]:
        a, b = fraction(cell["span"]["start"]), fraction(cell["span"]["end"])
        if a != cursor or b <= a or b > end:
            raise ValueError("invalid_reference_partition")
        cells.append({"start": a, "end": b, "signature": signature(cell["signature"])})
        cursor = b
    if cursor != end:
        raise ValueError("incomplete_reference_partition")
    return cells


def validate_binding(bundle, search, span):
    """Check every stored reading is represented, without invoking producers."""
    if bundle.get("source_labels_used") is not False or bundle.get("selected") is not None:
        raise ValueError("nonblind_or_selected_bundle")
    if bundle["sample"]["span"] != span or search["sample"] != bundle["sample"]:
        raise ValueError("lattice_sample_binding_mismatch")
    lattice = bundle["stages"]["lattice"]
    if lattice["status"] != "ready":
        if (search["status"] != "preserved_lattice_abstention"
                or search["lattice_status"] != lattice["status"]
                or search.get("semantic_groups") or search.get("proposals")):
            raise ValueError("lattice_abstention_binding_mismatch")
        return None
    points = [fraction(p) for p in lattice["plan"]["points"]]
    if (len(points) < 2 or points != sorted(set(points))
            or points[0] != fraction(span["start"]) or points[-1] != fraction(span["end"])):
        raise ValueError("invalid_lattice_points")
    edges = lattice["edges"]
    expected = {(i, j) for i, edge in enumerate(edges) for j in range(len(edge["readings"]))}
    covered = set()
    for group in search["semantic_groups"]:
        i = group["edge_index"]
        if type(i) is not int or not 0 <= i < len(edges):
            raise ValueError("invalid_edge_reference")
        edge = edges[i]
        if any(group[k] != edge[k] for k in ("from", "to", "span")):
            raise ValueError("group_edge_geometry_mismatch")
        a, b = group["from"], group["to"]
        if (type(a) is not int or type(b) is not int or not 0 <= a < b < len(points)
                or points[a] != fraction(group["span"]["start"])
                or points[b] != fraction(group["span"]["end"])):
            raise ValueError("invalid_group_geometry")
        origins = group["origin_reading_keys"]
        if group["adapter_reading_key"] not in origins:
            raise ValueError("missing_adapter_origin")
        for origin in origins:
            key = origin["edge"], origin["reading"]
            if key not in expected or key in covered or key[0] != i:
                raise ValueError("duplicate_or_unknown_origin")
            reading = edge["readings"][key[1]]
            if (signature((reading["root_spelling"], reading["members"]))
                    != signature((group["root_spelling"], group["members"]))
                    or reading["span"] != group["span"]
                    or reading["event_states"] != group["event_states"]
                    or sorted(reading["abstention_reasons"]) != sorted(group["candidate_blockers"])):
                raise ValueError("group_reading_meaning_mismatch")
            covered.add(key)
    universe = search["universe"]
    if (covered != expected or universe["stored_readings"] != len(expected)
            or universe["stored_edges"] != len(edges)
            or universe["semantic_groups"] != len(search["semantic_groups"])):
        raise ValueError("stored_inventory_not_complete")
    return points


def union_time(intervals):
    total, cursor = Fraction(), None
    for start, end in sorted(intervals):
        total += end - start if cursor is None or start >= cursor else max(Fraction(), end - cursor)
        cursor = end if cursor is None else max(cursor, end)
    return total


def diagnose(search, cells, points, previous_evaluation):
    """Minimum-edge exact reference witness; no exponential path enumeration."""
    if not all(c["signature"] is not None for c in cells):
        return {"outcome": "reference_not_fully_evaluable", "lattice_hit": None}
    if points is None:
        return {"outcome": "lattice_unavailable", "lattice_hit": None,
                "lattice_status": search["lattice_status"]}
    groups = search["semantic_groups"]
    if len({g["group_id"] for g in groups}) != len(groups):
        raise ValueError("duplicate_semantic_group")
    budget = search["budgets"]["max_segments"]
    if type(budget) is not int or budget <= 0:
        raise ValueError("invalid_segment_budget")
    missing_changes = [left["end"] for left, right in zip(cells, cells[1:])
                       if left["signature"] != right["signature"] and left["end"] not in points]
    incoming, local_intervals, compatible = defaultdict(list), [], []
    for group in sorted(groups, key=lambda g: g["group_id"]):
        a, b = fraction(group["span"]["start"]), fraction(group["span"]["end"])
        sig = signature((group["root_spelling"], group["members"]))
        matching = [(max(a, c["start"]), min(b, c["end"])) for c in cells
                    if c["signature"] == sig and max(a, c["start"]) < min(b, c["end"])]
        local_intervals.extend(matching)
        if sum((y-x for x, y in matching), Fraction()) == b-a:
            incoming[group["to"]].append(group)
            compatible.append((a, b))
    reached = {0: (0, ())}
    for end in range(1, len(points)):
        alternatives = [(reached[g["from"]][0]+1, reached[g["from"]][1]+(g["group_id"],))
                        for g in incoming[end] if g["from"] in reached]
        if alternatives:
            reached[end] = min(alternatives)
    witness = reached.get(len(points)-1)
    minimum = witness[0] if witness else None
    hit = witness is not None and minimum <= budget
    retained = previous_evaluation["candidate_hit"]
    if retained and not hit:
        raise ValueError("retained_hit_without_lattice_witness")
    total = cells[-1]["end"]-cells[0]["start"]
    local, usable = union_time(local_intervals), union_time(compatible)
    if retained:
        outcome = "selected_correct" if previous_evaluation["selected_hit"] else "selection_error"
    elif hit:
        outcome = "retention_or_search_budget_loss"
    elif witness:
        outcome = "segment_budget_loss"
    elif missing_changes:
        outcome = "semantic_change_point_absent"
    elif local < total:
        outcome = "local_spelled_signature_absent"
    else:
        outcome = "no_consistent_reference_partition"
    return {"outcome": outcome, "lattice_hit": hit, "unlimited_lattice_hit": witness is not None,
            "minimum_segments": minimum, "segment_budget": budget,
            "oracle_reference_witness": list(witness[1]) if witness else None,
            "witness_uses_reference_labels": True, "witness_is_selected_prediction": False,
            "missing_semantic_change_points": [rational(t) for t in missing_changes],
            "local_signature_available_time": rational(local), "compatible_edge_coverage_time": rational(usable),
            "context_time": rational(total), "unspelled_candidates_preserved": len(search["unspelled_candidates"]),
            "group_blockers_not_overridden_or_musically_validated": True,
            "reachable_point_indices": sorted(reached)}


def run(previous_path, output, expected_report_sha):
    started = perf_counter(); previous_path, output = Path(previous_path), Path(output)
    if output.exists():
        raise ValueError("output_exists_no_overwrite")
    inputs = {}
    def read(path, expected, compressed=False):
        path = Path(path); data = path.read_bytes(); sha = hashlib.sha256(data).hexdigest()
        if sha != expected:
            raise ValueError("input_sha_mismatch:"+str(path))
        inputs[str(path.resolve())] = sha
        return json.loads((gzip.decompress(data) if compressed else data).decode("utf-8"))
    def guard(hashes):
        for path, sha in hashes.items():
            if hashlib.sha256(Path(path).read_bytes()).hexdigest() != sha:
                raise ValueError("frozen_input_changed:"+path)
            inputs[str(Path(path).resolve())] = sha
    previous = read(previous_path / "report.json", expected_report_sha)
    if (previous.get("complete") is not True or previous.get("source_labels_used_for_selection") is not False
            or previous.get("training_performed") is not False or previous.get("blind_test_accuracy_measured") is not False):
        raise ValueError("invalid_development_recall_report")
    guard(previous["input_hashes"])
    guard({str(Path(__file__).with_name("harmony_candidate_recall.py")): previous["code_sha256"]})
    code_sha = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    rows, seen = [], set()
    for index, row in enumerate(previous["records"], 1):
        identity = row["pair_id"], row["plan_index"], row["sample_id"]
        if identity in seen:
            raise ValueError("duplicate_context")
        seen.add(identity)
        packet = read(row["artifact"], row["artifact_sha256"], True)
        entry = packet["provenance"]["manifest_entry"]; validate_policy(entry)
        if (packet["pair_id"] != row["pair_id"] or packet["plan_index"] != row["plan_index"]
                or packet["sample"]["sample_id"] != row["sample_id"]
                or packet["sample"]["span"] != row["sample_span"]
                or entry["work_family_id"] != row["work_family_id"] or entry["split"] != row["split"]
                or entry not in previous["package_manifest"] or packet["source_labels_used"] is not False):
            raise ValueError("recall_sample_binding_mismatch")
        context = read(packet["previous_context_artifact"], packet["previous_context_sha256"], True)
        bundle = context["bundle"]; search = packet["search"]
        if (context["pair_id"] != row["pair_id"] or context["plan_index"] != row["plan_index"]
                or bundle["sample"] != packet["sample"] or context["provenance"] != packet["provenance"]
                or _hash(bundle) != packet["input_bundle_content_sha256"]
                or search["input_bundle_content_sha256"] != packet["input_bundle_content_sha256"]):
            raise ValueError("native_context_binding_mismatch")
        points = validate_binding(bundle, search, row["sample_span"])
        cells = cells_from_record(row)
        if evaluate(paths_from_search(search, row["sample_span"]), cells) != row["evaluation"]:
            raise ValueError("previous_metric_changed")
        result = diagnose(search, cells, points, row["evaluation"])
        rows.append({k: row[k] for k in ("pair_id", "plan_index", "sample_id", "work_family_id", "split", "sample_span")}
                    | {"previous_evaluation": row["evaluation"], "diagnosis": result,
                       "source_context_artifact": packet["previous_context_artifact"],
                       "source_context_sha256": packet["previous_context_sha256"],
                       "search_artifact": row["artifact"], "search_artifact_sha256": row["artifact_sha256"]})
        if index % 40 == 0 or index == len(previous["records"]):
            print(f"[{index}/{len(previous['records'])}] frozen lattice coverage", flush=True)
        del packet, context, bundle, search
    full = sum(r["previous_evaluation"]["fully_evaluable"] for r in rows)
    counts = Counter(r["diagnosis"]["outcome"] for r in rows)
    hits = sum(r["diagnosis"]["lattice_hit"] is True for r in rows)
    tested = sum(r["diagnosis"]["lattice_hit"] is not None for r in rows)
    summary = {"contexts": len(rows), "packages": len({r["pair_id"] for r in rows}),
               "work_families": len({r["work_family_id"] for r in rows}), "fully_evaluable_contexts": full,
               "lattice_evaluable_contexts": tested, "lattice_hit_contexts": hits,
               "lattice_recall_over_all_reference_contexts": hits/full if full else None,
               "lattice_recall_given_available_lattice": hits/tested if tested else None,
               "retained_recall_at_24": previous["summary"]["recall_at_24"], "outcomes": dict(counts)}
    if any(summary[k] != previous["summary"][k] for k in ("contexts", "packages", "work_families", "fully_evaluable_contexts")):
        raise ValueError("denominator_changed")
    guard(dict(inputs))
    if hashlib.sha256(Path(__file__).read_bytes()).hexdigest() != code_sha:
        raise ValueError("code_changed_during_run")
    result = {"version": VERSION, "complete": True, "summary": summary, "records": rows,
              "input_hashes": inputs, "code_sha256": code_sha, "elapsed_seconds": perf_counter()-started,
              "reference_labels_used_by_evaluator": True, "reference_witnesses_are_inference": False,
              "training_performed": False, "production_modified": False, "eligibility_changed": False,
              "candidate_inventory_or_search_modified": False, "previous_predictions_modified": False,
              "scope": "development_root_and_spelled_members_time_only_not_Roman_inversion_or_musical_validity",
              "limits": ["Complete stored spelled inventory only; unspelled alternatives remain unsupported.",
                         "A reference-compatible path may contain blockers or incompatible NCT/voice assumptions.",
                         "Retention loss combines prefix/output/transition caps, not just the final24 cap.",
                         "Unavailable lattice is unknown, not proof of vocabulary absence.",
                         "Reference witness is an evaluator diagnostic, never a deployed prediction."]}
    output.mkdir(parents=True, exist_ok=False)
    (output / "report.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--previous", required=True); parser.add_argument("--output", required=True)
    parser.add_argument("--expected-report-sha", required=True)
    args = parser.parse_args()
    result = run(args.previous, args.output, args.expected_report_sha)
    print(json.dumps({"summary": result["summary"], "elapsed_seconds": result["elapsed_seconds"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
