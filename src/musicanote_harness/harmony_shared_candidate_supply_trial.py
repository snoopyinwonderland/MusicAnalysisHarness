"""Bounded five-context supplier equivalence/timing probe; no lattice cold replay."""
from __future__ import annotations

import argparse
from collections import Counter
import gzip
from hashlib import sha256
import json
from pathlib import Path
import re
from time import perf_counter

from . import harmony_candidate_catalog as legacy
from . import harmony_shared_candidate_supply as shared
from .musical_pattern_observation import digest, f, q
from .harmony_frozen_context_lineage_trial import write_new

ROOT = Path(__file__).resolve().parents[2]
VERSION = "shared-candidate-supply-trial-0.1.0"


def file_sha(path):
    h = sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()


def read(path):
    if Path(path).suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            return json.load(stream)
    with Path(path).open(encoding="utf-8") as stream:
        return json.load(stream)


def protect(protected, path, expected):
    if (type(path) is not str or str(Path(path).resolve(strict=True)) != path
            or type(expected) is not str or re.fullmatch(r"[0-9a-f]{64}", expected) is None):
        raise ValueError("canonical_absolute_SHA256_registration_required")
    if path in protected and protected[path] != expected:
        raise ValueError("conflicting_protected_SHA:" + path)
    protected[path] = expected


def registered(info, protected):
    path = Path(info["artifact"]).resolve(strict=True)
    if str(path) != info["artifact"] or file_sha(path) != info["sha256"]:
        raise ValueError("registered_input_SHA_mismatch")
    protect(protected, str(path), info["sha256"])
    return read(path)


