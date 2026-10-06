"""Fresh, explicitly enlarged source scope; never a rebound frozen analysis.

The expanded scope supplies literal source facts and new geometry hypotheses.
It is neither an mfco/fmview nor a SOURCE/alignment admission.  Full parent
replay belongs to prepare_scope/validate_scope; check_scope(ir=...) additionally
replays source facts without pretending to establish the absent parent trust.
"""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

from . import factor_context_observation as context
from . import factor_musical_view as common
from . import frozen_context_observation as frozen
from . import harmony_factorized_voice_paths as factors
from . import harmony_path_contrast as contrast
from . import harmony_voice_paths as voices
from . import musical_pattern_observation as pattern
from . import sounding_lineage_audit as lineage

VERSION = "factor-expanded-scope-0.1.0"
PREFIX = "fmes_"
CAP_KEYS = {"max_events", "max_factors", "max_edges"}
CONTEXT_OPTIONS = {"pre_measures", "post_measures", "max_events", "max_relations"}
SOURCE_KEYS = {"literal_observation", "sound_facts", "raw_lanes", "graphs", "source_audit",
               "lane_inventory", "full_IR_context_sound_refs", "literal_context_sound_refs",
               "unprojected_context_sound_snapshots", "outside_analysis_sound_refs",
               "context_sound_inventory_complete", "counts", "status", "reasons"}
BODY_KEYS = SOURCE_KEYS | {"version", "contract", "binding", "analysis_span", "anchor_span",
                          "original_target_span", "original_view_ref", "observation_ref", "audit_ref",
                          "extension_ref", "extension_options", "options", "scope_policy", "flags",
                          "selected", "preferred", "use_policy", "limits"}


def _flags():
    return {"original_window_or_path_or_bundle_extended": False,
            "source_statement_or_alignment_refs_invented": False,
            "source_annotations_used": False, "source_file_bytes_checked_by_pure_function": False,
            "parent_artifact_authority_established": False, "core_modified": False,
            "source_repaired": False, "partial_lane_or_sound_selection_performed": False,
            "voice_identity_confirmed": False, "harmony_confirmed": False, "key_confirmed": False,
            "function_confirmed": False, "resolution_confirmed": False, "cadence_confirmed": False,
            "nct_confirmed": False, "counts_are_confidence": False, "musical_accuracy_measured": False,
            "training_eligible": False, "gold_eligible": False, "generation_ready": False}


def _contract():
    modules = (common, frozen, context, pattern, lineage, factors, contrast, voices)
    sources = [{"module": __name__, "sha256": sha256(Path(__file__).read_bytes()).hexdigest()}]
    sources.extend({"module": module.__name__, "sha256": sha256(Path(module.__file__).read_bytes()).hexdigest()}
                   for module in modules)
    schemas = [{"kind": "view_core", "sha256": sha256(common._schema_bytes()).hexdigest()}]
    schemas.extend({"kind": name, "sha256": sha256(path.read_bytes()).hexdigest()}
                   for name, path in (("pattern_core", pattern.CORE_SCHEMA_PATH),
                                      ("literal_pattern", pattern.SCHEMA_PATH),
                                      ("frozen_core", frozen.CORE_SCHEMA_PATH),
                                      ("frozen_observation", frozen.SCHEMA_PATH)))
    return {"version": VERSION, "sources": sources, "schemas": schemas}


def _caps(max_events, max_factors, max_edges):
    result = {"max_events": max_events, "max_factors": max_factors, "max_edges": max_edges}
    for name, value in result.items():
        if type(value) is not int or value < 0:
            raise ValueError("nonnegative_integer_required:" + name)
    return result


def _binding(ir):
    return {"score_id": ir["score"]["score_id"], "ir_document_id": ir["ir_document_id"],
            "source_file_id": ir["score"]["source_file_id"], "ir_content_sha256": pattern.digest(ir),
            "source_files": deepcopy(ir["source_files"])}


def _in_span(sound, span):
    a, b = common._bounds(sound["span"], point=True)
    c, d = common.span_bounds(span)
    return c <= a < d if a == b else a < d and b > c


