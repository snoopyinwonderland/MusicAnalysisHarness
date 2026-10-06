"""Local musical hypotheses as exact factor conditions, never musical verdicts.

The compiler does not enumerate voice assignments, read source labels, choose a
voice or chord, or repair a sound. All candidate clauses refer to direct endpoint
edges. A geometry witness is not confidence, consonance, a key or a final role.
"""
from collections import defaultdict
from copy import deepcopy

from . import factor_musical_view as common
from .harmony_factorized_voice_paths import _graph
from .musical_pattern_observation import digest, f, q, span_bounds

VERSION = "factor-musical-rules-0.1.0"
PREFIX = "fmcr_"
LETTERS = "CDEFGAB"
NATURAL = dict(zip(LETTERS, (0, 2, 4, 5, 7, 9, 11)))


def _span(a, b):
    return {"start": q(a), "end": q(b)}


def _index(rows, key):
    result = {}
    for row in rows:
        value = row[key]
        if value in result:
            raise ValueError("duplicate_literal_reference:" + key)
        result[value] = row
    return result


def _guards(view, path, graph):
    common.validate_view(view)
    common.validate_path(view, path)
    body = _graph(graph)
    if body["binding"] != view["binding"] or body["span"] != view["context_span"]:
        raise ValueError("foreign_or_stale_musical_rule_graph_binding")
    a, b = span_bounds(view["context_span"])
    literal = _index(view["linked_sound_snapshots"], "sounding_event_id")
    expected = sorted((s for s in literal.values()
                       if (a <= f(s["span"]["start"]) < b if f(s["span"]["start"]) == f(s["span"]["end"])
                           else f(s["span"]["start"]) < b and f(s["span"]["end"]) > a)),
                      key=lambda s: (f(s["span"]["start"]), s["sounding_event_id"]))
    if body["context_sounding_events"] != expected:
        raise ValueError("graph_context_literal_inventory_mismatch")
    notes = _index(view["note_snapshots"], "note_id")
    ties = _index(view["tie_chain_snapshots"], "tie_chain_id")
    sources = _index(view["source_reference_snapshots"], "source_ref_id")
    selected_ties = [ties[tid] for tid in sorted({s.get("tie_chain_id") for s in expected
                     if s.get("tie_chain_id") is not None}) if tid in ties]
    ids = {nid for s in expected for nid in s["source_note_ids"]}
    ids.update(nid for chain in selected_ties for nid in chain["source_note_ids"])
    selected_notes = [notes[nid] for nid in sorted(ids) if nid in notes]
    refs = {n.get("source_ref_id") for n in selected_notes}
    selected_sources = [sources[r] for r in sorted(refs - {None}) if r in sources]
    if (body["source_note_events"] != selected_notes or body["tie_chains"] != selected_ties
            or body["source_references"] != selected_sources):
        raise ValueError("graph_note_tie_source_literal_inventory_mismatch")
    sounds = _index(view["sounds"], "sound_id")
    selected = {sid for sid, row in sounds.items() if row["lane"] == body["lane"]}
    if selected != {s["sounding_event_id"] for s in body["events"]}:
        raise ValueError("graph_active_lane_inventory_mismatch")
    for sid in selected:
        sound, row = literal[sid], sounds[sid]
        if (row["span"] != sound["span"] or row["source_note_ids"] != sound["source_note_ids"]
                or row["attack_note_id"] != sound["attack_note_id"] or row["pitch"] != sound["pitch"]):
            raise ValueError("view_graph_sound_literal_mismatch")
    selected_rows = {}
    for sid in selected:
        row = deepcopy(sounds[sid])
        row["_source_written_pitch_consistent"] = all(
            common.pitch_key(notes[nid]["written_pitch"], True) == common.pitch_key(row["pitch"], True)
            for nid in row["source_note_ids"])
        selected_rows[sid] = row
    return body, selected_rows


def _signature(segment):
    return (None if segment["root"] is None else common.pitch_key(segment["root"]),
            tuple(sorted(common.pitch_key(p) for p in segment["members"])),
            segment["status"], tuple(sorted(segment["blockers"])))