def selected_spans(ir, context):
    a, b = f(context["start"]), f(context["end"])
    points = {a, b}
    for sound in ir["sounding_events"]:
        for value in sound["span"].values():
            t = f(value)
            if a < t < b:
                points.add(t)
    points = sorted(points)
    if len(points) < 4:
        raise ValueError("three_nonempty_technical_segments_required")
    i, j = max(1, (len(points) - 1) // 3), min(len(points) - 2, 2 * (len(points) - 1) // 3)
    if i == j:
        j += 1
    spans = [context, {"start": q(a), "end": q(points[i])},
             {"start": q(points[i]), "end": q(points[j])},
             {"start": q(points[j]), "end": q(b)}]
    return [*spans, spans[1]]  # deliberate duplicate occurrence, not another span


def run(parent_directory, output):
    started = perf_counter()
    parent = Path(parent_directory).resolve(strict=True)
    output = Path(output).resolve()
    if output.exists() or output.is_relative_to(parent) or parent.is_relative_to(output):
        raise ValueError("append_only_new_output_directory_required")
    index_path, plan_path, report_path = (parent / name for name in
                                         ("context-index.json", "run-plan.json", "report.json"))
    index, old_plan, old_report = read(index_path), read(plan_path), read(report_path)
    if (len(index) != 5 or old_report["version"] != "factor-interval-lattice-trial-0.1.0"
            or old_report["failures"]):
        raise ValueError("registered_five_context_phase22_required")
    parent_files = {str(p.resolve()) for p in parent.rglob("*") if p.is_file()}
    protected = {p: file_sha(p) for p in parent_files}
    # Old producer/test inventory is protected, not amended with new files.
    for inventory in (old_report["artifact_hashes"], old_plan["code"]):
        for path, expected in inventory.items():
            protect(protected, path, expected)
    for path, expected in protected.items():
        if file_sha(path) != expected:
            raise ValueError("old_phase22_inventory_changed:" + path)
    cases = []
    for row in index:
        ir = registered(row["full_IR"], protected)
        scope = registered(row["registered_parent_metadata"]["expanded_scope"], protected)
        if (digest(ir) != row["full_IR"]["ir_content_sha256"]
                or scope["binding"]["ir_content_sha256"] != digest(ir)):
            raise ValueError("registered_full_IR_content_binding_mismatch")
        context = scope["analysis_span"]
        cases.append((row["context_key"], ir, context, selected_spans(ir, context)))
    code = shared.producer_contract()["file_sha256"]
    extra = [Path(__file__), ROOT / "tests/test_harmony_shared_candidate_supply.py",
             ROOT / "tests/test_harmony_shared_candidate_supply_trial.py"]
    code.update({str(p.resolve()): file_sha(p) for p in extra})
    for path, expected in code.items():
        protect(protected, path, expected)
    output.mkdir()
    plan = {"version": VERSION, "parent": str(parent), "protected_sha256": protected,
            "selection_policy": "all_five_registered_contexts_full_plus_three_observed_grid_thirds_and_duplicate_first",
            "source_labels_used_for_inference": False, "native_lattice_reexecuted": False,
            "original_parent_file_authority_replayed": False,
            "requests": [{"context_key": key, "context_span": context, "spans": spans}
                         for key, _, context, spans in cases]}
    write_new(output / "run-plan.json", plan)
    rows, artifacts = [], {}
    for number, (key, ir, context, spans) in enumerate(cases, 1):
        print("SUPPLIER PROBE START", key[0], flush=True)
        original_sha = digest(ir)
        t = perf_counter()
        baseline = [legacy.propose(ir, span, context) for span in spans]
        baseline_seconds = perf_counter() - t
        t = perf_counter(); target = shared.canonical_json(baseline)
        baseline_serialization_seconds = perf_counter() - t
        t = perf_counter(); session = shared.prepare_supply(ir, context)
        prepare_seconds = perf_counter() - t
        t = perf_counter(); cold = shared.supply_catalogs(session, spans)
        cold_public_seconds = perf_counter() - t
        t = perf_counter(); warm = shared.supply_catalogs(session, spans)
        warm_public_seconds = perf_counter() - t
        if cold["receipt"]["status"] != "complete" or warm["receipt"]["status"] != "complete":
            raise ValueError("whole_probe_held")
        if target != shared.canonical_json(cold["catalogs"]) or target != shared.canonical_json(warm["catalogs"]):
            raise ValueError("complete_ordered_catalog_payload_mismatch")
        if digest(ir) != original_sha:
            raise ValueError("original_IR_mutation")
        row = {"context_key": key, "context_span": context, "spans": spans,
               "candidate_counts": [len(c["candidates"]) for c in baseline],
               "providers": dict(Counter(c["provider"] for cat in baseline for c in cat["candidates"])),
               "baseline_payload_sha256": digest(baseline), "exact_cold_and_warm_equal": True,
               "baseline_seconds": baseline_seconds, "prepare_seconds": prepare_seconds,
               "baseline_serialization_seconds": baseline_serialization_seconds,
               "cold_public_seconds": cold_public_seconds, "warm_public_seconds": warm_public_seconds,
               "cold_receipt": cold["receipt"], "warm_receipt": warm["receipt"],
               "legacy_window_calls_structural_not_instrumented": sum(2 if span == context else 4 for span in spans),
               "catalogs": cold["catalogs"], "source_IR_unchanged": True}
        path = output / ("context-" + str(number) + ".json.gz")
        with gzip.open(path, "xt", encoding="utf-8") as stream:
            json.dump(row, stream, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        artifacts[str(path)] = file_sha(path)
        rows.append({k: v for k, v in row.items() if k != "catalogs"})
        print("SUPPLIER PROBE DONE", key[0], "legacy", round(baseline_seconds, 3),
              "cold", round(prepare_seconds + cold_public_seconds, 3),
              "warm", round(warm_public_seconds, 3), flush=True)
    changed = [path for path, expected in protected.items() if file_sha(path) != expected]
    if {str(p.resolve()) for p in parent.rglob("*") if p.is_file()} != parent_files:
        raise ValueError("frozen_parent_file_inventory_changed")
    if changed:
        raise ValueError("protected_inputs_or_code_changed:" + repr(changed))
    write_new(output / "context-index.json", rows)
    artifacts[str(output / "run-plan.json")] = file_sha(output / "run-plan.json")
    artifacts[str(output / "context-index.json")] = file_sha(output / "context-index.json")
    report = {"version": VERSION, "status": "exact_supplier_equivalence_complete",
              "contexts": len(rows), "request_occurrences": sum(len(row["spans"]) for row in rows),
              "distinct_context_span_queries": sum(row["cold_receipt"]["distinct_raw_spans"] for row in rows),
              "candidate_occurrences": sum(sum(row["candidate_counts"]) for row in rows),
              "baseline_seconds": sum(row["baseline_seconds"] for row in rows),
              "baseline_serialization_seconds": sum(row["baseline_serialization_seconds"] for row in rows),
              "prepare_plus_cold_seconds": sum(row["prepare_seconds"] + row["cold_public_seconds"] for row in rows),
              "warm_seconds": sum(row["warm_public_seconds"] for row in rows),
              "cold_window_calls": sum(row["cold_receipt"]["stats"]["window_calls"] for row in rows),
              "warm_window_calls": sum(row["warm_receipt"]["stats"]["window_calls"] for row in rows),
              "legacy_window_calls_structural_not_instrumented": sum(row["legacy_window_calls_structural_not_instrumented"] for row in rows),
              "protected_paths": len(protected), "changed_protected_paths": changed,
              "artifact_sha256": artifacts, "elapsed_seconds": perf_counter() - started,
              "music_accuracy_evaluated": False, "native_lattice_reexecuted": False,
              "old_saved_catalogs_replayed": False, "production_or_UI_connected": False,
              "limits": ["Small sequential subset, not a full lattice or cold native benchmark.",
                         "Baseline is untouched fresh legacy supplier, not original-parent authority.",
                         "Timing includes supplier output serialization/copy/checks, not RSS or final accuracy.",
                         "Five selected contexts are not the entire cohort or positive cadence/NCT coverage."]}
    write_new(output / "report.json", report)
    print(json.dumps({k: v for k, v in report.items() if k not in ("artifact_sha256", "limits")}), flush=True)
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--parent", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.parent, args.output)


if __name__ == "__main__":
    main()
