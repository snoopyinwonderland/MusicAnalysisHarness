"""Saved-only comparison of TWO complete requests in explicit bounded stages.

Each stage owns a separate, never-reset read account. This is not a one-GiB
whole pipeline claim or authenticated capability reload. Original bodies and
every selector are checked; no native/role producer is called. Review snapshots
are lossless gzip JSON, with physical output and decoded read costs separate.
"""
from collections import Counter
from dataclasses import asdict
from fractions import Fraction
import gzip
import hashlib
import io
import json
from pathlib import Path
import time

from . import completion_evidence_contrast as contrast
from . import completion_evidence_contrast_trial as previous
from . import progression_evidence_review as review
from . import progression_evidence_review_trial as saved
from . import factor_expanded_hypotheses as sealed
from . import native_progression_contrast as parent
from . import native_progression_contrast_trial as join
from . import native_progression_policy as policy
from . import source_progression_replay_trial as replay
from .musical_pattern_observation import digest, f, q

VERSION = "staged-completion-evidence-trial-0.1.0"


class Reader(previous.Reader):
    def snapshot(self, artifact, *, source=False):
        path = Path(artifact["path"]).resolve(strict=True)
        cap = self.limits.max_source_catalog_bytes if source else self.limits.max_json_file_bytes
        size = path.stat().st_size
        if size != artifact["bytes"] or size > self.limits.max_json_file_bytes:
            raise ValueError("snapshot_physical_size_limit")
        with path.open("rb") as stream:
            raw = stream.read(self.limits.max_json_file_bytes + 1)
        if len(raw) != size or hashlib.sha256(raw).hexdigest() != artifact["sha256"]:
            raise ValueError("snapshot_physical_pin_mismatch")
        parts, n = [], 0
        with gzip.GzipFile(fileobj=io.BytesIO(raw), mode="rb") as stream:
            while True:
                remaining = min(cap - n, self.limits.max_total_decoded_bytes - self.bytes)
                chunk = stream.read(min(1024 * 1024, remaining + 1))
                if not chunk:
                    break
                n += len(chunk)
                self.bytes += len(chunk)
                if n > cap or self.bytes > self.limits.max_total_decoded_bytes:
                    raise ValueError("stage_decoded_read_limit")
                parts.append(chunk)
        if n != artifact["decoded_bytes"]:
            raise ValueError("snapshot_decoded_length_mismatch")
        value = json.loads(b"".join(parts), object_pairs_hook=saved._pairs,
                           parse_constant=saved._invalid_constant)
        self.ledger.append({"path": str(path), "bytes": size, "decoded_bytes": n,
                            "sha256": artifact["sha256"]})
        return value

    def source_record(self, info, prefix, expected_sha256):
        # Caller pin, not the index's self-declared SHA, authorizes this read.
        if info["sha256"] != expected_sha256:
            raise ValueError("external_scope_pin_required")
        path = Path(info["artifact"]).resolve(strict=True)
        with path.open("rb") as stream:
            stream.seek(-4, 2)
            hint = int.from_bytes(stream.read(4), "little")
        value = self.snapshot({"path": str(path), "bytes": path.stat().st_size,
            "sha256": expected_sha256, "decoded_bytes": hint}, source=True)
        sealed._check(value, prefix)
        if sealed._ref(value) != info["record_ref"] or value["status"] != info["status"]:
            raise ValueError("source_record_reference_mismatch")
        return value


