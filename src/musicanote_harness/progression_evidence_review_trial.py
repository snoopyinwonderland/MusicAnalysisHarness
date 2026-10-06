"""Pinned saved-only review; no fresh native admission or capability reload."""
from collections import Counter
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import time

from . import progression_evidence_review as core
from . import factor_expanded_hypotheses as sealed
from . import native_progression_contrast as parent

VERSION = "progression-evidence-review-trial-0.1.0"


@dataclass(frozen=True)
class ReviewLimits:
    max_json_file_bytes: int = 64 * 1024 * 1024
    # Same source-once limit as shared.SourceLimits, not a raised generic cap.
    max_source_catalog_bytes: int = 256 * 1024 * 1024
    max_total_decoded_bytes: int = 1024 * 1024 * 1024
    max_output_file_bytes: int = 64 * 1024 * 1024
    max_total_output_bytes: int = 256 * 1024 * 1024
    max_groups: int = 20
    max_entries_per_group: int = 4096
    max_tasks: int = 1024

    def __post_init__(self):
        for name, value in asdict(self).items():
            if type(value) is not int or value < 0:
                raise ValueError("exact_nonnegative_review_limit:" + name)
        defaults = (67108864, 268435456, 1073741824, 67108864, 268435456, 20, 4096, 1024)
        if any(v > cap for v, cap in zip(asdict(self).values(), defaults)):
            raise ValueError("review_limits_may_only_be_lowered")


def _hash(path):
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            sha.update(chunk)
    return sha.hexdigest()


def _pairs(pairs):
    obj = {}
    for k, v in pairs:
        if k in obj:
            raise ValueError("duplicate_JSON_key")
        obj[k] = v
    return obj


def _invalid_constant(value):
    raise ValueError("nonfinite_JSON_constant:" + value)


class Reader:
    def __init__(self, limits):
        self.limits, self.bytes, self.ledger = limits, 0, []

    def read(self, path, sha, size=None, *, source=False):
        path = Path(path).resolve(strict=True)
        cap = self.limits.max_source_catalog_bytes if source else self.limits.max_json_file_bytes
        length = path.stat().st_size
        if (length > cap or self.bytes + length > self.limits.max_total_decoded_bytes
                or size is not None and length != size):
            raise ValueError("whole_saved_review_read_limit_or_length")
        with path.open("rb") as stream:
            raw = stream.read(cap + 1)
        self.bytes += len(raw)
        if len(raw) != length or hashlib.sha256(raw).hexdigest() != sha:
            raise ValueError("external_pin_or_physical_SHA_mismatch")
        value = json.loads(raw, object_pairs_hook=_pairs, parse_constant=_invalid_constant)
        self.ledger.append({"path": str(path), "bytes": length, "sha256": sha})
        return value

    def final_guard(self):
        for row in self.ledger:
            p = Path(row["path"])
            if p.stat().st_size != row["bytes"] or _hash(p) != row["sha256"]:
                raise ValueError("review_input_changed_after_read")


