from copy import deepcopy
from fractions import Fraction as F
import inspect
import gzip
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from musicanote_harness.harmony_candidate_recall import rational
from musicanote_harness.harmony_scored_decoder import (
    DEFAULT_WEIGHTS, Edge, Problem, decode, evaluation_path, feature_cost,
    observations, prepare, transition, weights_contract,
)
from musicanote_harness.harmony_scored_decoder_trial import evaluate_selection, retained_music, training_eligibility, run, summarize
from musicanote_harness.harmony_candidate_recall import evaluate, paths_from_search, summarize as recall_summary
from musicanote_harness.harmony_progression_search import _hash
from test_harmony_lattice_recall import C, D, cell, fixture, span


def note(eid, pitch=("C", 0), a=0, b=2):
    return {"sounding_event_id": eid, "source_note_ids": ["note_"+eid], "attack_note_id": "note_"+eid,
            "pitch": {"step": pitch[0], "alter": rational(F(pitch[1]))},
            "span": span(a, b), "sounding_duration": rational(F(b)-F(a)), "tie_chain_id": None}


def native(specs=((0, 2, C),), events=None, points=(0, 1, 2), budget=6):
    b, s, _ = fixture(points, specs, budget)
    events = [note("c"), note("e", ("E", 0)), note("g", ("G", 0))] if events is None else events
    b["stages"]["lattice"]["events"] = events
    obs = observations(events)
    for group, edge in zip(s["semantic_groups"], b["stages"]["lattice"]["edges"]):
        a, z = F(points[group["from"]]), F(points[group["to"]])
        active = [(o, min(o.end, z)-max(o.start, a)) for o in obs if o.start < z and a < o.end]
        states = {o.event_id: "spelling_unresolved" if o.pitch is None else "member" if o.pitch in group["members"] else "nonmember_not_confirmed_nct" for o, _ in active}
        group["event_states"] = deepcopy(states); edge["readings"][0]["event_states"] = deepcopy(states)
        group["objective_increment"] = {
            "total_note_time": rational(sum((dur for _, dur in active), F())),
            "raw_nonmember_note_time": rational(sum((dur for o, dur in active if states[o.event_id] == "nonmember_not_confirmed_nct"), F())),
            "spelling_unresolved_note_time": rational(sum((dur for o, dur in active if states[o.event_id] == "spelling_unresolved"), F())),
            "blocked_note_time": rational(F()), "optimistic_local_nct_potential_note_time": rational(F()),
        }
    return b, s


def manual_edge(gid, a, b, sig=C, emission=F(), attacks=frozenset()):
    return Edge(gid, a, b, F(a), F(b), sig, {"nonmember_exposure": emission}, attacks, (), (), {})


