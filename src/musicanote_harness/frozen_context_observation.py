"""Additive literal observations of trusted frozen context windows.

No SOURCE/alignment branch is accepted here. Window selection is label blind;
the inherited score/annotation hash-pair cohort is explicitly not annotation
independent. The caller checks file bytes and trusted report/contract inventory,
fresh-replays the selector and validates measure revisions once per package.
This pure adapter checks supplied parent content, identity and protected Core
projection. A record seal alone cannot establish trust in parent artifacts.
"""
from copy import deepcopy
from functools import lru_cache
import json
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from .musical_pattern_observation import (
    _payload as literal_payload, digest, f, span_bounds, CORE_SCHEMA_PATH,
    SCHEMA_PATH as PATTERN_SCHEMA_PATH)
from .harmony_path_contrast import token
from .source_locator_revision_trial import validate_policy

VERSION = "frozen-context-observation-0.1.0"
SCHEMA_NAME = "musicanote-frozen-context-observation"
SCHEMA_VERSION = "0.1.0"
SCHEMA_PATH = Path(__file__).resolve().parents[2] / "docs/harmony/schemas/frozen_context_observation.schema.json"
SELECTOR_VERSION = "harmony-breadth-trial-0.1.1"
SELECTOR_POLICY = "interior quantile indices per explicit lane over full score"
PARENT_ARGUMENTS = ("integration_index_row", "integration_packet", "original_stored_packet",
                    "frozen_plan_row", "package", "revision_row", "revision_sidecar", "parent_ir")
SCOPE_KEYS = {"score_id", "ir_document_id", "ir_content_sha256", "source_files",
              "target_span", "context_span"}


@lru_cache(maxsize=1)
def validator():
    resources = [json.loads(path.read_text(encoding="utf-8"))
                 for path in (CORE_SCHEMA_PATH, PATTERN_SCHEMA_PATH, SCHEMA_PATH)]
    registry = Registry()
    for schema in resources:
        Draft202012Validator.check_schema(schema)
        registry = registry.with_resource(schema["$id"], Resource.from_contents(schema))
    return Draft202012Validator(resources[-1], registry=registry)


def _same(a, b, reason):
    if digest(a) != digest(b):
        raise ValueError(reason)


def _flags(value, names, reason):
    if any(value.get(name) is not False for name in names):
        raise ValueError(reason)


def _sample(ir, sample):
    if set(sample) != {"sample_id", "lane", "attack_group_onsets", "seed_event_refs", "span", "abstention_reasons"}:
        raise ValueError("unsupported_frozen_sample_shape")
    lane = sample["lane"]
    if not isinstance(lane, list) or len(lane) != 2 or any(not isinstance(x, str) or not x for x in lane):
        raise ValueError("explicit_sampled_lane_required")
    onsets = sample["attack_group_onsets"]
    if len(onsets) != 3 or not f(onsets[0]) < f(onsets[1]) < f(onsets[2]):
        raise ValueError("three_ordered_attack_group_onsets_required")
    refs = sample["seed_event_refs"]
    if not refs or refs != sorted(set(refs)):
        raise ValueError("invalid_seed_event_inventory")
    if sample["sample_id"] != "cont_" + token([tuple(lane), onsets, refs]):
        raise ValueError("frozen_sample_identity_recipe_mismatch")
    notes = {n["note_id"]: n for n in ir["note_events"]}
    seeds = []
    for sound in ir["sounding_events"]:
        ns = [notes.get(nid) for nid in sound["source_note_ids"]]
        identities = {(n.get("part_id"), n.get("voice_id")) for n in ns if n is not None}
        if (ns and all(n is not None for n in ns) and identities == {tuple(lane)}
                and f(sound["span"]["start"]) in {f(t) for t in onsets}):
            seeds.append(sound)
    if sorted(s["sounding_event_id"] for s in seeds) != refs:
        raise ValueError("frozen_seed_lane_or_event_mismatch")
    expected = {"start": onsets[0], "end": max((s["span"]["end"] for s in seeds), key=f)}
    if sample["span"] != expected:
        raise ValueError("frozen_seed_span_mismatch")
    span_bounds(sample["span"])