def _fact(sound, notes, audit_row, analysis, anchor, attack_rows):
    ids = sound["source_note_ids"]
    owners = {(notes[nid]["part_id"], notes[nid]["voice_id"]) for nid in ids}
    lane = list(next(iter(owners))) if len(owners) == 1 else None
    a, b = common._bounds(sound["span"], point=True)
    point = a == b
    grace = any(notes[nid]["grace"]["is_grace"] for nid in ids)
    key = common.pitch_key(sound["pitch"], octave=True)
    pitch_passed = all(common.pitch_key(notes[nid]["written_pitch"], octave=True) == key for nid in ids)
    pitch_passed = pitch_passed and common.pitch_key(notes[sound["attack_note_id"]]["written_pitch"], octave=True) == key
    codes = list(audit_row["diagnostics"])
    if lane is None:
        codes.append("ambiguous_raw_lane_ownership")
    if not pitch_passed:
        codes.append("source_written_pitch_mismatch")
    integral = common.f(sound["pitch"]["alter"]).denominator == 1
    if not integral:
        codes.append("microtonal_ordinary_tonal_source_not_supported")
    attacks = [row for row in attack_rows if row["sounding_event_id"] == sound["sounding_event_id"]]
    attack_passed = (len(attacks) == 1 and attacks[0]["note_id"] == sound["attack_note_id"]
                     and common.f(attacks[0]["global_onset_quarter"]) == common.f(notes[sound["attack_note_id"]]["global_onset_quarter"]))
    if not attack_passed:
        codes.append("source_attack_event_inventory_or_lineage_mismatch")
    eligible = not point and not grace and lane is not None and integral and pitch_passed and attack_passed and audit_row["source_clock_consistency_passed"]
    return {"sound_ref": sound["sounding_event_id"], "sound_id": sound["sounding_event_id"],
            "source_note_refs": deepcopy(ids), "source_note_ids": deepcopy(ids),
            "attack_note_ref": sound["attack_note_id"], "attack_note_id": sound["attack_note_id"],
            "tie_chain_ref": sound.get("tie_chain_id"), "lane": lane, "pitch": deepcopy(sound["pitch"]),
            "span": deepcopy(sound["span"]),
            "observed_span": deepcopy(sound["span"]) if point else common.clipped(sound["span"], analysis),
            "anchor_overlap": common.clipped(sound["span"], anchor), "point": point, "grace": grace,
            "source_clock_passed": audit_row["source_clock_consistency_passed"],
            "source_pitch_consistency_passed": pitch_passed,
            "source_attack_consistency_passed": attack_passed,
            "source_audit_row_sha256": pattern.digest(audit_row),
            "diagnostics": sorted(set(codes)), "source_diagnostics": sorted(set(codes)),
            "eligible_as_analysis_source": eligible, "outside_analysis_metadata_only": False,
            "voice_identity_confirmed": False, "harmony_membership_evaluated": False,
            "resolution_eligible": False}


