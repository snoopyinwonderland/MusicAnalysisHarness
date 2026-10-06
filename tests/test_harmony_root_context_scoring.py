from copy import deepcopy
from dataclasses import replace
from fractions import Fraction as F
import random
import unittest

from musicanote_harness import harmony_root_context_scoring as context
from musicanote_harness import harmony_temporal_scoring as temporal
from musicanote_harness import harmony_bounded_recovery as bounded
from musicanote_harness.harmony_evidence_scoring import run_features
from musicanote_harness.formal_ir import q
from test_harmony_bounded_recovery import fixture
from test_harmony_exact_frontier import problem
from test_harmony_functional_scoring import C, G


def returning(chordal=False):
    bass = [("C3", 0, 1, "bass"), ("E3", 1, 2, "bass"), ("G3", 2, 3, "bass"), ("C3", 3, 4, "bass")]
    if chordal: bass = [("C3", 0, 1, "bass"), ("E3", 1, 3, "bass"), ("G3", 1, 3, "bass"), ("C3", 3, 4, "bass")]
    return fixture(bass+[("E4", 0, 4, "inner"), ("G4", 0, 4, "upper")])


class RootContextTests(unittest.TestCase):
    def value(self, ir=None, a=1, b=4, sig=C, grace_notes=()):
        graph, ev = problem(ir or returning())
        ctx = context.RootReturnContext(ev, grace_notes)
        return context.context_delay(graph, ev.source, ctx, F(a), F(b), sig), graph, ev, ctx

    def test_prior_lowest_root_return_softens_not_erases_delay(self):
        (value, receipt), graph, ev, _ = self.value()
        self.assertEqual(value, F(1, 4)); self.assertEqual(temporal.deferred_root(graph, ev.source, F(1), F(4), C)[0], F(1, 2))
        self.assertFalse(receipt[-1]["earlier_root_was_sounding_in_run"])
        self.assertFalse(receipt[-1]["nonmember_cost_removed"])
        self.assertEqual(receipt[-1]["prefix_distinct_nonroot_members"], [("E", 0), ("G", 0)])

    def test_equal_onset_duration_chord_groups_can_bridge(self):
        (value, receipt), _, _, _ = self.value(returning(True))
        self.assertEqual(value, F(1, 4)); self.assertEqual(receipt[-1]["conditional_step_patterns"], [])

    def test_short_contiguous_passing_bass_with_held_upper_members(self):
        ir = fixture([("C3", 0, F(3,4), "bass"), ("D3", F(3,4), 1, "bass"),
            ("E3", 1, F(3,2), "bass"), ("D3", F(3,2), F(7,4), "bass"), ("C3", F(7,4), 4, "bass"),
            ("E4", 0, 4, "inner"), ("G4", 0, 4, "upper")])
        (value, receipt), _, _, _ = self.value(ir)
        self.assertEqual(value, F(3,32)); self.assertEqual(len(receipt[-1]["conditional_step_patterns"]), 2)
        self.assertFalse(receipt[-1]["conditional_step_patterns"][0]["confirmed_nct"])

    def test_no_prior_root_keeps_raw_penalty(self):
        ir = returning(); ir["sounding_events"] = ir["sounding_events"][1:]; ir["note_events"] = ir["note_events"][1:]
        (value, receipt), _, _, _ = self.value(ir)
        self.assertEqual(value, F(1,2)); self.assertEqual(len(receipt), 1)

    def test_different_source_lane_not_silent_voice_match(self):
        ir = returning(); ir["note_events"][0]["voice_id"] = "other-lane"
        (value, receipt), _, _, _ = self.value(ir)
        self.assertEqual(value, F(1,2)); self.assertEqual(len(receipt), 1)

    def test_rest_gap_rejects_context_credit(self):
        ir = fixture([("C3", 0, F(3,4), "bass"), ("E3", 1, 3, "bass"), ("C3", 3, 4, "bass"),
                      ("E4", 0, 4, "inner"), ("G4", 0, 4, "upper")])
        self.assertEqual(self.value(ir)[0][0], F(1,2))

    def test_unequal_duration_overlap_is_not_unique_bridge(self):
        ir = returning(True); extra = fixture([("G2", F(1,2), 2, "bass")])
        ir["note_events"] += extra["note_events"]; ir["sounding_events"] += extra["sounding_events"]
        # fixture uses deterministic IDs; use disjoint IDs without dropping the overlap.
        for n in ir["note_events"][-1:]: n["note_id"] = "overlap-note"
        s = ir["sounding_events"][-1]; s.update(sounding_event_id="overlap-sound", source_note_ids=["overlap-note"], attack_note_id="overlap-note")
        self.assertEqual(self.value(ir)[0][0], F(1,2))

    def test_incompatible_or_long_nonmember_not_erased(self):
        ir = fixture([("C3", 0, 1, "bass"), ("F#3", 1, 3, "bass"), ("C3", 3, 4, "bass"),
                      ("E4", 0, 4, "inner"), ("G4", 0, 4, "upper")])
        self.assertEqual(self.value(ir)[0][0], F(1,2))

    def test_grace_barrier_retained_without_performed_timing(self):
        _, _, ev, _ = self.value(); lane = ev.rows[0]["identity"]
        grace = {"part_id": lane[0], "voice_id": lane[1], "global_onset_quarter": q(2)}
        self.assertEqual(self.value(grace_notes=[grace])[0][0], F(1,2))

    def test_unknown_meter_no_context_credit_and_changing_meter_priority(self):
        (_, _), graph, ev, _ = self.value()
        ev.source.measures = ((F(0), (4,4), 0), (F(1), (3,8), 0)); ev.source._measure_times = (F(0),F(1)); ev.source._metric_cache.clear()
        # Change the prior anchor's end to 0? No: the real endpoint 1 qualifies under both meters.
        self.assertTrue(context.RootReturnContext(ev).support(F(1),F(3),C))
        ev.source.measures = (); ev.source._measure_times = (); ev.source._metric_cache.clear()
        value, _ = context.context_delay(graph, ev.source, context.RootReturnContext(ev), F(1),F(4),C)
        self.assertEqual(value,F(1,2))

    def test_rootless_unknown_and_root_first_keep_original_contract(self):
        (_, _), graph, ev, ctx = self.value()
        for sig in (G, (None,C[1])):
            self.assertEqual(context.context_delay(graph,ev.source,ctx,F(0),F(1),sig)[0], temporal.deferred_root(graph,ev.source,F(0),F(1),sig)[0])
        self.assertEqual(context.context_delay(graph,ev.source,ctx,F(0),F(4),C)[0], 0)

    def test_prior_high_root_is_not_lowest_root_anchor(self):
        ir = fixture([("C4",0,1,"bass"),("E3",1,3,"bass"),("C3",3,4,"bass"),
            ("G2",0,1,"low"),("E4",0,4,"inner"),("G4",0,4,"upper")])
        self.assertEqual(self.value(ir)[0][0],F(1,2))

    def test_context_never_changes_raw_members_and_source_objects(self):
        ir = returning(); before = deepcopy(ir); (_, _),graph,ev,ctx = self.value(ir)
        raw,_ = run_features(graph,ev.source,F(1),F(4),C)
        _,Index,run = context.decoder(graph,ev,ctx)
        values,_ = run(graph,ev.source,F(1),F(4),C)
        self.assertEqual({k:values[k] for k in raw},raw); self.assertEqual(ir,before)

    def test_repeat_or_ending_history_barrier_withholds_credit(self):
        (_, _),graph,ev,_ = self.value()
        ctx=context.RootReturnContext(ev,context_barriers=[F(1)])
        self.assertEqual(context.context_delay(graph,ev.source,ctx,F(1),F(4),C)[0],F(1,2))

    def test_history_source_clock_rejection_retains_old_feature(self):
        (_, _),graph,ev,_=self.value()
        ctx=context.RootReturnContext(ev,history_gate=lambda a,b:False)
        self.assertEqual(context.context_delay(graph,ev.source,ctx,F(1),F(4),C)[0],F(1,2))

    def test_spelling_not_enharmonic_history_lookup(self):
        ir=returning(); p={"spelling":"B#2","step":"B","alter":q(1),"octave":2,"midi_pitch":48,"pitch_class":0}
        ir["sounding_events"][0]["pitch"]=p; ir["note_events"][0]["concert_pitch"]=deepcopy(p)
        self.assertEqual(self.value(ir)[0][0],F(1,2))

    def test_single_member_prefix_is_not_harmonic_support(self):
        ir=fixture([("C3",0,1,"bass"),("E3",1,3,"bass"),("C3",3,4,"bass")])
        self.assertEqual(self.value(ir)[0][0],F(1,2))

    def test_stale_root_cannot_be_borrowed(self):
        ir=fixture([("C3",0,F(1,2),"bass"),("E3",F(1,2),3,"bass"),("C3",3,4,"bass"),
                    ("E4",0,4,"inner"),("G4",0,4,"upper")])
        self.assertEqual(self.value(ir,a=2)[0][0],F(1,4))

    def test_invalid_lane_clock_is_not_filtered_to_make_good_chain(self):
        (_, _),graph,ev,_=self.value()
        ev.rows=tuple(dict(r,clock_valid=False) if r["start"]==1 else r for r in ev.rows)
        ctx=context.RootReturnContext(ev)
        self.assertEqual(context.context_delay(graph,ev.source,ctx,F(1),F(4),C)[0],F(1,2))

    def test_index_unindexed_all_intervals_signatures(self):
        (_, _),graph,ev,ctx = self.value(); _,Index,run = context.decoder(graph,ev,ctx); index=Index(graph,ev.source)
        for i,a in enumerate(graph.points):
            for b in graph.points[i+1:]:
                for sig in (C,G,(None,C[1])):
                    self.assertEqual(index.features(a,b,sig),run(graph,ev.source,a,b,sig))

    def test_all_arms_exhaustive_optimum_and_lex_path(self):
        graph,ev=problem(returning()); choices=tuple(e for e in graph.edges if e.signature in (C,G)); rng=random.Random(6491)
        for _ in range(12):
            tiny=replace(graph,edges=tuple(e for e in choices if rng.random()<.65),max_segments=rng.choice((1,2,3,4)))
            for arm in context.ARMS:
                paths=[]
                def visit(i,ids):
                    if i==len(tiny.points)-1: paths.append((context.score_path(tiny,ev,ids,arm=arm),ids)); return
                    if len(ids)>=tiny.max_segments:return
                    for e in tiny.edges:
                        if e.start_index==i:visit(e.end_index,ids+(e.group_id,))
                visit(0,()); selected=context.decode(tiny,ev,arm=arm)["selected"]
                if not paths:self.assertIsNone(selected);continue
                self.assertEqual((F(**selected["score_cost"]),tuple(s["semantic_group_ref"] for s in selected["segments"])),min(paths))

    def test_invalid_arm_budget_source_failure_and_old_global_unchanged(self):
        graph,ev=problem(); old=temporal.functional.run_features
        with self.assertRaisesRegex(ValueError,"unknown_root_context_arm"):context.decode(graph,ev,arm="invented")
        with self.assertRaisesRegex(ValueError,"invalid_transition_budget"):context.decode(graph,ev,transition_budget=True)
        self.assertIsNone(context.decode(graph,ev,transition_budget=1)["selected"])
        self.assertEqual(context.decode(replace(graph,status="source_failure"),ev)["status"],"source_failure")
        context.decode(graph,ev,functional_evidence=False); self.assertIs(temporal.functional.run_features,old)


if __name__ == "__main__": unittest.main()
