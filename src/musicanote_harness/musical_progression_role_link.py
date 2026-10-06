"""Bind one full progression/assignment to literal and conditional role evidence.

The chord assumption is assignment-independent. NCT conditions remain a
separate account for the supplied sampled assignment; neither a pedal shape
nor conditional NCT coverage changes raw membership or chooses a role.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from hashlib import sha256
import hmac
import json
import secrets
from weakref import WeakKeyDictionary
from .musical_pattern_observation import digest, f, q, span_bounds, validate_observation
from .musical_harmony_assumption import build_track, PITCH_BASIS
from .musical_role_evidence import analyze as role_analyze, ref
from . import musical_harmony_assumption as assumption_module
from . import musical_pattern_observation as observation_module
from . import musical_role_evidence as role_module
from .harmony_context_bundle import _validate_lattice
from .harmony_progression_joint_comparison import _validate_path, _raw, _origins
from .harmony_progression_evidence import vector
from .harmony_shared_context import catalog as geometry_catalog
from .harmony_voice_paths import partition
from .harmony_catalog_resolution import pitch_pair
from .harmony_reading_voice_context import spelled_height

VERSION = "musical-progression-role-link-0.1.1"


def _pitch(pair):
    if (not isinstance(pair, (list, tuple)) or len(pair) != 2
            or not isinstance(pair[0], str) or len(pair[0]) != 1
            or pair[0] not in "CDEFGAB" or type(pair[1]) is not int):
        raise ValueError("unsupported_progression_pitch_pair")
    return {"step": pair[0], "alter": q(pair[1])}


def _context_guards(ir, observation, bundle, pitch_policy):
    if not isinstance(pitch_policy, dict) or pitch_policy.get("harmonic_replay_allowed") is not True:
        raise ValueError("explicit_harmonic_replay_pitch_policy_required")
    validate_observation(observation, ir=ir)
    if pitch_policy.get("pitch_basis") != PITCH_BASIS:
        raise ValueError("explicit_written_ir_pitch_basis_required")
    if pitch_policy.get("ir_content_sha256") != digest(ir):
        raise ValueError("pitch_policy_ir_hash_mismatch")
    score_sources = [s for s in ir["source_files"] if s["source_file_id"] == ir["score"]["source_file_id"]]
    if len(score_sources) != 1 or pitch_policy.get("source_sha256") != score_sources[0]["sha256"]:
        raise ValueError("pitch_policy_source_hash_mismatch")
    for flag in ("nonzero_source_transposition", "malformed_or_unsupported_transposition",
                 "concert_pitch_normalization_verified"):
        if pitch_policy.get(flag) is not False:
            raise ValueError("unsupported_or_certified_pitch_policy:" + flag)
    if (bundle.get("parent_ir_document_id") != ir["ir_document_id"]
            or bundle.get("score_id") != ir["score"]["score_id"]
            or bundle.get("input_ir_content_sha256") != digest(ir)):
        raise ValueError("stale_or_foreign_progression_ir")
    context = observation["scope"]["context_span"]
    if bundle.get("sample", {}).get("span") != context:
        raise ValueError("observation_progression_context_mismatch")
    lattice = bundle["stages"]["lattice"]
    if lattice.get("status") != "ready": raise ValueError("progression_lattice_not_ready")
    if lattice["plan"]["context_span"] != context:
        raise ValueError("lattice_sample_context_mismatch")
    for stage in (bundle, *bundle["stages"].values()):
        if not isinstance(stage, dict): raise ValueError("invalid_progression_stage")
        if stage.get("selected") is not None: raise ValueError("selected_progression_input_forbidden")
        for flag in ("source_labels_used", "source_annotation_used", "accuracy_measured",
                     "ranking_performed", "confidence_generated", "production_modified"):
            if stage.get(flag, False) is not False:
                raise ValueError("nonblind_or_promoted_progression_stage:" + flag)
    _validate_lattice(ir, bundle["sample"], lattice)
    notes = {n["note_id"]: n for n in ir["note_events"]}
    sounds = {s["sounding_event_id"]: s for s in ir["sounding_events"]}
    for sound in lattice["events"]:
        source = sounds[sound["sounding_event_id"]]
        if sound.get("attack_note_id") != source["attack_note_id"]:
            raise ValueError("progression_attack_note_reference_mismatch")
        attack = notes[source["attack_note_id"]]
        if sound["pitch"] != attack["written_pitch"]:
            raise ValueError("progression_written_pitch_basis_mismatch")
    _validate_assignments(lattice, notes, bundle["sample"].get("lane"))
    _validate_patterns(lattice)
    return lattice, notes, sounds


def _proposal_guards(lattice, proposal):
    if not isinstance(proposal, dict) or not isinstance(proposal.get("proposal_id"), str) or not proposal["proposal_id"]:
        raise ValueError("explicit_identified_progression_proposal_required")
    if proposal.get("selected") is not None: raise ValueError("selected_proposal_forbidden")
    if "semantic_group_refs" in proposal and not isinstance(proposal["semantic_group_refs"], list):
        raise ValueError("invalid_explicit_semantic_group_refs")
    _validate_path(lattice, proposal["path"])
    for choice in proposal["path"]:
        edge = lattice["edges"][choice["edge"]]
        reading = edge["readings"][choice["reading"]]
        scoped = {s["sounding_event_id"]: s for s in lattice["events"]
                  if f(s["span"]["start"]) < f(edge["span"]["end"])
                  and f(s["span"]["end"]) > f(edge["span"]["start"])}
        members = {tuple(pair) for pair in reading["members"]}
        expected = {sid: "spelling_unresolved" if spelled_height(sound["pitch"]) is None else
                    "member" if tuple(pitch_pair(sound["pitch"])) in members else "nonmember_not_confirmed_nct"
                    for sid, sound in scoped.items()}
        if reading["event_states"] != expected:
            raise ValueError("selected_reading_raw_membership_mismatch")


def _assignment(lattice, assignment_ref):
    assignments = [a for a in lattice["assignments"] if a["assignment_id"] == assignment_ref]
    if len(assignments) != 1: raise ValueError("unknown_or_duplicate_shared_assignment")
    return assignments[0]


def _guards(ir, observation, bundle, proposal, assignment_ref, pitch_policy):
    lattice, notes, sounds = _context_guards(ir, observation, bundle, pitch_policy)
    _proposal_guards(lattice, proposal)
    return lattice, _assignment(lattice, assignment_ref), notes, sounds


def _validate_assignments(lattice, notes, lane):
    if (not isinstance(lane, (list, tuple)) or len(lane) != 2
            or any(not isinstance(value, str) or not value for value in lane)):
        raise ValueError("invalid_explicit_sample_lane")
    events = []
    for sound in lattice["events"]:
        keys = {(notes[nid]["part_id"], notes[nid]["voice_id"]) for nid in sound["source_note_ids"]}
        if len(keys) != 1: raise ValueError("sound_crosses_raw_lanes")
        if next(iter(keys)) == tuple(lane): events.append(sound)
    if not events: raise ValueError("empty_sampled_assignment_scope")
    for assignment in lattice["assignments"]:
        if partition(events, assignment["links"]) != assignment["tracks"]:
            raise ValueError("sampled_assignment_partition_mismatch")


def _validate_patterns(lattice):
    """Replay the existing bounded shape vocabulary, not a new NCT classifier."""
    points = lattice["plan"]["points"]
    dummy = {"status": "ready", "span": lattice["plan"]["context_span"], "events": lattice["events"],
             "assignments": lattice["assignments"], "hold_readings": [], "boundaries": []}
    patterns, withheld = {}, {}
    for cut in points[1:-1] or [q((f(points[0]) + f(points[-1])) / 2)]:
        dummy["boundaries"] = [{"status": "ready", "boundary": cut,
                                "left": {"readings": []}, "right": {"readings": []}}]
        result = geometry_catalog(dummy, 0)
        for pattern in result["patterns"]:
            for side in ("hold", "left", "right"): pattern.pop(side + "_reading_indices")
            patterns[pattern["pattern_id"]] = pattern
        withheld.update(result["withheld_pattern_reasons"])
    if lattice["patterns"] != list(patterns.values()) or lattice["withheld_pattern_reasons"] != withheld:
        raise ValueError("progression_pattern_geometry_replay_mismatch")


def _search_context_guards(bundle, search_result):
    if search_result is None: return {}
    if (not isinstance(search_result, dict) or search_result.get("input_bundle_content_sha256") != digest(bundle)
            or search_result.get("sample") != bundle["sample"]):
        raise ValueError("search_bundle_binding_mismatch")
    if search_result.get("selected") is not None:
        raise ValueError("selected_search_forbidden")
    for flag in ("source_labels_used", "source_annotation_used", "accuracy_measured", "production_modified"):
        if search_result.get(flag, False) is not False: raise ValueError("nonblind_or_promoted_search:" + flag)
    groups = {g["group_id"]: g for g in search_result["semantic_groups"]}
    if len(groups) != len(search_result["semantic_groups"]): raise ValueError("duplicate_search_semantic_group")
    return groups


def _search_origins(lattice, bundle, proposal, search_result):
    if search_result is None:
        if proposal.get("semantic_group_refs") is not None:
            raise ValueError("semantic_groups_require_bound_search_result")
        return _origins(lattice, proposal, {}), None
    groups = _search_context_guards(bundle, search_result)
    if [p for p in search_result["proposals"] if p.get("proposal_id") == proposal["proposal_id"]] != [proposal]:
        raise ValueError("missing_duplicate_or_changed_search_proposal")
    keys = _origins(lattice, proposal, groups)
    for choice, gid, group_keys in zip(proposal["path"], proposal.get("semantic_group_refs", []), keys):
        edge = lattice["edges"][choice["edge"]]; reading = edge["readings"][choice["reading"]]
        key = lambda value: json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        signature = {"edge_index": choice["edge"], "from": edge["from"], "to": edge["to"], "span": edge["span"],
            "root_spelling": reading["root_spelling"], "root_provenance": reading.get("root_provenance"),
            "members": sorted(reading["members"], key=key),
            "candidate_blockers": sorted(reading["abstention_reasons"], key=key), "event_states": reading["event_states"]}
        if gid != "pgroup_" + digest(signature)[:24]: raise ValueError("search_semantic_group_identity_mismatch")
        expected_keys = []
        for index, other in enumerate(edge["readings"]):
            if (other.get("root_spelling") == reading.get("root_spelling")
                    and other.get("root_provenance") == reading.get("root_provenance")
                    and sorted(other["members"], key=key) == signature["members"]
                    and sorted(other["abstention_reasons"], key=key) == signature["candidate_blockers"]
                    and other["event_states"] == reading["event_states"]):
                expected_keys.append({"edge": choice["edge"], "reading": index})
        if sorted(group_keys, key=key) != sorted(expected_keys, key=key):
            raise ValueError("search_semantic_group_origin_loss")
        origins = [{"reading_key": c, **{field: deepcopy(edge["readings"][c["reading"]].get(field)) for field in
                    ("candidate_ref", "alternative_index", "origin_pointer", "provider", "display_label")}} for c in group_keys]
        if groups[gid]["origins"] != origins: raise ValueError("search_origin_provenance_mismatch")
    return keys, digest(search_result)


def _segments(lattice, proposal):
    segments, origins = [], []
    for index, choice in enumerate(proposal["path"]):
        reading = lattice["edges"][choice["edge"]]["readings"][choice["reading"]]
        members = [_pitch(pair) for pair in reading["members"]]
        blockers = list(dict.fromkeys(reading["abstention_reasons"]))
        if not members and "empty_candidate_members" not in blockers: blockers.append("empty_candidate_members")
        label = reading["display_label"]
        if not isinstance(label, str) or not label: raise ValueError("missing_explicit_candidate_display_label")
        origin = {"path_index": index, "reading_key": deepcopy(choice),
                  **{key: deepcopy(reading.get(key)) for key in ("candidate_ref", "alternative_index", "origin_pointer",
                      "provider", "display_label", "root_spelling", "root_provenance", "span", "members",
                      "missing_spellings", "abstention_reasons")}}
        sid = "mprseg_" + digest(origin)[:24]
        segments.append({"segment_id": sid, "span": deepcopy(reading["span"]), "label": label,
                         "root": None if reading.get("root_spelling") is None else _pitch(reading["root_spelling"]),
                         "members": members, "status": "blocked" if blockers else "usable",
                         "blockers": blockers, "source_locator": None})
        origins.append({**origin, "segment_id": sid, "adapter_blockers": blockers})
    return segments, origins


def _sound_refs(lattice, notes, sounds, ir):
    sources = {s["source_ref_id"]: s for s in ir["source_references"]}
    rows = []
    for event in lattice["events"]:
        sound = sounds[event["sounding_event_id"]]
        rows.append({"sounding_event_id": sound["sounding_event_id"],
            "span": deepcopy(sound["span"]), "source_note_ids": deepcopy(sound["source_note_ids"]),
            "attack_note_id": sound["attack_note_id"], "sounding_duration": deepcopy(sound["sounding_duration"]),
            "written_pitch": deepcopy(notes[sound["attack_note_id"]]["written_pitch"]),
            "note_refs": [{"note_id": nid, "raw_lane": {"part_id": notes[nid]["part_id"], "voice_id": notes[nid]["voice_id"]},
                "display_staff_id": notes[nid]["display_staff_id"],
                "global_onset_quarter": deepcopy(notes[nid]["global_onset_quarter"]),
                "notated_duration_quarter": deepcopy(notes[nid]["notated_duration_quarter"]),
                "source_ref_id": notes[nid]["source_ref_id"],
                "source_ref": deepcopy(sources[notes[nid]["source_ref_id"]])} for nid in sound["source_note_ids"]]})
    return rows


def _pattern_links(lattice, evidence, sound_refs, assignment_ref):
    indices = {p["pattern_id"]: p for p in lattice["patterns"]}
    if len(indices) != len(lattice["patterns"]): raise ValueError("duplicate_progression_pattern_id")
    refs = {r["sounding_event_id"]: r for r in sound_refs}
    context = span_bounds(evidence["context_span"])
    rows = []
    for pid in evidence["accounting"]["active_pattern_refs"]:
        pattern = indices[pid]
        if assignment_ref not in pattern["supporting_assignment_refs"]:
            raise ValueError("active_pattern_assignment_mismatch")
        for requirement in pattern["requirements"]:
            a, b = span_bounds(requirement["span"])
            if not context[0] <= a < b <= context[1]:
                raise ValueError("active_pattern_requires_outside_progression_context")
        event_ids = set(pattern["event_refs"]) | {pattern["affected_event_ref"]} | {r["event_ref"] for r in pattern["requirements"]}
        if not event_ids <= refs.keys(): raise ValueError("unknown_active_pattern_event")
        rows.append({"pattern_ref": pid, "pattern": deepcopy(pattern), "shared_assignment_ref": assignment_ref,
            "withheld_reasons": deepcopy(lattice["withheld_pattern_reasons"].get(pid, [])),
            "source_refs_by_event": [{"event_ref": sid, "source_note_ids": deepcopy(refs[sid]["source_note_ids"]),
                "source_ref_ids": [n["source_ref_id"] for n in refs[sid]["note_refs"]]} for sid in sorted(event_ids)],
            "accounting_item_indices": [i for i, row in enumerate(evidence["accounting"]["items"])
                if pid in row["conditional_pattern_refs"] or pid in row["withheld_pattern_refs"]],
            "confirmed_nct": False, "raw_membership_exemption": False})
    return rows


def _role_links(role_evidence, track_ref, accounting_items):
    rows = []
    for condition in role_evidence["conditional"]:
        if condition["assumption_ref"] != track_ref: raise ValueError("role_assumption_reference_mismatch")
        for kind, profiles in (("pedal_profile", condition["pedal_profiles"]), ("sequential_profile", condition["sequential_profiles"])):
            for index, profile in enumerate(profiles):
                if kind == "pedal_profile":
                    episode = next(e for e in role_evidence["literal"]["pitch_episodes"] if e["episode_id"] == profile["episode_id"])
                    ids = set(episode["sounding_event_ids"])
                    profile_span = episode["observed_span"]
                else:
                    ids = {sid for group in profile["onset_groups"] for sid in group["sounding_event_ids"]}
                    profile_span = profile["span"]
                a, b = span_bounds(profile_span)
                links = [{"accounting_item_index": i,
                          "overlap_span": {"start": q(max(a, f(item["span"]["start"]))),
                                           "end": q(min(b, f(item["span"]["end"])))} }
                         for i, item in enumerate(accounting_items)
                         if item["event_ref"] in ids and f(item["span"]["start"]) < b and a < f(item["span"]["end"])]
                rows.append({"profile_kind": kind, "profile_index": index, "assumption_ref": deepcopy(track_ref),
                    "status": profile["status"], "alternatives": deepcopy(profile["alternatives"]),
                    "blockers": deepcopy(profile["blockers"]), "sounding_event_refs": sorted(ids),
                    "profile_span": deepcopy(profile_span), "accounting_item_indices": [row["accounting_item_index"] for row in links],
                    "accounting_extent_links": links,
                    "raw_lane_is_sampled_assignment": False, "nct_waives_role_blockers": False,
                    "role_selected": None, "roles_validated": False})
    return rows


def _verified_track(ir, segments, provenance):
    """Same builder contract after the internal context already validated Core."""
    duration = f(ir["score"]["duration_quarters"])
    if any(span_bounds(row["span"])[1] > duration for row in segments):
        raise ValueError("harmony_segment_outside_score")
    payload = {"schema_name": assumption_module.SCHEMA_NAME, "schema_version": assumption_module.SCHEMA_VERSION,
               "producer_version": assumption_module.VERSION,
               "binding": {"score_id": ir["score"]["score_id"], "ir_document_id": ir["ir_document_id"],
                           "ir_content_sha256": digest(ir), "source_files": deepcopy(ir["source_files"])},
               "provenance": deepcopy(provenance), "segments": deepcopy(segments),
               "coverage_holes": assumption_module._holes(segments, duration), "import_diagnostics": [],
               "use_policy": deepcopy(assumption_module.USE_POLICY)}
    track = assumption_module._seal(payload)
    # This still checks schema, seal, members, ranges and provenance. The only
    # omitted repeated operation is full Core validation of this private snapshot.
    assumption_module.validate_track(track)
    return track


def _verified_roles(observation, track, geometry):
    """Exact role payload over once-validated immutable literal geometry."""
    scope = observation["scope"]
    binding = {key: scope[key] for key in ("score_id", "ir_document_id", "ir_content_sha256", "source_files")}
    if track["binding"] != binding: raise ValueError("foreign_harmony_track")
    payload = {"schema_name": "musicanote-musical-role-evidence", "schema_version": "0.1.0",
               "producer_version": role_module.VERSION, "observation_ref": ref(observation), "scope": deepcopy(scope),
               "literal": deepcopy(geometry), "conditional": [{"assumption_ref": ref(track),
                   "pedal_profiles": [role_module._pedal_profile(episode, track) for episode in geometry["pitch_episodes"]],
                   "sequential_profiles": role_module._sequential_profiles(geometry, track, span_bounds(scope["context_span"]))}],
               "semantics": {"roles_validated": False, "melody_or_bass_selected": False,
                             "chord_assumption_selected": False, "generation_ready": False},
               "use_policy": {"research_only": True, "training_eligible": False, "gold_status": "not_established"}}
    payload["record_sha256"] = digest(payload)
    payload["record_id"] = "mre_" + payload["record_sha256"][:24]
    role_module.validate_evidence(payload)
    return payload


def _proposal_fixed(ir, observation, bundle, proposal, search_result, *, geometry=None):
    lattice = bundle["stages"]["lattice"]
    _proposal_guards(lattice, proposal)
    segments, origins = _segments(lattice, proposal)
    group_keys, search_hash = _search_origins(lattice, bundle, proposal, search_result)
    origin_groups = []
    for index, keys in enumerate(group_keys):
        full_origins = []
        for key in keys:
            reading = lattice["edges"][key["edge"]]["readings"][key["reading"]]
            full_origins.append({"reading_key": deepcopy(key), **{field: deepcopy(reading.get(field)) for field in
                ("candidate_ref", "alternative_index", "origin_pointer", "provider", "display_label", "root_spelling",
                 "root_provenance", "span", "members", "missing_spellings", "abstention_reasons")}})
        origin_groups.append({"path_index": index, "segment_id": segments[index]["segment_id"],
                              "semantic_group_ref": proposal.get("semantic_group_refs", [None] * len(group_keys))[index],
                              "adapter_origin": origins[index], "origin_reading_keys": deepcopy(keys), "origins": full_origins,
                              "representative_origin_preferred": False})
    provenance = {"kind": "caller_hypothesis", "engine_version": VERSION,
        "source_document_sha256": None, "source_path": None,
        "pitch_basis": PITCH_BASIS, "status": "hypothesis_not_gold"}
    track = build_track(ir, segments, provenance) if geometry is None else _verified_track(ir, segments, provenance)
    roles = role_analyze(ir, observation, [track]) if geometry is None else _verified_roles(observation, track, geometry)
    return {"track": track, "roles": roles, "origin_groups": origin_groups, "search_hash": search_hash,
            "proposal_content_sha256": digest(proposal)}


def _assemble(ir, observation, bundle, proposal, assignment_ref, pitch_policy, fixed, sound_refs):
    lattice = bundle["stages"]["lattice"]
    assignment = _assignment(lattice, assignment_ref)
    notes = {n["note_id"]: n for n in ir["note_events"]}
    track, roles = fixed["track"], fixed["roles"]
    evidence = vector(lattice, proposal["path"], assignment_ref)
    patterns = _pattern_links(lattice, evidence, sound_refs, assignment_ref)
    by_event = {r["sounding_event_id"]: r for r in sound_refs}
    cells = {digest(c["span"]): c for c in evidence["cells"]}
    item_refs = []
    for index, item in enumerate(evidence["accounting"]["items"]):
        cell = cells[digest(item["span"])]; sound = by_event[item["event_ref"]]
        raw = cell["membership"][item["event_ref"]]
        permitted = {"member": {"member"}, "unknown": {"spelling_unresolved"},
                     "nonmember": {"unexplained_nonmember", "conditional_nonmember", "withheld_nonmember"}}
        if item["bucket"] not in permitted[raw]: raise ValueError("raw_membership_accounting_bucket_mismatch")
        overlaps = []
        for nid in sound["source_note_ids"]:
            note = notes[nid]
            a = max(f(item["span"]["start"]), f(note["global_onset_quarter"]))
            b = min(f(item["span"]["end"]), f(note["global_onset_quarter"]) + f(note["notated_duration_quarter"]))
            if a < b:
                overlaps.append({"note_id": nid, "span": {"start": q(a), "end": q(b)}, "source_ref_id": note["source_ref_id"]})
        item_refs.append({"accounting_item_index": index, "event_ref": item["event_ref"],
            "span": deepcopy(item["span"]), "raw_membership": raw, "notated_note_overlap_refs": overlaps,
            "conditional_bucket": item["bucket"], "source_note_ids": deepcopy(sound["source_note_ids"]),
            "attack_note_id": sound["attack_note_id"], "source_ref_ids": [n["source_ref_id"] for n in sound["note_refs"]]})
    return {"version": VERSION, "status": "linked_conditional_research_evidence_not_verdict",
        "binding": {"score_id": ir["score"]["score_id"], "ir_document_id": ir["ir_document_id"],
                    "ir_content_sha256": digest(ir), "source_files": deepcopy(ir["source_files"])},
        "input_refs": {"observation_ref": ref(observation), "bundle_content_sha256": digest(bundle),
                       "proposal_content_sha256": digest(proposal), "pitch_policy_content_sha256": digest(pitch_policy),
                       "search_result_content_sha256": fixed["search_hash"]},
        "scope": deepcopy(observation["scope"]), "pitch_policy": deepcopy(pitch_policy),
        "proposal": deepcopy(proposal), "sample": deepcopy(bundle["sample"]),
        "shared_assignment": deepcopy(assignment), "candidate_origins": fixed["origin_groups"],
        "harmony_assumption_track": track, "role_evidence": roles,
        "progression_evidence": evidence, "raw_note_time": _raw(evidence),
        "sound_source_refs": sound_refs, "note_time_source_refs": item_refs,
        "active_pattern_links": patterns, "unresolved_role_links": _role_links(roles, ref(track), evidence["accounting"]["items"]),
        "semantics": {"raw_membership_changed": False, "assignments_merged": False,
                      "nct_confirmed": False, "harmony_selected": False, "roles_validated": False,
                      "pedal_confirmed": False, "arpeggio_confirmed": False, "generation_ready": False},
        "use_policy": {"research_only": True, "training_eligible": False, "gold_status": "not_established"},
        "limits": ["A full path is an explicit conditional proposal, not the winning harmony or score-wide coverage.",
                   "Literal part/voice lanes and sampled assignment links remain different scopes.",
                   "NCT coverage does not add chord members, exempt raw foreign notes or waive role-shape blockers.",
                   "Only exact written-pitch-compatible IR material is linked; concert pitch is not certified.",
                   "Source locators remain original IR references and retain parser limitations.",
                   "Track coverage holes outside the local context are preserved; no harmonic extrapolation.",
                   "Same proposal may share an assignment-independent track while its NCT link records remain separate."]}


def _payload(ir, observation, bundle, proposal, assignment_ref, pitch_policy, search_result):
    lattice, _, notes, sounds = _guards(ir, observation, bundle, proposal, assignment_ref, pitch_policy)
    fixed = _proposal_fixed(ir, observation, bundle, proposal, search_result)
    return _assemble(ir, observation, bundle, proposal, assignment_ref, pitch_policy, fixed,
                     _sound_refs(lattice, notes, sounds, ir))


def _seal_link(payload):
    payload["record_sha256"] = digest(payload)
    payload["record_id"] = "mprl_" + payload["record_sha256"][:24]
    return payload


def link(ir, observation, bundle, proposal, assignment_ref, *, pitch_policy, search_result=None):
    inputs = (ir, observation, bundle, proposal, assignment_ref, pitch_policy, search_result)
    before = [digest(value) for value in inputs]
    record = _seal_link(_payload(*inputs))
    if before != [digest(value) for value in inputs]: raise ValueError("progression_role_link_mutated_inputs")
    return record


def validate_link(record, *, ir, observation, bundle, proposal, assignment_ref, pitch_policy, search_result=None):
    payload = {k: v for k, v in record.items() if k not in ("record_id", "record_sha256")}
    expected = digest(payload)
    if record.get("record_sha256") != expected or record.get("record_id") != "mprl_" + expected[:24]:
        raise ValueError("progression_role_link_seal_mismatch")
    if payload != _payload(ir, observation, bundle, proposal, assignment_ref, pitch_policy, search_result):
        raise ValueError("progression_role_link_replay_mismatch")


def _encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


@dataclass(frozen=True)
class _FrozenBody:
    body: bytes
    sha256: str
    authentication: bytes
    domain: str


@dataclass(frozen=True)
class _PreparedState:
    inputs: _FrozenBody
    context: _FrozenBody
    contract: tuple
    authentication: bytes
    proposals: dict = field(default_factory=dict)


class PreparedContext:
    """Opaque lifecycle-bound handle; caller hashes or skip flags cannot create it."""
    __slots__ = ("__weakref__",)


_PREPARED_CONTEXTS = WeakKeyDictionary()
_PREPARED_SECRET = secrets.token_bytes(32)


def _contract():
    paths = (observation_module.CORE_SCHEMA_PATH, observation_module.SCHEMA_PATH,
             assumption_module.SCHEMA_PATH, role_module.SCHEMA_PATH)
    return (VERSION, observation_module.VERSION, assumption_module.VERSION, role_module.VERSION,
            tuple((str(path), sha256(path.read_bytes()).hexdigest()) for path in paths))


def _authenticate(value):
    return hmac.digest(_PREPARED_SECRET, _encoded(value), "sha256")


def _freeze(value, domain="temporary"):
    body = _encoded(value)
    checksum = sha256(body).hexdigest()
    return _FrozenBody(body, checksum, _authenticate([domain, checksum]), domain)


def _check_body(value, domain):
    if (type(value) is not _FrozenBody or type(value.body) is not bytes
            or value.domain != domain or sha256(value.body).hexdigest() != value.sha256
            or not hmac.compare_digest(value.authentication, _authenticate([domain, value.sha256]))):
        raise ValueError("prepared_context_internal_content_mutation")


def _state_signature(prepared, state):
    return _authenticate([id(prepared), state.inputs.sha256, state.context.sha256, state.contract])


def _proposal_domain(prepared, state, key):
    return "proposal:" + str(id(prepared)) + ":" + state.inputs.sha256 + ":" + key


def _prepared_state(prepared):
    if type(prepared) is not PreparedContext or prepared not in _PREPARED_CONTEXTS:
        raise ValueError("unregistered_internal_prepared_context_required")
    state = _PREPARED_CONTEXTS[prepared]
    if (type(state) is not _PreparedState or state.contract != _contract()
            or not hmac.compare_digest(state.authentication, _state_signature(prepared, state))):
        raise ValueError("prepared_context_contract_changed")
    _check_body(state.inputs, "inputs"); _check_body(state.context, "context")
    for key, value in state.proposals.items():
        _check_body(value, _proposal_domain(prepared, state, key))
        if json.loads(value.body)["proposal_content_sha256"] != key:
            raise ValueError("prepared_proposal_cache_identity_mismatch")
    return state


def prepare_context(ir, observation, bundle, *, pitch_policy, search_result=None):
    """Validate and privately snapshot a fixed unit once, without trusting claims.

    No cache survives its opaque handle. Inputs are JSON-copied, content-bound
    and fully validated before reuse; the public fresh replay APIs stay intact.
    """
    source = {"ir": ir, "observation": observation, "bundle": bundle,
              "pitch_policy": pitch_policy, "search_result": search_result}
    inputs = _freeze(source, "inputs")
    snapshot = json.loads(inputs.body)
    lattice, notes, sounds = _context_guards(snapshot["ir"], snapshot["observation"],
                                              snapshot["bundle"], snapshot["pitch_policy"])
    _search_context_guards(snapshot["bundle"], snapshot["search_result"])
    geometry = role_module._geometry(snapshot["observation"])
    context = _freeze({"geometry": geometry,
                       "sound_refs": _sound_refs(lattice, notes, sounds, snapshot["ir"])}, "context")
    if _encoded(source) != inputs.body: raise ValueError("prepared_context_mutated_caller_inputs")
    prepared = PreparedContext()
    state = _PreparedState(inputs, context, _contract(), b"")
    _PREPARED_CONTEXTS[prepared] = _PreparedState(inputs, context, state.contract, _state_signature(prepared, state))
    _prepared_state(prepared)
    return prepared


def _prepared_payload(prepared, proposal, assignment_ref):
    state = _prepared_state(prepared)
    inputs, context = json.loads(state.inputs.body), json.loads(state.context.body)
    # A canonical JSON snapshot also protects cached track/roles from caller
    # mutations of the original proposal or any previously returned record.
    proposal_body = _freeze(proposal)
    fixed_proposal = json.loads(proposal_body.body)
    key = proposal_body.sha256
    _assignment(inputs["bundle"]["stages"]["lattice"], assignment_ref)
    if key not in state.proposals:
        fixed = _proposal_fixed(inputs["ir"], inputs["observation"], inputs["bundle"], fixed_proposal,
                                inputs["search_result"], geometry=context["geometry"])
        state.proposals[key] = _freeze(fixed, _proposal_domain(prepared, state, key))
    fixed = json.loads(state.proposals[key].body)
    payload = _assemble(inputs["ir"], inputs["observation"], inputs["bundle"], fixed_proposal,
                        assignment_ref, inputs["pitch_policy"], fixed, context["sound_refs"])
    if _encoded(proposal) != proposal_body.body: raise ValueError("prepared_link_mutated_caller_proposal")
    _prepared_state(prepared)
    return payload


def link_prepared(prepared, proposal, assignment_ref):
    """Fresh assignment-specific accounting over a once-validated private unit."""
    return _seal_link(_prepared_payload(prepared, proposal, assignment_ref))


def validate_link_prepared(record, prepared, proposal, assignment_ref):
    """Seal and fresh assignment replay; only verified invariant work is shared."""
    payload = {key: value for key, value in record.items() if key not in ("record_id", "record_sha256")}
    expected = digest(payload)
    if record.get("record_sha256") != expected or record.get("record_id") != "mprl_" + expected[:24]:
        raise ValueError("progression_role_link_seal_mismatch")
    if payload != _prepared_payload(prepared, proposal, assignment_ref):
        raise ValueError("progression_role_link_replay_mismatch")