def _revision(ir, parent, source, row, sidecar):
    """Guard exact chosen revision and invariant projection, not file authority.

    The runner additionally calls validate_revision(parent,candidate,sidecar)
    once per package; this adapter cannot certify a replay/source file's bytes.
    """
    status = sidecar.get("status")
    if sidecar.get("version") != "source-physical-measure-revision-0.1.0" or status not in (
            "not_required", "candidate_core_ready", "candidate_core_ready_parent_bound_residuals"):
        raise ValueError("unsupported_or_blocked_measure_revision")
    if sidecar.get("blockers") != [] or sidecar.get("allowed_scope") != "note_rest_measure_core_only":
        raise ValueError("unsafe_measure_revision_scope")
    _flags(sidecar, ("extensions_rebound", "annotation_retargeted", "old_analysis_rebound",
                    "source_labels_used", "gold_promoted", "training_promoted", "production_ready"),
           "unsafe_measure_revision_flags")
    ph = digest(parent)
    if (sidecar.get("parent_ir_document_id") != parent["ir_document_id"]
            or sidecar.get("parent_content_sha256") != ph
            or sidecar.get("protected_projection_sha256") != ph
            or sidecar.get("source_sha256") != source["manifest_entry"]["score_sha256"]):
        raise ValueError("revision_parent_binding_mismatch")
    if sidecar.get("verified_replay_package_content_sha256") != digest(sidecar["verification_payload"]):
        raise ValueError("revision_verification_payload_mismatch")
    if (row["status"] != status or row["parent_ir_document_id"] != parent["ir_document_id"]
            or row["working_ir_document_id"] != ir["ir_document_id"]
            or row["summary"] != sidecar.get("summary", sidecar.get("counts", {}))):
        raise ValueError("revision_row_sidecar_mismatch")
    candidate = status != "not_required"
    if row["candidate_created"] is not candidate or (row["candidate_ir"] is not None) is not candidate:
        raise ValueError("revision_selection_mismatch")
    if not candidate:
        if sidecar.get("candidate_ir_document_id") is not None or sidecar.get("candidate_content_sha256") is not None:
            raise ValueError("unexpected_candidate_revision")
        _same(ir, parent, "parent_ir_swap_or_mutation")
        return "historical_parent"
    if (sidecar.get("candidate_ir_document_id") != ir["ir_document_id"]
            or sidecar.get("candidate_content_sha256") != digest(ir)
            or ir["ir_document_id"] == parent["ir_document_id"]):
        raise ValueError("candidate_ir_swap_or_mutation")
    # Only the existing measure-core revision fields may differ. Array order,
    # source IDs, spelling, duration, ties, grace and all extensions are protected.
    reduced = deepcopy(ir)
    reduced["ir_document_id"] = parent["ir_document_id"]
    for field in ("measures", "note_events", "rest_events"):
        if len(reduced[field]) != len(parent[field]):
            raise ValueError("revision_protected_projection_changed")
        for new, old in zip(reduced[field], parent[field]):
            for key in (("measure_id", "printed_measure_number") if field == "measures"
                        else ("measure_id", "onset_in_measure")):
                new[key] = deepcopy(old[key])
    _same(reduced, parent, "revision_protected_projection_changed")
    return "measure_core_candidate"