def _source_payload(ir, binding, analysis, anchor, caps):
    scope = {key: deepcopy(binding[key]) for key in ("score_id", "ir_document_id", "ir_content_sha256", "source_files")}
    scope.update(target_span=deepcopy(analysis), context_span=deepcopy(analysis))
    slots, projection, lanes = common._selected_literal(ir, scope)
    literal = {"scope": scope, "slots": slots, "core_projection": projection, "raw_lanes": lanes,
               "kind": "explicit_expanded_literal_scope_not_MPO_mfco_or_fmview",
               "source_statement_or_alignment_refs_invented": False}
    closure = projection["sounding_events"]
    source_audit = lineage.audit_sounding_lineage(ir, sound_ids=[s["sounding_event_id"] for s in closure], context_span=analysis)
    audited = {row["sounding_event_ref"]: row for row in source_audit["sounding_audits"]}
    notes = {n["note_id"]: n for n in ir["note_events"]}
    active = [s for s in closure if _in_span(s, analysis)]
    facts = [_fact(sound, notes, audited[sound["sounding_event_id"]], analysis, anchor, projection["attack_events"])
             for sound in active]
    full_context = [s for s in ir["sounding_events"] if _in_span(s, analysis)]
    projected_ids = {s["sounding_event_id"] for s in active}
    unmatched = sorted((s for s in full_context if s["sounding_event_id"] not in projected_ids),
                       key=lambda sound: sound["sounding_event_id"])
    graphs, inventory = [], []
    reasons = []
    for row in lanes:
        lane = [row["part_id"], row["voice_id"]]
        graph = factors.factorize(ir, analysis, lane, **caps)
        graphs.append(graph)
        lane_facts = [s for s in facts if s["lane"] == lane]
        source_holds = [s["sound_ref"] for s in lane_facts if not s["eligible_as_analysis_source"]]
        geometry_reasons = list(graph["reasons"])
        lane_reasons = ["geometry:" + reason for reason in geometry_reasons]
        if source_holds:
            lane_reasons.append("involved_source_guards_unestablished")
        if unmatched:
            lane_reasons.append("full_IR_context_sound_missing_from_literal_projection")
        inventory.append({"lane": lane, "event_refs": deepcopy(row["event_ids"]), "graph_ref": common.ref(graph),
                          "geometry_status": graph["status"], "status": "withheld" if lane_reasons else "ready",
                          "reasons": sorted(set(lane_reasons)),
                          "positive_sound_refs": [s["sound_ref"] for s in lane_facts if not s["point"]],
                          "point_sound_refs": [s["sound_ref"] for s in lane_facts if s["point"]],
                          "grace_sound_refs": [s["sound_ref"] for s in lane_facts if s["grace"]],
                          "source_hold_refs": source_holds, "baseline_voice_is_confirmed": False,
                          "all_no_link_geometry_alternatives_retained": True})
        reasons.extend("lane:" + "/".join(lane) + ":" + reason for reason in lane_reasons)
    if unmatched:
        reasons.append("full_IR_context_sound_missing_from_literal_projection")
    complete = not unmatched
    status = ("whole_scope_abstention" if not complete else "expanded_scope_with_lane_holds" if reasons else "ready_expanded_scope")
    return {"literal_observation": literal, "sound_facts": facts, "raw_lanes": lanes,
            "graphs": graphs, "source_audit": source_audit, "lane_inventory": inventory,
            "full_IR_context_sound_refs": sorted(s["sounding_event_id"] for s in full_context),
            "literal_context_sound_refs": sorted(projected_ids),
            "unprojected_context_sound_snapshots": deepcopy(unmatched),
            "outside_analysis_sound_refs": sorted(s["sounding_event_id"] for s in closure if not _in_span(s, analysis)),
            "context_sound_inventory_complete": complete,
            "counts": {"literal_slots": len(slots), "literal_closure_sounds": len(closure),
                       "analysis_positive_sounds": sum(not row["point"] for row in facts),
                       "analysis_point_sounds": sum(row["point"] for row in facts), "raw_lanes": len(lanes),
                       "graphs_ready": sum(g["status"] == "ready" for g in graphs),
                       "graphs_held": sum(g["status"] != "ready" for g in graphs),
                       "source_guard_held_sounds": sum(not row["eligible_as_analysis_source"] for row in facts),
                       "unprojected_context_sounds": len(unmatched)},
            "status": status, "reasons": sorted(set(reasons))}


