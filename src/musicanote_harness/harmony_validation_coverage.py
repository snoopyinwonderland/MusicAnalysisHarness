"""Separate code-test counts, musical coverage, and proposed expansion cohorts.

This read-only source audit does not replay harmony, assign gold labels, or
change a dataset split.  A naming-derived identity is explicitly conservative;
only matching score AND annotation hashes connect a prepared package to the
existing manifest's policy.  New packages remain policy-blocked proposals.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path

from .harmony_dataset_manifest import _package_identity
from .harmony_progression_evidence_trial import digest, load, write

VERSION = "harmony-validation-coverage-0.1.0"
SONATA_COLLECTIONS = {"beethoven-sonatas", "mozart-sonatas"}


def _hash_key(row):
    return row.get("score_sha256"), row.get("annotation_sha256")


def _known_identity(entry):
    return all(entry.get(k) for k in
               ("corpus_id", "collection_id", "work_family_id", "movement_id")) and (
        entry.get("work_family_confidence") != "unresolved_work_family")


def audit(latest, shared, provenances, tracks, manifest, identities, *,
          unit_test_count=None, family_limit=6):
    """Pure report/planner; ``identities`` are preparation-report-derived refs."""
    if family_limit < 1:
        raise ValueError("positive_family_limit_required")
    if unit_test_count is not None and (
        isinstance(unit_test_count, bool) or not isinstance(unit_test_count, int)
        or unit_test_count < 0
    ):
        raise ValueError("nonnegative_integer_test_count_required")
    entries = manifest["entries"]
    by_hash = defaultdict(list)
    family_splits = defaultdict(set)
    score_splits = defaultdict(set)
    annotation_splits = defaultdict(set)
    for entry in entries:
        key = _hash_key(entry)
        if all(key):
            by_hash[key].append(entry)
        family_splits[entry.get("work_family_id")].add(entry.get("split"))
        if entry.get("score_sha256"):
            score_splits[entry["score_sha256"]].add(entry.get("split"))
        if entry.get("annotation_sha256"):
            annotation_splits[entry["annotation_sha256"]].add(entry.get("split"))
    leaked_families = sorted(str(k) for k, splits in family_splits.items()
                             if len(splits) > 1 or None in splits)
    leaked_scores = sorted(k for k, splits in score_splits.items()
                           if len(splits) > 1 or None in splits)
    leaked_annotations = sorted(k for k, splits in annotation_splits.items()
                                if len(splits) > 1 or None in splits)

    case_identities = {}
    for row in latest["records"]:
        case = row["case_id"]
        if case in case_identities:
            continue
        if case not in provenances:
            raise ValueError("latest_case_missing_provenance")
        entry = provenances[case]["manifest_entry"]
        matches = by_hash.get(_hash_key(entry), [])
        if not _known_identity(entry) or not matches or any(
            other.get(k) != entry.get(k) for other in matches
            for k in ("work_family_id", "movement_id", "collection_id", "split")
        ):
            raise ValueError("latest_identity_not_verified_against_manifest")
        case_identities[case] = deepcopy(entry)
    pilot_families = {e["work_family_id"] for e in case_identities.values()}
    pilot_scores = {e["score_sha256"] for e in case_identities.values()}
    pilot_annotations = {e["annotation_sha256"] for e in case_identities.values()}
    pilot_keys = {(e["corpus_id"], e["collection_id"], e["work_family_id"], e["movement_id"])
                  for e in case_identities.values()}
    pilot_counts = Counter(row["case_id"] for row in latest["records"])
    shared_cases = {row["case_id"]: row for row in shared.get("real", [])}

    quality_counts = Counter()
    review_counts = Counter()
    alignment_total = 0
    complete_sonata = []
    for track in tracks:
        quality_counts[track.get("alignment_quality", "unknown")] += 1
        review_counts[track.get("human_review_status", "unknown")] += 1
        alignment_total += bool(track.get("alignment_eligible"))
        identity = identities.get(track["pair_id"])
        if not identity:
            raise ValueError("prepared_track_identity_missing")
        if (track.get("alignment_quality") != "validated_complete"
            or identity["collection_id"] not in SONATA_COLLECTIONS):
            continue
        matches = by_hash.get(_hash_key(identity), [])
        compatible = len(matches) == 1 and _known_identity(matches[0]) and all(
            matches[0].get(k) == identity.get(k)
            for k in ("work_family_id", "collection_id", "movement_id")
        )
        policy = deepcopy(matches[0]) if compatible else None
        family = identity["work_family_id"]
        blockers = []
        if not policy:
            blockers.append("unknown_cross_manifest_split_or_identity")
        else:
            if family in leaked_families:
                blockers.append("work_family_split_conflict")
            if identity["score_sha256"] in leaked_scores:
                blockers.append("score_hash_split_conflict")
            if identity["annotation_sha256"] in leaked_annotations:
                blockers.append("annotation_hash_split_conflict")
            if policy.get("split") not in {"train", "dev", "holdout"}:
                blockers.append("unknown_cross_manifest_split")
            if not policy.get("rights", {}).get("internal_research_use"):
                blockers.append("internal_research_not_approved")
            if policy.get("split") == "holdout":
                blockers.append("protected_holdout_not_replayed_by_this_planner")
        if not track.get("alignment_eligible"):
            blockers.append("alignment_not_eligible")
        if not _known_identity(identity):
            blockers.append("unresolved_work_family_identity")
        complete_sonata.append({
            "pair_id": track["pair_id"], "identity": deepcopy(identity),
            "identity_basis": "preparation_report_collection_naming_convention",
            "manifest_entry": policy,
            "alignment_quality": track["alignment_quality"],
            "human_review_status": track.get("human_review_status", "unknown"),
            "canonical_ir_path": track.get("canonical_ir_path"),
            "preparation_report_path": track.get("report_path"),
            "exact_alignments": track.get("exact_alignments", 0),
            "verified_transform_alignments": track.get("verified_transform_alignments", 0),
            "blockers": blockers,
            "internal_development_replay_eligible": not blockers,
            "existing_blind_evaluation_eligibility": (
                policy.get("eligibility", {}).get("blind_evaluation", False) if policy else None),
            "gold_eligibility": None, "training_eligibility_promoted": False,
        })

    groups = defaultdict(list)
    excluded_identity_overlap = []
    for item in complete_sonata:
        identity = item["identity"]
        if identity["work_family_id"] in pilot_families:
            continue
        if identity["score_sha256"] in pilot_scores or identity["annotation_sha256"] in pilot_annotations:
            excluded_identity_overlap.append(item["pair_id"])
        else:
            groups[item["identity"]["work_family_id"]].append(item)
    proposals = []
    for family, members in groups.items():
        # Family-wide compatibility prevents a known movement from laundering an
        # unknown movement's split or rights.  Preserve every original policy.
        blockers = sorted({b for item in members for b in item["blockers"]})
        splits = {item["manifest_entry"].get("split") for item in members
                  if item["manifest_entry"]}
        if len(splits) > 1:
            blockers.append("work_family_split_conflict")
        identity = members[0]["identity"]
        proposals.append({
            "work_family_id": family,
            "collection_id": identity["collection_id"],
            "work_family_source_key": identity["work_family_source_key"],
            "existing_splits": sorted(splits), "members": sorted(members, key=lambda m: m["pair_id"]),
            "blockers": sorted(set(blockers)),
            "internal_development_replay_eligible": not blockers,
            "proposal_only": True,
        })
    proposals.sort(key=lambda p: (bool(p["blockers"]),
                                 all(m["manifest_entry"] is None for m in p["members"]),
                                 p["collection_id"], p["work_family_source_key"], p["work_family_id"]))
    selected = proposals[:family_limit]
    return {
        "version": VERSION,
        "code_tests": {"count": unit_test_count, "unit": "Python test cases",
                       "music_work_count": False, "harmony_accuracy_metric": False},
        "latest_real_pilot": {
            "sample_records": len(latest["records"]),
            "unique_sample_keys": len({(r["case_id"], r["sample"]) for r in latest["records"]}),
            "unique_movements": len(pilot_keys), "unique_work_families": len(pilot_families),
            "status_counts": dict(Counter(r.get("status", "unknown") for r in latest["records"])),
            "movements": [{"case_id": case, "title": shared_cases.get(case, {}).get("title"),
                           "identity": entry, "latest_samples": pilot_counts[case],
                           "earlier_shared_context_samples": shared_cases.get(case, {}).get("samples")}
                          for case, entry in sorted(case_identities.items())],
        },
        "earlier_shared_context": {
            "sample_windows": sum(r.get("samples", 0) for r in shared.get("real", [])),
            "movement_case_records": len(shared.get("real", [])),
            "not_additional_unique_works": True,
        },
        "prepared_data": {
            "package_records": len(tracks), "alignment_quality_counts": dict(quality_counts),
            "alignment_eligible_packages": alignment_total,
            "human_review_status_counts": dict(review_counts),
            "complete_sonata_packages": len(complete_sonata),
            "complete_sonata_by_collection": dict(Counter(
                item["identity"]["collection_id"] for item in complete_sonata)),
            "alignment_validation_is_harmony_accuracy": False,
            "gold_status_inferred": False,
        },
        "cohort_plan": {
            "selection": "deterministic whole-work-family proposals; known policy first",
            "family_limit": family_limit, "candidate_families": len(proposals),
            "selected_families": len(selected),
            "selected_movements": sum(len(p["members"]) for p in selected),
            "selected_internal_replay_eligible_families": sum(
                p["internal_development_replay_eligible"] for p in selected),
            "excluded_pilot_family_ids": sorted(pilot_families),
            "existing_manifest_split_conflicts": leaked_families,
            "existing_manifest_score_hash_split_conflicts": leaked_scores,
            "existing_manifest_annotation_hash_split_conflicts": leaked_annotations,
            "excluded_pilot_score_or_annotation_overlap": sorted(excluded_identity_overlap),
            "selected": selected,
            "unselected_families": [p["work_family_id"] for p in proposals[family_limit:]],
            "evaluation_protocol": {
                "keep_whole_work_families_together": True,
                "same_work_editions_and_annotation_lineages_must_not_cross_splits": True,
                "require_positive_cases_and_close_counterexamples": True,
                "report_unsupported_and_abstention_separately": True,
                "source_labels_for_posthoc_comparison_only": True,
                "no_corpus_replay_performed": True,
                "no_new_blind_or_gold_eligibility": True,
            },
        },
        "accuracy_measured": False, "production_modified": False,
        "split_or_rights_modified": False, "external_transmission_performed": False,
    }


def run(latest_report, shared_report, prepared_tracks, manifest_path, output, *,
        unit_test_count=None, family_limit=6):
    paths = [Path(p).resolve() for p in
             (latest_report, shared_report, prepared_tracks, manifest_path)]
    frozen = {str(p): digest(p) for p in paths}

    def freeze(path, expected=None):
        path = Path(path).resolve()
        value = digest(path)
        if expected is not None and value != expected:
            raise ValueError("input_hash_changed")
        if str(path) in frozen and frozen[str(path)] != value:
            raise ValueError("input_hash_changed")
        frozen[str(path)] = value

    latest, shared, manifest = load(paths[0]), load(paths[1]), load(paths[3])
    import json
    tracks = [json.loads(line) for line in paths[2].read_text(encoding="utf-8").splitlines()
              if line.strip()]
    provenances = {}
    for row in latest["records"]:
        freeze(row["artifact"], row["sha256"])
    for case in {r["case_id"] for r in latest["records"]}:
        ref = next((r for r in shared.get("real", []) if r["case_id"] == case), None)
        if ref is None:
            raise ValueError("latest_case_missing_shared_reference")
        folder = paths[1].parent / "real-cases" / case / "source-snapshot"
        for name, sha in ref["source_hashes"].items():
            if Path(name).name != name:
                raise ValueError("snapshot_path_must_be_local_filename")
            freeze(folder / name, sha)
        provenance = folder / "case-provenance.json"
        if "case-provenance.json" not in ref["source_hashes"]:
            raise ValueError("provenance_hash_missing")
        provenances[case] = load(provenance)
    identities = {}
    source_root = paths[2].parent / "pairs"
    for track in tracks:
        report_path = Path(track["report_path"]).resolve()
        freeze(report_path)
        preparation = load(report_path)
        if preparation["source_sha256"] != track["source_sha256"]:
            raise ValueError("prepared_report_hash_identity_conflict")
        identity = _package_identity(report_path.parent, source_root, preparation)
        if track["pair_id"] in identities:
            raise ValueError("duplicate_prepared_pair_id")
        identities[track["pair_id"]] = identity
    answer = audit(latest, shared, provenances, tracks, manifest, identities,
                   unit_test_count=unit_test_count, family_limit=family_limit)
    for family in answer["cohort_plan"]["selected"]:
        for member in family["members"]:
            freeze(member["canonical_ir_path"])
    for path, sha in frozen.items():
        if digest(Path(path)) != sha:
            raise ValueError("input_mutated")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    write(output / "run-contract.json", {
        "version": VERSION, "input_sha256": frozen,
        "code_sha256": {str(p.resolve()): digest(p) for p in
                        (Path(__file__), Path(__file__).with_name("harmony_dataset_manifest.py"),
                         Path(__file__).with_name("harmony_progression_evidence_trial.py"))},
        "internal_only": True, "no_source_overwrite": True,
        "external_api_transmission": False, "model_training": False,
        "source_ir_semantics_revalidated": False,
    })
    write(output / "report.json", answer)
    return answer


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("latest-report", "shared-report", "prepared-tracks", "manifest", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--unit-test-count", type=int)
    parser.add_argument("--family-limit", type=int, default=6)
    args = parser.parse_args()
    answer = run(args.latest_report, args.shared_report, args.prepared_tracks, args.manifest,
                 args.output, unit_test_count=args.unit_test_count, family_limit=args.family_limit)
    print({"pilot_movements": answer["latest_real_pilot"]["unique_movements"],
           "prepared_packages": answer["prepared_data"]["package_records"],
           "proposed_families": answer["cohort_plan"]["selected_families"],
           "eligible_internal_replay_families":
               answer["cohort_plan"]["selected_internal_replay_eligible_families"]})
