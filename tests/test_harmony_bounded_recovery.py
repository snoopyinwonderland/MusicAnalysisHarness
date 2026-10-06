from copy import deepcopy
from dataclasses import replace
from fractions import Fraction as F
import inspect
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from musicanote_harness import harmony_bounded_recovery as recovery
from musicanote_harness import harmony_bounded_recovery_trial as trial
from musicanote_harness.harmony_functional_scoring import decode, score_path, supply
from musicanote_harness.harmony_evidence_scoring import run_features
from musicanote_harness.harmony_common_benchmark import evaluate, native_reference, native_prediction, summarize
from musicanote_harness.harmony_progression_search import _hash
from musicanote_harness.harmony_scored_decoder import Problem
from musicanote_harness.formal_ir import q
from test_harmony_open_candidates import score


def fixture(specs=None, end=4):
    specs = specs or [("C3", 0, end, "b"), ("E3", 0, end, "i"), ("G3", 0, end, "j"),
                      ("C4", 0, 1, "lead"), ("D4", 1, 2, "lead"), ("E4", 2, end, "lead")]
    ir = score(specs); ir["ir_document_id"] = "toy-ir"
    ir["score"] = {"score_id": "toy-score", "duration_quarters": q(end)}
    for n, s in zip(ir["note_events"], ir["sounding_events"]):
        n.update(concert_pitch=deepcopy(s["pitch"]), global_onset_quarter=s["span"]["start"],
                 notated_duration_quarter=q(recovery.f(s["span"]["end"])-recovery.f(s["span"]["start"])))
        s["attack_note_id"] = n["note_id"]; s["sounding_duration"] = n["notated_duration_quarter"]
    m = deepcopy(ir["measures"][0]); ir["measures"] = []
    t = F()
    while t < end:
        new = deepcopy(m); new.update(measure_id="m"+str(t), global_start_quarter=q(t), actual_duration_quarter=q(min(F(4), end-t)))
        ir["measures"].append(new); t += 4
    return ir


def add_grace(ir, t=1):
    n = deepcopy(ir["note_events"][-1]); s = deepcopy(ir["sounding_events"][-1])
    n.update(note_id="grace-note", global_onset_quarter=q(t), notated_duration_quarter=q(0),
             grace={"is_grace": True, "order": 0, "anchor_note_id": ir["note_events"][-1]["note_id"]})
    s.update(sounding_event_id="grace-sound", source_note_ids=[n["note_id"]],
             attack_note_id=n["note_id"], tie_chain_id=None, sounding_duration=q(0), span={"start": q(t), "end": q(t)})
    ir["note_events"].append(n); ir["sounding_events"].append(s)
    ir["attack_events"] = [{"attack_event_id": "grace-attack", "note_id": n["note_id"], "sounding_event_id": s["sounding_event_id"]}]
    ir["voices"] = [{"event_ids": [n["note_id"], ir["note_events"][0]["note_id"]]}]
    ir["chord_onset_groups"] = [{"note_ids": [n["note_id"]]}]
    return n, s


def sample(end=4, reasons=None):
    return {"sample_id": "frozen", "span": {"start": q(0), "end": q(end)}, "lane": ["x", "y"],
            "seed_event_refs": [], "abstention_reasons": reasons or []}


