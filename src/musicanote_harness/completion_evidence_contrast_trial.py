"""Bounded saved-only, complete-request link-sensitivity review.

Uses externally pinned receipts and original native/role batches. It does not
re-admit live parser authority, infer voices or rerun native/role producers.
Every selector in the declared request is retained, not a favourable prefix.
"""
from collections import Counter
from copy import deepcopy
from dataclasses import asdict
import gzip
import hashlib
import io
import json
from pathlib import Path
import time

from . import completion_evidence_contrast as core
from . import progression_evidence_review as review
from . import progression_evidence_review_trial as saved
from . import factor_expanded_hypotheses as sealed
from . import native_progression_contrast as parent
from . import native_progression_contrast_trial as join
from . import native_progression_policy as policy
from . import source_progression_replay_trial as replay
from .musical_pattern_observation import digest, f

VERSION = "completion-evidence-contrast-trial-0.1.0"


class Reader(saved.Reader):
    def record(self, info, prefix, registry, root):
        path = Path(info["artifact"]).resolve(strict=True)
        if (root not in path.parents or registry.get(str(path)) != info["sha256"]
                or path.suffix != ".gz"):
            raise ValueError("original_pinned_archive_record_required")
        size, cap = path.stat().st_size, self.limits.max_json_file_bytes
        if size > cap:
            raise ValueError("compressed_record_physical_limit")
        with path.open("rb") as stream:
            compressed = stream.read(cap + 1)
        if len(compressed) != size or hashlib.sha256(compressed).hexdigest() != info["sha256"]:
            raise ValueError("original_archive_physical_pin_mismatch")
        parts, n = [], 0
        with gzip.GzipFile(fileobj=io.BytesIO(compressed), mode="rb") as stream:
            while True:
                remaining = min(cap - n, self.limits.max_total_decoded_bytes - self.bytes)
                chunk = stream.read(min(1024 * 1024, remaining + 1))
                if not chunk:
                    break
                n += len(chunk)
                self.bytes += len(chunk)
                if n > cap or self.bytes > self.limits.max_total_decoded_bytes:
                    raise ValueError("whole_decoded_archive_read_limit")
                parts.append(chunk)
        value = json.loads(b"".join(parts), object_pairs_hook=saved._pairs,
                           parse_constant=saved._invalid_constant)
        sealed._check(value, prefix)
        if sealed._ref(value) != info["record_ref"] or value["status"] != info["status"]:
            raise ValueError("original_archive_record_reference_mismatch")
        self.ledger.append({"path": str(path), "bytes": size, "decoded_bytes": n, "sha256": info["sha256"]})
        return value


def _flags(row):
    if (any(row[k] is not None for k in ("selected", "rank", "confidence")) or
            any(v is not False for v in row["flags"].values())):
        raise ValueError("unpromoted_saved_review_required")


def _registry(receipt, root):
    found = [r for r in receipt["storage_execution"]["plan"]["protected_roots"]
             if Path(r["directory"]).resolve(strict=True) == root]
    if len(found) != 1:
        raise ValueError("one_pinned_original_archive_root_required")
    return {str(Path(p).resolve(strict=True)): sha for p, sha in found[0]["registered_sha256"].items()}


def _index(rows, scope, lattice, source_index):
    if type(source_index) is not int or not 0 <= source_index < len(rows):
        raise ValueError("exact_original_source_index_required")
    row = rows[source_index]
    if (row["error"] is not None or row["scope"]["record_ref"] != sealed._ref(scope)
            or row["fresh_lattice"]["record_ref"] != sealed._ref(lattice)):
        raise ValueError("original_index_source_binding_required")
    return row


