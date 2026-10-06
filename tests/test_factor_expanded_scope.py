"""Fresh expanded scope facts; synthetic parents are not SOURCE authority."""
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from jsonschema.exceptions import ValidationError

from musicanote_harness import factor_context_observation as context
from musicanote_harness import factor_expanded_scope as expanded
from musicanote_harness import factor_musical_view as common
from musicanote_harness import harmony_factorized_voice_paths as factors
from musicanote_harness import musical_pattern_observation as pattern
from musicanote_harness import sounding_lineage_audit as lineage
from test_factor_context_observation import physical_clocks
from test_factor_musical_view import make_observation, reseal, span
from test_musical_role_evidence import event, make_ir


class FactorExpandedScopeTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def fixture(self, lanes=None, *, extent=None, clocks=None, modify=None, **context_options):
        ir = make_ir(self.temp.name, lanes or [[event("C4", 0, 1), event("D4", 1, 1),
                                              event("E4", 2, 1), event("F4", 3, 1)]])
        if clocks is not None:
            physical_clocks(ir, clocks)
        if modify is not None:
            modify(ir)
        extent = extent or span(1, 2)
        observation = make_observation(ir, extent)
        ids = [row["sounding_event_id"] for row in observation["core_projection"]["sounding_events"]]
        audit = lineage.audit_sounding_lineage(ir, sound_ids=ids, context_span=extent)
        view = common.prepare(ir, observation, audit)
        extension = context.observe_context(ir, view, observation, audit, **context_options)
        return ir, view, observation, audit, extension

    def prepare(self, fixture, **options):
        return expanded.prepare_scope(*fixture, **options)

    def validate(self, fixture, record, **options):
        return expanded.validate_scope(record, ir=fixture[0], view=fixture[1], observation=fixture[2],
                                       audit=fixture[3], extension=fixture[4], **options)

    def facts(self, record, spelling):
        return [row for row in record["sound_facts"] if row["pitch"]["spelling"] == spelling]

    def test_new_typed_scope_complete_explicit_envelope_not_old_window(self):
        fx = self.fixture()
        record = self.prepare(fx)
        self.assertTrue(record["record_id"].startswith("fmes_"))
        self.assertEqual(record["analysis_span"], span(0, 4))
        self.assertEqual(record["anchor_span"], span(1, 2))
        self.assertEqual(record["original_target_span"], span(1, 2))
        self.assertEqual(record["extension_ref"], common.ref(fx[4]))
        self.assertEqual(record["original_view_ref"], common.ref(fx[1]))
        self.assertEqual(record["observation_ref"], common.ref(fx[2]))
        self.assertEqual(record["audit_ref"], common.ref(fx[3]))
        scope = record["literal_observation"]["scope"]
        self.assertEqual(scope["target_span"], span(0, 4))
        self.assertEqual(scope["context_span"], span(0, 4))
        self.assertNotIn("source_statement_ref", scope)
        self.assertNotIn("alignment_ref", scope)
        self.assertNotIn("record_id", record["literal_observation"])

    def test_fresh_parent_and_IR_replay_determinism_no_input_mutation(self):
        fx = self.fixture()
        before = deepcopy(fx)
        record = self.prepare(fx)
        self.assertEqual(fx, before)
        self.assertEqual(self.prepare(fx), record)
        self.assertTrue(self.validate(fx, record))
        self.assertTrue(expanded.check_scope(record, ir=fx[0]))
        self.assertEqual(fx, before)

    def test_output_has_no_mutable_alias_to_inputs_or_previous_output(self):
        fx = self.fixture()
        record = self.prepare(fx)
        saved = deepcopy(record)
        def mutable_ids(value):
            ids = {id(value)} if isinstance(value, (dict, list)) else set()
            if isinstance(value, dict):
                for child in value.values(): ids.update(mutable_ids(child))
            elif isinstance(value, (list, tuple)):
                for child in value: ids.update(mutable_ids(child))
            return ids
        self.assertFalse(mutable_ids(record) & mutable_ids(fx))
        record["sound_facts"][0]["pitch"]["step"] = "G"
        record["graphs"][0]["events"].clear()
        record["literal_observation"]["slots"][0]["core_event"]["notation"]["test"] = "mutation"
        self.assertEqual(self.prepare(fx), saved)

    def test_output_repeated_snapshots_have_no_internal_mutable_aliases(self):
        record = self.prepare(self.fixture())
        def object_ids(value):
            result = [id(value)] if isinstance(value, (dict, list)) else []
            if isinstance(value, dict):
                for child in value.values(): result.extend(object_ids(child))
            elif isinstance(value, list):
                for child in value: result.extend(object_ids(child))
            return result
        ids = object_ids(record)
        self.assertEqual(len(ids), len(set(ids)))

    def test_resealed_numeric_boolean_alias_is_rejected(self):
        record = self.prepare(self.fixture())
        for area in ("flags", "use_policy", "sound_facts"):
            modified = deepcopy(record)
            if area == "sound_facts": modified[area][0]["source_clock_passed"] = 1
            else: modified[area][next(iter(modified[area]))] = 0
            with self.subTest(area=area), self.assertRaises(ValueError):
                expanded.check_scope(reseal(modified, expanded.PREFIX))

    def test_research_flags_are_not_verdicts_or_source_authority(self):
        record = self.prepare(self.fixture())
        self.assertIsNone(record["selected"])
        self.assertIsNone(record["preferred"])
        self.assertTrue(all(value is False for value in record["flags"].values()))
        self.assertTrue(all(value is False for value in record["use_policy"].values()))
        self.assertTrue(all(row["baseline_voice_is_confirmed"] is False for row in record["lane_inventory"]))
        self.assertTrue(all(row["resolution_eligible"] is False for row in record["sound_facts"]))

    def test_exact_slots_projection_and_denominators_replay_common_literal_kernel(self):
        fx = self.fixture([[event(["C4", "E4"], 0, 1), event("D4", 1, 1), event("G4", 2, 2)],
                           [event(None, 0, 4)]])
        record = self.prepare(fx)
        slots, projection, lanes = common._selected_literal(fx[0], record["literal_observation"]["scope"])
        self.assertEqual(record["literal_observation"]["slots"], slots)
        self.assertEqual(record["literal_observation"]["core_projection"], projection)
        self.assertEqual(record["raw_lanes"], lanes)
        self.assertEqual(len(record["graphs"]), len(lanes))
        self.assertEqual(len(record["lane_inventory"]), len(lanes))

    def test_every_graph_fresh_full_IR_bound_new_span_not_old_graph(self):
        fx = self.fixture()
        record = self.prepare(fx)
        for graph in record["graphs"]:
            self.assertTrue(factors.validate_graph(graph, ir=fx[0], span=record["analysis_span"], lane=graph["lane"]))
            old = factors.factorize(fx[0], record["anchor_span"], graph["lane"])
            self.assertNotEqual(common.ref(graph), common.ref(old))
            self.assertEqual(graph["binding"], record["binding"])

    def test_rest_only_lane_is_retained_held_and_other_lane_remains_ready(self):
        fx = self.fixture([[event("C4", 0, 1), event("D4", 1, 1), event("E4", 2, 2)],
                           [event(None, 0, 4)]])
        record = self.prepare(fx)
        self.assertEqual(len(record["raw_lanes"]), 2)
        held = [row for row in record["lane_inventory"] if row["geometry_status"] != "ready"]
        ready = [row for row in record["lane_inventory"] if row["geometry_status"] == "ready"]
        self.assertEqual(len(held), 1)
        self.assertEqual(len(ready), 1)
        self.assertIn("geometry:empty_lane", held[0]["reasons"])
        self.assertEqual(record["status"], "expanded_scope_with_lane_holds")
        self.assertTrue(expanded.check_scope(record, ir=fx[0]))

    def test_point_grace_lane_held_without_discarding_valid_other_lane(self):
        fx = self.fixture([[event("C4", 0, 1), event("D4", 1, 1), event("E4", 2, 2)],
                           [event("G4", 0, 1), event("A4", 1, 0, grace=True), event("B4", 1, 3)]], extent=span(0, 1))
        record = self.prepare(fx)
        points = [row for row in record["sound_facts"] if row["point"]]
        self.assertEqual(len(points), 1)
        self.assertTrue(points[0]["grace"])
        self.assertFalse(points[0]["eligible_as_analysis_source"])
        self.assertEqual(record["counts"]["graphs_ready"], 1)
        self.assertEqual(record["counts"]["graphs_held"], 1)
        self.assertTrue(any(row["point_sound_refs"] for row in record["lane_inventory"]))

    def test_full_tie_chain_keeps_source_span_attack_and_source_closure(self):
        fx = self.fixture([[event("C4", 0, 1, tie_role="start"), event("C4", 1, 1, tie_role="stop"),
                           event("D4", 2, 1), event("E4", 3, 1)]], extent=span(Fraction(3, 2), 2))
        record = self.prepare(fx)
        row = self.facts(record, "C4")[0]
        self.assertEqual(row["span"], span(0, 2))
        self.assertEqual(row["anchor_overlap"], span(Fraction(3, 2), 2))
        self.assertEqual(len(row["source_note_refs"]), 2)
        self.assertTrue(row["source_clock_passed"])
        self.assertEqual(row["attack_note_id"], fx[1]["sounds"][0]["attack_note_id"])
        self.assertEqual(len(record["literal_observation"]["core_projection"]["tie_chains"]), 1)

    def test_source_clock_gap_kept_held_even_if_anchor_clip_is_good(self):
        fx = self.fixture([[event("C4", 0, 1, tie_role="start"), event("C4", 3, 1, tie_role="stop")]], extent=span(0, 1))
        record = self.prepare(fx)
        row = self.facts(record, "C4")[0]
        self.assertFalse(row["source_clock_passed"])
        self.assertFalse(row["eligible_as_analysis_source"])
        self.assertIn("full_source_timeline_gap", row["source_diagnostics"])
        self.assertEqual(row["span"], fx[0]["sounding_events"][0]["span"])
        self.assertTrue(expanded.check_scope(record, ir=fx[0]))

    def test_continuation_origin_not_promoted_to_new_attack(self):
        def change(ir):
            note = ir["note_events"][0]
            note["tie_role"] = "stop"
        fx = self.fixture(modify=change)
        record = self.prepare(fx)
        row = self.facts(record, "C4")[0]
        self.assertIn("attack_is_tie_continuation_or_stop_origin", row["diagnostics"])
        self.assertFalse(row["eligible_as_analysis_source"])
        self.assertEqual(record["literal_observation"]["slots"][0]["core_event"]["tie_role"], "stop")

    def test_source_pitch_mismatch_local_hold_not_source_repair(self):
        def change(ir):
            ir["sounding_events"][0]["pitch"] = deepcopy(ir["note_events"][-1]["written_pitch"])
        fx = self.fixture(modify=change)
        record = self.prepare(fx)
        row = next(row for row in record["sound_facts"] if row["sound_id"] == fx[0]["sounding_events"][0]["sounding_event_id"])
        self.assertFalse(row["source_pitch_consistency_passed"])
        self.assertFalse(row["eligible_as_analysis_source"])
        self.assertIn("source_written_pitch_mismatch", row["diagnostics"])
        self.assertEqual(row["pitch"], fx[0]["sounding_events"][0]["pitch"])
        self.assertEqual(len(record["sound_facts"]), 4)

    def test_added_source_attack_event_mismatch_is_guard_hold_not_repaired(self):
        def change(ir):
            last = ir["attack_events"][-1]
            last["note_id"] = ir["note_events"][0]["note_id"]
        record = self.prepare(self.fixture(modify=change))
        row = self.facts(record, "F4")[0]
        self.assertFalse(row["source_attack_consistency_passed"])
        self.assertFalse(row["eligible_as_analysis_source"])
        self.assertIn("source_attack_event_inventory_or_lineage_mismatch", row["diagnostics"])
        self.assertTrue(self.facts(record, "D4")[0]["source_attack_consistency_passed"])

    def test_added_missing_attack_event_is_guard_hold_not_invented(self):
        def change(ir):
            ir["attack_events"].pop()
        record = self.prepare(self.fixture(modify=change))
        row = self.facts(record, "F4")[0]
        self.assertFalse(row["source_attack_consistency_passed"])
        self.assertEqual(len(record["literal_observation"]["core_projection"]["attack_events"]), 3)

    def test_rational_microtonal_pitch_preserved_as_guard_hold(self):
        def change(ir):
            note = ir["note_events"][0]
            for key in ("written_pitch", "concert_pitch"):
                note[key].update(alter=common.q(Fraction(1, 2)), spelling="C-half-sharp4", midi_pitch=None, pitch_class=None)
            sound = next(row for row in ir["sounding_events"] if note["note_id"] in row["source_note_ids"])
            sound["pitch"] = deepcopy(note["written_pitch"])
        record = self.prepare(self.fixture(modify=change))
        row = self.facts(record, "C-half-sharp4")[0]
        self.assertEqual(row["pitch"]["alter"], common.q(Fraction(1, 2)))
        self.assertFalse(row["eligible_as_analysis_source"])
        self.assertTrue(row["source_clock_passed"])
        self.assertTrue(row["source_pitch_consistency_passed"])

    def test_neighbor_outside_envelope_is_not_an_analysis_source(self):
        fx = self.fixture([[event("C4", 0, 1), event(None, 1, 4), event("D4", 5, 1),
                           event(None, 6, 4), event("E4", 10, 2)]], extent=span(5, 6),
                          clocks=[(0, 4), (4, 4), (8, 4)], pre_measures=0, post_measures=0)
        record = self.prepare(fx)
        self.assertEqual(record["analysis_span"], span(4, 8))
        self.assertEqual({row["pitch"]["spelling"] for row in record["sound_facts"]}, {"D4"})
        self.assertTrue(any(row["pitch"]["spelling"] == "E4" for row in fx[4]["sound_facts"]))
        self.assertEqual({row["pitch"]["spelling"] for row in record["graphs"][0]["events"]}, {"D4"})

    def test_linked_tie_outside_envelope_preserved_not_retimed_or_new_attack(self):
        fx = self.fixture([[event("C4", 0, 4, tie_role="start"), event("C4", 4, 4, tie_role="stop"),
                           event("D4", 8, 4)]], extent=span(5, 6), clocks=[(0, 4), (4, 4), (8, 4)],
                          pre_measures=0, post_measures=0)
        record = self.prepare(fx)
        row = self.facts(record, "C4")[0]
        self.assertEqual(row["span"], span(0, 8))
        self.assertEqual(row["observed_span"], span(4, 8))
        self.assertEqual(len(row["source_note_ids"]), 2)
        outside_slot = record["literal_observation"]["slots"][0]
        self.assertEqual(outside_slot["context_relation"], "linked_context_only")
        self.assertIsNone(outside_slot["target_overlap"])

    def test_half_open_end_point_and_positive_onset_not_in_scope(self):
        fx = self.fixture([[event("C4", 0, 4), event("D4", 4, 0, grace=True), event("E4", 4, 4)]],
                          extent=span(1, 2), clocks=[(0, 4), (4, 4)], pre_measures=0, post_measures=0)
        record = self.prepare(fx)
        self.assertEqual(record["analysis_span"], span(0, 4))
        self.assertEqual({row["pitch"]["spelling"] for row in record["sound_facts"]}, {"C4"})
        self.assertEqual(record["counts"]["analysis_point_sounds"], 0)

    def test_note_releasing_at_anchor_start_is_not_in_anchor_but_new_scope_fact(self):
        record = self.prepare(self.fixture([[event("A4", 0, 1), event("F4", 1, 1), event("E4", 2, 2)]]))
        row = self.facts(record, "A4")[0]
        self.assertIsNone(row["anchor_overlap"])
        self.assertEqual(row["observed_span"], span(0, 1))
        self.assertFalse(row["resolution_eligible"])

    def test_no_pitch_pruning_all_equal_endpoint_alternatives_remain(self):
        fx = self.fixture([[event(["C4", "E4"], 0, 1), event(["D4", "F4"], 1, 1),
                           event("G4", 2, 2)]])
        record = self.prepare(fx)
        graph = record["graphs"][0]
        factor = next(row for row in graph["factors"] if common.f(row["time"]) == 1)
        self.assertEqual(len(factor["source_refs"]), 2)
        self.assertEqual(len(factor["target_refs"]), 2)
        self.assertEqual(factor["legal_edge_count"], 4)
        self.assertEqual(factors.query(graph)["status"], "exact_count")

    def test_geometry_limits_hold_entire_lane_inventory_not_successful_subset(self):
        fx = self.fixture()
        full = self.prepare(fx)
        for setting in ("max_events", "max_factors", "max_edges"):
            options = {setting: 0}
            record = self.prepare(fx, **options)
            with self.subTest(setting=setting):
                self.assertEqual(record["raw_lanes"], full["raw_lanes"])
                self.assertEqual(record["sound_facts"], full["sound_facts"])
                self.assertEqual(record["source_audit"], full["source_audit"])
                self.assertEqual(record["graphs"][0]["events"], full["graphs"][0]["events"])
                self.assertEqual(record["counts"]["graphs_held"], 1)
                self.assertTrue(self.validate(fx, record, **options))

    def test_whole_context_budget_hold_cannot_partially_admit_scope(self):
        for options in ({"max_events": 0}, {"max_relations": 0}):
            fx = self.fixture(**options)
            with self.subTest(options=options), self.assertRaisesRegex(ValueError, "whole_context_budget_hold"):
                self.prepare(fx)

    def test_invalid_caps_rejected_before_parent_reads(self):
        for field in ("max_events", "max_factors", "max_edges"):
            for value in (-1, True, 1.5, "1", None):
                with self.subTest(field=field, value=value), patch.object(context, "validate_context", side_effect=AssertionError("no read")):
                    with self.assertRaisesRegex(ValueError, "nonnegative_integer"):
                        expanded.prepare_scope(None, None, None, None, None, **{field: value})

    def test_graph_projection_mismatch_is_explicit_whole_scope_hold_no_source_fill(self):
        fx = self.fixture([[event("C4", 0, 1, tie_role="start"), event("C4", 11, 1, tie_role="stop"),
                           event("D4", 5, 1), event(None, 6, 4)]], extent=span(5, 6),
                          clocks=[(0, 4), (4, 4), (8, 4)], pre_measures=0, post_measures=0)
        record = self.prepare(fx)
        self.assertEqual(record["analysis_span"], span(4, 8))
        self.assertFalse(record["context_sound_inventory_complete"])
        self.assertEqual(record["status"], "whole_scope_abstention")
        self.assertEqual(len(record["unprojected_context_sound_snapshots"]), 1)
        self.assertNotIn("C4", {row["pitch"]["spelling"] for row in record["sound_facts"]})
        self.assertIn("C4", {row["pitch"]["spelling"] for row in record["graphs"][0]["events"]})
        self.assertTrue(expanded.check_scope(record, ir=fx[0]))

    def test_resealed_sound_guard_projection_audit_inventory_and_policy_tamper_rejected(self):
        fx = self.fixture()
        record = self.prepare(fx)
        changes = {
            "guard": lambda row: row["sound_facts"][0].update(source_clock_passed=False),
            "pitch": lambda row: row["sound_facts"][0]["pitch"].update(step="G"),
            "notes": lambda row: row["sound_facts"][0]["source_note_ids"].clear(),
            "snapshot": lambda row: row["literal_observation"]["slots"].pop(),
            "lane": lambda row: row["lane_inventory"].pop(),
            "audit": lambda row: row["source_audit"].update(source_clock_consistency_passed=False),
            "promotion": lambda row: row["flags"].update(generation_ready=True),
            "unknown": lambda row: row.update(confidence=0.99),
            "counts": lambda row: row["counts"].update(analysis_positive_sounds=99),
        }
        for name, change in changes.items():
            modified = deepcopy(record)
            change(modified)
            with self.subTest(name=name), self.assertRaises((ValueError, ValidationError, KeyError)):
                expanded.check_scope(reseal(modified, expanded.PREFIX))

    def test_old_graph_foreign_graph_or_omitted_graph_rejected_even_resealed(self):
        fx = self.fixture()
        record = self.prepare(fx)
        for kind in ("old", "foreign", "omitted", "duplicate"):
            modified = deepcopy(record)
            if kind == "old":
                modified["graphs"][0] = factors.factorize(fx[0], span(1, 2), record["graphs"][0]["lane"])
            elif kind == "foreign":
                graph = deepcopy(modified["graphs"][0]); graph["binding"]["ir_document_id"] = "foreign"
                modified["graphs"][0] = reseal(graph, "vfgraph_")
            elif kind == "omitted": modified["graphs"].clear()
            else: modified["graphs"].append(deepcopy(modified["graphs"][0]))
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                expanded.check_scope(reseal(modified, expanded.PREFIX))

    def test_foreign_or_mutated_parent_and_extension_fail_closed(self):
        fx = self.fixture()
        record = self.prepare(fx)
        for kind in ("ir", "view", "observation", "audit", "extension"):
            modified = list(deepcopy(fx))
            if kind == "ir": modified[0]["note_events"][0]["notation"]["test"] = "changed"
            elif kind == "view":
                modified[1]["sounds"][0]["source_clock_passed"] = False
                modified[1] = reseal(modified[1])
            elif kind == "observation":
                modified[2]["slots"].pop()
                modified[2] = reseal(modified[2], "mfco_")
            elif kind == "audit":
                modified[3]["source_clock_consistency_passed"] = False
                modified[3] = reseal(modified[3], "msla_")
            else:
                modified[4]["envelope_span"] = span(1, 2)
                modified[4] = reseal(modified[4], context.PREFIX)
            with self.subTest(kind=kind), self.assertRaises((ValueError, ValidationError)):
                self.validate(modified, record)

    def test_changed_caps_or_extension_option_cannot_validate_old_scope(self):
        fx = self.fixture()
        record = self.prepare(fx)
        with self.assertRaises(ValueError): self.validate(fx, record, max_edges=0)
        changed = list(fx)
        changed[4] = context.observe_context(*fx[:4], pre_measures=0, post_measures=0)
        with self.assertRaisesRegex(ValueError, "stale_foreign_or_modified"):
            self.validate(changed, record)

    def test_contract_schema_and_actual_helper_code_stamp_invalidates_old_scope(self):
        fx = self.fixture()
        record = self.prepare(fx)
        original = common._schema_bytes()
        with patch.object(common, "_schema_bytes", return_value=original + b"\n"):
            with self.assertRaisesRegex(ValueError, "unsupported_stale"):
                expanded.check_scope(record)
        original_read = Path.read_bytes
        target = Path(factors.__file__)
        def changed_bytes(path):
            raw = original_read(path)
            return raw + b"\n" if path == target else raw
        with patch.object(Path, "read_bytes", changed_bytes):
            with self.assertRaisesRegex(ValueError, "unsupported_stale"):
                expanded.check_scope(record)

    def test_IR_only_check_freshly_rebuilds_and_never_claims_parent_authority(self):
        fx = self.fixture()
        record = self.prepare(fx)
        with patch.object(context, "validate_context", side_effect=AssertionError("IR-only is not parent replay")):
            self.assertTrue(expanded.check_scope(record, ir=fx[0]))
        changed_ir = deepcopy(fx[0]); changed_ir["note_events"][0]["notation"]["test"] = "change"
        with self.assertRaisesRegex(ValueError, "stale_or_foreign"):
            expanded.check_scope(record, ir=changed_ir)
        self.assertFalse(record["flags"]["parent_artifact_authority_established"])

    def test_public_validator_always_fresh_replays_extension_and_all_original_parents(self):
        fx = self.fixture()
        record = self.prepare(fx)
        actual = context.validate_context
        with patch.object(context, "validate_context", wraps=actual) as fresh:
            self.validate(fx, record)
            self.validate(fx, record)
            self.assertEqual(len(fresh.call_args_list), 2)
            self.assertTrue(all(call.kwargs["ir"] is fx[0] and call.kwargs["view"] is fx[1]
                                and call.kwargs["observation"] is fx[2] and call.kwargs["audit"] is fx[3]
                                for call in fresh.call_args_list))

    def test_no_old_view_path_key_bundle_or_inference_fabricated(self):
        from musicanote_harness import factor_functional_overlay as overlay
        from musicanote_harness import factor_functional_resolution as resolution
        fx = self.fixture()
        with patch.object(common, "make_path", side_effect=AssertionError("old path forbidden")), \
             patch.object(overlay, "make_key_track", side_effect=AssertionError("old key forbidden")), \
             patch.object(resolution, "make_bundle", side_effect=AssertionError("old bundle forbidden")), \
             patch.object(resolution, "compile_resolutions", side_effect=AssertionError("inference forbidden")):
            record = self.prepare(fx)
        self.assertFalse(record["flags"]["original_window_or_path_or_bundle_extended"])


if __name__ == "__main__":
    unittest.main()