class BoundedRecoveryTests(unittest.TestCase):
    def test_grace_is_retained_without_inventing_performance(self):
        ir = fixture(); n, s = add_grace(ir); before = deepcopy(ir)
        view, receipt = recovery.grace_projection(ir)
        self.assertEqual(ir, before); self.assertEqual(receipt["grace_note_events"], [n])
        self.assertEqual(receipt["grace_sounding_events"], [s]); self.assertIsNone(receipt["performed_timing"])
        self.assertNotIn(n, view["note_events"]); self.assertNotIn(s, view["sounding_events"])
        self.assertEqual(view["attack_events"], []); self.assertEqual(view["chord_onset_groups"], [])
        self.assertFalse(receipt["formal_canonical_revision"])
        self.assertEqual(receipt["original_ir_sha256"], _hash(ir)); self.assertEqual(receipt["consumer_view_sha256"], _hash(view))

    def test_zero_non_grace_not_silently_removed(self):
        ir = fixture(); n, _ = add_grace(ir); n["grace"]["is_grace"] = False
        with self.assertRaisesRegex(ValueError, "not_verified_grace"): recovery.grace_projection(ir)

    def test_missing_grace_source_or_tie_rejected(self):
        for mode in ("missing", "tie", "clock"):
            ir = fixture(); n, s = add_grace(ir)
            if mode == "missing": s["source_note_ids"] = ["absent"]
            if mode == "tie": s["tie_chain_id"] = "tie"
            if mode == "clock": n["global_onset_quarter"] = q(2)
            with self.assertRaisesRegex(ValueError, "not_verified_grace"): recovery.grace_projection(ir)

    def test_negative_sound_rejected(self):
        ir = fixture(); ir["sounding_events"][0]["span"]["end"] = q(-1)
        with self.assertRaisesRegex(ValueError, "negative"): recovery.grace_projection(ir)

    def test_positive_grace_not_reinterpreted_as_ordinary_note(self):
        ir = fixture(); ir["note_events"][0]["grace"] = {"is_grace": True}
        view, receipt = recovery.grace_projection(ir)
        self.assertEqual(view["note_events"][0]["grace"], {"is_grace": True})
        self.assertEqual(receipt["grace_note_events"], [])

    def test_unknown_performed_grace_cannot_create_direct_voice_link(self):
        ir = fixture(); add_grace(ir, 1)
        view, receipt = recovery.grace_projection(ir)
        ev, func, withholding = recovery.bound_evidence(view, sample()["span"], receipt)
        self.assertGreater(withholding["direct_functional_links_withheld"], 0)
        self.assertGreater(withholding["ornament_neighbor_triples_withheld"], 0)
        self.assertFalse(ev.neighbors)
        self.assertFalse(any(p["end"] == n["start"] == 1 for p, n in func.links))

    def test_tile_seams_carry_original_sound_not_new_attack(self):
        ir = fixture(end=24); p = recovery.tile_plan(ir, sample(24)["span"])
        self.assertEqual(p["status"], "ready"); self.assertGreater(len(p["tiles"]), 1)
        bass = ir["sounding_events"][0]["sounding_event_id"]
        seam = p["tiles"][1]
        self.assertIn(bass, seam["carried_sound_refs"]); self.assertNotIn(bass, seam["attack_sound_refs"])
        self.assertEqual(ir["sounding_events"][0]["span"], {"start": q(0), "end": q(24)})
        self.assertFalse(p["tile_seams_are_harmonic_boundaries"])

    def test_plan_full_partition_no_hidden_end_truncation(self):
        p = recovery.tile_plan(fixture(end=40), sample(40)["span"])
        cursor = q(0)
        for tile in p["tiles"]:
            self.assertEqual(tile["span"]["start"], cursor); self.assertTrue(tile["context_policy"]["accepted"])
            cursor = tile["span"]["end"]
        self.assertEqual(cursor, q(40))

    def test_global_cell_limit_retains_entire_context(self):
        ir = fixture(end=40)
        with patch.object(recovery, "CONFIG", dict(recovery.CONFIG, global_cells=2)):
            p = recovery.tile_plan(ir, sample(40)["span"])
        self.assertIn("global_cell_budget_no_truncation", p["blockers"])
        self.assertEqual(p["points"][-1], q(40)); self.assertEqual(p["tiles"][-1]["span"]["end"], q(40))

    def test_global_sound_limit_is_not_top_voice_pruning(self):
        ir = fixture()
        with patch.object(recovery, "CONFIG", dict(recovery.CONFIG, global_sounds=2)):
            p = recovery.tile_plan(ir, sample()["span"])
        self.assertIn("global_sound_budget_no_pruning", p["blockers"])

    def test_repeat_and_meter_barriers_not_overridden_by_tiles(self):
        ir = fixture(end=8); ir["measures"][0]["repeat_barline"] = {"repeat_direction": "backward", "location": "right"}
        self.assertIn("repeat_or_ending_barrier", recovery.tile_plan(ir, sample(8)["span"])["blockers"])
        ir["measures"][0]["repeat_barline"] = {}; ir["measures"][1]["time_signature"]["beats"] = 3
        self.assertIn("meter_changed", recovery.tile_plan(ir, sample(8)["span"])["blockers"])

    def test_missing_measure_coverage_and_invalid_span_rejected(self):
        ir = fixture(end=8); ir["measures"] = ir["measures"][:1]
        self.assertEqual(recovery.tile_plan(ir, sample(8)["span"])["status"], "unsplittable_observation_cell")
        with self.assertRaisesRegex(ValueError, "invalid"): recovery.tile_plan(ir, {"start": q(2), "end": q(1)})

    def test_joint_decoder_crosses_seam_without_chord_change(self):
        specs = [("C3", 0, 4, "b"), ("E3", 0, 4, "i"), ("G3", 0, 4, "j")]
        specs += [("C4", F(i, 2), F(i+1, 2), "lead") for i in range(8)]
        ir = fixture(specs); before = deepcopy(ir)
        with patch.object(recovery, "CONFIG", dict(recovery.CONFIG, tile_cells=2)):
            result, problem = recovery.infer(ir, sample())
        self.assertEqual(ir, before); chosen = result["selected_prediction"]
        self.assertIsNotNone(chosen); self.assertGreater(len(chosen["segments"]), 1)
        self.assertEqual(len(chosen["harmonic_runs"]), 1)
        self.assertEqual(chosen["harmonic_runs"][0]["root_spelling"], ("C", 0))
        self.assertEqual(chosen["harmonic_runs"][0]["span"], sample()["span"])
        self.assertTrue(result["exact_optimum_under_declared_graph"])
        self.assertEqual(problem.max_segments, 6*len(result["tile_plan"]["tiles"]))

    def test_joint_optimum_matches_exhaustive_paths_on_tiled_toy(self):
        ir = fixture([(p, 0, 2, v) for p, v in (("C3", "b"), ("E3", "i"), ("G3", "j"))]
                     + [("C4", 0, 1, "lead"), ("E4", 1, 2, "lead")], end=2)
        view, grace = recovery.grace_projection(ir)
        with patch.object(recovery, "CONFIG", dict(recovery.CONFIG, tile_cells=1)):
            plan = recovery.tile_plan(view, sample(2)["span"])
        ev, func, _ = recovery.bound_evidence(view, sample(2)["span"], grace)
        problem, _ = recovery.build_problem(view, plan, ev)
        allowed = {(("C", 0), (("C", 0), ("E", 0), ("G", 0))),
                   (("C", 0), (("B", 0), ("C", 0), ("E", 0), ("G", 0)))}
        problem = replace(problem, edges=tuple(e for e in problem.edges if e.signature in allowed))
        paths = []
        def visit(index, ids):
            if index == len(problem.points)-1: paths.append(ids); return
            if len(ids) >= problem.max_segments: return
            for edge in problem.edges:
                if edge.start_index == index: visit(edge.end_index, ids+(edge.group_id,))
        visit(0, ()); self.assertGreater(len(paths), 1)
        expected = min((score_path(problem, func, ids), ids) for ids in paths)
        selected = decode(problem, func)["selected"]
        self.assertEqual(recovery.f(selected["score_cost"]), expected[0])
        self.assertEqual(tuple(s["semantic_group_ref"] for s in selected["segments"]), expected[1])

    def test_catalog_source_loss_rejected(self):
        ir = fixture(); view, grace = recovery.grace_projection(ir)
        plan = recovery.tile_plan(view, sample()["span"]); ev, _, _ = recovery.bound_evidence(view, sample()["span"], grace)
        real = recovery.propose
        def broken(*args):
            result = real(*args); result["providers"]["base"]["event_units"].popitem(); return result
        with patch.object(recovery, "propose", side_effect=broken):
            with self.assertRaisesRegex(ValueError, "event_loss"): recovery.build_problem(view, plan, ev)

    def test_duplicate_note_and_positive_duration_binding_rejected(self):
        ir = fixture(); ir["note_events"].append(deepcopy(ir["note_events"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate_note"): recovery.grace_projection(ir)
        ir = fixture(); ir["sounding_events"][0]["sounding_duration"] = q(2)
        with self.assertRaisesRegex(ValueError, "duration_mismatch"): recovery.infer(ir, sample())

    def test_long_simple_context_can_use_bounded_joint_graph(self):
        ir = fixture([(p, 0, 24, v) for p, v in (("C3", "b"), ("E3", "i"), ("G3", "j"))], end=24)
        result, _ = recovery.infer(ir, sample(24))
        self.assertIsNotNone(result["selected_prediction"])
        self.assertEqual(len(result["selected_prediction"]["harmonic_runs"]), 1)

    def test_all_part_source_coverage_and_original_timing(self):
        ir = fixture(); view, grace = recovery.grace_projection(ir); span = {"start": q(1), "end": q(3)}
        plan = recovery.tile_plan(view, span); ev, func, _ = recovery.bound_evidence(view, span, grace)
        problem, origins = recovery.build_problem(view, plan, ev)
        for edge in problem.edges:
            expected = {s["sounding_event_id"] for s in recovery.intersecting(ir, edge.start, edge.end)}
            self.assertEqual(set(edge.source_event_ids), expected)
        self.assertTrue(origins); self.assertEqual(ev.events[0].start, F(0))
        sig = (("C", 0), (("C", 0), ("E", 0), ("G", 0)))
        self.assertEqual(run_features(problem, ev, F(1), F(3), sig)[0]["nonmember_exposure"], F(1, 8))

    def test_inference_no_gold_or_piece_specific_argument(self):
        self.assertEqual(tuple(inspect.signature(recovery.infer).parameters), ("ir", "sample"))
        ir = fixture(); before = recovery.infer(ir, sample())[0]["selected_prediction"]
        ir["annotations"] = ["V7/V"]; ir["score"]["title"] = "POISON_V7"; ir["extensions"] = {"gold": "I"}
        after = recovery.infer(ir, sample())[0]["selected_prediction"]
        self.assertEqual(before, after)

    def test_scope_failure_not_cleared_just_because_grace_exists(self):
        ir = fixture(); add_grace(ir)
        result, _ = recovery.infer(ir, sample(reasons=["complete_sound_outside_frozen_scope", "nonpositive_duration"]))
        self.assertIsNone(result["selected_prediction"])
        self.assertEqual(result["tile_plan"]["blockers"], ["complete_sound_outside_frozen_scope"])

    def test_candidate_and_decoder_budgets_abstain_not_prune(self):
        ir = fixture()
        with patch.object(recovery, "CONFIG", dict(recovery.CONFIG, global_candidate_edges=1)):
            result, problem = recovery.infer(ir, sample())
        self.assertEqual(result["status"], "global_candidate_budget_no_pruning"); self.assertFalse(problem.edges)
        with patch.object(recovery, "CONFIG", dict(recovery.CONFIG, decoder_transition_budget=1)):
            result, _ = recovery.infer(ir, sample())
        self.assertEqual(result["status"], "transition_budget_abstention"); self.assertIsNone(result["selected_prediction"])

    def test_positive_exposure_not_replaced_by_grace_only_music(self):
        ir = fixture(); add_grace(ir)
        ir["sounding_events"] = ir["sounding_events"][-1:]; ir["note_events"] = ir["note_events"][-1:]
        result, _ = recovery.infer(ir, sample())
        self.assertEqual(result["status"], "no_positive_sounding_exposure")

    def test_prediction_seal_precedes_reference_read_and_no_resampling(self):
        code = inspect.getsource(trial.run)
        self.assertLess(code.index('save(output/"prediction-freeze.json"'), code.index('baseline = read(source/"report.json"'))
        self.assertNotIn("freeze_score(", code)
        with TemporaryDirectory() as t:
            with self.assertRaisesRegex(ValueError, "output_exists"): trial.run("missing", t)

    def disk_trial(self, root, mode="missing"):
        source = root/"baseline"; source.mkdir(); output = root/"paired"
        ir = fixture(); ir_path = source/"observation.json.gz"; trial.write_packet(ir_path, ir)
        s = sample(); key = {"pair_id": "dcml:c:w", "work_family_id": "family", "collection_id": "c"}
        prediction = {"source_labels_used_for_selection": False, "segments": [{"span": s["span"],
            "root_spelling": ["C", 0], "members": [["C", 0], ["E", 0], ["G", 0]]}]} if mode == "control" else None
        row = dict(key, sample_id=s["sample_id"], sample_span=s["span"], plan_index=7,
            status="source_preflight_abstention" if mode == "blocked" else "selected_untrained_hypothesis" if prediction else "baseline_not_ready",
            selected_prediction=prediction, reference_binding_verified=mode != "blocked")
        packet = source/"prediction.json.gz"; trial.write_packet(packet, row)
        item = {"entry": key, "observation_ir_path": str(ir_path), "observation_ir_content_sha256": _hash(ir),
            "blockers": ["source_binding"] if mode == "blocked" else [], "plan": {"selected_samples": [{"sample": s, "plan_index": 7}]}}
        trial.write(source/"frozen-plan.json", {"packages": [item]})
        trial.write(source/"prediction-freeze.json", {"contexts": 1, "labels_read": False, "prediction_hashes": {str(packet): trial.digest(packet)}})
        trial.write(source/"run-contract.json", {"code_pins": {}, "source_labels_used_at_inference": False})
        row["reference_cells"] = [{"span": s["span"], "signature": None if mode == "blocked" else
                                  [["C", 0], [["C", 0], ["E", 0], ["G", 0]]], "reason": None}]
        row["evaluation"] = evaluate(native_reference(row), native_prediction(prediction, s["span"]), s["span"], selected=prediction is not None)
        row["candidate_ceiling"] = {"lattice_hit": None, "outcome": "unavailable"}
        report = {"records": [row], "table": summarize([row]), "input_hashes": {}, "code_hashes": {}, "artifact_hashes": {}}
        trial.write(source/"report.json", report); real_load = trial.load
        def read(path):
            if Path(path) == source/"report.json":
                receipt = real_load(output/"prediction-freeze.json")
                self.assertFalse(receipt["labels_read"]); self.assertEqual(receipt["contexts"], 1)
                for p, sha in receipt["prediction_hashes"].items(): self.assertEqual(trial.digest(p), sha)
            return real_load(path)
        def infer(unannotated, frozen):
            self.assertFalse((output/"prediction-freeze.json").exists()); self.assertNotIn("reference_cells", unannotated)
            self.assertEqual(frozen["span"], s["span"])
            if mode == "error": raise ValueError("synthetic")
            if mode == "tamper": trial.write_packet(ir_path, {"changed": True})
            return ({"status": "unavailable", "selected_prediction": None}, Problem((), (), 0, F(), "unavailable"))
        with patch.object(trial, "BASELINE_REPORT_SHA", trial.digest(source/"report.json")), patch.object(trial, "load", side_effect=read), patch.object(trial, "infer", side_effect=infer) as mocked:
            result = trial.run(source, output)
            self.assertEqual(mocked.call_count, 0 if mode in ("blocked", "control") else 1)
        return result

    def test_real_disk_phase_seal_and_missing_prediction_denominator(self):
        with TemporaryDirectory() as t: result = self.disk_trial(Path(t))
        self.assertEqual(result["table"]["contexts"], 1)
        self.assertEqual(result["table"]["components"]["root_members"]["eligible_time"], q(4))
        self.assertEqual(result["table"]["components"]["root_members"]["time_agreement"], 0)

    def test_control_and_source_blocker_cannot_trigger_recovery(self):
        for mode in ("control", "blocked"):
            with TemporaryDirectory() as t: result = self.disk_trial(Path(t), mode)
            self.assertEqual(result["recovery_attempts"], 0)
            self.assertEqual(result["table"]["selected_contexts"], int(mode == "control"))

    def test_engine_error_stays_in_accuracy_denominator(self):
        with TemporaryDirectory() as t: result = self.disk_trial(Path(t), "error")
        self.assertEqual(result["status_counts"], {"execution_error": 1})
        self.assertEqual(result["table"]["components"]["root_members"]["eligible_time"], q(4))

    def test_changed_physical_ir_artifact_aborts_report(self):
        with TemporaryDirectory() as t:
            with self.assertRaisesRegex(ValueError, "artifact_changed"): self.disk_trial(Path(t), "tamper")
            self.assertFalse((Path(t)/"paired"/"report.json").exists())


if __name__ == "__main__": unittest.main()