def run(receipt_path, control_report_path, archive_root, source_catalog_path, output, *,
        receipt_sha256, control_sha256, source_index, completion_index, limits=None, progress=None):
    limits = saved.ReviewLimits() if limits is None else limits
    if type(limits) is not saved.ReviewLimits:
        raise ValueError("exact_completion_review_limits_required")
    started, reader = time.perf_counter(), Reader(limits)
    receipt_path, control_path = (Path(p).resolve(strict=True) for p in (receipt_path, control_report_path))
    root = Path(archive_root).resolve(strict=True)
    source_path = Path(source_catalog_path).resolve(strict=True)
    output = Path(output).resolve()
    if (output.exists() or any(output == p or p in output.parents or output in p.parents
            for p in (root, receipt_path.parent, control_path.parent, source_path.parent))):
        raise ValueError("new_disjoint_completion_output_required")
    receipt = reader.read(receipt_path, receipt_sha256)
    control_report = reader.read(control_path, control_sha256)
    if (receipt["storage_execution"]["storage_terminal"]["selected_request_storage_complete"] is not True
            or control_report["physical_inputs_unchanged"] is not True
            or control_report["role_predicates_reinferred"] is not False):
        raise ValueError("complete_pinned_control_review_required")
    _flags(control_report)
    registry = _registry(receipt, root)
    index_path = root / "context-index.json"
    rows = reader.read(index_path, registry[str(index_path)])
    # The prior receipt pins the source-once artifact separately from the native
    # archive. No public JSON number is restored as a native capability.
    source_registry = _registry(receipt, source_path.parent.parent)
    source = reader.read(source_path, source_registry[str(source_path)], source=True)
    scope, lattice, bundles = source["source_scope"], source["lattice"], source["bundles"]
    context = _index(rows, scope, lattice, source_index)
    if type(completion_index) is not int or not 0 <= completion_index < len(context["jobs"]):
        raise ValueError("exact_original_completion_index_required")
    job = context["jobs"][completion_index]
    if (job["status"] != "computed_native_role_source_requests_not_selected"
            or job["error"] is not None or job["unpersisted_selector_ranges"]):
        raise ValueError("complete_original_linked_request_required")
    bundle = reader.record(job["bundle"], replay.engine.native.BUNDLE_PREFIX, registry, root)
    if bundles.get(bundle["record_id"]) != bundle or not bundle["materialized_witness_links"]:
        raise ValueError("same_source_nonempty_link_completion_required")
    plan = reader.record(job["plan"], "npsreplayplan_", registry, root)
    terminal = reader.record(job["job"], replay.engine.PREFIX, registry, root)
    count = plan["planned_selectors"]
    if (count != job["planned_selector_occurrences"] or count > limits.max_entries_per_group * limits.max_groups
            or len(job["batches"]) != plan["planned_batches"] or plan["reasons"]
            or terminal["reasons"] or terminal["bundle_ref"] != sealed._ref(bundle)
            or terminal["scope_ref"] != sealed._ref(scope) or terminal["lattice_ref"] != sealed._ref(lattice)
            or terminal["plan_ref"] != sealed._ref(plan) or terminal["proposal_ref"] != plan["proposal_ref"]
            or terminal["fresh_registered_links"] != bundle["materialized_witness_links"]):
        raise ValueError("complete_original_request_plan_terminal_join_required")
    _flags(terminal)
    if (control_report["summary"]["reviewed_candidates"] != count
            or control_report["selected_completion"]["completion_requests"] != 1):
        raise ValueError("whole_counterpart_control_required")
    artifact_map = {a["path"]: a for a in control_report["artifacts"]}
    controls = {}
    if len(control_report["groups"]) > limits.max_groups:
        raise ValueError("whole_control_group_limit")
    for g in control_report["groups"]:
        p = (control_path.parent / g["review_file"]).resolve(strict=True)
        if p.parent != control_path.parent:
            raise ValueError("foreign_control_review_artifact")
        a = artifact_map[str(p)]
        group = reader.read(p, a["sha256"], a["bytes"])
        if (group["source_catalog_ref"] != sealed._ref(source) or group["catalog_ref"] != g["catalog_ref"]
                or len(group["candidate_reviews"]) > limits.max_entries_per_group):
            raise ValueError("same_source_complete_control_group_required")
        for row in group["candidate_reviews"]:
            i = row["original_selector_index"]
            if type(i) is not int or i in controls:
                raise ValueError("unique_original_control_selector_required")
            cb = bundles[row["bundle_ref"]["record_id"]]
            if cb["materialized_witness_links"] or cb["status"] != "complete_all_lane_witness":
                raise ValueError("all_no_link_counterpart_control_required")
            controls[i] = row
    if set(controls) != set(range(count)):
        raise ValueError("every_original_control_selector_required")
    keys = parent._lookup(lattice["keys"], "completion_review_key")
    origins = parent._lookup([o for c in lattice["catalog_inventory"] for o in c["origins"]], "completion_review_origin")
    sounds = {s["sound_ref"]: s for s in scope["sound_facts"]}
    cache = {"profiles": {}, "guards": {sid: {
        "strict": not sealed._source_blockers(s) and not parent.temporal._guard_codes(s),
        "role_blocked": bool(parent.temporal._guard_codes(s))} for sid, s in sounds.items()}}
    output.mkdir(parents=True, exist_ok=False)
    artifacts, total = [], 0
    def save(name, value):
        nonlocal total
        raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        if len(raw) > limits.max_output_file_bytes or total + len(raw) > limits.max_total_output_bytes:
            raise ValueError("whole_completion_output_limit")
        p = output / name
        with p.open("xb") as stream:
            if stream.write(raw) != len(raw):
                raise OSError("short_completion_output_write")
        total += len(raw)
        artifacts.append({"path": str(p), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
    save("source-context.json", {"binding": scope["binding"], "analysis_span": scope["analysis_span"],
        "sound_facts": scope["sound_facts"], "source_audit": scope["source_audit"],
        "source_catalog_ref": sealed._ref(source), "completion": bundle,
        "source_file_reparsed": False, "musical_voice_validated": False})
    summary, issues, selectors, refs = Counter(), Counter(), [], []
    counts = replay._empty_counts(count, plan["planned_batches"])
    counts["fresh_bundle_registrations"] = 1  # An archived count, not a new registration.
    seen_paths = set()
    for bi, batch in enumerate(job["batches"]):
        lo, hi = batch["selector_start"], batch["selector_end_exclusive"]
        if type(lo) is not int or type(hi) is not int or batch["batch_index"] != bi or lo != len(selectors) or not lo < hi <= count:
            raise ValueError("complete_original_batch_order_required")
        comparison = reader.record(batch["comparison"], replay.engine.native.COMPARISON_PREFIX, registry, root)
        explanation = reader.record(batch["explanation"], replay.engine.roles.PREFIX, registry, root)
        current_selectors = comparison["selectors"]
        planned = {k: batch[k] for k in replay.PLAN_BATCH_KEYS}
        replay._batch(comparison, explanation, current_selectors,
                      {"scope": scope, "lattice": lattice}, bundle, planned, plan["resource_limits"])
        if len(current_selectors) != hi - lo:
            raise ValueError("complete_original_batch_positions_required")
        result_rows = []
        for ordinal, (selector, path, role) in enumerate(zip(current_selectors, comparison["paths"], explanation["paths"])):
            identity = digest(path["logical_tuple"])
            if identity in seen_paths:
                raise ValueError("duplicate_original_logical_path")
            seen_paths.add(identity)
            entry = join._entry(path, role, selector, comparison, explanation, lattice, scope, bundle, origins, keys)
            facet = parent._facet(entry, scope, [origins[i] for i in selector["origin_ids"]], sounds)
            entry_refs = {k: facet[k] for k in ("native_path_ref", "role_path_ref", "comparison_ref", "explanation_ref")}
            key = policy._validate_facet(facet, entry_refs, scope, keys, bundles, origins, sounds, cache)
            linked = review.review_facet(facet, key)
            i = lo + ordinal
            contrast = core.compare_reviews(controls[i], linked, scope, bundles)
            result_rows.append({"original_selector_index": i, "linked_review": linked, "contrast": contrast})
            credit_delta = f(contrast["conditional_credit_delta_quarters"])
            summary["paired_original_candidates"] += 1
            summary["conditional_credit_increased_candidates"] += credit_delta > 0
            summary["conditional_credit_decreased_candidates"] += credit_delta < 0
            summary["conditional_credit_unchanged_candidates"] += credit_delta == 0
            summary["source_credit_difference_spans"] += len(contrast["changed_sound_credit_spans"])
            for t in contrast["transition_contrasts"]:
                summary["joint_truth_" + "_to_".join(t["joint_truth_change"])] += 1
                summary["whole_template_" + "_to_".join(t["whole_template_truth_change"])] += 1
            summary["linked_all_internal_transitions_conditionally_supported"] += bool(linked["transitions"]) and all(
                t["state"] == "conditional_joint_supported" for t in linked["transitions"])
            issues.update(r["reason"] for r in linked["issues"])
        selectors.extend(current_selectors)
        replay._add_batch(counts, comparison, explanation, bundle)
        refs.append({**deepcopy(planned), "comparison_ref": sealed._ref(comparison), "explanation_ref": sealed._ref(explanation)})
        save(f"batch-{bi:04d}.json", {"version": VERSION, "batch_index": bi, "selector_start": lo,
            "selector_end_exclusive": hi, "rows": result_rows, "selected": None})
        if progress and (bi % 8 == 0 or bi + 1 == len(job["batches"])):
            progress(f"linked evidence {bi + 1}/{len(job['batches'])} batches; {hi}/{count} paired candidates")
    replay._finish_counts(counts)
    if (len(selectors) != count or digest(selectors) != plan["selector_inventory_sha256"]
            or terminal["batch_refs"] != refs or terminal["summary"] != counts
            or job["summary"] != counts):
        raise ValueError("whole_original_selector_inventory_and_terminal_required")
    reader.final_guard()
    for a in artifacts:
        p = Path(a["path"])
        if p.stat().st_size != a["bytes"] or saved._hash(p) != a["sha256"]:
            raise ValueError("completion_output_changed")
    report = {"version": VERSION, "status": "complete_saved_completion_sensitivity_review_not_selected",
        "source_index": source_index, "completion_index": completion_index, "context_key": context["context_key"],
        "analysis_span": scope["analysis_span"], "raw_lanes": len(scope["raw_lanes"]),
        "source_sound_facts": len(sounds), "completion_kind": job["completion_kind"],
        "materialized_witness_links": len(bundle["materialized_witness_links"]),
        "completed_batches": len(refs), "summary": dict(summary), "linked_issues": dict(issues),
        "archived_native_role_summary": counts, "receipt_sha256": receipt_sha256,
        "control_report_sha256": control_sha256, "read_ledger": reader.ledger, "decoded_bytes": reader.bytes,
        "artifacts": artifacts.copy(), "output_bytes_before_report": total, "limits": asdict(limits),
        "physical_inputs_unchanged": True, "role_predicates_reinferred": False,
        "source_file_reparsed": False, "saved_JSON_restores_capability": False,
        "full_archive_complete": False, "independent_musical_accuracy_measured": False,
        "elapsed_seconds": time.perf_counter() - started,
        "selected": None, "rank": None, "confidence": None, "flags": parent._flags()}
    save("report.json", report)
    return report
