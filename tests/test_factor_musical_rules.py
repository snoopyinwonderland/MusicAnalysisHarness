"""Local clauses, counterreadings and guards; no legacy assignment enumeration."""
from copy import deepcopy
from fractions import Fraction
from tempfile import TemporaryDirectory
import unittest

from musicanote_harness import factor_musical_rules as rules
from musicanote_harness import factor_musical_view as common
from musicanote_harness import harmony_factorized_voice_paths as factors
from musicanote_harness.musical_pattern_observation import digest, q
from test_musical_role_evidence import make_ir, event
from test_factor_musical_view import make_view


def span(a, b):
    return {"start": q(a), "end": q(b)}


def member(step, alter=0):
    return {"step": step, "alter": q(alter)}


def segment(name, a, b, members=("C", "E", "G"), *, root="C", blockers=()):
    return {"segment_id": name, "span": span(a, b),
            "root": None if root is None else member(root),
            "members": [member(p) if isinstance(p, str) else p for p in members],
            "status": "blocked" if blockers else "usable", "blockers": list(blockers)}


def path_for(view, segments):
    return common.make_path(view, segments, {"kind": "caller_hypothesis", "engine_version": "test-v1",
        "source_document_sha256": None, "source_path": None,
        "pitch_basis": "written_IR_not_concert_certified", "status": "hypothesis_not_gold"})


class FactorMusicalRulesTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def fixture(self, events, extent=None, *, extra_lanes=()):
        events = list(events)
        end = max(r["onset"] + r["duration"] for r in events)
        if end < 4:
            events.append(event(None, end, 4 - end))
            extra_lanes = [*extra_lanes, [event("C2", 0, 4)]]
        ir = make_ir(self.temp.name, [events, *extra_lanes])
        extent = extent or span(0, 4)
        view = make_view(ir, extent)
        first = next(n for n in ir["note_events"] if n["part_id"] == ir["parts"][0]["part_id"])
        lane = [first["part_id"], first["voice_id"]]
        graph = factors.factorize(ir, extent, lane)
        return ir, view, graph

    def passing(self, pitches=("C4", "D4", "E4"), extent=None):
        return self.fixture([event(p, i, 1) for i, p in enumerate(pitches)], extent)

    def compile(self, view, graph, segments=None, **kwargs):
        path = path_for(view, segments or [segment("all", 0, 4)])
        return path, rules.compile_rules(view, path, graph, **kwargs)

    def family(self, record, name):
        return [r for r in record["rules"] if r["family"] == name]

    def test_passing_two_direct_links_exact_explained_middle_and_immutability(self):
        ir, view, graph = self.passing()
        before = deepcopy((ir, view, graph))
        path, record = self.compile(view, graph)
        row = self.family(record, "passing")[0]
        ids = row["involved_sound_refs"]
        self.assertEqual(row["status"], "conditional_shape")
        self.assertEqual(row["alternatives"], [{"required_links": [ids[:2], ids[1:]], "forbidden_links": []}])
        self.assertEqual(row["explained_items"], [{"sound_id": ids[1], "span": span(1, 2)}])
        self.assertEqual([r["observed"] for r in row["prerequisites"]["membership_requirements"]], ["member", "nonmember", "member"])
        self.assertTrue(rules.validate_rules(view, path, graph, record))
        self.assertEqual((ir, view, graph), before)
        self.assertFalse(record["limits"]["confirmed_nct"])
        self.assertFalse(record["limits"]["global_assignments_enumerated"])

    def test_neighbor_exact_spelled_register_and_other_member_reading(self):
        _, view, graph = self.passing(("C4", "D4", "C4"))
        _, record = self.compile(view, graph)
        self.assertEqual(self.family(record, "neighbor")[0]["status"], "conditional_shape")
        _, changed = self.compile(view, graph, [segment("other", 0, 4, ("C", "D", "G"))])
        row = self.family(changed, "neighbor")[0]
        self.assertEqual(row["status"], "withheld")
        self.assertIn("harmony_membership_not_satisfied", row["blockers"])

    def test_octave_return_is_not_neighbor_and_leap_is_withheld_not_forced(self):
        _, view, graph = self.passing(("C4", "D4", "C5"))
        _, record = self.compile(view, graph)
        self.assertEqual(self.family(record, "neighbor"), [])
        self.assertEqual(self.family(record, "passing_neighbor_unsupported")[0]["status"], "withheld")

    def test_chromatic_unison_step_retained_as_unsupported(self):
        _, view, graph = self.passing(("C4", "C#4", "D4"))
        _, record = self.compile(view, graph, [segment("all", 0, 4, ("C", "D", "G"))])
        row = self.family(record, "chromatic_passing")[0]
        self.assertEqual(row["status"], "withheld")
        self.assertIn("chromatic_step_role_not_supported", row["blockers"])

    def test_microtone_not_integer_truncated(self):
        ir, _, original_graph = self.passing()
        middle = next(n for n in ir["note_events"] if n["written_pitch"]["step"] == "D")
        for name in ("written_pitch", "concert_pitch"):
            middle[name]["alter"] = q(Fraction(1, 2))
            middle[name]["midi_pitch"] = middle[name]["pitch_class"] = None
        sound = next(s for s in ir["sounding_events"] if s["attack_note_id"] == middle["note_id"])
        sound["pitch"] = deepcopy(middle["written_pitch"])
        view = make_view(ir, span(0, 4))
        graph = factors.factorize(ir, span(0, 4), original_graph["lane"])
        _, record = self.compile(view, graph)
        row = self.family(record, "passing_neighbor_unsupported")[0]
        self.assertIn("microtonal_role_rule_not_supported", row["blockers"])
        self.assertEqual(row["prerequisites"]["motion"][0]["semitones"], q(Fraction(5, 2)))

    def test_source_clock_origin_conflict_retained_and_withheld(self):
        ir, _, original_graph = self.passing()
        attack = original_graph["events"][0]["attack_note_id"]
        next(n for n in ir["note_events"] if n["note_id"] == attack)["tie_role"] = "stop"
        view = make_view(ir, span(0, 4))
        graph = factors.factorize(ir, span(0, 4), original_graph["lane"])
        _, record = self.compile(view, graph)
        row = self.family(record, "passing")[0]
        self.assertEqual(row["status"], "withheld")
        self.assertTrue(any(code.startswith("source_clock_not_passed:") for code in row["blockers"]))
        self.assertTrue(any(not fact["passed"] for fact in row["prerequisites"]["source_clock"]))

    def test_original_sound_pitch_not_matching_written_source_is_withheld(self):
        ir, _, original_graph = self.passing()
        attack = original_graph["events"][1]["attack_note_id"]
        changed = next(n for n in ir["note_events"] if n["note_id"] == attack)
        changed["written_pitch"].update(step="F", spelling="F4", midi_pitch=65, pitch_class=5)
        view = make_view(ir, span(0, 4))
        graph = factors.factorize(ir, span(0, 4), original_graph["lane"])
        _, record = self.compile(view, graph)
        row = self.family(record, "passing")[0]
        self.assertEqual(row["status"], "withheld")
        self.assertTrue(any(reason.startswith("source_written_pitch_inconsistent:") for reason in row["blockers"]))

    def test_required_outside_context_kept_as_withheld(self):
        _, view, graph = self.passing(extent=span(Fraction(1, 2), 4))
        _, record = self.compile(view, graph, [segment("all", Fraction(1, 2), 4)])
        row = self.family(record, "passing")[0]
        self.assertEqual(row["status"], "withheld")
        self.assertIn("required_evidence_outside_frozen_context", row["blockers"])
        self.assertEqual(record["total_candidates"], 2)

    def test_blocked_harmony_is_unknown_and_not_waived_by_geometry(self):
        _, view, graph = self.passing()
        _, record = self.compile(view, graph, [segment("all", 0, 4, blockers=("meter_missing_or_changed",))])
        row = self.family(record, "passing")[0]
        self.assertIn("harmony_membership_unknown", row["blockers"])
        self.assertEqual(row["status"], "withheld")

    def test_held_anticipation_same_sound_has_no_required_edge(self):
        _, view, graph = self.fixture([event("C4", 0, 3), event("D4", 3, 1)])
        _, record = self.compile(view, graph, [segment("left", 0, 1, ("D", "F", "A"), root="D"), segment("right", 1, 4)])
        row = self.family(record, "anticipation_held")[0]
        self.assertEqual(row["status"], "conditional_shape")
        self.assertEqual(row["alternatives"], [{"required_links": [], "forbidden_links": []}])
        self.assertEqual(row["explained_items"][0]["span"], span(0, 1))
        self.assertTrue(row["prerequisites"]["actually_held_same_sound"])

    def test_reattack_anticipation_is_not_tie_and_requires_direct_link(self):
        _, view, graph = self.fixture([event("C4", 0, 1), event("C4", 1, 1), event("G4", 2, 1)])
        _, record = self.compile(view, graph, [segment("left", 0, 1, ("D", "F", "A"), root="D"), segment("right", 1, 4)])
        row = self.family(record, "anticipation_reattack")[0]
        self.assertEqual(row["status"], "conditional_shape")
        self.assertEqual(row["alternatives"][0]["required_links"], [row["involved_sound_refs"]])
        self.assertFalse(row["prerequisites"]["is_tie_or_sustain"])

    def test_enharmonic_equal_midi_does_not_enable_reattack_anticipation(self):
        _, view, graph = self.fixture([event("C#4", 0, 1), event("D-4", 1, 1), event("G4", 2, 1)])
        _, record = self.compile(view, graph, [segment("left", 0, 1), segment("right", 1, 4, (member("D", -1), "F", "A"), root="D")])
        row = self.family(record, "anticipation_reattack")[0]
        self.assertIn("anticipation_reattack_pitch_not_identical", row["blockers"])

    def test_prepared_actual_hold_suspension_withheld_for_semantic_prerequisites(self):
        _, view, graph = self.fixture([event("F4", 0, 3), event("E4", 3, 1)])
        _, record = self.compile(view, graph, [segment("left", 0, 1, ("F", "A", "C"), root="F"), segment("right", 1, 4)])
        row = self.family(record, "prepared_held_suspension")[0]
        self.assertEqual(row["status"], "withheld")
        self.assertEqual(row["explained_items"][0]["span"], span(1, 3))
        self.assertEqual(row["alternatives"][0]["required_links"], [row["involved_sound_refs"]])
        self.assertNotIn("harmony_membership_not_satisfied", row["blockers"])
        self.assertIn("accent_not_verified", row["blockers"])
        self.assertIn("preparation_consonance_not_verified", row["blockers"])

    def test_reattacked_preparation_does_not_become_held_suspension(self):
        _, view, graph = self.fixture([event("F4", 0, 1), event("F4", 1, 2), event("E4", 3, 1)])
        _, record = self.compile(view, graph, [segment("left", 0, 1, ("F", "A", "C"), root="F"), segment("right", 1, 4)])
        self.assertEqual(self.family(record, "prepared_held_suspension"), [])

    def test_broken_chord_three_members_only_role_alternative_no_explained_time(self):
        _, view, graph = self.passing(("C4", "E4", "G4"))
        _, record = self.compile(view, graph)
        row = self.family(record, "broken_chord_shape")[0]
        self.assertEqual(row["status"], "conditional_shape")
        self.assertEqual(row["explained_items"], [])
        self.assertEqual(row["prerequisites"]["distinct_spellings"], 3)
        self.assertFalse(row["prerequisites"]["arpeggio_confirmed"])

    def test_held_bass_profile_retains_nonmember_without_selecting_structural_bass(self):
        _, view, graph = self.fixture([event("C4", 0, 4)])
        _, record = self.compile(view, graph, [segment("left", 0, 1), segment("right", 1, 4, ("D", "F", "A"), root="D")])
        row = self.family(record, "held_bass_shape")[0]
        self.assertEqual(row["status"], "conditional_shape")
        self.assertEqual(row["explained_items"], [])
        self.assertFalse(row["prerequisites"]["structural_bass_confirmed"])
        self.assertEqual([p["observed"] for p in row["prerequisites"]["membership_requirements"]], ["member", "nonmember"])

    def test_identical_harmony_partition_introduces_no_fake_boundary_rules(self):
        _, view, graph = self.passing()
        _, one = self.compile(view, graph)
        _, split = self.compile(view, graph, [segment("a", 0, 1), segment("b", 1, 4)])
        self.assertEqual(one["candidate_inventory"], split["candidate_inventory"])
        self.assertEqual(sorted(r["family"] for r in one["rules"]), sorted(r["family"] for r in split["rules"]))
        self.assertEqual(sorted((r["family"], r["status"], r["explained_items"]) for r in one["rules"]),
                         sorted((r["family"], r["status"], r["explained_items"]) for r in split["rules"]))

    def test_whole_inventory_budget_preserves_count_and_no_success_subset(self):
        _, view, graph = self.passing()
        _, record = self.compile(view, graph, max_candidates=1)
        self.assertEqual(record["status"], "candidate_budget_abstention")
        self.assertEqual(record["total_candidates"], 2)
        self.assertEqual(record["rules"], [])
        for value in (-1, True, 1.5):
            with self.assertRaises(ValueError):
                self.compile(view, graph, max_candidates=value)

    def test_polyphonic_endpoint_products_all_triples_no_global_enumeration(self):
        events = [event(p, i, 1) for i, ps in enumerate((("C4", "G4"), ("D4", "A4"), ("E4", "B4"))) for p in ps]
        _, view, graph = self.fixture(events)
        _, record = self.compile(view, graph)
        self.assertEqual(record["candidate_inventory"]["direct_triples"], 8)
        self.assertEqual(record["total_candidates"], 16)
        self.assertEqual(len(record["rules"]), 16)

    def test_resealed_graph_context_omission_and_source_note_swap_rejected(self):
        _, view, graph = self.passing()
        path = path_for(view, [segment("all", 0, 4)])
        for collection in ("source_note_events", "source_references"):
            altered = deepcopy(graph)
            altered[collection][0]["test_literal_tamper"] = True
            body = factors._body(altered["binding"], altered["span"], altered["lane"], altered["context_sounding_events"],
                altered["source_note_events"], altered["source_references"], altered["tie_chains"], altered["resource_limits"])
            altered = common.seal(body, "vfgraph_")
            with self.assertRaisesRegex(ValueError, "literal_inventory_mismatch"):
                rules.compile_rules(view, path, altered)
        altered = deepcopy(graph)
        altered["context_sounding_events"].pop()
        body = factors._body(altered["binding"], altered["span"], altered["lane"], altered["context_sounding_events"],
            altered["source_note_events"], altered["source_references"], altered["tie_chains"], altered["resource_limits"])
        with self.assertRaisesRegex(ValueError, "context_literal_inventory_mismatch"):
            rules.compile_rules(view, path, common.seal(body, "vfgraph_"))

    def test_stale_record_resealed_deleted_rules_and_foreign_path_rejected(self):
        _, view, graph = self.passing()
        path, record = self.compile(view, graph)
        body = common.check(record, rules.PREFIX)
        body["rules"] = []
        with self.assertRaisesRegex(ValueError, "stale_foreign"):
            rules.validate_rules(view, path, graph, common.seal(body, rules.PREFIX))
        other = path_for(view, [segment("other", 0, 4, ("C", "D", "G"))])
        with self.assertRaisesRegex(ValueError, "stale_foreign"):
            rules.validate_rules(view, other, graph, record)
        self.assertEqual(record["path_ref"], common.ref(path))
        self.assertEqual(record["view_ref"], common.ref(view))
        self.assertEqual(record["graph_ref"], common.ref(graph))


if __name__ == "__main__":
    unittest.main()
