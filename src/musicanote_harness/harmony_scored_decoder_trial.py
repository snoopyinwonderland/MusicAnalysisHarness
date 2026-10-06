"""Frozen development comparison, separate from label-blind inference."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from fractions import Fraction
import gzip
import hashlib
import json
from pathlib import Path
from time import perf_counter

from .harmony_candidate_recall import agreement, fraction, paths_from_search, rational
from .harmony_lattice_recall import cells_from_record
from .harmony_scored_decoder import (
    VERSION as DECODER_VERSION, FEATURE_VERSION, DEFAULT_WEIGHTS, decode,
    evaluation_path, feature_cost, prepare, transition,
)
from .harmony_progression_search import _hash
from .source_locator_revision_trial import validate_policy

VERSION = "harmony-scored-decoder-trial-0.1.0"


def training_eligibility(entry):
    """Audit only: this experiment never changes or grants these fields."""
    reasons = []
    if entry.get("split") != "train":
        reasons.append("not_train_split")
    if entry.get("eligibility", {}).get("automatic_training") is not True:
        reasons.append("automatic_training_not_approved")
    if entry.get("rights", {}).get("model_training_approved") is not True:
        reasons.append("model_training_not_approved")
    if entry.get("rights", {}).get("internal_research_use") is not True:
        reasons.append("internal_research_not_approved")
    return {"eligible": not reasons, "reasons": reasons}


def retained_music(problem, paths):
    by_id = {e.group_id: e for e in problem.edges}
    scored = []
    for path in paths:
        cost, previous = Fraction(), None
        for segment in path["segments"]:
            edge = by_id[segment["group_id"]]
            cost += feature_cost(edge.features, DEFAULT_WEIGHTS)+feature_cost(transition(previous, edge), DEFAULT_WEIGHTS)
            previous = edge.signature
        scored.append((cost, tuple(s["group_id"] for s in path["segments"]), path["proposal_id"], path))
    return min(scored, key=lambda row: row[:3])[3] if scored else None


def evaluate_selection(path, cells):
    total = sum((c["end"]-c["start"] for c in cells), Fraction())
    eligible = sum((c["end"]-c["start"] for c in cells if c["signature"] is not None), Fraction())
    root, members = agreement(path, cells)
    full = total == eligible
    changes = lambda seq: {a["end"] for a, b in zip(seq, seq[1:]) if a["signature"] != b["signature"]}
    boundary = None
    if full:
        ref = changes(cells); predicted = changes(path["segments"]) if path else set()
        boundary = {"matched": len(ref & predicted), "extra": len(predicted-ref), "missed": len(ref-predicted)}
    return {"fully_evaluable": full, "eligible_time": rational(eligible), "context_time": rational(total),
            "selected_root_time": rational(root), "selected_root_members_time": rational(members),
            "selected_hit": members == total if full else None,
            "selected": path is not None, "semantic_boundary_exact": boundary}


def summarize(rows, arm):
    selected = full = hits = 0
    eligible = root = members = Fraction()
    boundary = Counter(); family = defaultdict(list)
    for row in rows:
        val = row["evaluations"][arm]
        selected += val["selected"]; full += val["fully_evaluable"]; hits += val["selected_hit"] is True
        eligible += fraction(val["eligible_time"]); root += fraction(val["selected_root_time"])
        members += fraction(val["selected_root_members_time"])
        if val["semantic_boundary_exact"] is not None:
            boundary.update(val["semantic_boundary_exact"])
        family[row["work_family_id"]].append(val)
    tp, fp, fn = (boundary[k] for k in ("matched", "extra", "missed"))
    macro = []
    for items in family.values():
        time = sum((fraction(v["eligible_time"]) for v in items), Fraction())
        if time:
            macro.append(sum((fraction(v["selected_root_members_time"]) for v in items), Fraction())/time)
    return {"contexts": len(rows), "selected_contexts": selected, "abstained_contexts": len(rows)-selected,
            "fully_evaluable_contexts": full, "selected_correct_contexts": hits,
            "selected_context_agreement": hits/full if full else None,
            "eligible_time": rational(eligible), "selected_root_time_agreement": float(root/eligible) if eligible else None,
            "selected_root_members_time_agreement": float(members/eligible) if eligible else None,
            "work_family_macro_root_members_agreement": float(sum(macro, Fraction())/len(macro)) if macro else None,
            "semantic_boundary_exact": {**dict(boundary), "precision": tp/(tp+fp) if tp+fp else None,
                                        "recall": tp/(tp+fn) if tp+fn else None,
                                        "f1": 2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None},
            "overlapping_context_time_is_not_unique_score_duration": True}


def run(recall_path, lattice_path, output, expected_recall_sha, expected_lattice_sha):
    started = perf_counter(); output = Path(output)
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
    recall = read(recall_path, expected_recall_sha)
    lattice = read(lattice_path, expected_lattice_sha)
    if (recall.get("complete") is not True or lattice.get("complete") is not True
            or recall.get("source_labels_used_for_selection") is not False
            or recall.get("training_performed") is not False or lattice.get("training_performed") is not False):
        raise ValueError("invalid_parent_report")
    guard(lattice["input_hashes"])
    guard({str(Path(__file__).with_name("harmony_candidate_recall.py")): recall["code_sha256"],
           str(Path(__file__).with_name("harmony_lattice_recall.py")): lattice["code_sha256"]})
    code_paths = [Path(__file__), Path(__file__).with_name("harmony_scored_decoder.py")]
    code_hashes = {str(p.resolve()): hashlib.sha256(p.read_bytes()).hexdigest() for p in code_paths}
    if len(recall["records"]) != len(lattice["records"]):
        raise ValueError("parent_context_count_mismatch")
    manifest = recall["package_manifest"]
    policy = [{"manifest_entry_id": e["manifest_entry_id"], "split": e["split"],
               **training_eligibility(e)} for e in manifest]
    rows, seen = [], set(); times = Counter(); statuses = Counter()
    for index, (row, old) in enumerate(zip(recall["records"], lattice["records"]), 1):
        identity = tuple(row[k] for k in ("pair_id", "plan_index", "sample_id"))
        if identity in seen or identity != tuple(old[k] for k in ("pair_id", "plan_index", "sample_id")):
            raise ValueError("duplicate_or_mismatched_context")
        seen.add(identity)
        packet = read(old["search_artifact"], old["search_artifact_sha256"], True)
        context = read(old["source_context_artifact"], old["source_context_sha256"], True)
        entry = packet["provenance"]["manifest_entry"]; validate_policy(entry)
        bundle, search = context["bundle"], packet["search"]
        if (entry not in manifest or packet["pair_id"] != row["pair_id"]
                or packet["plan_index"] != row["plan_index"] or packet["sample"]["sample_id"] != row["sample_id"]
                or packet["sample"]["span"] != row["sample_span"] or entry["split"] != row["split"]
                or entry["work_family_id"] != row["work_family_id"] or context["provenance"] != packet["provenance"]
                or context["pair_id"] != row["pair_id"] or context["plan_index"] != row["plan_index"]
                or _hash(bundle) != packet["input_bundle_content_sha256"]
                or search["input_bundle_content_sha256"] != packet["input_bundle_content_sha256"]):
            raise ValueError("frozen_context_binding_mismatch")
        t = perf_counter(); problem = prepare(bundle, search); times["prepare_seconds"] += perf_counter()-t
        t = perf_counter(); main = decode(problem); times["joint_decode_seconds"] += perf_counter()-t
        t = perf_counter(); emission = decode(problem, include_transitions=False); times["segment_only_decode_seconds"] += perf_counter()-t
        paths = paths_from_search(search, row["sample_span"])
        t = perf_counter(); retained = retained_music(problem, paths); times["retained_score_seconds"] += perf_counter()-t
        # References are accessed ONLY after all three predictions are fixed.
        cells = cells_from_record(row)
        from .harmony_candidate_recall import select
        predictions = {"retained_raw_baseline": select(paths), "retained_music": retained,
                       "direct_segment_only": evaluation_path(emission), "direct_joint_music": evaluation_path(main)}
        evaluations = {name: evaluate_selection(path, cells) for name, path in predictions.items()}
        base = evaluations["retained_raw_baseline"]
        if any(base[k] != row["evaluation"][k] for k in ("fully_evaluable", "selected_hit", "eligible_time", "selected_root_time", "selected_root_members_time")):
            raise ValueError("baseline_metric_changed")
        statuses[main["status"]] += 1
        rows.append({k: row[k] for k in ("pair_id", "plan_index", "sample_id", "work_family_id", "split", "sample_span")}
                    | {"selected_prediction": main["selected"], "decoder_status": main["status"],
                       "decoder_transitions": main["transitions"], "exact_optimum_under_declared_score": main["exact_optimum_under_declared_score"],
                       "zero_duration_observation_refs": problem.zero_duration_event_ids,
                       "evaluations": evaluations, "lattice_diagnosis": old["diagnosis"]["outcome"],
                       "lattice_hit": old["diagnosis"]["lattice_hit"],
                       "ablation_group_refs": {name: [s["group_id"] for s in path["segments"]] if path else None
                                               for name, path in predictions.items() if name != "direct_joint_music"},
                       "search_artifact": old["search_artifact"], "search_artifact_sha256": old["search_artifact_sha256"],
                       "source_context_artifact": old["source_context_artifact"], "source_context_sha256": old["source_context_sha256"]})
        if index % 40 == 0 or index == len(recall["records"]):
            print(f"[{index}/{len(recall['records'])}] scored joint decoding", flush=True)
        del packet, context, bundle, search, problem
    arms = list(rows[0]["evaluations"])
    summary = {name: summarize(rows, name) for name in arms}
    previous = recall["summary"]
    if any(summary["retained_raw_baseline"][k] != previous[k] for k in (
        "fully_evaluable_contexts", "selected_correct_contexts", "selected_context_agreement", "eligible_time",
        "selected_root_time_agreement", "selected_root_members_time_agreement",
    )):
        raise ValueError("frozen_summary_changed")
    guard(dict(inputs)); guard(code_hashes)
    result = {"version": VERSION, "decoder_version": DECODER_VERSION, "feature_version": FEATURE_VERSION,
              "complete": True, "summary": summary,
              "by_split": {split: {name: summarize([r for r in rows if r["split"] == split], name) for name in arms}
                           for split in sorted({r["split"] for r in rows})},
              "decoder_statuses": dict(statuses), "inference_seconds": dict(times),
              "records": rows, "input_hashes": inputs, "code_hashes": code_hashes,
              "weights": {k: rational(v) for k, v in DEFAULT_WEIGHTS.items()},
              "weights_origin": "fixed_heuristic_before_first_trial_not_learned_or_dev_tuned",
              "training_policy_audit": policy, "training_performed": False, "eligibility_changed": False,
              "source_labels_used_for_selection": False, "reference_labels_used_by_evaluator": True,
              "independent_test_accuracy_measured": False, "production_modified": False,
              "candidate_inventory_modified": False, "previous_predictions_modified": False,
              "metric_scope": "absolute_root_and_spelled_members_time_not_full_Roman_inversion_key_NCT_cadence",
              "elapsed_seconds": perf_counter()-started,
              "limits": ["Previously exposed train/dev contexts; overlapping, not independent works.",
                         "Exact optimum is relative to fixed score, available candidates and six-segment cap, not musical truth.",
                         "No consistent NCT/voice/applied-resolution score: masks remain unavailable.",
                         "Optimistic NCT bound is NOT subtracted as a licensed explanation.",
                         "All 33 package training permissions remain unapproved; no fitting performed.",
                         "Transition score observes attacks/root distance/shared members, not functional resolution."]}
    output.mkdir(parents=True, exist_ok=False)
    (output/"report.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recall", required=True); parser.add_argument("--lattice", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--expected-recall-sha", required=True); parser.add_argument("--expected-lattice-sha", required=True)
    args = parser.parse_args()
    result = run(args.recall, args.lattice, args.output, args.expected_recall_sha, args.expected_lattice_sha)
    print(json.dumps({"summary": result["summary"], "statuses": result["decoder_statuses"],
                      "elapsed_seconds": result["elapsed_seconds"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