class Writer:
    def __init__(self, output, limits):
        self.output, self.limits, self.artifacts = output, limits, []
        self.physical_bytes, self.decoded_bytes = 0, 0

    def save(self, name, value, *, source=False, compress=True):
        if Path(name).name != name:
            raise ValueError("plain_output_filename_required")
        raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                         allow_nan=False).encode("utf-8")
        cap = self.limits.max_source_catalog_bytes if source else self.limits.max_output_file_bytes
        if len(raw) > cap:
            raise ValueError("staged_output_decoded_file_limit")
        physical = gzip.compress(raw, compresslevel=1, mtime=0) if compress else raw
        if (len(physical) > self.limits.max_output_file_bytes or
                self.physical_bytes + len(physical) > self.limits.max_total_output_bytes):
            raise ValueError("staged_output_physical_limit")
        path = self.output / name
        with path.open("xb") as stream:
            if stream.write(physical) != len(physical):
                raise OSError("short_staged_output_write")
        result = {"path": str(path), "bytes": len(physical), "decoded_bytes": len(raw),
                  "sha256": hashlib.sha256(physical).hexdigest()}
        self.artifacts.append(result)
        self.physical_bytes += len(physical)
        self.decoded_bytes += len(raw)
        return result

    def final_guard(self):
        for a in self.artifacts:
            p = Path(a["path"])
            if p.stat().st_size != a["bytes"] or saved._hash(p) != a["sha256"]:
                raise ValueError("staged_output_changed")


def _job(context, index, limits):
    if type(index) is not int or not 0 <= index < len(context["jobs"]):
        raise ValueError("exact_completion_index_required")
    job = context["jobs"][index]
    if (job["status"] != "computed_native_role_source_requests_not_selected" or
            job["error"] is not None or job["unpersisted_selector_ranges"] or
            not job["batches"] or len(job["batches"]) > limits.max_tasks):
        raise ValueError("complete_original_request_required")
    return job


def _validate_request(scope, lattice, bundle, plan, terminal, job, limits):
    n = plan["planned_selectors"]
    if (type(n) is not int or not 0 < n <= limits.max_entries_per_group * limits.max_groups
            or n != job["planned_selector_occurrences"] or plan["reasons"] or terminal["reasons"]
            or len(job["batches"]) != plan["planned_batches"]
            or len(plan["batches"]) != plan["planned_batches"]
            or plan["scope_ref"] != sealed._ref(scope) or plan["lattice_ref"] != sealed._ref(lattice)
            or bundle["scope_ref"] != sealed._ref(scope) or bundle["lattice_ref"] != sealed._ref(lattice)
            or terminal["scope_ref"] != sealed._ref(scope) or terminal["lattice_ref"] != sealed._ref(lattice)
            or terminal["bundle_ref"] != sealed._ref(bundle) or terminal["plan_ref"] != sealed._ref(plan)
            or terminal["proposal_ref"] != plan["proposal_ref"]
            or terminal["fresh_registered_links"] != bundle["materialized_witness_links"]
            or bundle["status"] != "complete_all_lane_witness"):
        raise ValueError("complete_source_plan_terminal_join_required")
    previous._flags(terminal)
    lo = 0
    for bi, batch in enumerate(job["batches"]):
        a, b = batch["selector_start"], batch["selector_end_exclusive"]
        if (type(a) is not int or type(b) is not int or batch["batch_index"] != bi or
                a != lo or not a < b <= n or
                {k: batch[k] for k in replay.PLAN_BATCH_KEYS} != plan["batches"][bi]):
            raise ValueError("whole_original_batch_order_required")
        lo = b
    if lo != n:
        raise ValueError("complete_selector_coverage_required")


