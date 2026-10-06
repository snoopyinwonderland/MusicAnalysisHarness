from copy import deepcopy
from dataclasses import replace
from fractions import Fraction as F
import random
import unittest

from musicanote_harness import harmony_component_support_scoring as scoring
from musicanote_harness import harmony_root_context_scoring as prior
from musicanote_harness.harmony_evidence_scoring import run_features
from musicanote_harness.harmony_progression_search import _hash
from musicanote_harness.formal_ir import q
from test_harmony_bounded_recovery import fixture
from test_harmony_exact_frontier import problem
from test_harmony_functional_scoring import C,G,G7,F64


def bridge():
    return fixture([("C3",0,1,"bass"),("D3",1,F(5,4),"bass"),("E3",F(5,4),2,"bass"),
        ("C4",0,4,"inner"),("G4",0,4,"upper")])


class ComponentSupportTests(unittest.TestCase):
    def value(self,ir=None,a=1,b=2,sig=C,**kwargs):
        graph,ev = problem(ir or bridge())
        context = scoring.ComponentContext(ev,**kwargs)
        return scoring.features(graph,ev.source,context,F(a),F(b),sig),graph,ev,context

    def test_defining_third_perfect_fifth_and_unknown_masks(self):
        self.assertEqual(scoring.defining_members(C),(("E",0),))
        self.assertEqual(set(scoring.defining_members(G7)),{("B",0),("F",0)})
        self.assertIsNone(scoring.defining_members((None,C[1])))
        self.assertIsNone(scoring.defining_members(F64))

    def test_augmented_diminished_fifths_define_quality(self):
        for quality in ("o","+","o7","%7","+M7"):
            chord=scoring.chord(("C",0),quality)
            sig=(("C",0),tuple(sorted(map(tuple,chord["members"]))))
            self.assertIn(tuple(chord["members"][2]),scoring.defining_members(sig))

    def test_absent_third_soft_cost_not_chord_ban(self):
        ir=fixture([("C3",0,4,"bass"),("G4",0,4,"upper")])
        (values,details),graph,ev,_ = self.value(ir,a=0,b=4)
        self.assertEqual(values["unobserved_defining_member_exposure"],1)
        self.assertFalse(details[0]["omission_prohibited"])
        self.assertIsNotNone(scoring.decode(graph,ev)["selected"])

    def test_late_third_is_observed_in_arpeggiated_union(self):
        ir=fixture([("C3",0,1,"bass"),("G3",1,2,"bass"),("E3",2,4,"bass")])
        values=self.value(ir,a=0,b=4)[0][0]
        self.assertEqual(values["unobserved_defining_member_exposure"],0)

    def test_never_observed_seventh_not_supported_by_major_triad(self):
        ir=fixture([("G3",0,4,"bass"),("B3",0,4,"inner"),("D4",0,4,"upper")])
        self.assertEqual(self.value(ir,a=0,b=4,sig=G7)[0][0]["unobserved_defining_member_exposure"],F(1,2))

    def test_source_spelling_not_midi_equivalence(self):
        ir=fixture([("C3",0,4,"bass"),("G3",0,4,"inner"),("Fb4",0,4,"upper")])
        self.assertEqual(self.value(ir,a=0,b=4)[0][0]["unobserved_defining_member_exposure"],1)

    def test_full_source_step_and_two_held_members(self):
        (values,details),graph,_,_=self.value()
        self.assertGreater(values["held_member_step_support_exposure"],0)
        receipt=details[-1]
        self.assertEqual(receipt["kind"],"held_member_cross_run_passing_like")
        self.assertEqual(receipt["supporting_distinct_spellings"],[("C",0),("G",0)])
        self.assertEqual(receipt["credited_span"],{"start":q(1),"end":q(F(5,4))})
        self.assertFalse(receipt["confirmed_nct"])
        self.assertFalse(receipt["raw_nonmember_cost_removed"])

    def test_neighbor_geometry_also_supported(self):
        ir=bridge();ir["sounding_events"][2]["pitch"]=deepcopy(ir["sounding_events"][0]["pitch"])
        ir["note_events"][2]["concert_pitch"]=deepcopy(ir["sounding_events"][0]["pitch"])
        self.assertEqual(self.value(ir)[0][1][-1]["kind"],"held_member_cross_run_neighbor_like")

    def test_same_run_does_not_double_count_existing_credit(self):
        self.assertEqual(self.value(a=0,b=4)[0][0]["held_member_step_support_exposure"],0)

    def test_current_run_overlap_only_and_no_exemption(self):
        (values,_),graph,ev,context=self.value(a=F(9,8),b=2)
        self.assertEqual(values["held_member_step_support_exposure"],F(1,8)/graph.total_note_time)
        base,_=run_features(graph,ev.source,F(9,8),F(2),C)
        run=scoring.decoder(graph,ev,context,"combined")[2]
        actual,_=run(graph,ev.source,F(9,8),F(2),C)
        self.assertEqual({k:actual[k] for k in base},base)

    def test_single_pitch_doubling_not_two_held_members(self):
        ir=fixture([("C3",0,1,"bass"),("D3",1,F(5,4),"bass"),("E3",F(5,4),2,"bass"),
            ("G4",0,4,"inner"),("G5",0,4,"upper")])
        self.assertEqual(self.value(ir)[0][0]["held_member_step_support_exposure"],0)

    def test_arpeggiated_union_does_not_invent_sustained_members(self):
        ir=fixture([("C3",0,1,"bass"),("D3",1,F(5,4),"bass"),("E3",F(5,4),2,"bass"),
            ("C4",0,1,"inner"),("G4",F(5,4),4,"upper")])
        self.assertEqual(self.value(ir)[0][0]["held_member_step_support_exposure"],0)

    def test_rest_gap_withholds_step_credit(self):
        ir=bridge();ir["note_events"][0]["notated_duration_quarter"]=q(F(3,4))
        ir["sounding_events"][0].update(span={"start":q(0),"end":q(F(3,4))},sounding_duration=q(F(3,4)))
        self.assertEqual(self.value(ir)[0][0]["held_member_step_support_exposure"],0)

    def test_long_nonmember_not_short_ornament(self):
        ir=fixture([("C3",0,1,"bass"),("D3",1,2,"bass"),("E3",2,4,"bass"),
            ("C4",0,4,"inner"),("G4",0,4,"upper")])
        self.assertEqual(self.value(ir)[0][0]["held_member_step_support_exposure"],0)

    def test_repeat_and_clock_barriers(self):
        for kwargs in ({"context_barriers":[F(1)]},{"history_gate":lambda a,b:False}):
            self.assertEqual(self.value(**kwargs)[0][0]["held_member_step_support_exposure"],0)

    def test_grace_barrier(self):
        _,_,ev,_=self.value();lane=ev.rows[0]["identity"]
        grace={"part_id":lane[0],"voice_id":lane[1],"global_onset_quarter":q(F(9,8))}
        self.assertEqual(self.value(grace_notes=[grace])[0][0]["held_member_step_support_exposure"],0)

    def test_unknown_meter_withholds_step(self):
        _,graph,ev,_=self.value();ev.source.measures=();ev.source._measure_times=();ev.source._metric_cache.clear()
        context=scoring.ComponentContext(ev)
        self.assertEqual(scoring.features(graph,ev.source,context,F(1),F(2),C)[0]["held_member_step_support_exposure"],0)

    def test_invalid_clock_and_cross_voice_do_not_receive_support(self):
        _,graph,ev,_=self.value()
        ev.rows=tuple(dict(r,clock_valid=False) if r["start"]==1 else r for r in ev.rows)
        context=scoring.ComponentContext(ev)
        self.assertEqual(scoring.features(graph,ev.source,context,F(1),F(2),C)[0]["held_member_step_support_exposure"],0)

    def test_unresolved_spelling_preserves_none(self):
        _,graph,ev,context=self.value()
        ev.source.events=tuple(replace(e,pitch=None) if e.start==1 else e for e in ev.source.events)
        values,_=scoring.features(graph,ev.source,context,F(1),F(2),C)
        self.assertEqual(values,{"unobserved_defining_member_exposure":None,"held_member_step_support_exposure":None})

    def test_all_intervals_index_matches_direct_scanner(self):
        _,graph,ev,context=self.value()
        for arm in scoring.ARMS:
            _,Index,run,_,_=scoring.decoder(graph,ev,context,arm);index=Index(graph,ev.source)
            for i,a in enumerate(graph.points):
                for b in graph.points[i+1:]:
                    for sig in (C,G,G7,F64,(None,C[1])):
                        self.assertEqual(index.features(a,b,sig),run(graph,ev.source,a,b,sig))

    def test_control_costs_match_prior_with_same_global_functions(self):
        _,graph,ev,_=self.value();before=(prior.temporal.functional.run_features,prior.temporal.frontier.RunIndex)
        old=prior.decode(graph,ev);new=scoring.decode(graph,ev,arm="control")
        self.assertEqual(old["selected"]["score_cost"],new["selected"]["score_cost"])
        self.assertEqual([s["semantic_group_ref"] for s in old["selected"]["segments"]],[s["semantic_group_ref"] for s in new["selected"]["segments"]])
        self.assertEqual(before,(prior.temporal.functional.run_features,prior.temporal.frontier.RunIndex))

    def test_source_not_mutated_or_labels_consumed(self):
        ir=bridge();before=_hash(ir);_,graph,ev,_=self.value(ir)
        result=scoring.decode(graph,ev)
        self.assertEqual(_hash(ir),before);self.assertFalse(result["component_support_contract"]["source_labels_used"])

    def test_history_gate_is_lazy_but_mandatory_for_consumed_credit(self):
        _,graph,ev,_=self.value();calls=[]
        context=scoring.ComponentContext(ev,history_gate=lambda a,b:calls.append((a,b)) or True)
        self.assertEqual(calls,[])
        # Already-credited full-run pattern does not need extra context gate.
        scoring.features(graph,ev.source,context,F(0),F(4),C)
        self.assertEqual(calls,[])
        self.assertGreater(scoring.features(graph,ev.source,context,F(1),F(2),C)[0]["held_member_step_support_exposure"],0)
        self.assertEqual(len(calls),1)
        scoring.features(graph,ev.source,context,F(1),F(2),C)
        self.assertEqual(len(calls),1)

    def test_exhaustive_paths_all_arms_and_lexicographic_ties(self):
        _,graph,ev,_=self.value();rng=random.Random(6501)
        edges=tuple(e for e in graph.edges if e.signature in (C,G))
        for _ in range(8):
            tiny=replace(graph,edges=tuple(e for e in edges if rng.random()<.65),max_segments=rng.choice((1,2,3)))
            for arm in scoring.ARMS:
                paths=[]
                def visit(i,ids):
                    if i==len(tiny.points)-1:paths.append((scoring.score_path(tiny,ev,ids,arm=arm),ids));return
                    if len(ids)>=tiny.max_segments:return
                    for e in tiny.edges:
                        if e.start_index==i:visit(e.end_index,ids+(e.group_id,))
                visit(0,());result=scoring.decode(tiny,ev,arm=arm)
                if not paths:self.assertIsNone(result["selected"]);continue
                selected=result["selected"]
                self.assertEqual((F(**selected["score_cost"]),tuple(s["semantic_group_ref"] for s in selected["segments"])),min(paths))

    def test_invalid_arm_budget_and_source_failure(self):
        _,graph,ev,_=self.value()
        with self.assertRaisesRegex(ValueError,"unknown_component_support_arm"):scoring.decode(graph,ev,arm="invented")
        with self.assertRaisesRegex(ValueError,"invalid_transition_budget"):scoring.decode(graph,ev,transition_budget=True)
        self.assertIsNone(scoring.decode(graph,ev,transition_budget=1)["selected"])
        self.assertEqual(scoring.decode(replace(graph,status="source_failure"),ev)["status"],"source_failure")


if __name__=="__main__":unittest.main()