class ScoredDecoderTests(unittest.TestCase):
    def test_complete_triad_evidence(self):
        b, s = native(); problem = prepare(b, s); f = problem.edges[0].features
        self.assertEqual(f["nonmember_exposure"], 0); self.assertEqual(f["missing_member_fraction"], 0)
        self.assertEqual(f["missing_root"], 0)
        self.assertIsNone(f["consistent_voice_nct_explanation"])
        r = decode(problem); self.assertEqual(r["status"], "selected_untrained_hypothesis")
        self.assertTrue(r["exact_optimum_under_declared_score"])
        self.assertIsNone(r["selected"]["confidence"])
        self.assertFalse(r["selected"]["music_constraints_fully_validated"])

    def test_missing_members_are_not_fabricated_observations(self):
        b, s = native(events=[note("e", ("E", 0))]); e = prepare(b, s).edges[0]
        self.assertEqual(e.features["missing_member_fraction"], F(2, 3))
        self.assertEqual(e.features["missing_root"], 1)
        self.assertEqual(e.source_event_ids, ("e",))

    def test_unresolved_spelling_masks_presence(self):
        b, s = native(events=[note("micro", ("C", F(1, 2)))]); e = prepare(b, s).edges[0]
        self.assertIsNone(e.features["missing_member_fraction"])
        self.assertIsNone(e.features["missing_root"])
        self.assertEqual(e.features["unresolved_spelling_exposure"], 1)

    def test_nonmember_not_nct_exemption(self):
        b, s = native(events=[note("d", ("D", 0))])
        s["semantic_groups"][0]["objective_increment"]["optimistic_local_nct_potential_note_time"] = rational(F(2))
        e = prepare(b, s).edges[0]
        self.assertEqual(e.features["nonmember_exposure"], 1)
        self.assertIsNone(e.features["consistent_voice_nct_explanation"])

    def test_quarter_duration_exact_and_duplicate_octaves_time_accounted(self):
        b, s = native(events=[note("c", a=0, b=F(1, 3)), note("e", ("E", 0), 0, F(1, 3))])
        self.assertEqual(prepare(b, s).total_note_time, F(2, 3))

    def test_enharmonic_spelling_is_not_collapsed(self):
        b, s = native(events=[note("fb", ("F", -1))]); e = prepare(b, s).edges[0]
        self.assertEqual(e.features["nonmember_exposure"], 1)
        self.assertEqual(e.features["missing_member_fraction"], 1)

    def test_tie_continuation_is_not_attack(self):
        b, s = native(specs=((1, 2, C),), events=[note("c", a=0, b=2)])
        e = prepare(b, s).edges[0]
        self.assertNotIn(("C", 0), e.attack_spellings)
        self.assertEqual(e.source_event_ids, ("c",))

    def test_objective_corruption_rejected(self):
        b, s = native(); s["semantic_groups"][0]["objective_increment"]["total_note_time"] = rational(F(1))
        with self.assertRaisesRegex(ValueError, "observation_binding"):
            prepare(b, s)

    def test_consistently_corrupted_membership_is_still_rejected(self):
        b, s = native(); s["semantic_groups"][0]["event_states"]["c"] = "nonmember_not_confirmed_nct"
        b["stages"]["lattice"]["edges"][0]["readings"][0]["event_states"]["c"] = "nonmember_not_confirmed_nct"
        with self.assertRaisesRegex(ValueError, "membership_observation"):
            prepare(b, s)

    def test_duplicate_observation_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate_or_negative"):
            observations([note("c"), note("c")])

    def test_negative_duration_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate_or_negative"):
            observations([note("c", a=1, b=0)])

    def test_unsupported_lattice_abstention_preserved(self):
        b, s = native(); b["stages"]["lattice"] = {"status": "baseline_not_ready"}
        s.update(status="preserved_lattice_abstention", lattice_status="baseline_not_ready", semantic_groups=[])
        self.assertEqual(decode(prepare(b, s))["status"], "baseline_not_ready")

    def test_no_positive_sound_abstains(self):
        b, s = native(events=[]); self.assertEqual(decode(prepare(b, s))["status"], "no_positive_sounding_exposure")

    def test_zero_duration_notation_preserved_without_duration_support(self):
        b, s = native(events=[note("e", ("E", 0)), note("grace_c", a=1, b=1)])
        p = prepare(b, s); e = p.edges[0]
        self.assertEqual(p.zero_duration_event_ids, ("grace_c",))
        self.assertIn("grace_c", e.source_event_ids)
        self.assertEqual(p.total_note_time, 2)
        self.assertEqual(e.features["missing_root"], 1)
        self.assertEqual(e.features["missing_member_fraction"], F(2, 3))
        self.assertNotIn(("C", 0), e.attack_spellings)

    def test_zero_only_context_is_abstention_not_stretched_note(self):
        b, s = native(events=[note("grace_c", a=1, b=1)]); p = prepare(b, s)
        self.assertEqual(p.zero_duration_event_ids, ("grace_c",))
        self.assertEqual(decode(p)["status"], "no_positive_sounding_exposure")

    def test_unknown_root_preserved(self):
        sig = (None, C[1]); b, s = native(specs=((0, 2, sig),))
        r = decode(prepare(b, s)); self.assertIsNone(r["selected"]["segments"][0]["root_spelling"])
        self.assertIsNone(r["selected"]["segments"][0]["features"]["missing_root"])

    def test_previous_signature_state_is_required(self):
        # Cheap prefix C loses after a costly C->D; more costly prefix D wins.
        es = (manual_edge("c", 0, 1), manual_edge("d", 0, 1, D, F(1, 100)), manual_edge("end", 1, 2, D))
        p = Problem((F(0), F(1), F(2)), es, 2, F(1), "ready")
        r = decode(p)
        self.assertEqual([s["semantic_group_ref"] for s in r["selected"]["segments"]], ["d", "end"])
        q = decode(p, include_transitions=False)
        self.assertEqual([s["semantic_group_ref"] for s in q["selected"]["segments"]], ["c", "end"])

    def test_dag_matches_exhaustive_first_order_search(self):
        es = tuple(manual_edge(str(i)+str(j)+str(k), i, j, sig, F(i+j+k, 100), frozenset(sig[1]))
                   for i in range(3) for j in range(i+1, 4) for k, sig in enumerate((C, D)))
        p = Problem(tuple(map(F, range(4))), es, 3, F(1), "ready")
        all_paths = []
        def visit(pos, previous, cost, ids):
            if pos == 3:
                all_paths.append((cost, ids)); return
            if len(ids) >= 3:
                return
            for edge in es:
                if edge.start_index == pos:
                    visit(edge.end_index, edge.signature,
                          cost+feature_cost(edge.features, DEFAULT_WEIGHTS)+feature_cost(transition(previous, edge), DEFAULT_WEIGHTS),
                          ids+(edge.group_id,))
        visit(0, None, F(), ())
        r = decode(p)
        self.assertEqual(fraction_value(r["selected"]["score_cost"]), min(all_paths)[0])
        self.assertEqual(tuple(s["semantic_group_ref"] for s in r["selected"]["segments"]), min(all_paths)[1])

    def test_segment_cap_does_not_return_incomplete_prediction(self):
        p = Problem(tuple(map(F, (0, 1, 2))), (manual_edge("a", 0, 1), manual_edge("b", 1, 2)), 1, F(1), "ready")
        self.assertEqual(decode(p)["status"], "no_complete_path_under_segment_cap")

    def test_transition_budget_abstains_not_approximate_winner(self):
        b, s = native(specs=((0, 2, C), (0, 2, D)))
        r = decode(prepare(b, s), transition_budget=1)
        self.assertEqual(r["status"], "transition_budget_abstention"); self.assertIsNone(r["selected"])

    def test_fixed_tie_break_does_not_depend_on_inventory_order(self):
        b, s = native(specs=((0, 2, C), (0, 2, C)))
        p = prepare(b, s); left = decode(p)
        right = decode(Problem(p.points, tuple(reversed(p.edges)), p.max_segments, p.total_note_time, p.status))
        self.assertEqual(left["selected"], right["selected"])

    def test_retained_music_cannot_find_absent_path(self):
        b, s = native(); self.assertIsNone(retained_music(prepare(b, s), []))

    def test_signature_agreement_not_roman_accuracy(self):
        b, s = native(); path = evaluation_path(decode(prepare(b, s)))
        r = evaluate_selection(path, [cell()]); self.assertTrue(r["selected_hit"])
        self.assertEqual(r["semantic_boundary_exact"], {"matched": 0, "extra": 0, "missed": 0})

    def test_missing_prediction_stays_in_time_denominator(self):
        r = evaluate_selection(None, [cell(0, 1), cell(1, 2, D)])
        self.assertFalse(r["selected_hit"]); self.assertEqual(r["eligible_time"], rational(F(2)))
        self.assertEqual(r["semantic_boundary_exact"]["missed"], 1)

    def test_partial_reference_not_boundary_gold(self):
        r = evaluate_selection(None, [cell(0, 1), cell(1, 2, None)])
        self.assertIsNone(r["selected_hit"]); self.assertIsNone(r["semantic_boundary_exact"])

    def test_no_reference_argument_in_inference_interfaces(self):
        self.assertEqual(tuple(inspect.signature(prepare).parameters), ("bundle", "search"))
        self.assertNotIn("reference", inspect.signature(decode).parameters)

    def test_strict_weights_allow_signed_exact_but_not_float_or_unknown(self):
        weights = dict(DEFAULT_WEIGHTS); weights["missing_root"] = F(-1, 10)
        self.assertEqual(weights_contract(weights)["missing_root"], F(-1, 10))
        weights["missing_root"] = 0.1
        with self.assertRaises(ValueError):
            weights_contract(weights)
        with self.assertRaises(ValueError):
            weights_contract({})

    def test_training_gate_not_inferred_from_internal_use(self):
        entry = {"split": "train", "eligibility": {"automatic_training": False},
                 "rights": {"internal_research_use": True, "model_training_approved": False}}
        self.assertFalse(training_eligibility(entry)["eligible"])
        self.assertEqual(len(training_eligibility(entry)["reasons"]), 2)
        entry["eligibility"]["automatic_training"] = True; entry["rights"]["model_training_approved"] = True
        self.assertTrue(training_eligibility(entry)["eligible"])
        entry["split"] = "dev"; self.assertFalse(training_eligibility(entry)["eligible"])