def validate_parent_provenance(ir, *, integration_index_row, integration_packet,
                               original_stored_packet, frozen_plan_row, package,
                               revision_row, revision_sidecar, parent_ir):
    """Return exact scope/origin after checking all explicit parent content.

    File-byte/report trust, full selector replay and full physical revision replay
    remain explicit package-level runner checks, not certifications by this API.
    """
    row, packet, old, planned = integration_index_row, integration_packet, original_stored_packet, frozen_plan_row
    source, plan = package["source"], package["plan"]
    provenance, bundle = packet["provenance"], packet["bundle"]
    pair = package["pair_id"]
    if any(value.get("pair_id") != pair for value in (source, row, packet, revision_row, revision_sidecar)):
        raise ValueError("frozen_parent_pair_mismatch")
    if (packet.get("version") != "harmony-context-integration-trial-0.1.0"
            or bundle.get("version") != "harmony-context-bundle-0.1.0"
            or old.get("version") != SELECTOR_VERSION or plan.get("version") != SELECTOR_VERSION
            or plan.get("selection") != SELECTOR_POLICY or plan.get("source_labels_used") is not False):
        raise ValueError("unsupported_frozen_parent_version_or_selector")
    if (type(planned["plan_index"]) is not int or type(planned["lane_index"]) is not int
            or planned["plan_index"] < 0 or planned["lane_index"] < 0
            or sum(digest(r) == digest(planned) for r in plan["selected_samples"]) != 1
            or sum(r["plan_index"] == planned["plan_index"] for r in plan["selected_samples"]) != 1):
        raise ValueError("frozen_plan_row_not_unique")
    sample = planned["sample"]
    _sample(parent_ir, sample)
    if (row["plan_index"] != planned["plan_index"] or packet["plan_index"] != planned["plan_index"]
            or row["sample_id"] != sample["sample_id"] or bundle["sample"] != sample or old["sample"] != sample):
        raise ValueError("frozen_sample_index_packet_mismatch")
    inventory = [r for r in plan["lane_inventory"] if r["lane"] == sample["lane"]]
    if len(inventory) != 1 or planned["lane_index"] not in inventory[0]["selected_lane_indices"]:
        raise ValueError("frozen_sample_lane_index_mismatch")
    entry = source["manifest_entry"]
    validate_policy(entry)
    if (entry["score_id"] != parent_ir["score"]["score_id"] or entry["ir_document_id"] != parent_ir["ir_document_id"]
            or parent_ir["source_files"] != ir["source_files"] or len(ir["source_files"]) != 1
            or entry["score_sha256"] != ir["source_files"][0]["sha256"]
            or source["source_files"].get(entry["score_source_path"]) != entry["score_sha256"]
            or entry["annotation_sha256"] not in source["source_files"].values()):
        raise ValueError("frozen_manifest_source_identity_mismatch")
    _same(provenance["manifest_entry"], entry, "integration_manifest_mismatch")
    _same(provenance["pitch_policy"], source["pitch_policy"], "integration_pitch_policy_mismatch")
    selection = _revision(ir, parent_ir, source, revision_row, revision_sidecar)
    if (provenance["historical_ir_document_id"] != parent_ir["ir_document_id"]
            or provenance["working_ir_document_id"] != ir["ir_document_id"]
            or provenance["measure_revision_status"] != revision_sidecar["status"]
            or provenance["measure_revision_sidecar"] != revision_row["sidecar"]
            or provenance["ir_use_scope"] != "note_rest_measure_core_only"):
        raise ValueError("integration_revision_binding_mismatch")
    _flags(provenance, ("source_labels_used", "annotation_retargeted", "extensions_consumed",
                        "source_locator_revision_applied", "independent_source_occurrence_certified"),
           "unsafe_integration_provenance")
    _flags(packet, ("musical_accuracy_measured", "production_modified"), "unsafe_integration_packet")
    _flags(bundle, ("ranking_performed", "confidence_generated", "harmonic_analysis_confirmed",
                    "source_labels_used", "production_modified", "annotation_retargeted",
                    "gate_changed", "core_modified", "accuracy_measured"), "unsafe_context_bundle")
    if any(value.get("selected") is not None for value in (packet, bundle, old)):
        raise ValueError("frozen_parent_contains_selected_verdict")
    if (row["working_ir_document_id"] != ir["ir_document_id"] or bundle["parent_ir_document_id"] != ir["ir_document_id"]
            or bundle["score_id"] != ir["score"]["score_id"] or bundle["input_ir_content_sha256"] != digest(ir)
            or bundle["input_sample_content_sha256"] != digest(old)):
        raise ValueError("integration_working_ir_or_stored_packet_mismatch")
    if (row["status"] != bundle["status"] or row["summary"] != bundle["counts"]
            or row["previous_status"] != old["summary"]["status"]):
        raise ValueError("integration_index_status_or_counts_mismatch")
    if (not set(old["stages"]) <= set(bundle["stages"])
            or set(bundle["stages"]) - set(old["stages"]) - {"missing_evidence"}):
        raise ValueError("original_stored_stages_not_preserved_or_unknown_added_stage")
    _same({key: bundle["stages"][key] for key in old["stages"]}, old["stages"],
          "original_stored_stages_not_preserved")
    if "missing_evidence" in set(bundle["stages"]) - set(old["stages"]):
        added = bundle["stages"]["missing_evidence"]
        if added.get("version") != "missing-evidence-audit-0.1.0" or added.get("selected") is not None:
            raise ValueError("unsupported_added_integration_stage")
        _flags(added, ("gate_changed", "accuracy_measured", "production_modified"),
               "unsafe_added_integration_stage")
    _same(bundle["stage_statuses"],
          {key: value.get("status", "no_stage_status") for key, value in bundle["stages"].items()},
          "integration_stage_status_inventory_mismatch")
    _same(bundle["stored_summary"], old["summary"], "original_stored_summary_not_preserved")
    _flags(old, ("production_modified",), "unsafe_original_stored_packet")
    for value in (old["summary"], *old["stages"].values()):
        if not isinstance(value, dict):
            raise ValueError("invalid_original_stored_stage")
        if any(value.get(flag, False) is not False for flag in
               ("source_labels_used", "source_annotation_used", "accuracy_measured", "production_modified", "ranking_performed", "engine_recomputed")):
            raise ValueError("original_stored_stage_not_label_blind")
    scope = {"score_id": ir["score"]["score_id"], "ir_document_id": ir["ir_document_id"],
             "ir_content_sha256": digest(ir), "source_files": deepcopy(ir["source_files"]),
             "target_span": deepcopy(sample["span"]), "context_span": deepcopy(sample["span"])}
    parents = dict(zip(PARENT_ARGUMENTS, (row, packet, old, planned, package, revision_row, revision_sidecar, parent_ir)))
    origin = {"kind": "frozen_context_window", "pair_id": pair,
              "plan_index": planned["plan_index"], "lane_index": planned["lane_index"],
              "sample": deepcopy(sample), "target_policy": "full_frozen_context",
              "selector": {"version": SELECTOR_VERSION, "policy": SELECTOR_POLICY,
                           "window_selection_label_independent": True,
                           "sampled_lane_is_seed_metadata_only": True, "all_parts_projected": True},
              "cohort_dependency": {"kind": "inherited_score_annotation_hash_pair_and_alignment_eligibility",
                                    "annotation_independent_cohort": False,
                                    "manifest_entry_id": entry["manifest_entry_id"],
                                    "annotation_sha256": entry["annotation_sha256"],
                                    "annotation_lineage_id": entry.get("annotation_lineage_id"),
                                    "work_family_id": entry["work_family_id"], "split": entry["split"]},
              "working_ir_selection": selection,
              "historical_ir_document_id": parent_ir["ir_document_id"],
              "historical_ir_content_sha256": digest(parent_ir),
              "parent_content_sha256": {key: digest(value) for key, value in parents.items()},
              "artifact_references": {"integration_artifact": row["artifact"], "integration_file_sha256": row["sha256"],
                                      "original_stored_artifact": provenance["reused_stage_artifact"],
                                      "original_stored_file_sha256": provenance["reused_stage_sha256"],
                                      "revision_sidecar": revision_row["sidecar"],
                                      "historical_ir_file_sha256": source["ir_sha256"]},
              "parent_statuses": {"original": row["previous_status"], "integration": row["status"],
                                  "measure_revision": revision_sidecar["status"]},
              "source_statement_or_alignment_certified": False,
              "source_file_bytes_checked_by_pure_function": False,
              "selector_and_revision_fresh_replay_required_by_runner": True,
              "annotation_or_parent_locator_retargeted": False}
    return {"scope": scope, "origin": origin}