def _cuts(path):
    return [f(right["span"]["start"]) for left, right in zip(path["segments"], path["segments"][1:])
            if _signature(left) != _signature(right)]


def _motion(left, right):
    p, r = left["pitch"], right["pitch"]
    delta = 7 * (r["octave"] - p["octave"]) + LETTERS.index(r["step"]) - LETTERS.index(p["step"])
    semitones = (12 * (r["octave"] - p["octave"]) + NATURAL[r["step"]]
                 - NATURAL[p["step"]] + f(r["alter"]) - f(p["alter"]))
    integral = f(p["alter"]).denominator == f(r["alter"]).denominator == 1
    step = integral and abs(delta) == 1 and abs(semitones) in (1, 2) and delta * semitones > 0
    chromatic = integral and delta == 0 and abs(semitones) == 1
    return {"diatonic_steps": delta, "semitones": q(semitones), "ordinary_step": step,
            "chromatic_unison_step": chromatic, "integer_spelling_supported": integral}


def _requirements(path, pairs):
    return [{"sound_id": row["sound_id"], "span": deepcopy(extent), "expected": expected,
             "observed": common.membership(path, row["pitch"], extent)}
            for row, extent, expected in pairs]


def _rule(view, path, graph, family, rows, explained, required, prerequisites, blockers=()):
    codes = list(blockers)
    context = span_bounds(view["context_span"])
    extents = [r["span"] for r in prerequisites.get("membership_requirements", [])]
    extents.extend(prerequisites.get("required_context_spans", []))
    covered = all(context[0] <= f(s["start"]) < f(s["end"]) <= context[1] for s in extents)
    if not covered:
        codes.append("required_evidence_outside_frozen_context")
    if graph["status"] != "ready":
        codes.append("factor_graph_not_ready")
        codes.extend("graph:" + reason for reason in graph["reasons"])
    for row in rows:
        if row["source_clock_passed"] is not True:
            codes.append("source_clock_not_passed:" + row["sound_id"])
        if f(row["pitch"]["alter"]).denominator != 1:
            codes.append("microtonal_role_rule_not_supported")
        if row["_source_written_pitch_consistent"] is not True:
            codes.append("source_written_pitch_inconsistent:" + row["sound_id"])
    for item in prerequisites.get("membership_requirements", []):
        if item["observed"] != item["expected"]:
            codes.append("harmony_membership_unknown" if item["observed"] == "unknown" else "harmony_membership_not_satisfied")
        for segment in path["segments"]:
            if common.clipped(item["span"], segment["span"]) is not None:
                codes.extend("harmony:" + reason for reason in segment["blockers"])
    prerequisites = {**deepcopy(prerequisites), "context_covers_required_spans": covered,
        "source_clock": [{"sound_id": r["sound_id"], "passed": r["source_clock_passed"],
                          "diagnostics": deepcopy(r["source_diagnostics"])} for r in rows],
        "source_written_pitch": [{"sound_id": r["sound_id"], "consistent": r["_source_written_pitch_consistent"]}
                                 for r in rows],
        "pitch_basis": "written_IR_not_concert_certified",
        "key": "unassessed", "function": "unassessed", "cadence": "unassessed"}
    body = {"family": family, "involved_sound_refs": [r["sound_id"] for r in rows],
        "note_refs": [nid for r in rows for nid in r["source_note_ids"]],
        "explained_items": deepcopy(explained),
        "alternatives": [{"required_links": [list(edge) for edge in required], "forbidden_links": []}],
        "prerequisites": prerequisites, "blockers": sorted(set(codes)),
        "status": "withheld" if codes else "conditional_shape"}
    return {"rule_id": "fmrule_" + digest([common.ref(view), common.ref(path), graph["record_id"], body])[:24], **body}


def _uniform_chord(path, extent):
    a, b = span_bounds(extent)
    rows = [s for s in path["segments"] if f(s["span"]["start"]) < b and f(s["span"]["end"]) > a]
    return bool(rows) and len({_signature(s) for s in rows}) == 1