def _stage_review(source, job, reader, registry, root, writer, label, progress):
    scope, lattice, bundles = source["scope"], source["lattice"], source["bundles"]
    plan, terminal = source["plans"][label], source["terminals"][label]
    bundle = bundles[terminal["bundle_ref"]["record_id"]]
    keys = parent._lookup(lattice["keys"], "staged_key")
    origins = parent._lookup([o for c in lattice["catalog_inventory"] for o in c["origins"]], "staged_origin")
    sounds = {s["sound_ref"]: s for s in scope["sound_facts"]}
    if len(sounds) != len(scope["sound_facts"]):
        raise ValueError("unique_original_sounds_required")
    cache = {"profiles": {}, "guards": {sid: {
        "strict": not sealed._source_blockers(s) and not parent.temporal._guard_codes(s),
        "role_blocked": bool(parent.temporal._guard_codes(s))} for sid, s in sounds.items()}}
    selectors, refs, artifacts, seen = [], [], [], set()
    counts = replay._empty_counts(plan["planned_selectors"], plan["planned_batches"])
    counts["fresh_bundle_registrations"] = 1  # Archived count, not a new registration.
    for bi, batch in enumerate(job["batches"]):
        comparison = reader.record(batch["comparison"], replay.engine.native.COMPARISON_PREFIX, registry, root)
        explanation = reader.record(batch["explanation"], replay.engine.roles.PREFIX, registry, root)
        current = comparison["selectors"]
        planned = {k: batch[k] for k in replay.PLAN_BATCH_KEYS}
        replay._batch(comparison, explanation, current, {"scope": scope, "lattice": lattice},
                      bundle, planned, plan["resource_limits"])
        if len(current) != batch["selector_end_exclusive"] - batch["selector_start"]:
            raise ValueError("exact_batch_selector_count_required")
        rows = []
        for ordinal, (selector, path, role) in enumerate(zip(current, comparison["paths"], explanation["paths"])):
            logical = digest(path["logical_tuple"])
            if logical in seen:
                raise ValueError("duplicate_original_path")
            seen.add(logical)
            entry = join._entry(path, role, selector, comparison, explanation, lattice, scope, bundle, origins, keys)
            facet = parent._facet(entry, scope, [origins[i] for i in selector["origin_ids"]], sounds)
            entry_refs = {k: facet[k] for k in ("native_path_ref", "role_path_ref", "comparison_ref", "explanation_ref")}
            key = policy._validate_facet(facet, entry_refs, scope, keys, bundles, origins, sounds, cache)
            rows.append({"original_selector_index": batch["selector_start"] + ordinal,
                         "review": review.review_facet(facet, key)})
        selectors.extend(current)
        replay._add_batch(counts, comparison, explanation, bundle)
        refs.append({**planned, "comparison_ref": sealed._ref(comparison), "explanation_ref": sealed._ref(explanation)})
        artifacts.append(writer.save(f"{label}-{bi:04d}.json.gz", {"rows": rows, "source_scope_ref": sealed._ref(scope),
            "batch_index": bi, "selector_start": batch["selector_start"],
            "selector_end_exclusive": batch["selector_end_exclusive"], "bundle_ref": sealed._ref(bundle)}))
        if progress and (bi % 8 == 0 or bi + 1 == len(job["batches"])):
            progress(f"{label}: {bi + 1}/{len(job['batches'])} batches, {len(selectors)}/{plan['planned_selectors']} candidates")
    replay._finish_counts(counts)
    if (digest(selectors) != plan["selector_inventory_sha256"] or terminal["batch_refs"] != refs
            or counts != terminal["summary"] or counts != job["summary"]):
        raise ValueError("complete_original_inventory_terminal_required")
    reader.final_guard()
    return artifacts, counts


def _pair_batches(left, right, scope, bundles):
    for k in ("source_scope_ref", "batch_index", "selector_start", "selector_end_exclusive"):
        if left[k] != right[k]:
            raise ValueError("identical_original_batch_required")
    n = left["selector_end_exclusive"] - left["selector_start"]
    if len(left["rows"]) != n or len(right["rows"]) != n:
        raise ValueError("every_original_pair_required")
    result = []
    for ordinal, (a, b) in enumerate(zip(left["rows"], right["rows"])):
        i = left["selector_start"] + ordinal
        if a["original_selector_index"] != i or b["original_selector_index"] != i:
            raise ValueError("exact_original_pair_position_required")
        if a["review"]["bundle_ref"] != left["bundle_ref"] or b["review"]["bundle_ref"] != right["bundle_ref"]:
            raise ValueError("snapshot_bundle_reference_required")
        result.append({"original_selector_index": i,
                       "contrast": contrast.compare_reviews(a["review"], b["review"], scope, bundles)})
    return result