def _snapshot_source_replay(body):
    """Reconstruct stored-source consistency, not the absent full IR authority.

    The temporary snapshot document is only a verification model. Its digest
    is never published as the original IR digest; the expected record binding
    is explicitly checked separately. Full-IR replay remains the ir= branch.
    """
    literal = body["literal_observation"]
    projection = literal["core_projection"]
    snapshot = {key: deepcopy(projection[key]) for key in pattern.COLLECTIONS
                if key not in ("note_events", "rest_events")}
    snapshot["note_events"] = [deepcopy(row["core_event"]) for row in literal["slots"] if row["event_kind"] == "note"]
    snapshot["rest_events"] = [deepcopy(row["core_event"]) for row in literal["slots"] if row["event_kind"] == "rest"]
    snapshot["parser_manifest"] = deepcopy(projection["parser_manifest"])
    if pattern.digest(snapshot["source_files"]) != pattern.digest(body["binding"]["source_files"]):
        raise ValueError("expanded_projection_source_file_binding_mismatch")
    def merge(collection, key, rows):
        existing = {row[key]: row for row in snapshot[collection]}
        for row in rows:
            if row[key] in existing:
                if existing[row[key]] != row:
                    raise ValueError("expanded_snapshot_alias_content_mismatch:" + key)
            else:
                snapshot[collection].append(deepcopy(row))
                existing[row[key]] = row
    merge("sounding_events", "sounding_event_id", body["unprojected_context_sound_snapshots"])
    for graph in body["graphs"]:
        merge("note_events", "note_id", graph["source_note_events"])
        merge("source_references", "source_ref_id", graph["source_references"])
        merge("tie_chains", "tie_chain_id", graph["tie_chains"])
    for key, identity, schema in (("note_events", "note_id", "note"), ("rest_events", "rest_id", "rest"),
                                 ("sounding_events", "sounding_event_id", "sounding"),
                                 ("tie_chains", "tie_chain_id", "tieChain"),
                                 ("attack_events", "attack_event_id", "attack"),
                                 ("source_references", "source_ref_id", "sourceRef"),
                                 ("measures", "measure_id", "measure"),
                                 ("parts", "part_id", "part"), ("staves", "staff_id", "staff"),
                                 ("voices", "voice_id", "voice"),
                                 ("chord_onset_groups", "chord_onset_group_id", "chordGroup")):
        common._literal(snapshot[key], identity, schema)
    indices = {name: common._index(snapshot[name], key) for name, key in pattern.COLLECTIONS.items()}
    all_ids = [identity for rows in indices.values() for identity in rows]
    if len(all_ids) != len(set(all_ids)):
        raise ValueError("expanded_snapshot_ID_namespace_collision")
    for event in [*snapshot["note_events"], *snapshot["rest_events"]]:
        if event["score_id"] != body["binding"]["score_id"]:
            raise ValueError("expanded_snapshot_foreign_event_score")
        for key, collection in (("part_id", "parts"), ("voice_id", "voices"), ("display_staff_id", "staves"),
                                ("measure_id", "measures"), ("source_ref_id", "source_references")):
            if event[key] not in indices[collection]:
                raise ValueError("expanded_snapshot_dangling_event_reference:" + key)
        measure = indices["measures"][event["measure_id"]]
        source = indices["source_references"][event["source_ref_id"]]
        if source["source_file_id"] not in indices["source_files"]:
            raise ValueError("expanded_snapshot_foreign_source_file")
        onset, duration = common.f(event["global_onset_quarter"]), common.f(event["notated_duration_quarter"])
        if onset < 0 or duration < 0 or onset != common.f(measure["global_start_quarter"]) + common.f(event["onset_in_measure"]):
            raise ValueError("expanded_snapshot_invalid_measure_clock")
    duration = max([common.f(body["analysis_span"]["end"]),
                    *[common.f(row["span"]["end"]) for row in snapshot["sounding_events"]],
                    *[common.f(row["global_onset_quarter"]) + common.f(row["notated_duration_quarter"])
                      for row in [*snapshot["note_events"], *snapshot["rest_events"]]]])
    binding = body["binding"]
    snapshot["ir_document_id"] = binding["ir_document_id"]
    snapshot["score"] = {"score_id": binding["score_id"], "source_file_id": binding["source_file_id"],
                         "duration_quarters": common.q(duration)}
    expected = _source_payload(snapshot, binding, body["analysis_span"], body["anchor_span"], body["options"])
    # Geometry/audit kernels hash the verification model. Compare their actual
    # payloads with the already independently checked original binding instead.
    audit_body = common.check(expected["source_audit"], lineage.PREFIX)
    audit_body["binding"] = {key: deepcopy(binding[key]) for key in
                             ("score_id", "ir_document_id", "ir_content_sha256", "source_files")}
    expected["source_audit"] = common.seal(audit_body, lineage.PREFIX)
    for graph, inventory in zip(expected["graphs"], expected["lane_inventory"]):
        graph_body = common.check(graph, "vfgraph_")
        graph_body["binding"] = deepcopy(binding)
        rebuilt = common.seal(graph_body, "vfgraph_")
        graph.clear()
        graph.update(rebuilt)
        inventory["graph_ref"] = common.ref(graph)
    return expected