def _membership_profile(path, row):
    result = []
    for segment in path["segments"]:
        extent = common.clipped(row["span"], segment["span"])
        if extent is not None:
            state = common.membership(path, row["pitch"], extent)
            result.append({"sound_id": row["sound_id"], "span": extent,
                           "expected": state if state != "unknown" else "known_membership",
                           "observed": state})
    return result


def _triples(view, path, graph, rows, outgoing):
    for x in sorted(outgoing):
        for y in outgoing[x]:
            for z in outgoing.get(y, []):
                chain = [rows[s] for s in (x, y, z)]
                motion = [_motion(chain[0], chain[1]), _motion(chain[1], chain[2])]
                dx, dy = (f(m["semitones"]) for m in motion)
                ordinary = all(m["ordinary_step"] for m in motion)
                same = common.pitch_key(chain[0]["pitch"], True) == common.pitch_key(chain[2]["pitch"], True)
                chromatic = all(m["ordinary_step"] or m["chromatic_unison_step"] for m in motion) and dx * dy > 0
                family = "neighbor" if ordinary and same else "passing" if ordinary and dx * dy > 0 else "chromatic_passing" if chromatic else "passing_neighbor_unsupported"
                blockers = [] if family in ("neighbor", "passing") else ["chromatic_step_role_not_supported" if family == "chromatic_passing" else "passing_neighbor_geometry_not_supported"]
                reqs = _requirements(path, [(r, r["span"], state) for r, state in zip(chain, ("member", "nonmember", "member"))])
                yield _rule(view, path, graph, family, chain,
                    [{"sound_id": y, "span": deepcopy(chain[1]["span"])}], [(x, y), (y, z)],
                    {"membership_requirements": reqs, "motion": motion,
                     "accent": "unassessed", "consonance": "unassessed"}, blockers)
                extent = _span(f(chain[0]["span"]["start"]), f(chain[-1]["span"]["end"]))
                distinct = len({common.pitch_key(r["pitch"]) for r in chain})
                shape_blockers = []
                if distinct < 3:
                    shape_blockers.append("fewer_than_three_distinct_spelled_members")
                if not _uniform_chord(path, extent):
                    shape_blockers.append("changing_harmony_inside_broken_chord_shape")
                yield _rule(view, path, graph, "broken_chord_shape", chain, [], [(x, y), (y, z)],
                    {"membership_requirements": _requirements(path, [(r, r["span"], "member") for r in chain]),
                     "required_context_spans": [extent], "distinct_spellings": distinct,
                     "role_alternatives": ["arpeggio", "chord_tone_melody", "other_texture"],
                     "arpeggio_confirmed": False}, shape_blockers)


def _boundary_rules(view, path, graph, rows, outgoing, cuts):
    for cut in cuts:
        for sid in sorted(rows):
            row = rows[sid]
            a, b = span_bounds(row["span"])
            if a < cut < b:
                before, after = _span(a, cut), _span(cut, b)
                yield _rule(view, path, graph, "anticipation_held", [row],
                    [{"sound_id": sid, "span": before}], [],
                    {"membership_requirements": _requirements(path, [(row, before, "nonmember"), (row, after, "member")]),
                     "harmonic_cut": q(cut), "actually_held_same_sound": True, "accent": "unassessed"})
                profile = _membership_profile(path, row)
                # A nonmember cell is a competing pedal/linear relation, not a
                # reason to erase this original sustained slot alternative.
                yield _rule(view, path, graph, "held_bass_shape", [row], [], [],
                    {"membership_requirements": profile, "required_context_spans": [row["span"]],
                     "harmonic_cut": q(cut),
                     "actually_held_same_sound": True, "structural_bass_confirmed": False,
                     "role_alternatives": ["held_bass", "sustained_inner_or_upper_voice", "pedal", "other_texture"]})
                for target in outgoing.get(sid, []):
                    following = rows[target]
                    motion = _motion(row, following)
                    blocked = ["preparation_consonance_not_verified", "boundary_dissonance_not_verified",
                               "resolution_consonance_not_verified", "accent_not_verified"]
                    if not motion["ordinary_step"] or motion["diatonic_steps"] != -1:
                        blocked.append("resolution_not_downward_spelled_step")
                    yield _rule(view, path, graph, "prepared_held_suspension", [row, following],
                        [{"sound_id": sid, "span": after}], [(sid, target)],
                        {"membership_requirements": _requirements(path, [(row, before, "member"),
                            (row, after, "nonmember"), (following, following["span"], "member")]),
                         "harmonic_cut": q(cut), "actually_held_same_sound": True, "motion": motion,
                         "preparation_consonance": "unassessed", "boundary_dissonance": "unassessed",
                         "resolution_consonance": "unassessed", "accent": "unassessed"}, blocked)
            if b == cut:
                for target in outgoing.get(sid, []):
                    following = rows[target]
                    same = common.pitch_key(row["pitch"], True) == common.pitch_key(following["pitch"], True)
                    yield _rule(view, path, graph, "anticipation_reattack", [row, following],
                        [{"sound_id": sid, "span": deepcopy(row["span"])}], [(sid, target)],
                        {"membership_requirements": _requirements(path, [(row, row["span"], "nonmember"),
                            (following, following["span"], "member")]), "harmonic_cut": q(cut),
                         "same_spelled_register": same, "is_tie_or_sustain": False, "accent": "unassessed"},
                        [] if same else ["anticipation_reattack_pitch_not_identical"])


