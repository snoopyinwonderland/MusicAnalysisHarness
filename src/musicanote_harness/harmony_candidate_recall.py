"""Post-hoc recall@24 and a label-blind fixed-rule development baseline.

Scores frozen proposals, never regenerates them from reference labels. This
first metric is absolute root + spelled chord members over exact time, NOT
full Roman/function/inversion accuracy or a new independent test benchmark.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from fractions import Fraction
from functools import lru_cache
import gzip
import hashlib
import json
from pathlib import Path
import re
from time import perf_counter

VERSION = "harmony-candidate-recall-0.1.0"
NATURAL_FIFTHS = {"F": -1, "C": 0, "G": 1, "D": 2, "A": 3, "E": 4, "B": 5}
BASELINE = "lexicographic_raw_nonmember_blocked_unknown_ratios_then_segments_then_id"


def fraction(value):
    if (not isinstance(value, dict) or type(value.get("numerator")) is not int
            or type(value.get("denominator")) is not int or value["denominator"] <= 0):
        raise ValueError("invalid_rational_coordinate")
    return Fraction(value["numerator"], value["denominator"])


def rational(value):
    return {"numerator": value.numerator, "denominator": value.denominator}


def spelling(value):
    if (not isinstance(value, (list, tuple)) or len(value) != 2
            or value[0] not in NATURAL_FIFTHS or type(value[1]) is not int):
        raise ValueError("invalid_spelling")
    return tuple(value)


def fifths_spelling(value):
    if type(value) is not int:
        raise ValueError("noninteger_fifths")
    step = next(s for s, n in NATURAL_FIFTHS.items() if (value - n) % 7 == 0)
    return step, (value - NATURAL_FIFTHS[step]) // 7


@lru_cache(maxsize=1024)
def _tonic_fifths(global_key, local_key, minor):
    # Reference-only key resolution. No result from here reaches select().
    from music21 import key, roman
    if not global_key or not local_key or minor not in ("0", "1"):
        raise ValueError("missing_source_key")
    token = global_key[:1] + global_key[1:].replace("b", "-")
    tonic = roman.RomanNumeral(local_key, key.Key(token)).root()
    alter = tonic.accidental.alter if tonic.accidental else 0
    if int(alter) != alter:
        raise ValueError("microtonal_source_key")
    return NATURAL_FIFTHS[tonic.step] + 7 * int(alter)


def source_signature(annotation):
    """DCML relative fifths, not pitch-class/enharmonic erasure or slash removal."""
    raw = annotation.get("raw_fields", {})
    if raw.get("pedal"):
        raise ValueError("pedal_reference_projection_unsupported")
    root, tones = raw.get("root", ""), raw.get("chord_tones", "")
    if not re.fullmatch(r"-?\d+", str(root)):
        raise ValueError("missing_or_ambiguous_source_root")
    tones = str(tones).strip()
    if tones.startswith("(") and tones.endswith(")"):
        tones = tones[1:-1].strip()
    if not re.fullmatch(r"-?\d+(?:\s*,\s*-?\d+)*", tones):
        raise ValueError("missing_or_ambiguous_source_members")
    tonic = _tonic_fifths(raw.get("globalkey"), raw.get("localkey"), raw.get("localkey_is_minor"))
    members = tuple(sorted({fifths_spelling(tonic + int(x.strip())) for x in tones.split(",")}))
    return fifths_spelling(tonic + int(root)), members


def reference_cells(span, annotations, alignments):
    start, end = fraction(span["start"]), fraction(span["end"])
    if start < 0 or end <= start:
        raise ValueError("invalid_context_span")
    approved = {}
    for item in alignments:
        aid = item["annotation_id"]
        if aid in approved:
            raise ValueError("duplicate_alignment")
        approved[aid] = item
    rows, seen = [], set()
    for item in annotations:
        aid = item["annotation_id"]
        if aid in seen:
            raise ValueError("duplicate_annotation")
        seen.add(aid)
        target = (item.get("target") or {}).get("span")
        if not target:
            continue
        a, b = fraction(target["start"]), fraction(target["end"])
        if b < a:
            raise ValueError("negative_reference_span")
        if a < end and start < b:
            rows.append((a, b, item))
    points = sorted({start, end, *[max(start, a) for a, _, _ in rows],
                     *[min(end, b) for _, b, _ in rows]})
    cells = []
    for a, b in zip(points, points[1:]):
        active = [row for x, y, row in rows if x <= a and b <= y]
        signature, reason, aid = None, None, None
        if len(active) != 1:
            reason = "annotation_gap" if not active else "annotation_overlap"
        else:
            row = active[0]; aid = row["annotation_id"]
            alignment = approved.get(aid, {})
            if (alignment.get("mapping_status") not in ("exact", "verified_transform")
                    or alignment.get("target") != row.get("target")):
                reason = "unverified_or_mismatched_alignment"
            else:
                try:
                    signature = source_signature(row)
                except Exception as exc:
                    # Keep unsupported cells in the coverage denominator.
                    reason = str(exc) if isinstance(exc, ValueError) else "source_key_projection_error"
        cells.append({"start": a, "end": b, "signature": signature,
                      "reason": reason, "annotation_id": aid})
    return cells


def paths_from_search(search, span):
    if search.get("source_labels_used") is not False or search.get("selected") is not None:
        raise ValueError("nonblind_or_already_selected_search")
    groups = {g["group_id"]: g for g in search.get("semantic_groups", [])}
    if len(groups) != len(search.get("semantic_groups", [])):
        raise ValueError("duplicate_semantic_group")
    start, end = fraction(span["start"]), fraction(span["end"])
    paths = []
    proposals = search.get("proposals", [])
    if len(proposals) > 24:
        raise ValueError("not_recall_at_24")
    ids = set()
    for proposal in proposals:
        pid = proposal["proposal_id"]
        if pid in ids or proposal.get("complete_context_path") is not True:
            raise ValueError("duplicate_or_incomplete_proposal")
        ids.add(pid)
        segments, cursor = [], start
        refs = proposal["semantic_group_refs"]
        if not refs or len(refs) != len(proposal["path"]):
            raise ValueError("proposal_reference_inventory_mismatch")
        for ref, adapter in zip(refs, proposal["path"]):
            if ref not in groups or adapter != groups[ref]["adapter_reading_key"]:
                raise ValueError("proposal_adapter_reference_mismatch")
            group = groups[ref]
            a, b = fraction(group["span"]["start"]), fraction(group["span"]["end"])
            if a != cursor or b <= a or b > end:
                raise ValueError("invalid_proposal_partition")
            root = None if group["root_spelling"] is None else spelling(group["root_spelling"])
            members = tuple(sorted({spelling(v) for v in group["members"]}))
            segments.append({"start": a, "end": b, "signature": (root, members), "group_id": ref})
            cursor = b
        if cursor != end:
            raise ValueError("incomplete_proposal_partition")
        paths.append({"proposal_id": pid, "segments": segments, "objective": proposal["objective"]})
    return paths


def select(paths):
    """A fixed, untrained baseline with no annotation or reference argument."""
    def rank(path):
        obj = path["objective"]
        total = fraction(obj["total_note_time"])
        if total <= 0:
            raise ValueError("nonpositive_baseline_note_time")
        values = [fraction(obj[k]) for k in ("raw_nonmember_note_time", "blocked_note_time", "spelling_unresolved_note_time")]
        if any(v < 0 or v > total for v in values):
            raise ValueError("invalid_baseline_objective")
        if obj["segment_count"] != len(path["segments"]):
            raise ValueError("segment_count_mismatch")
        return (*[v / total for v in values], obj["segment_count"], path["proposal_id"])
    return min(paths, key=rank) if paths else None


def agreement(path, cells):
    root_time, member_time = Fraction(), Fraction()
    for segment in path["segments"] if path else []:
        for cell in cells:
            signature = cell["signature"]
            if signature is None:
                continue
            duration = min(segment["end"], cell["end"]) - max(segment["start"], cell["start"])
            if duration > 0:
                if segment["signature"][0] == signature[0]:
                    root_time += duration
                if segment["signature"] == signature:
                    member_time += duration
    return root_time, member_time


def evaluate(paths, cells):
    selected = select(paths)  # Gold is not used to choose a candidate.
    eligible = sum((c["end"] - c["start"] for c in cells if c["signature"] is not None), Fraction())
    total = sum((c["end"] - c["start"] for c in cells), Fraction())
    if not total:
        raise ValueError("empty_reference_cells")
    selected_root, selected_members = agreement(selected, cells)
    agreements = [(p, *agreement(p, cells)) for p in paths]
    best_members = max((v[2] for v in agreements), default=Fraction())
    best_root = max((v[1] for v in agreements), default=Fraction())
    fully_evaluable = eligible == total
    hits = [p["proposal_id"] for p, _, m in agreements if fully_evaluable and m == total]
    selected_hit = selected_members == total if fully_evaluable else None
    if fully_evaluable:
        outcome = ("selected_correct" if selected_hit else "selection_error_with_reference_in_candidates"
                   if hits else "no_proposals" if not paths else "reference_not_in_retained_candidates")
    else:
        outcome = "reference_not_fully_evaluable"
    return {"proposal_count": len(paths), "fully_evaluable": fully_evaluable,
            "candidate_hit": bool(hits) if fully_evaluable else None,
            "matching_proposal_ids": hits, "selected_hit": selected_hit,
            "selected_proposal_id": selected["proposal_id"] if selected else None,
            "outcome": outcome, "eligible_time": rational(eligible), "context_time": rational(total),
            "selected_root_time": rational(selected_root), "selected_root_members_time": rational(selected_members),
            "oracle_root_time": rational(best_root), "oracle_root_members_time": rational(best_members)}


def _public_path(path):
    if not path:
        return None
    return {"proposal_id": path["proposal_id"], "selection_policy": BASELINE,
            "confidence": None, "human_validated": False, "source_labels_used_for_selection": False,
            "segments": [{"span": {"start": rational(s["start"]), "end": rational(s["end"])},
                          "root_spelling": s["signature"][0], "members": s["signature"][1],
                          "semantic_group_ref": s["group_id"]} for s in path["segments"]]}


def summarize(rows):
    total, eligible, selected_root, selected_members, oracle_root, oracle_members = (Fraction() for _ in range(6))
    full = hits = selected_hits = 0
    family = defaultdict(list)
    for row in rows:
        score = row["evaluation"]
        total += fraction(score["context_time"]); eligible += fraction(score["eligible_time"])
        selected_root += fraction(score["selected_root_time"])
        selected_members += fraction(score["selected_root_members_time"])
        oracle_root += fraction(score["oracle_root_time"])
        oracle_members += fraction(score["oracle_root_members_time"])
        full += score["fully_evaluable"]; hits += score["candidate_hit"] is True
        selected_hits += score["selected_hit"] is True
        family[row["work_family_id"]].append(score)
    def ratio(a, b):
        return float(a / b) if b else None
    return {"contexts": len(rows), "packages": len({r["pair_id"] for r in rows}), "work_families": len(family),
            "fully_evaluable_contexts": full, "candidate_hit_contexts": hits, "recall_at_24": ratio(hits, full),
            "selected_correct_contexts": selected_hits, "selected_context_agreement": ratio(selected_hits, full),
            "outcomes": dict(Counter(r["evaluation"]["outcome"] for r in rows)),
            "total_context_time": rational(total), "eligible_time": rational(eligible), "time_coverage": ratio(eligible, total),
            "selected_root_time_agreement": ratio(selected_root, eligible),
            "selected_root_members_time_agreement": ratio(selected_members, eligible),
            "oracle_root_time_agreement": ratio(oracle_root, eligible),
            "oracle_root_members_time_agreement": ratio(oracle_members, eligible),
            "family_context_recall": {fid: {"contexts": len(v), "fully_evaluable": sum(s["fully_evaluable"] for s in v),
                "hits": sum(s["candidate_hit"] is True for s in v)} for fid, v in sorted(family.items())},
            "overlapping_context_time_is_not_unique_score_duration": True}


def run(previous, output, expected_report_sha):
    started = perf_counter(); previous, output = Path(previous), Path(output)
    if output.exists():
        raise ValueError("output_exists_no_overwrite")
    inputs = {}
    def read(path, expected=None, compressed=False, lines=False):
        path = Path(path); payload = path.read_bytes(); digest = hashlib.sha256(payload).hexdigest()
        if expected and digest != expected:
            raise ValueError("input_sha_mismatch:" + str(path))
        name = str(path.resolve())
        if name in inputs and inputs[name] != digest:
            raise ValueError("input_changed_during_run")
        inputs[name] = digest
        text = (gzip.decompress(payload) if compressed else payload).decode("utf-8")
        return [json.loads(line) for line in text.splitlines() if line.strip()] if lines else json.loads(text)
    report = read(previous / "report.json", expected_report_sha)
    if (report.get("complete") is not True or report.get("source_labels_used") is not False
            or report.get("inputs_and_code_unchanged") is not True or report.get("artifacts_unchanged") is not True):
        raise ValueError("invalid_frozen_proposal_report")
    contract = read(previous / "run-contract.json", report["contract_sha256"])
    if contract["search_config"]["max_complete_paths"] != 24:
        raise ValueError("not_frozen_recall_at_24")
    rows, packages, entries, reference_reasons, seen = [], {}, {}, Counter(), set()
    from .source_locator_revision_trial import validate_policy
    for index, record in enumerate(report["records"], 1):
        packet = read(record["artifact"], record["sha256"], compressed=True)
        entry = packet["provenance"]["manifest_entry"]; validate_policy(entry)
        pair = record["pair_id"]
        if (packet["pair_id"] != pair or packet["plan_index"] != record["plan_index"]
                or packet["sample"]["sample_id"] != record["sample_id"]
                or packet.get("source_labels_used") is not False):
            raise ValueError("sample_binding_mismatch")
        identity = pair, record["sample_id"], record["plan_index"]
        if identity in seen:
            raise ValueError("duplicate_context")
        seen.add(identity)
        if pair in entries and entries[pair] != entry:
            raise ValueError("package_manifest_changed")
        entries[pair] = entry
        paths = paths_from_search(packet["search"], packet["sample"]["span"])
        chosen = _public_path(select(paths))  # Selection happens before reference loading.
        if pair not in packages:
            folder = Path(entry["package_path"])
            annotations = read(folder / "imported_annotations.jsonl", lines=True)
            alignments = read(folder / "alignment_records.jsonl", lines=True)
            if any(a.get("source_asset_sha256") != entry["annotation_sha256"]
                   or a.get("target") and a["target"].get("score_id") != entry["score_id"] for a in annotations):
                raise ValueError("reference_source_binding_mismatch")
            packages[pair] = annotations, alignments
        annotations, alignments = packages[pair]
        cells = reference_cells(packet["sample"]["span"], annotations, alignments)
        if packet["provenance"]["measure_revision_status"] != "not_required":
            # Do not retarget annotation spans onto a changed IR without a verified adapter.
            for cell in cells:
                cell.update(signature=None, reason="revised_ir_reference_binding_not_verified")
        score = evaluate(paths, cells)
        for cell in cells:
            if cell["reason"]:
                reference_reasons[cell["reason"]] += 1
        rows.append({"pair_id": pair, "sample_id": record["sample_id"], "plan_index": record["plan_index"],
                     "work_family_id": entry["work_family_id"], "split": entry["split"],
                     "artifact": record["artifact"], "artifact_sha256": record["sha256"],
                     "sample_span": packet["sample"]["span"], "selected_prediction": chosen, "evaluation": score,
                     "reference_cells": [{"span": {"start": rational(c["start"]), "end": rational(c["end"])},
                        "signature": c["signature"], "reason": c["reason"], "annotation_id": c["annotation_id"]} for c in cells]})
        if index % 40 == 0 or index == len(report["records"]):
            print(f"[{index}/{len(report['records'])}] development recall@24", flush=True)
        del packet
    expected = report["summary"]
    summary = summarize(rows)
    if (summary["contexts"] != expected["samples"] or summary["packages"] != expected["packages"]
            or summary["work_families"] != expected["work_families"]):
        raise ValueError("frozen_denominator_mismatch")
    changed = [p for p, sha in inputs.items() if hashlib.sha256(Path(p).read_bytes()).hexdigest() != sha]
    if changed:
        raise ValueError("inputs_changed:" + repr(changed))
    result = {"version": VERSION, "complete": True, "summary": summary,
              "reference_reason_counts": dict(reference_reasons), "records": rows,
              "elapsed_seconds": perf_counter() - started, "input_hashes": inputs,
              "code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "baseline_policy": BASELINE, "package_manifest": list(entries.values()),
              "metric_scope": "exact_absolute_root_and_spelled_members_over_time_not_full_Roman_or_inversion",
              "evaluation_scope": "previously_exposed_train_dev_contexts_development_diagnostic_not_independent_test",
              "source_labels_used_for_selection": False, "reference_labels_used_by_evaluator": True,
              "blind_test_accuracy_measured": False, "whole_score_accuracy_measured": False,
              "training_performed": False, "production_modified": False,
              "core_or_original_annotations_modified": False, "eligibility_changed": False,
              "limits": ["At most24 retained complete paths, not24 local chord labels.",
                         "Root/member semantics only: no inversion, local-key, function, or cadence correctness claim.",
                         "Partial/unsupported references and absent proposals remain explicit denominators.",
                         "Contexts overlap; their time sum and322 contexts are not independent pieces.",
                         "Oracle best path sees reference labels for evaluation only; baseline does not.",
                         "No automatic model training approval or source annotation promotion."]}
    output.mkdir(parents=True, exist_ok=False)
    (output / "report.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--previous", required=True); parser.add_argument("--output", required=True)
    parser.add_argument("--expected-report-sha", required=True)
    args = parser.parse_args()
    result = run(args.previous, args.output, args.expected_report_sha)
    print(json.dumps({"summary": result["summary"], "reference_reasons": result["reference_reason_counts"],
                      "elapsed_seconds": result["elapsed_seconds"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