def run(receipt_path, archive_root, output, *, receipt_sha256, scope_sha256,
        source_index, control_index=0, linked_index=1, limits=None, progress=None):
    limits = saved.ReviewLimits() if limits is None else limits
    if type(limits) is not saved.ReviewLimits:
        raise ValueError("exact_stage_limits_required")
    started = time.perf_counter()
    receipt_path, root = Path(receipt_path).resolve(strict=True), Path(archive_root).resolve(strict=True)
    output = Path(output).resolve()
    if (output.exists() or any(output == p or p in output.parents or output in p.parents
                              for p in (root, receipt_path.parent))):
        raise ValueError("new_disjoint_stage_output_required")
    bootstrap = Reader(limits)
    receipt = bootstrap.read(receipt_path, receipt_sha256)
    registry = previous._registry(receipt, root)
    index_path = root / "context-index.json"
    rows = bootstrap.read(index_path, registry[str(index_path)])
    if type(source_index) is not int or not 0 <= source_index < len(rows):
        raise ValueError("exact_source_index_required")
    context = rows[source_index]
    scope_path = Path(context["scope"]["artifact"]).resolve(strict=True)
    if output == scope_path.parent or scope_path.parent in output.parents or output in scope_path.parents:
        raise ValueError("disjoint_scope_output_required")
    scope = bootstrap.source_record(context["scope"], "fmes_", scope_sha256)
    li = context["fresh_lattice"]
    if registry.get(str(Path(li["artifact"]).resolve(strict=True))) != li["sha256"]:
        raise ValueError("pinned_original_lattice_required")
    lattice = bootstrap.source_record(li, "fmilat_", li["sha256"])
    previous._index(rows, scope, lattice, source_index)
    jobs = {"control": _job(context, control_index, limits), "linked": _job(context, linked_index, limits)}
    source = {"scope": scope, "lattice": lattice, "bundles": {}, "plans": {}, "terminals": {}}
    for label, job in jobs.items():
        bundle = bootstrap.record(job["bundle"], replay.engine.native.BUNDLE_PREFIX, registry, root)
        plan = bootstrap.record(job["plan"], "npsreplayplan_", registry, root)
        terminal = bootstrap.record(job["job"], replay.engine.PREFIX, registry, root)
        _validate_request(scope, lattice, bundle, plan, terminal, job, limits)
        if bool(bundle["materialized_witness_links"]) != (label == "linked"):
            raise ValueError("no_link_control_and_nonempty_link_probe_required")
        source["bundles"][bundle["record_id"]] = bundle
        source["plans"][label], source["terminals"][label] = plan, terminal
    if source["plans"]["control"] != source["plans"]["linked"]:
        raise ValueError("same_whole_request_plan_required")
    bootstrap.final_guard()
    output.mkdir(parents=True, exist_ok=False)
    writer = Writer(output, limits)
    source_artifact = writer.save("source-context.json.gz", source, source=True)
    stage_ledgers = [{"stage": "bootstrap", "decoded_bytes": bootstrap.bytes, "read_ledger": bootstrap.ledger}]
    reviews, archived_counts = {}, {}
    for label in ("control", "linked"):
        reader = Reader(limits)  # Explicit independent stage, not a reset inside a stage.
        current = reader.snapshot(source_artifact, source=True)
        reviews[label], archived_counts[label] = _stage_review(current, jobs[label], reader, registry, root,
                                                               writer, label, progress)
        stage_ledgers.append({"stage": label, "decoded_bytes": reader.bytes, "read_ledger": reader.ledger})
        del current
    reader = Reader(limits)
    current = reader.snapshot(source_artifact, source=True)
    summary, joint_axes, issues, key_counts = Counter(), Counter(), Counter(), Counter()
    diagnostic_indices = {"joint_supported": [], "whole_supported_joint_not_true": [], "control_intrinsic_credit": []}
    credit_delta = Fraction()
    for bi, (ca, la) in enumerate(zip(reviews["control"], reviews["linked"])):
        left, right = reader.snapshot(ca), reader.snapshot(la)
        paired = _pair_batches(left, right, current["scope"], current["bundles"])
        for a, b, row in zip(left["rows"], right["rows"], paired):
            c, r, i = row["contrast"], b["review"], row["original_selector_index"]
            delta = f(c["conditional_credit_delta_quarters"])
            credit_delta += delta
            summary["paired_original_candidates"] += 1
            summary["credit_increased"] += delta > 0
            summary["credit_decreased"] += delta < 0
            summary["credit_unchanged"] += delta == 0
            summary["changed_sound_span_occurrences"] += len(c["changed_sound_credit_spans"])
            key_counts[r["key_ref"]["record_id"]] += 1
            issues.update(v["reason"] for v in r["issues"])
            if f(a["review"]["note_time_account"]["note_time_quarters"]["conditional_explained_nonmember"]) > 0:
                diagnostic_indices["control_intrinsic_credit"].append(i)
            for t, d in zip(r["transitions"], c["transition_contrasts"]):
                summary["joint_" + "_to_".join(d["joint_truth_change"])] += 1
                summary["whole_" + "_to_".join(d["whole_template_truth_change"])] += 1
                if t["joint_support"] is True:
                    diagnostic_indices["joint_supported"].append(i)
                if t["whole_ordinary_template_support"] is True and t["joint_support"] is not True:
                    diagnostic_indices["whole_supported_joint_not_true"].append(i)
                if t["prerequisite_axes"]:
                    joint_axes.update(k for k, v in t["prerequisite_axes"].items() if v is False)
        writer.save(f"contrast-{bi:04d}.json.gz", {"batch_index": bi, "rows": paired,
                    "control_snapshot": ca, "linked_snapshot": la, "selected": None})
        if progress and (bi % 16 == 0 or bi + 1 == len(reviews["control"])):
            progress(f"paired: {bi + 1}/{len(reviews['control'])} batches")
    n = source["plans"]["control"]["planned_selectors"]
    if summary["paired_original_candidates"] != n:
        raise ValueError("all_original_pairs_required")
    reader.final_guard()
    bootstrap.final_guard()
    writer.final_guard()
    stage_ledgers.append({"stage": "paired", "decoded_bytes": reader.bytes, "read_ledger": reader.ledger})
    # Earlier stage inputs must also stay unchanged until the WHOLE terminal.
    protected = {a["path"]: a for s in stage_ledgers for a in s["read_ledger"]}
    for a in protected.values():
        p = Path(a["path"])
        if p.stat().st_size != a["bytes"] or saved._hash(p) != a["sha256"]:
            raise ValueError("earlier_stage_input_changed_before_terminal")
    report = {"version": VERSION, "status": "complete_staged_saved_evidence_review_not_selected",
        "context_key": context["context_key"], "source_index": source_index,
        "analysis_span": scope["analysis_span"], "source_sound_facts": len(scope["sound_facts"]),
        "raw_lanes": len(scope["raw_lanes"]), "control_index": control_index, "linked_index": linked_index,
        "summary": dict(summary), "conditional_credit_delta_selector_sum": q(credit_delta),
        "key_candidate_counts": dict(key_counts), "linked_false_prerequisite_axes": dict(joint_axes),
        "linked_issues": dict(issues), "diagnostic_original_indices": diagnostic_indices,
        "archived_native_role_summaries": archived_counts, "stage_accounts": stage_ledgers,
        "aggregate_decoded_bytes": sum(s["decoded_bytes"] for s in stage_ledgers),
        "pipeline_claimed_to_fit_single_read_account": False,
        "terminal_guarded_input_files": len(protected),
        "limits_per_stage": asdict(limits), "output_physical_bytes_before_report": writer.physical_bytes,
        "output_decoded_bytes_before_report": writer.decoded_bytes, "artifacts": writer.artifacts.copy(),
        "receipt_sha256": receipt_sha256, "scope_external_sha256": scope_sha256,
        "physical_inputs_unchanged": True, "role_predicates_reinferred": False,
        "saved_JSON_restores_capability": False, "source_file_reparsed": False,
        "full_archive_complete": False, "independent_musical_accuracy_measured": False,
        "musical_voice_validated": False, "elapsed_seconds": time.perf_counter() - started,
        "selected": None, "rank": None, "confidence": None, "flags": parent._flags()}
    writer.save("report.json", report, compress=False)
    return report