def prepare_scope(ir, view, observation, audit, extension, *, max_events=4096,
                  max_factors=4096, max_edges=65536):
    """Freshly admit one entire fmctx envelope with all source/geometry holds.

    A context-level whole-budget abstention is not permission for partial
    admission. Geometry limits apply per raw lane and preserve every lane.
    File bytes and historical report authority remain runner responsibilities.
    """
    caps = _caps(max_events, max_factors, max_edges)
    before = pattern.digest([ir, view, observation, audit, extension])
    contract = _contract()
    common.check(extension, context.PREFIX)
    common._closed(extension["options"], CONTEXT_OPTIONS, "context_options")
    context.validate_context(extension, ir=ir, view=view, observation=observation, audit=audit,
                             **extension["options"])
    if extension["status"] != "ready_literal_context_not_analysis" or not extension["relations_complete"]:
        raise ValueError("whole_context_budget_hold_cannot_admit_expanded_scope")
    binding = _binding(ir)
    if binding != view["binding"] or binding != extension["binding"]:
        raise ValueError("expanded_scope_parent_IR_binding_mismatch")
    analysis, anchor = extension["envelope_span"], view["context_span"]
    c, d = common.span_bounds(analysis)
    a, b = common.span_bounds(anchor)
    if not c <= a < b <= d <= common.f(ir["score"]["duration_quarters"]):
        raise ValueError("expanded_scope_does_not_contain_anchor_or_exceeds_score")
    body = {"version": VERSION, "contract": contract, "binding": binding,
            "analysis_span": deepcopy(analysis), "anchor_span": deepcopy(anchor),
            "original_target_span": deepcopy(view["target_span"]),
            "original_view_ref": common.ref(view), "observation_ref": common.ref(observation),
            "audit_ref": common.ref(audit), "extension_ref": common.ref(extension),
            "extension_options": deepcopy(extension["options"]), "options": caps,
            "scope_policy": "new_target_and_context_equal_entire_validated_fmctx_envelope",
            **_source_payload(ir, binding, analysis, anchor, caps), "flags": _flags(),
            "selected": None, "preferred": None, "use_policy": deepcopy(common.POLICY),
            "limits": ["This new scope does not extend or rebind any old observation, path, key or bundle.",
                       "Raw lanes and geometry completions are hypotheses, never confirmed musical voices.",
                       "Full source spans and outside linked closure remain intact; only analysis overlaps are admitted.",
                       "Source guard holds are local facts; no held source is dropped to choose another pitch.",
                       "No source statement/alignment, chord/key/cadence verdict or use-policy promotion exists.",
                       "Fresh full-parent replay is distinct from intrinsic seals or IR-only source replay."]}
    if pattern.digest([ir, view, observation, audit, extension]) != before or _contract() != contract:
        raise ValueError("expanded_scope_inputs_or_contract_changed")
    # An output tree has no mutable aliases even between its repeated literal
    # inventories. JSON round-trip preserves canonical values, not object IDs.
    result = json.loads(json.dumps(common.seal(body, PREFIX), ensure_ascii=False, allow_nan=False))
    check_scope(result)
    return result