def _payload(ir, scope, origin):
    if set(scope) != SCOPE_KEYS or scope["target_span"] != scope["context_span"] or scope["context_span"] != origin["sample"]["span"]:
        raise ValueError("frozen_scope_sample_mismatch_or_source_branch")
    _sample(ir, origin["sample"])
    body = literal_payload(ir, scope)
    body.update(schema_name=SCHEMA_NAME, schema_version=SCHEMA_VERSION, producer_version=VERSION,
                origin=deepcopy(origin))
    return body


def observe(ir, **parents):
    if set(parents) != set(PARENT_ARGUMENTS):
        raise ValueError("all_explicit_frozen_parent_arguments_required")
    checked = validate_parent_provenance(ir, **parents)
    body = _payload(ir, **checked)
    sha = digest(body)
    record = {**body, "record_id": "mfco_" + sha[:24], "record_sha256": sha}
    validate_observation(record)
    return record


def validate_observation(record, *, ir=None, scope=None, **parents):
    validator().validate(record)
    body = {k: v for k, v in record.items() if k not in ("record_id", "record_sha256")}
    sha = digest(body)
    if record["record_sha256"] != sha or record["record_id"] != "mfco_" + sha[:24]:
        raise ValueError("frozen_observation_seal_mismatch")
    if (record["scope"]["target_span"] != record["scope"]["context_span"]
            or record["scope"]["context_span"] != record["origin"]["sample"]["span"]):
        raise ValueError("frozen_scope_sample_mismatch_or_source_branch")
    if scope is not None and record["scope"] != scope:
        raise ValueError("frozen_observation_scope_mismatch")
    if parents:
        if ir is None or set(parents) != set(PARENT_ARGUMENTS):
            raise ValueError("all_explicit_frozen_parent_arguments_and_ir_required")
        checked = validate_parent_provenance(ir, **parents)
        if record["scope"] != checked["scope"] or record["origin"] != checked["origin"]:
            raise ValueError("frozen_parent_origin_or_scope_mismatch")
    if ir is not None and body != _payload(ir, record["scope"], record["origin"]):
        raise ValueError("frozen_observation_reconstruction_mismatch")
    return True


def reconstruct(record):
    """Return unchanged scoped notated events, not a standalone score export."""
    validate_observation(record)
    return [deepcopy(slot["core_event"]) for slot in record["slots"]]
