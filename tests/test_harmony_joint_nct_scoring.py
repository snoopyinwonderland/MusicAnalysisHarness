from copy import deepcopy
from dataclasses import replace
from fractions import Fraction as F
import random
import unittest

from musicanote_harness import harmony_joint_nct_scoring as scoring
from musicanote_harness import harmony_component_support_scoring as prior
from musicanote_harness.harmony_progression_search import _hash
from test_harmony_bounded_recovery import fixture
from test_harmony_exact_frontier import problem
from test_harmony_functional_scoring import C,G,G7

EM=(("E",0),(("B",0),("E",0),("G",0)))
GM=(("G",0),(("B",-1),("D",-1),("G",0)))
EB=(("E",-1),(("B",-1),("E",-1),("G",0)))


def shared_bridge():
    return fixture([("C5",0,1,"lead"),("D5",1,F(5,4),"lead"),("E5",F(5,4),2,"lead"),
        ("E4",0,4,"inner"),("G4",0,4,"upper"),("C3",0,F(5,4),"bass"),("E3",F(5,4),4,"bass")])


class JointNCTTests(unittest.TestCase):
    def assess(self,ir=None,left=C,right=EM,arm="shared_support",start=0,boundary=F(5,4),**kw):
        graph,ev=problem(ir or shared_bridge());context=scoring.JointContext(ev,**kw)
        return context.assess(graph,F(start),F(boundary),left,right,arm),graph,ev,context

    def test_joint_selected_roles_and_two_shared_held_members(self):
        (value,rows),graph,_,_=self.assess()
        self.assertEqual(value,F(1,4)/graph.total_note_time)
        self.assertEqual(rows[0]["status"],"conditional_support")
        self.assertEqual(rows[0]["shared_held_spellings"],[("E",0),("G",0)])
        self.assertFalse(rows[0]["confirmed_nct"])
        self.assertFalse(rows[0]["raw_nonmember_cost_removed"])
        self.assertTrue(rows[0]["arrival_only_membership"])

    def test_actual_right_signature_not_borrowed_left_membership(self):
        (value,rows),_,_,_=self.assess(right=G,arm="selected_roles")
        self.assertEqual(value,0)
        self.assertIn("arrival_not_selected_right_member",rows[0]["withheld_reasons"])

    def test_wrong_competitor_only_one_shared_sustain(self):
        ir=fixture([("Db5",0,1,"lead"),("C5",1,F(5,4),"lead"),("Bb4",F(5,4),2,"lead"),
            ("G4",0,4,"inner"),("Db4",0,4,"upper")])
        self.assertGreater(self.assess(ir,GM,EB,"selected_roles")[0][0],0)
        (value,rows),_,_,_=self.assess(ir,GM,EB)
        self.assertEqual(value,0)
        self.assertIn("fewer_than_two_actual_shared_members_at_arrival",rows[0]["withheld_reasons"])

    def test_preparation_outside_selected_left_run_is_not_borrowed(self):
        self.assertEqual(self.assess(start=F(1,2))[0],(F(),[]))

    def test_middle_not_at_this_transition_is_not_credited(self):
        self.assertEqual(self.assess(boundary=F(3,2))[0],(F(),[]))

    def test_middle_is_member_not_nct(self):
        wide=(C[0],tuple(sorted(C[1]+(("D",0),))))
        self.assertEqual(self.assess(left=wide)[0],(F(),[]))

    def test_held_members_must_really_continue_into_arrival(self):
        ir=fixture([("C5",0,1,"lead"),("D5",1,F(5,4),"lead"),("E5",F(5,4),2,"lead"),
            ("E4",0,F(5,4),"inner"),("G4",0,F(5,4),"upper")])
        self.assertGreater(self.assess(ir,arm="selected_roles")[0][0],0)
        self.assertEqual(self.assess(ir)[0][0],0)

    def test_doubling_and_arpeggiation_not_two_sustained_members(self):
        for support in ([('E4',0,4,'i'),('E3',0,4,'j')],
                        [('E4',0,1,'i'),('G4',1,4,'j')]):
            ir=fixture([('C5',0,1,'l'),('D5',1,F(5,4),'l'),('E5',F(5,4),2,'l')]+support)
            self.assertEqual(self.assess(ir)[0],(F(),[]))

    def test_repeat_grace_clock_withhold_and_history_gate_consumed(self):
        self.assertEqual(self.assess(context_barriers=(F(1),))[0],(F(),[]))
        grace={"part_id":"p1","voice_id":"v-lead","global_onset_quarter":{"numerator":1,"denominator":1}}
        graph,ev=problem(shared_bridge());lane=scoring.JointContext(ev).step_candidates[0][0]['identity']
        grace['part_id'],grace['voice_id']=lane
        self.assertEqual(self.assess(grace_notes=(grace,))[0],(F(),[]))
        calls=[]
        (value,rows),_,_,_=self.assess(history_gate=lambda a,b: calls.append((a,b)) or False)
        self.assertEqual(value,0);self.assertEqual(len(calls),1)
        self.assertIn("source_clock_context_withheld",rows[0]["withheld_reasons"])

    def test_spelling_not_enharmonic_and_unknown_members_not_invented(self):
        right=(EM[0],tuple(sorted((("B",0),("F",-1),("G",0)))))
        self.assertEqual(self.assess(right=right)[0][0],0)

    def test_context_memoization_does_not_skip_required_gate(self):
        calls=[]
        (_, _),graph,_,context=self.assess(history_gate=lambda a,b:calls.append((a,b)) or True)
        context.assess(graph,F(),F(5,4),C,EM,"shared_support")
        self.assertEqual(len(calls),1)

    def test_control_scores_and_selection_equal_existing_module(self):
        for ir in (shared_bridge(),fixture(),fixture([('G3',0,4,'b'),('B3',0,4,'i'),('F4',0,4,'j')])):
            graph,ev=problem(ir);old=prior.decode(graph,ev,arm='control');actual=scoring.decode(graph,ev,arm='control')
            self.assertEqual(actual['status'],old['status'])
            self.assertEqual([(s['span'],s['root_spelling'],s['members']) for s in actual['selected']['segments']],
                             [(s['span'],s['root_spelling'],s['members']) for s in old['selected']['segments']])
            self.assertEqual(actual['selected']['score_cost'],old['selected']['score_cost'])

    def test_joint_credit_is_scored_once_across_raw_edge_subdivisions(self):
        graph,ev=problem(shared_bridge());by={(e.start,e.end,e.signature):e for e in graph.edges}
        def eid(a,b,sig):return by[F(a),F(b),sig].group_id
        for ids in ((eid(0,F(5,4),C),eid(F(5,4),4,EM)),
                    (eid(0,1,C),eid(1,F(5,4),C),eid(F(5,4),2,EM),eid(2,4,EM))):
            base=scoring.score_path(graph,ev,ids,arm='control')
            value=scoring.score_path(graph,ev,ids,arm='shared_support')
            self.assertEqual(value-base,scoring.STEP_WEIGHT*F(1,4)/graph.total_note_time)
            rows=scoring.path_observations(graph,ev,ids,arm='shared_support')
            self.assertEqual(sum(r['status']=='conditional_support' for r in rows),1)

    def test_exhaustive_joint_optimum_and_lex_tie_all_arms(self):
        graph,ev=problem(shared_bridge());rng=random.Random(6601)
        edges=tuple(e for e in graph.edges if e.signature in (C,EM,G))
        for _ in range(10):
            tiny=replace(graph,edges=tuple(e for e in edges if rng.random()<.7),max_segments=rng.choice((2,3,4)))
            for arm in scoring.ARMS:
                paths=[]
                def visit(i,ids):
                    if i==len(tiny.points)-1:paths.append((scoring.score_path(tiny,ev,ids,arm=arm),ids));return
                    if len(ids)>=tiny.max_segments:return
                    for e in tiny.edges:
                        if e.start_index==i:visit(e.end_index,ids+(e.group_id,))
                visit(0,());actual=scoring.decode(tiny,ev,arm=arm)
                if not paths:self.assertIsNone(actual['selected']);continue
                selected=actual['selected']
                self.assertEqual((F(**selected['score_cost']),tuple(s['semantic_group_ref'] for s in selected['segments'])),min(paths))

    def test_source_and_original_module_unchanged(self):
        ir=shared_bridge();saved=deepcopy(ir);graph,ev=problem(ir)
        old=prior.decode(graph,ev,arm='control')
        result=scoring.decode(graph,ev)
        self.assertEqual(saved,ir);self.assertEqual(old,prior.decode(graph,ev,arm='control'))
        self.assertIsNone(result['selected']['confidence'])
        self.assertFalse(result['selected']['human_validated'])

    def test_disabled_evidence_has_no_joint_credit(self):
        graph,ev=problem(shared_bridge())
        for arm in scoring.ARMS:
            selected=scoring.decode(graph,ev,arm=arm,functional_evidence=False)['selected']
            ids=tuple(s['semantic_group_ref'] for s in selected['segments'])
            self.assertEqual(selected['joint_nct_score_cost'],{'numerator':0,'denominator':1})
            self.assertEqual(scoring.score_path(graph,ev,ids,arm=arm,functional_evidence=False),F(**selected['score_cost']))

    def test_invalid_arm_budget_and_problem(self):
        graph,ev=problem()
        with self.assertRaisesRegex(ValueError,'unknown_joint_nct_arm'):scoring.decode(graph,ev,arm='x')
        with self.assertRaisesRegex(ValueError,'invalid_transition_budget'):scoring.decode(graph,ev,transition_budget=True)
        self.assertIsNone(scoring.decode(graph,ev,transition_budget=1)['selected'])
        self.assertEqual(scoring.decode(replace(graph,status='bad_source'),ev)['status'],'bad_source')
        with self.assertRaisesRegex(ValueError,'invalid_frontier_problem'):scoring.decode(replace(graph,total_note_time=F()),ev)


if __name__=='__main__':unittest.main()