def check_scope(record, *, ir=None):
    """Check intrinsic contract; optional IR replays all new source/geometry facts.

    This does not fresh-replay the absent original/fmctx parent artifacts.
    validate_scope is the explicit all-parent authority check at the runner.
    """
    body = common.check(record, PREFIX)
    common._closed(body, BODY_KEYS, "expanded_scope")
    if (body["version"] != VERSION or body["contract"] != _contract() or body["flags"] != _flags()
            or body["selected"] is not None or body["preferred"] is not None or body["use_policy"] != common.POLICY
            or any(type(value) is not bool for value in body["flags"].values())
            or any(type(value) is not bool for value in body["use_policy"].values())
            or body["scope_policy"] != "new_target_and_context_equal_entire_validated_fmctx_envelope"):
        raise ValueError("unsupported_stale_or_promoting_expanded_scope")
    common._binding(body["binding"])
    caps = body["options"]
    common._closed(caps, CAP_KEYS, "expanded_geometry_options")
    _caps(**caps)
    common._closed(body["extension_options"], CONTEXT_OPTIONS, "context_options")
    for name, prefix in (("original_view_ref", common.PREFIX), ("observation_ref", "mfco_"),
                         ("audit_ref", lineage.PREFIX), ("extension_ref", context.PREFIX)):
        common._reference(body[name], prefix)
    c, d = common.span_bounds(body["analysis_span"])
    a, b = common.span_bounds(body["anchor_span"])
    t, u = common.span_bounds(body["original_target_span"])
    if not c <= a <= t < u <= b <= d:
        raise ValueError("expanded_scope_original_spans_not_contained")
    literal = body["literal_observation"]
    scope = literal["scope"]
    expected_scope = {key: body["binding"][key] for key in ("score_id", "ir_document_id", "ir_content_sha256", "source_files")}
    expected_scope.update(target_span=body["analysis_span"], context_span=body["analysis_span"])
    if (scope != expected_scope or literal["raw_lanes"] != body["raw_lanes"]
            or literal["kind"] != "explicit_expanded_literal_scope_not_MPO_mfco_or_fmview"
            or literal["source_statement_or_alignment_refs_invented"] is not False):
        raise ValueError("expanded_literal_scope_contract_mismatch")
    common._closed(literal, {"scope", "slots", "core_projection", "raw_lanes", "kind", "source_statement_or_alignment_refs_invented"}, "expanded_literal")
    graph_by_lane = {}
    for graph in body["graphs"]:
        graph_body = factors._graph(graph)
        lane = tuple(graph_body["lane"])
        if (lane in graph_by_lane or graph_body["binding"] != body["binding"]
                or graph_body["span"] != body["analysis_span"] or graph_body["resource_limits"] != caps):
            raise ValueError("foreign_old_or_duplicate_expanded_geometry")
        graph_by_lane[lane] = graph
    expected_lanes = [[row["part_id"], row["voice_id"]] for row in body["raw_lanes"]]
    if len(expected_lanes) != len({tuple(row) for row in expected_lanes}) or sorted(graph_by_lane) != sorted(tuple(row) for row in expected_lanes):
        raise ValueError("expanded_raw_lane_geometry_denominator_mismatch")
    if [row["lane"] for row in body["lane_inventory"]] != expected_lanes:
        raise ValueError("expanded_lane_inventory_denominator_mismatch")
    for row in body["lane_inventory"]:
        if row["graph_ref"] != common.ref(graph_by_lane[tuple(row["lane"])]):
            raise ValueError("expanded_lane_inventory_foreign_graph")
    intrinsic = _snapshot_source_replay(body)
    if pattern.digest(intrinsic) != pattern.digest({key: body[key] for key in SOURCE_KEYS}):
        raise ValueError("expanded_scope_stored_source_geometry_reconstruction_mismatch")
    if ir is not None:
        pattern.validate_core(ir)
        if _binding(ir) != body["binding"]:
            raise ValueError("stale_or_foreign_expanded_scope_IR")
        if d > common.f(ir["score"]["duration_quarters"]):
            raise ValueError("expanded_scope_exceeds_IR_duration")
        fresh = _source_payload(ir, body["binding"], body["analysis_span"], body["anchor_span"], caps)
        if pattern.digest(fresh) != pattern.digest({key: body[key] for key in SOURCE_KEYS}):
            raise ValueError("expanded_scope_source_geometry_exact_replay_mismatch")
    return True


def validate_scope(record, *, ir, view, observation, audit, extension, max_events=4096,
                   max_factors=4096, max_edges=65536):
    """Always freshly rebuild every old parent, literal fact, audit and graph."""
    check_scope(record)
    if record != prepare_scope(ir, view, observation, audit, extension, max_events=max_events,
                               max_factors=max_factors, max_edges=max_edges):
        raise ValueError("stale_foreign_or_modified_expanded_scope")
    return True
