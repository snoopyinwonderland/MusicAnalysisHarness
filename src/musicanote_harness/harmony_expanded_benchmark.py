"""J3b frozen, label-free inference on additional development scores.

Original holdouts remain protected. This is not a blind benchmark, training,
Roman-numeral evaluation, or a production migration. Freeze ALL predictions
before opening ANY imported annotation labels.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path
from time import perf_counter
import traceback

from jsonschema import Draft202012Validator

from .harmony_breadth_trial import freeze_score, analyze_sample, source_transposition
from .harmony_candidate_recall import fraction, rational, reference_cells, paths_from_search, evaluate as recall_evaluate
from .harmony_common_benchmark import evaluate, native_reference, native_prediction, summarize, identity_overlap
from .harmony_context_bundle import bundle
from .harmony_dataset_manifest import _package_identity
from .harmony_evidence_scoring import prepare_with_evidence, BASE_WEIGHTS, EVIDENCE_WEIGHTS
from .harmony_functional_scoring import prepare_functional_evidence, supply, decode, PAIR_WEIGHTS, ROLE_COST
from .harmony_lattice_recall import diagnose
from .harmony_progression_search import search, _hash
from .source_sequence_replay_audit import audit as replay_audit
from .source_physical_measure_audit import audit as measure_audit

VERSION = "harmony-expanded-benchmark-0.1.0"
PLAN_SHA = "f504636ca42212c122680650f57c564bf564c768f73ebe6c579b242d92dfa5dd"
MANIFEST_SHA = "1b32ef777d5ad2c3982de65cb183e09a8761decbb17cb0df7c61b4dc1f02eb5f"
EXPOSED_SHA = "f12397eb53544dfa153974a9f0006f7cb06467d09c10ce1ecaf8da2e2d21f0eb"
ARM = "frozen_J2e_functional_supply_and_resolution"
CONFIG = {"samples_per_lane": 1, "max_segments": 6, "per_state_limit": 6,
          "max_complete_paths": 24, "search_transition_budget": 200000,
          "decoder_transition_budget": 2000000}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def write_packet(path, value):
    data = json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
    Path(path).write_bytes(gzip.compress(data, mtime=0))


def observation_ir(parent):
    """Keep Core IDs/geometry; do not pass annotations, mode or textual hints."""
    fields = ("schema_name", "schema_version", "ir_document_id", "source_files", "source_references",
              "score", "parts", "staves", "voices", "measures", "note_events", "rest_events",
              "tie_chains", "sounding_events", "attack_events", "chord_onset_groups", "parser_manifest", "validation_summary")
    result = {k: deepcopy(parent[k]) for k in fields if k in parent}
    result["extensions"] = {}
    for name in ("title", "composer", "movement"):
        result["score"][name] = None
    result["score"]["metadata"] = {}
    for measure in result["measures"]:
        measure.get("key_signature", {}).pop("mode_hint", None)
    return result


def execution_schedule(plan, manifest, exposed):
    """A new internal DEVELOPMENT scope, never an override of a holdout gate."""
    selected, excluded, seen = [], [], set()
    for family in plan["schedule"]:
        for item in family["metadata_complete_packages"]:
            pair = item["pair_id"]
            if pair in seen: raise ValueError("duplicate_staged_pair")
            seen.add(pair)
            if (item["status"] != "metadata_candidate_exposure_unknown"
                    or item["known_overlap_fields"] or item["historical_exposure"]
                    or item["work_family_id"] != family["work_family_id"]):
                raise ValueError("invalid_staged_identity")
            old = [e for e in manifest["entries"] if identity_overlap(item, [e])]
            blockers = []
            if any(e.get("split") == "holdout" for e in old): blockers.append("original_holdout_protected")
            if identity_overlap(item, exposed["package_manifest"]): blockers.append("known_development_overlap")
            if any(e.get("rights", {}).get("internal_research_use") is not True for e in old):
                blockers.append("original_internal_research_not_approved")
            row = dict(item, original_manifest_matches=old, blockers=blockers,
                       evaluation_scope="expanded_internal_development_exposure_history_unknown",
                       blind_test_approved=False, training_approved=False)
            (excluded if blockers else selected).append(row)
    return selected, excluded


def source_gate(parent, replay, physical, pitch):
    blockers = []
    if replay["status"] != "complete_replay": blockers.append("source_note_rest_replay_not_complete")
    if physical["status"] != "complete_parent_event_mapping": blockers.append("physical_measure_mapping_not_complete")
    if not pitch["harmonic_replay_allowed"]: blockers.append("written_concert_transposition_unverified")
    if physical["counts"].get("duplicate_measure_id_groups"):
        blockers.append("duplicate_measure_ids_revision_required")
    if physical["counts"].get("local_onset_mismatches"):
        blockers.append("local_measure_clock_revision_required")
    if any(r["resolved_sequential_measure_index"] not in r["legacy_referenced_sequence_indices"]
           for r in physical["events"]): blockers.append("physical_measure_membership_revision_required")
    if any(n["written_pitch"] != n["concert_pitch"] for n in parent["note_events"]):
        blockers.append("written_concert_pitch_disagreement")
    return sorted(set(blockers))


def infer(ir, sample):
    """Only observation IR and a frozen score-derived sample are arguments."""
    before = _hash(ir)
    stages = analyze_sample(ir, sample)
    b = bundle(ir, stages)
    proposed = search(b, max_segments=CONFIG["max_segments"], per_state_limit=CONFIG["per_state_limit"],
                      max_complete_paths=CONFIG["max_complete_paths"], transition_budget=CONFIG["search_transition_budget"])
    problem, ev = prepare_with_evidence(ir, b, proposed)
    functional = prepare_functional_evidence(ir, ev)
    expanded, receipts = supply(problem, functional)
    chosen = decode(expanded, functional, transition_budget=CONFIG["decoder_transition_budget"])
    if _hash(ir) != before: raise ValueError("inference_mutated_ir")
    return chosen, proposed, expanded, receipts, stages["summary"], functional.voice_statuses


def candidate_diagnostic(proposed, expanded, cells, span):
    retained = recall_evaluate(paths_from_search(proposed, span), cells)
    oracle = dict(proposed, semantic_groups=[{
        "group_id": e.group_id, "from": e.start_index, "to": e.end_index,
        "span": {"start": rational(e.start), "end": rational(e.end)},
        "root_spelling": e.signature[0], "members": e.signature[1]} for e in expanded.edges])
    # The added functional alternatives are not in the old retained24. Keep
    # retained24 and expanded-lattice ceilings explicitly separate.
    ceiling = diagnose(oracle, cells, expanded.points if expanded.status == "ready" else None,
                       {"candidate_hit": False, "selected_hit": False})
    return retained, ceiling


def run(plan_path, manifest_path, exposed_path, output):
    output = Path(output)
    if output.exists(): raise ValueError("output_exists_no_overwrite")
    started = perf_counter(); inputs = {}; artifacts = {}
    def pin(path, expected=None):
        p = Path(path); value = digest(p); name = str(p.resolve())
        if expected is not None and value != expected: raise ValueError("input_sha_mismatch:"+name)
        if name in inputs and inputs[name] != value: raise ValueError("input_changed_during_read")
        inputs[name] = value
        return p
    def read(path, expected=None, lines=False):
        data = pin(path, expected).read_text(encoding="utf-8")
        return [json.loads(x) for x in data.splitlines() if x.strip()] if lines else json.loads(data)
    plan = read(plan_path, PLAN_SHA); manifest = read(manifest_path, MANIFEST_SHA)
    exposed = read(exposed_path, EXPOSED_SHA)
    selected, excluded = execution_schedule(plan, manifest, exposed)
    schema_path = Path(__file__).resolve().parents[2]/"MUSICANOTE_Canonical_Music_IR/schemas/canonical_music_ir.schema.json"
    validator = Draft202012Validator(read(schema_path))
    codes = {str(p.resolve()): digest(p) for p in Path(__file__).parent.glob("*.py")}
    output.mkdir(parents=True, exist_ok=False); (output/"sources").mkdir(); (output/"predictions").mkdir()
    def save(path, value, compressed=False):
        (write_packet if compressed else write)(path, value)
        artifacts[str(path.resolve())] = digest(path)
        return str(path.resolve())
    contract = {"version": VERSION, "scope": "additional_development_scores_not_independent_blind_test",
        "config": CONFIG, "arm": ARM, "source_labels_used_at_inference": False,
        "prediction_before_any_reference_label_read": True, "source_harmony_elements_removed_by_importer": True,
        "weights": {k: str(v) for k, v in (BASE_WEIGHTS|EVIDENCE_WEIGHTS|PAIR_WEIGHTS).items()}|{"functional_role_complexity": str(ROLE_COST)},
        "input_pins": dict(inputs), "code_pins": codes,
        "selected_packages": selected, "excluded_packages": excluded,
        "selection": "all J3a staged packages except existing protected/overlap gates; one interior quantile per explicit lane",
        "user_scope": "approved_continuation_of_internal_performance_tests",
        "training_performed": False, "training_eligibility_granted": False, "commercial_use_approved": False,
        "external_transmission": False, "production_modified": False, "original_splits_or_rights_modified": False,
        "blind_test_accuracy_measured": False, "full_historical_exposure_audit_complete": False}
    save(output/"run-contract.json", contract)
    packages = []; prepared_irs = {}
    # Every package and window is frozen before the first harmonic engine call.
    for i, entry in enumerate(selected, 1):
        prep_path = Path(entry["preparation_report"]); folder = prep_path.parent
        prep = read(prep_path, entry["preparation_report_sha256"])
        identity = _package_identity(folder, folder.parents[1], prep)
        if any(identity[k] != entry[k] for k in identity): raise ValueError("staged_identity_changed")
        for kind, path in prep["source_paths"].items(): pin(path, prep["source_sha256"][kind])
        # Labels stay as bytes/hash guards. JSONL contents are first read below
        # only after the entire prediction phase has been sealed on disk.
        reference_paths = {n: str(pin(folder/n).resolve()) for n in ("imported_annotations.jsonl", "alignment_records.jsonl")}
        parent = read(folder/"canonical_music_ir.json"); validator.validate(parent)
        if parent["ir_document_id"] != prep["ir_document_id"] or parent["score"]["score_id"] != prep["score_id"]:
            raise ValueError("prepared_ir_identity_changed")
        ir = observation_ir(parent); frozen = freeze_score(ir, CONFIG["samples_per_lane"])
        replay = replay_audit(parent, prep["source_paths"]["score"])
        physical = measure_audit(parent, replay["raw_measures"], replay["observations"])
        pitch = source_transposition(prep["source_paths"]["score"])
        blockers = source_gate(parent, replay, physical, pitch)
        key = hashlib.sha256(entry["pair_id"].encode()).hexdigest()[:20]
        ir_path = save(output/"sources"/(key+"-observation-ir.json.gz"), ir, True)
        audit_path = save(output/"sources"/(key+"-audit.json.gz"), {"replay": replay, "physical": physical, "pitch": pitch}, True)
        item = {"entry": entry, "preparation": prep, "plan": frozen, "blockers": blockers,
                "observation_ir_path": ir_path, "observation_ir_content_sha256": _hash(ir),
                "source_audit_path": audit_path, "replay_status": replay["status"], "physical_status": physical["status"],
                "source_event_counts": replay["counts"], "physical_counts": physical["counts"], "reference_paths": reference_paths}
        packages.append(item); prepared_irs[entry["pair_id"]] = ir
        print(f"[preflight {i}/{len(selected)}] {entry['pair_id']}: {blockers or 'ready'}", flush=True)
    save(output/"frozen-plan.json", {"version": VERSION, "packages": packages, "labels_read": False})
    records = []; candidates = {}
    for item in packages:
        entry = item["entry"]; pair = entry["pair_id"]; ir = prepared_irs[pair]
        for planned in item["plan"]["selected_samples"]:
            sample = planned["sample"]; tick = perf_counter()
            row = {"pair_id": pair, "work_family_id": entry["work_family_id"], "collection_id": entry["collection_id"],
                "plan_index": planned["plan_index"], "sample_id": sample["sample_id"], "sample_span": sample["span"],
                "source_ir_content_sha256": _hash(ir), "selected_prediction": None, "reference_binding_verified": not item["blockers"]}
            if item["blockers"]:
                row.update(status="source_preflight_abstention", blockers=item["blockers"])
            else:
                try:
                    chosen, proposed, expanded, receipts, stages, voices = infer(ir, sample)
                    row.update(status=chosen["status"], selected_prediction=chosen["selected"], transitions=chosen["transitions"],
                               stage_summary=stages, voice_clock_statuses=voices, functional_candidate_receipts=receipts,
                               lattice_edge_count=len(expanded.edges), proposal_count=len(proposed["proposals"]))
                    candidates[(pair, sample["sample_id"])] = proposed, expanded
                except Exception as error:
                    row.update(status="execution_error", error_type=type(error).__name__, error=str(error), traceback=traceback.format_exc())
            row["elapsed_seconds"] = perf_counter()-tick
            name = hashlib.sha256(repr((pair, sample["sample_id"])).encode()).hexdigest()[:20]
            row["prediction_artifact"] = save(output/"predictions"/(name+".json.gz"), deepcopy(row), True)
            records.append(row)
            save(output/"progress.json", {"complete": False, "phase": "inference_labels_unopened", "contexts": len(records),
                "last_status": row["status"], "elapsed_seconds": perf_counter()-started})
            print(f"[prediction {len(records)}] {pair} {sample['sample_id']}: {row['status']}", flush=True)
    # A checksum-sealed receipt is physically written BEFORE reading gold.
    save(output/"prediction-freeze.json", {"version": VERSION, "labels_read": False,
        "prediction_hashes": {r["prediction_artifact"]: artifacts[r["prediction_artifact"]] for r in records},
        "contexts": len(records), "config": CONFIG, "code_pins": codes})
    for item in packages:
        entry = item["entry"]; pair = entry["pair_id"]
        annotations = read(item["reference_paths"]["imported_annotations.jsonl"], lines=True)
        alignments = read(item["reference_paths"]["alignment_records.jsonl"], lines=True)
        if any(a["source_asset_sha256"] != entry["annotation_sha256"] or
               a.get("target") and a["target"]["score_id"] != item["preparation"]["score_id"] for a in annotations):
            raise ValueError("reference_identity_changed")
        for row in (r for r in records if r["pair_id"] == pair):
            cells = reference_cells(row["sample_span"], annotations, alignments)
            if not row["reference_binding_verified"]:
                for c in cells: c.update(signature=None, reason="source_replay_or_measure_binding_unverified")
            row["reference_cells"] = [{"span": {"start": rational(c["start"]), "end": rational(c["end"])},
                "signature": c["signature"], "reason": c.get("reason"), "annotation_id": c.get("annotation_id")} for c in cells]
            row["evaluation"] = evaluate(native_reference(row), native_prediction(row["selected_prediction"], row["sample_span"]),
                                         row["sample_span"], selected=row["selected_prediction"] is not None)
            key = pair, row["sample_id"]
            if key in candidates:
                row["retained24"], row["candidate_ceiling"] = candidate_diagnostic(*candidates.pop(key), cells, row["sample_span"])
            else:
                row["retained24"] = {"candidate_hit": None, "outcome": "inference_unavailable"}
                row["candidate_ceiling"] = {"lattice_hit": None, "outcome": "inference_unavailable"}
    changed = [p for p, h in (inputs|codes|artifacts).items() if digest(p) != h]
    if changed: raise ValueError("frozen_inputs_or_artifacts_changed:"+repr(changed))
    table = summarize(records)
    full = [r for r in records if r["evaluation"]["fully_evaluable"]]
    def category(r):
        if r["evaluation"]["selected_hit"]: return "selected_correct"
        hit = r["candidate_ceiling"]["lattice_hit"]
        return "candidate_present_selection_error" if hit is True else "candidate_ceiling_missing" if hit is False else "candidate_ceiling_unavailable"
    result = {"version": VERSION, "complete": True, "arm": ARM, "table": table,
        "by_collection": {c: summarize([r for r in records if r["collection_id"] == c]) for c in sorted({r["collection_id"] for r in records})},
        "inventory": {"staged_packages": len(selected)+len(excluded), "excluded_packages": excluded,
            "attempted_packages": len(packages), "work_families": len({p["entry"]["work_family_id"] for p in packages}),
            "source_ready_packages": sum(not p["blockers"] for p in packages),
            "source_blocked_packages": [{"pair_id": p["entry"]["pair_id"], "blockers": p["blockers"]} for p in packages if p["blockers"]]},
        "status_counts": dict(Counter(r["status"] for r in records)),
        "candidate_diagnostics": dict(Counter(category(r) for r in full)),
        "retained24": {"fully_evaluable_contexts": len(full), "hits": sum(r["retained24"]["candidate_hit"] is True for r in full),
            "unknown": sum(r["retained24"]["candidate_hit"] is None for r in full), "scope": "original_retained24_not_added_functional_alternatives"},
        "reference_reason_counts": dict(Counter(c["reason"] for r in records for c in r["reference_cells"] if c["reason"])),
        "records": records, "input_hashes": inputs, "code_hashes": codes, "artifact_hashes": artifacts,
        "elapsed_seconds": perf_counter()-started, "source_labels_used_at_inference": False,
        "all_predictions_frozen_before_reference_loading": True, "training_performed": False, "development_tuning_performed": False,
        "independent_test_accuracy_measured": False, "full_roman_accuracy_measured": False,
        "production_modified": False, "original_core_annotations_splits_rights_modified": False,
        "limits": ["Work-family naming is conservative, not expert deduplication across all corpora.",
            "New source-derived sampled windows, not whole-score coverage or independent movements.",
            "Past result exposure is unknown; no blind-test or public-model superiority claim.",
            "Root and spelled members only; quality/inversion/local key/Roman remain unavailable.",
            "No label-guided window selection, weight tuning, source repair, commercial deployment or external transmission."]}
    write(output/"report.json", result)
    return {k: v for k, v in result.items() if k not in ("records", "input_hashes", "code_hashes", "artifact_hashes")}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for n in ("plan", "manifest", "exposed", "output"): parser.add_argument("--"+n, required=True)
    args = parser.parse_args()
    result = run(args.plan, args.manifest, args.exposed, args.output)
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    if result["status_counts"].get("execution_error"): raise SystemExit(1)
