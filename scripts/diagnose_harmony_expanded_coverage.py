"""Post-hoc J3b coverage diagnosis; never resample or repair reference clocks."""
import argparse
from collections import Counter, defaultdict
from fractions import Fraction
import gzip
import hashlib
import json
from pathlib import Path

from musicanote_harness.harmony_candidate_recall import fraction, rational
from musicanote_harness.harmony_path_context import plan as context_plan


def read(path):
    data = Path(path).read_bytes()
    return json.loads(gzip.decompress(data) if str(path).endswith(".gz") else data)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def brief(row):
    selected = row["selected_prediction"]
    return {"pair_id": row["pair_id"], "sample_id": row["sample_id"],
            "span": row["sample_span"], "status": row["status"],
            "elapsed_seconds": row["elapsed_seconds"],
            "stage_summary": row.get("stage_summary"),
            "candidate_ceiling": row["candidate_ceiling"]["lattice_hit"],
            "retained24_hit": row["retained24"]["candidate_hit"],
            "selected_hit": row["evaluation"]["selected_hit"],
            "components": row["evaluation"]["components"]["root_members"],
            "prediction": [{k: s[k] for k in ("span", "root_spelling", "members")}
                           for s in selected["segments"]] if selected else None,
            "reference": row["reference_cells"]}


def run(source, output):
    source, output = Path(source), Path(output)
    if output.exists():
        raise ValueError("choose_new_diagnostic_output")
    report = read(source/"report.json")
    audit = read(source/"diagnostics-r1/audit.json")
    if not audit["complete"] or audit["report_sha256"] != digest(source/"report.json"):
        raise ValueError("audited_report_changed")
    records = report["records"]
    plan = read(source/"frozen-plan.json")
    packages = {p["entry"]["pair_id"]: p for p in plan["packages"]}
    totals = defaultdict(lambda: {k: Fraction() for k in ("context", "eligible", "matched", "covered")})
    counts = Counter()
    unsupported = defaultdict(Fraction)
    tails = []
    full_cross = Counter()
    for row in records:
        start, end = (fraction(row["sample_span"][k]) for k in ("start", "end"))
        status = row["status"]
        counts[status] += 1
        totals[status]["context"] += end-start
        component = row["evaluation"]["components"]["root_members"]
        for name in ("eligible", "matched"):
            totals[status][name] += fraction(component[name])
        totals[status]["covered"] += fraction(component["covered"])
        if row["evaluation"]["fully_evaluable"]:
            full_cross[str((row["candidate_ceiling"]["lattice_hit"],
                            row["retained24"]["candidate_hit"], row["evaluation"]["selected_hit"]))] += 1
        for cell in row["reference_cells"]:
            a, b = (fraction(cell["span"][k]) for k in ("start", "end"))
            if cell["reason"]:
                unsupported[cell["reason"]] += b-a
            if max(a.denominator, b.denominator) > 1000000:
                # Bounded approximation is ONLY a receipt to diagnose imported
                # decimal residue. It never enters metrics or chord selection.
                deltas = [v-v.limit_denominator(4096) for v in (a, b)]
                tails.append({"pair_id": row["pair_id"], "sample_id": row["sample_id"],
                              "annotation_id": cell["annotation_id"], "span": cell["span"],
                              "reason": cell["reason"],
                              "endpoint_decimal_residue_probe": [rational(v) for v in deltas],
                              "probe_is_not_a_verified_source_clock_repair": True})
    status_rows = {s: {"contexts": counts[s], **{k+"_time": rational(v) for k, v in t.items()}}
                   for s, t in totals.items()}
    columns = {name: {"contexts": table["contexts"], "full": table["fully_evaluable_contexts"],
                     "correct": table["selected_correct_contexts"], "selected": table["selected_contexts"],
                     "root": table["components"]["root"]["time_agreement"],
                     "root_members": table["components"]["root_members"]["time_agreement"],
                     "coverage": table["components"]["root_members"]["prediction_coverage"],
                     "boundary_f1": table["semantic_boundary_exact"]["f1"]}
               for name, table in report["by_collection"].items()}
    long = sorted(records, key=lambda r: fraction(r["sample_span"]["end"])-fraction(r["sample_span"]["start"]), reverse=True)
    abstentions = [brief(r) for r in records if r["selected_prediction"] is None]
    for row in abstentions:
        package = packages[row["pair_id"]]
        sample = next(s["sample"] for s in package["plan"]["selected_samples"]
                      if s["sample"]["sample_id"] == row["sample_id"])
        path = package["observation_ir_path"]
        if digest(path) != report["artifact_hashes"][path]:
            raise ValueError("observation_ir_changed")
        ir = read(path)
        row["frozen_sample_abstention_reasons"] = sample["abstention_reasons"]
        row["score_only_context_policy"] = context_plan(ir, sample["span"], {"span": sample["span"]})
        sounds = {s["sounding_event_id"]: s for s in ir["sounding_events"]}
        notes = {n["note_id"]: n for n in ir["note_events"]}
        row["seed_sound_receipts"] = []
        for event_id in sample["seed_event_refs"]:
            sound = sounds[event_id]
            row["seed_sound_receipts"].append({"sounding_event_id": event_id, "span": sound["span"],
                "notes": [{k: n[k] for k in ("note_id", "measure_id", "part_id", "voice_id", "grace", "notated_duration_quarter") if k in n}
                          for n in (notes[nid] for nid in sound["source_note_ids"])]})
    result = {"version": "harmony-expanded-coverage-diagnosis-0.1.0", "complete": True,
              "report_sha256": digest(source/"report.json"), "auditor_sha256": digest(source/"diagnostics-r1/audit.json"),
              "diagnostic_code_sha256": digest(__file__), "collection_table": columns,
              "status_time": status_rows,
              "unsupported_reference_time": {k: rational(v) for k, v in unsupported.items()},
              "full_reference_cross_table_keys": ["expanded_ceiling", "retained24_hit", "selected_hit"],
              "full_reference_cross_table": dict(full_cross),
              "ceiling_outcome_control_caveat": "J3b passed candidate_hit=False to the expanded oracle. Its retention_or_search_budget_loss string is not an actual retained24 failure count. Use this cross table, not that string.",
              "decimal_tail_cells": tails,
              "longest_contexts": [brief(r) for r in long[:6]],
              "abstentions": abstentions,
              "examples": [brief(c["record"]) for c in audit["examples"]],
              "selection_and_reference_unchanged": True,
              "no_resampling_or_weight_tuning": True,
              "not_new_accuracy_sample_or_blind_test": True}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k not in ("longest_contexts", "abstentions", "examples", "decimal_tail_cells")}, ensure_ascii=False, indent=2))
    print("decimal_tail_cells="+str(len(tails)))
    print(json.dumps([{k: r[k] for k in ("pair_id", "sample_id", "span", "status", "components")} for r in result["longest_contexts"]], indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    run(args.source, args.output)