def fraction_value(value):
    return F(value["numerator"], value["denominator"])


def physical_fixture(folder, reference=C, split="dev"):
    """Genuine gzip/observations, SYNTHETIC parent receipts (not corpus gold)."""
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    entry = {"manifest_entry_id": "m0", "score_sha256": "synthetic-score", "work_family_id": "family",
             "split": split, "rights": {"internal_research_use": True, "model_training_approved": False},
             "eligibility": {"automatic_training": False}}
    bundle, search = native()
    search["proposals"] = [{"proposal_id": "p0", "complete_context_path": True, "semantic_group_refs": ["g0"],
                            "path": [{"edge": 0, "reading": 0}],
                            "objective": search["semantic_groups"][0]["objective_increment"] | {"segment_count": 1}}]
    search["input_bundle_content_sha256"] = _hash(bundle)
    provenance = {"manifest_entry": entry}
    context = folder/"context.json.gz"; packet = folder/"search.json.gz"
    context.write_bytes(gzip.compress(json.dumps({"pair_id": "pair", "plan_index": 0, "provenance": provenance, "bundle": bundle}).encode()))
    packet.write_bytes(gzip.compress(json.dumps({"pair_id": "pair", "plan_index": 0, "sample": bundle["sample"],
        "provenance": provenance, "search": search, "source_labels_used": False,
        "input_bundle_content_sha256": _hash(bundle)}).encode()))
    evaluation = evaluate(paths_from_search(search, span(0, 2)), [cell(sig=reference)])
    row = {"pair_id": "pair", "plan_index": 0, "sample_id": "sample", "work_family_id": "family", "split": split,
           "sample_span": span(0, 2), "evaluation": evaluation, "reference_cells": [{"span": span(0, 2), "signature": reference}]}
    src = Path(__file__).resolve().parents[1]/"src/musicanote_harness"
    recall = folder/"recall.json"; lattice = folder/"lattice.json"
    recall.write_text(json.dumps({"complete": True, "source_labels_used_for_selection": False, "training_performed": False,
        "code_sha256": digest(src/"harmony_candidate_recall.py"), "package_manifest": [entry], "records": [row],
        "summary": recall_summary([row])}), encoding="utf-8")
    lattice.write_text(json.dumps({"complete": True, "training_performed": False, "records": [
        {k: row[k] for k in ("pair_id", "plan_index", "sample_id")} | {
            "search_artifact": str(packet), "search_artifact_sha256": digest(packet),
            "source_context_artifact": str(context), "source_context_sha256": digest(context),
            "diagnosis": {"outcome": "selected_correct" if reference == C else "local_spelled_signature_absent", "lattice_hit": reference == C}}],
        "input_hashes": {str(packet): digest(packet), str(context): digest(context)},
        "code_sha256": digest(src/"harmony_lattice_recall.py")}), encoding="utf-8")
    return recall, lattice, digest(recall), digest(lattice), packet