def compile_rules(view, path, graph, *, max_candidates=4096):
    """Compile every local potential clause; an inventory budget never prunes."""
    if type(max_candidates) is not int or max_candidates < 0:
        raise ValueError("nonnegative_integer_candidate_budget_required")
    body, rows = _guards(view, path, graph)
    outgoing = defaultdict(list)
    incoming = defaultdict(int)
    for factor in body["factors"]:
        for source in factor["source_refs"]:
            outgoing[source].extend(factor["target_refs"])
        for target in factor["target_refs"]:
            incoming[target] += len(factor["source_refs"])
    for targets in outgoing.values():
        targets.sort()
    cuts = _cuts(path)
    triples = sum(incoming[sid] * len(targets) for sid, targets in outgoing.items())
    boundary_count = 0
    for cut in cuts:
        for sid, row in rows.items():
            a, b = span_bounds(row["span"])
            if a < cut < b:
                boundary_count += 2 + len(outgoing.get(sid, []))
            if b == cut:
                boundary_count += len(outgoing.get(sid, []))
    count = 2 * triples + boundary_count
    reasons, rules = [], []
    if count > max_candidates:
        status = "candidate_budget_abstention"
        reasons.append("whole_candidate_inventory_exceeds_budget_no_pruning")
    else:
        status = "ready" if body["status"] == "ready" else "graph_not_ready"
        if body["status"] != "ready":
            reasons = ["factor_graph_not_ready", *body["reasons"]]
        rules = list(_triples(view, path, graph, rows, outgoing))
        rules.extend(_boundary_rules(view, path, graph, rows, outgoing, cuts))
        rules.sort(key=lambda row: row["rule_id"])
        if len(rules) != count:
            raise ValueError("local_candidate_inventory_accounting_mismatch")
    return common.seal({"version": VERSION, "view_ref": common.ref(view), "path_ref": common.ref(path),
        "graph_ref": common.ref(graph), "max_candidates": max_candidates, "rules": rules,
        "status": status, "reasons": sorted(set(reasons)), "total_candidates": count,
        "candidate_inventory": {"direct_triples": triples, "triple_family_candidates": 2 * triples,
                                "boundary_family_candidates": boundary_count},
        "limits": {"global_assignments_enumerated": False, "source_labels_used": False,
                   "selected": False, "confirmed_nct": False, "consonance_certified": False,
                   "structural_bass_certified": False, "generation_ready": False,
                   "counts_are_confidence": False, "direct_edges_only": True,
                   "unrequired_edges_are_not_inferred": True,
                   "same_event_holding_is_not_reattack": True}}, PREFIX)


def validate_rules(view, path, graph, record):
    """Verify seal, full input references and a fresh local inventory replay."""
    common.check(record, PREFIX)
    fresh = compile_rules(view, path, graph, max_candidates=record["max_candidates"])
    if fresh != record:
        raise ValueError("stale_foreign_or_modified_factor_musical_rules")
    return True