def receipt_inventory(prior, continuation, prior_root, new_root):
    """External pin belongs to caller. Internal seals alone grant nothing."""
    pt = prior["storage_execution"]["storage_terminal"]
    nt = continuation["storage_execution"]["storage_terminal"]
    plan = continuation["storage_execution"]["plan"]
    for t in (pt, nt):
        if (t["storage_integrity_passed"] is not True or t["terminal_persisted"] is not True
                or t["physical_closure_verified_terminally"] is not True):
            raise ValueError("pinned_terminal_storage_closure_required")
    if nt["selected_request_storage_complete"] is not True:
        raise ValueError("complete_selected_comparison_required")
    artifacts = {}
    for terminal, root in ((pt, prior_root), (nt, new_root)):
        for a in terminal["artifact_attempts"]:
            p = Path(a["artifact"]).resolve(strict=True)
            if p.parent != root or p.name in artifacts:
                raise ValueError("foreign_or_duplicate_borrowed_artifact")
            if (a["persisted"] is not True or a["stream_complete"] is not True
                    or a["physical_sha256"] != a["attempted_sha256"]
                    or a["physical_bytes"] != a["attempted_bytes"]):
                raise ValueError("complete_physical_artifact_required")
            # Duplicate run-plan/report names are intentionally not imported.
            if a["kind"] in ("source_catalog", "local_catalog", "block"):
                artifacts[p.name] = {"path": str(p), "bytes": a["physical_bytes"],
                    "sha256": a["physical_sha256"], "kind": a["kind"]}
    confirmed = plan["prior_confirmed_tasks"] + nt["remaining_task_ledger"]
    ordered = sorted(confirmed, key=lambda r: (r["group_index"], r["task_index"]))
    if len({(r["group_index"], r["task_index"]) for r in ordered}) != len(ordered):
        raise ValueError("duplicate_continuation_task")
    for r in ordered:
        if r["status"] != "computed_persisted" or r["persisted_pairs"] != r["task"]["expected_pairs"]:
            raise ValueError("whole_persisted_task_coverage_required")
        name = f"group-{r['group_index']:04d}-block-{r['task_index']:06d}.json"
        a = artifacts.get(name)
        if a is None or a["sha256"] != r["encoded_sha256"] or a["bytes"] != r["encoded_bytes"]:
            raise ValueError("task_artifact_receipt_mismatch")
    return artifacts, ordered, plan


