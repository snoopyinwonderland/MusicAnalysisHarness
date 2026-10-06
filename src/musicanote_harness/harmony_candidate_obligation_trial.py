"""Bounded, externally pinned saved-only candidate-obligation experiment."""
from dataclasses import asdict
from pathlib import Path
import time

from . import harmony_candidate_obligation_policy as core
from . import staged_completion_evidence_trial as storage
from . import progression_evidence_review_trial as saved
from . import factor_expanded_hypotheses as sealed
from . import native_progression_contrast as parent

VERSION = "harmony-candidate-obligation-trial-0.1.0"


def run(report_path, output, *, report_sha256, labels=("control", "linked"), limits=None,
        max_pairs=20000, progress=None):
    limits = limits or saved.ReviewLimits()
    if (not labels or len(set(labels)) != len(labels)
            or any(label not in ("control", "linked") for label in labels)):
        raise ValueError("explicit_unique_archived_completion_labels_required")
    report_path, output = Path(report_path).resolve(strict=True), Path(output).resolve()
    if output.exists():
        raise ValueError("new_obligation_output_required")
    started = time.monotonic()
    implementation = {str(Path(path).resolve()): saved._hash(Path(path)) for path in (core.__file__, __file__)}
    reader = storage.Reader(limits)
    report = reader.read(report_path, report_sha256)
    if (report["status"] != "complete_staged_saved_evidence_review_not_selected"
            # Parent certifies two complete requests in one context, NOT all
            # contexts of the historical archive. Do not inflate its scope.
            or report["full_archive_complete"] is not False
            or report["physical_inputs_unchanged"] is not True
            or any(report[k] is not None for k in ("selected", "rank", "confidence"))):
        raise ValueError("complete_pinned_parent_experiment_required")
    root = report_path.parent
    artifacts = {}
    for a in report["artifacts"]:
        p = Path(a["path"]).resolve(strict=True)
        if p.parent != root or p.name in artifacts:
            raise ValueError("unique_same_root_parent_artifacts_required")
        artifacts[p.name] = a
    source = reader.snapshot(artifacts["source-context.json.gz"], source=True)
    scope, bundles = source["scope"], source["bundles"]
    sealed._check(scope, "fmes_")
    keys = {k["record_id"]: k for k in source["lattice"]["keys"]}
    if len(keys) != len(source["lattice"]["keys"]):
        raise ValueError("unique_archived_key_hypotheses_required")
    for bundle in bundles.values():
        sealed._check(bundle, "fmilbundle_")
        if bundle["scope_ref"] != sealed._ref(scope):
            raise ValueError("source_bundle_closure_required")
    n = report["summary"]["paired_original_candidates"]
    if type(n) is not int or not 0 < n <= limits.max_entries_per_group*limits.max_groups:
        raise ValueError("complete_bounded_original_denominator_required")
    output.mkdir(parents=True, exist_ok=False)
    writer = storage.Writer(output, limits)
    summaries = {}
    writer.save("source-evidence.json.gz", {"scope": scope, "bundles": bundles,
        "key_hypotheses": source["lattice"]["keys"], "parent_report_sha256": report_sha256,
        "parent_source_artifact": artifacts["source-context.json.gz"],
        "source_XML_reparsed": False, "saved_JSON_restores_capability": False})
    for label in labels:
        plan, terminal = source["plans"][label], source["terminals"][label]
        sealed._check(plan, "npsreplayplan_")
        sealed._check(terminal, "npsreplayjob_")
        if (plan["planned_selectors"] != n or terminal["plan_ref"] != sealed._ref(plan)
                or terminal["scope_ref"] != sealed._ref(scope) or plan["reasons"] or terminal["reasons"]):
            raise ValueError("original_full_request_plan_terminal_required")
        names = sorted(name for name in artifacts if name.startswith(label+"-") and name.endswith(".json.gz"))
        if len(names) != plan["planned_batches"] or len(names) > limits.max_tasks:
            raise ValueError("all_original_review_batches_required")
        rows, lo = [], 0
        for bi, name in enumerate(names):
            if name != f"{label}-{bi:04d}.json.gz":
                raise ValueError("whole_original_review_batch_order_required")
            batch = reader.snapshot(artifacts[name])
            hi = batch["selector_end_exclusive"]
            expected = plan["batches"][bi]
            if (batch["source_scope_ref"] != sealed._ref(scope) or batch["bundle_ref"] != terminal["bundle_ref"]
                    or batch["batch_index"] != bi or batch["selector_start"] != lo
                    or type(hi) is not int or not lo < hi <= n
                    or batch["selector_start"] != expected["selector_start"]
                    or hi != expected["selector_end_exclusive"]
                    or [r["original_selector_index"] for r in batch["rows"]] != list(range(lo, hi))
                    or any(r["review"]["bundle_ref"] != batch["bundle_ref"] for r in batch["rows"])):
                raise ValueError("complete_review_position_source_bundle_binding_required")
            for row in batch["rows"]:
                review = row["review"]
                key = keys[review["key_ref"]["record_id"]]
                if (review["key_ref"] != sealed._ref(key)
                        or review["key_coordinate_available"] is not (bool(key["segments"]) and all(
                            s["tonic"] is not None and s["mode"] != "unknown" for s in key["segments"]))):
                    raise ValueError("original_key_hypothesis_not_inferred_required")
            rows.extend(batch["rows"])
            lo = hi
            if progress and (bi % 24 == 0 or bi+1 == len(names)):
                progress(f"{label}: read {len(rows)}/{n} complete candidate reviews")
        if lo != n:
            raise ValueError("whole_original_review_selector_coverage_required")
        result = core.compare_candidates(rows, scope, bundles, max_pairs=max_pairs)
        reader.final_guard()
        result.update(parent_report_sha256=report_sha256, archived_completion_label=label,
                      input_review_artifacts=[artifacts[name] for name in names])
        writer.save(label+"-candidate-policy.json.gz", result)
        summaries[label] = result["summary"]
        if progress:
            progress(f"{label}: {result['summary']}")
    writer.final_guard()
    reader.final_guard()
    if any(saved._hash(Path(path)) != sha for path, sha in implementation.items()):
        raise ValueError("obligation_implementation_changed_during_run")
    result = {"version": VERSION, "status": "computed_saved_candidate_obligation_policy_not_selected",
        "parent_report_sha256": report_sha256, "source_scope_ref": sealed._ref(scope),
        "complete_candidates_per_completion": n, "completion_summaries": summaries,
        "limits": asdict(limits), "max_pairs": max_pairs, "decoded_read_bytes": reader.bytes,
        "implementation_sha256": implementation,
        "read_ledger": reader.ledger, "artifacts": writer.artifacts.copy(),
        "elapsed_seconds": time.monotonic()-started, "physical_inputs_unchanged": True,
        "selected": None, "rank": None, "confidence": None, "flags": parent._flags(),
        "musical_accuracy_measured": False, "production_UI_modified": False,
        "key_or_completion_credit_unioned": False, "native_or_role_producer_replayed": False}
    writer.save("report.json", result, compress=False)
    return result