class ScoredTrialTests(unittest.TestCase):
    def test_physical_runner_outputs_and_preserves_pins(self):
        with TemporaryDirectory() as tmp:
            folder = Path(tmp); r, l, rs, ls, _ = physical_fixture(folder)
            result = run(r, l, folder/"out", rs, ls)
            self.assertEqual(result["summary"]["direct_joint_music"]["selected_correct_contexts"], 1)
            self.assertFalse(result["training_performed"]); self.assertFalse(result["production_modified"])
            self.assertFalse(result["training_policy_audit"][0]["eligible"])
            self.assertEqual(hashlib.sha256(r.read_bytes()).hexdigest(), rs)
            self.assertEqual(hashlib.sha256(l.read_bytes()).hexdigest(), ls)
            saved = json.loads((folder/"out/report.json").read_text(encoding="utf-8"))
            chosen = saved["records"][0]["selected_prediction"]
            total = sum((fraction_value(s["segment_cost"])+fraction_value(s["transition_cost"]) for s in chosen["segments"]), F())
            self.assertEqual(total, fraction_value(chosen["score_cost"]))
            with self.assertRaisesRegex(ValueError, "overwrite"):
                run(r, l, folder/"out", rs, ls)

    def test_frozen_artifact_change_rejected_before_output(self):
        with TemporaryDirectory() as tmp:
            folder = Path(tmp); r, l, rs, ls, p = physical_fixture(folder)
            p.write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "frozen_input_changed"):
                run(r, l, folder/"out", rs, ls)
            self.assertFalse((folder/"out").exists())

    def test_protected_split_cannot_be_inferred(self):
        with TemporaryDirectory() as tmp:
            folder = Path(tmp); r, l, rs, ls, _ = physical_fixture(folder, split="holdout")
            with self.assertRaisesRegex(ValueError, "protected_or_unassigned"):
                run(r, l, folder/"out", rs, ls)
            self.assertFalse((folder/"out").exists())

    def test_changed_reference_cannot_change_prediction(self):
        with TemporaryDirectory() as tmp:
            folder = Path(tmp); a = folder/"a"; b = folder/"b"; a.mkdir(); b.mkdir()
            r, l, rs, ls, _ = physical_fixture(a); first = run(r, l, a/"out", rs, ls)
            r, l, rs, ls, _ = physical_fixture(b, reference=D); second = run(r, l, b/"out", rs, ls)
            self.assertEqual(first["records"][0]["selected_prediction"], second["records"][0]["selected_prediction"])
            self.assertNotEqual(first["records"][0]["evaluations"], second["records"][0]["evaluations"])

    def test_empty_summary_is_unavailable_not_perfect(self):
        result = summarize([], "direct_joint_music")
        self.assertIsNone(result["selected_context_agreement"])
        self.assertIsNone(result["semantic_boundary_exact"]["f1"])


if __name__ == "__main__":
    unittest.main()