def run(prior_report, continuation_report, output, *, prior_sha256, continuation_sha256,
        limits=None, progress=None):
    limits = ReviewLimits() if limits is None else limits
    if type(limits) is not ReviewLimits:
        raise ValueError("exact_review_limits_required")
    reader, started = Reader(limits), time.perf_counter()
    prior_path, current_path = Path(prior_report).resolve(strict=True), Path(continuation_report).resolve(strict=True)
    output = Path(output).resolve()
    if output.exists() or any(output == p.parent or output.is_relative_to(p.parent) for p in (prior_path, current_path)):
        raise ValueError("new_disjoint_review_output_required")
    prior = reader.read(prior_path, prior_sha256)
    current = reader.read(current_path, continuation_sha256)
    plan = current["storage_execution"]["plan"]
    if (plan["prior_receipt_external_SHA"] != prior_sha256
            or Path(plan["prior_receipt_path"]).resolve() != prior_path):
        raise ValueError("pinned_receipt_chain_mismatch")
    oldroot, newroot = prior_path.parent / "comparison-storage", current_path.parent / "comparison-storage"
    inventory, ordered, plan = receipt_inventory(prior, current, oldroot, newroot)
    groups = plan["groups"]
    if (len(groups) > limits.max_groups or len(ordered) > limits.max_tasks
            or any(g["original"]["planned_entries"] > limits.max_entries_per_group for g in groups)):
        raise ValueError("whole_review_inventory_limit_no_prefix")
    expected_tasks = [(i, j, t) for i, g in enumerate(groups) for j, t in enumerate(g["tasks"])]
    if [(r["group_index"], r["task_index"], r["task"]) for r in ordered] != expected_tasks:
        raise ValueError("all_original_selected_tasks_required")
    sources = [a for a in inventory.values() if a["kind"] == "source_catalog"]
    if len(sources) != 1 or any(g["source_index"] != 0 for g in groups):
        raise ValueError("this_review_adapter_requires_one_selected_source")
    # Full exact byte preflight, not successful-prefix read semantics.
    planned = reader.bytes + sum(a["bytes"] for a in inventory.values())
    if planned > limits.max_total_decoded_bytes:
        raise ValueError("whole_review_total_read_limit_no_prefix")
    source = reader.read(sources[0]["path"], sources[0]["sha256"], sources[0]["bytes"], source=True)
    scope = source["source_scope"]
    output.mkdir(parents=True, exist_ok=False)
    written, total_written = [], 0

    def save(name, value):
        nonlocal total_written
        raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        if len(raw) > limits.max_output_file_bytes or total_written + len(raw) > limits.max_total_output_bytes:
            raise ValueError("review_output_limit_no_overwrite")
        p = output / name
        with p.open("xb") as stream:
            if stream.write(raw) != len(raw):
                raise OSError("short_review_write")
        total_written += len(raw)
        written.append({"path": str(p), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})

    # Reproducible note pitches/ties/durations, not a newly parsed IR certificate.
    save("source-context.json", {"binding": scope["binding"], "analysis_span": scope["analysis_span"],
        "sound_facts": scope["sound_facts"], "literal_observation": scope["literal_observation"],
        "source_audit": scope["source_audit"], "source_catalog_ref": sealed._ref(source),
        "source_file_reparsed": False, "flags": parent._flags()})
    result_groups, all_counts, pair_counts, audited = [], Counter(), Counter(), 0
    for i, g in enumerate(groups):
        a = inventory[f"group-{i:04d}-catalog.json"]
        catalog = reader.read(a["path"], a["sha256"], a["bytes"])
        if sealed._ref(catalog) != g["catalog_ref"]:
            raise ValueError("plan_catalog_binding_mismatch")
        result = core.review_catalog(catalog, source)
        if (len(result["candidate_reviews"]) != g["original"]["planned_entries"]
                or result["group"]["original_selector_indices"] != g["original"]["selector_indices"]):
            raise ValueError("original_candidates_or_selectors_lost")
        if progress:
            progress(f"group {i + 1}/{len(groups)}: {len(result['candidate_reviews'])} candidates reviewed")
        group_pairs, kinds = 0, Counter()
        for row in (r for r in ordered if r["group_index"] == i):
            a = inventory[f"group-{i:04d}-block-{row['task_index']:06d}.json"]
            block = reader.read(a["path"], a["sha256"], a["bytes"])
            checked = core.audit_pair_block(block, catalog, task=row["task"])
            group_pairs += checked["audited_pairs"]
            kinds.update(checked["pair_kind_counts"])
            del block
        if group_pairs != g["original"]["planned_pairs"]:
            raise ValueError("whole_group_pair_coverage_required")
        result["pair_audit"] = {"audited_pairs": group_pairs, "counts": dict(kinds),
            "source_pointer_materialization_replayed": False}
        save(f"group-{i:04d}-evidence-review.json", result)
        result_groups.append({"group_index": i, "catalog_ref": result["catalog_ref"],
            "key_ref": result["group"]["key_ref"], "summary": result["summary"],
            "audited_pairs": group_pairs, "review_file": f"group-{i:04d}-evidence-review.json"})
        all_counts.update(result["summary"])
        pair_counts.update(kinds)
        audited += group_pairs
        if progress:
            progress(f"group {i + 1}: {group_pairs} stored pair margins verified; no winner selected")
        del result, catalog
    reader.final_guard()
    for a in written:
        if Path(a["path"]).stat().st_size != a["bytes"] or _hash(Path(a["path"])) != a["sha256"]:
            raise ValueError("review_output_changed_before_terminal")
    report = {"version": VERSION, "core_version": core.VERSION,
        "status": "complete_selected_saved_evidence_review_not_selected",
        "summary": dict(all_counts), "audited_pairs": audited, "pair_counts": dict(pair_counts),
        "actual_contexts_reviewed": 1, "actual_raw_lanes_reviewed": len(scope["raw_lanes"]),
        "original_denominators": plan["original_denominators"], "whole_original": plan["whole_original"],
        "selected_completion": plan["selected_completion"], "omitted_completions": plan["omitted_completions"],
        "groups": result_groups, "read_ledger": reader.ledger, "decoded_bytes": reader.bytes,
        "limits": asdict(limits), "artifacts": written.copy(),
        "elapsed_seconds": time.perf_counter() - started, "physical_inputs_unchanged": True,
        "independent_musical_accuracy_measured": False, "full_archive_complete": False,
        "role_predicates_reinferred": False, "original_XML_reparsed": False,
        "saved_JSON_restores_capability": False, "selected": None, "rank": None,
        "confidence": None, "musical_outcome": None, "flags": parent._flags()}
    save("report.json", report)
    return report
