from copy import deepcopy
from fractions import Fraction as F
import unittest

from test_harmony_bounded_recovery import fixture
from musicanote_harness.harmony_whole_score_diagnosis import evidence, graph, fixed_receipt, project_baseline
from musicanote_harness.harmony_whole_score import model_weights
from musicanote_harness.harmony_evidence_scoring import run_features
from musicanote_harness.harmony_scored_decoder import Problem

C=(('C',0),(('C',0),('E',0),('G',0)))


def setup():
    ir=fixture()
    ev,points,pages,args=evidence(ir,F(4))
    path=[]
    for a,b in zip(points,points[1:]):
        active=sorted(e.event_id for e in ev.source.events if e.start<b and a<e.end)
        path.append(dict(start=str(a),end=str(b),signature=C,source_event_ids=active,blockers=[]))
    return ev,points,args,path


class DiagnosisTests(unittest.TestCase):
    def test_replay_is_complete_and_preserves_cost(self):
        ev,points,args,path=setup();before=deepcopy(path)
        r=fixed_receipt(graph(ev,points,path),ev,args,model_weights())
        self.assertEqual(r['run_count'],1)
        self.assertEqual(path,before)
        self.assertEqual(sum(map(F,r['term_costs'].values()),F()),F(r['cost']))

    def test_missing_or_changed_source_refs_are_rejected(self):
        ev,points,args,path=setup();path[0]['source_event_ids']=[]
        with self.assertRaisesRegex(ValueError,'source_event_refs'):graph(ev,points,path)
        with self.assertRaisesRegex(ValueError,'incomplete'):graph(ev,points,path[:-1])

    def test_exact_unique_baseline_projection_is_counterfactual(self):
        ev,points,args,path=setup()
        projected,r=project_baseline(path,[dict(start='0',end='4',root_pc=0,pcs=[0,4,7])],ev)
        self.assertIsNotNone(projected);self.assertEqual(r['issues'],[])
        self.assertIn('unverified',r['graph_reachability'])
        self.assertEqual(projected[0]['signature'],C)

    def test_active_gap_not_filled(self):
        ev,points,args,path=setup()
        projected,r=project_baseline(path,[],ev)
        self.assertIsNone(projected);self.assertTrue(r['issues'])

    def test_label_change_inside_cell_not_rounded(self):
        ev,points,args,path=setup()
        spans=[dict(start='0',end='1/2',root_pc=0,pcs=[0,4,7]),
               dict(start='1/2',end='4',root_pc=7,pcs=[7,11,2])]
        projected,r=project_baseline(path,spans,ev)
        self.assertIsNone(projected)
        self.assertEqual(r['issues'][0]['issue'],'gap_or_label_change_inside_atomic_cell')

    def test_unsupported_pc_set_not_converted_to_fake_triad(self):
        ev,points,args,path=setup()
        projected,r=project_baseline(path,[dict(start='0',end='4',root_pc=0,pcs=[0,2,4,7])],ev)
        self.assertIsNone(projected)
        self.assertEqual(r['issues'][0]['options'],0)

    def test_expanded_shape_has_unavailable_roles_not_known_zero(self):
        ev,points,args,path=setup()
        expanded=(('C',0),(('B',-1),('C',0),('D',0),('E',0),('G',0)))
        for row in path:row['signature']=expanded
        r=fixed_receipt(graph(ev,points,path),ev,args,model_weights())
        self.assertFalse(r['aggregate_availability']['absent_third_exposure'])
        self.assertEqual(r['unavailable_runs']['absent_third_exposure'],1)
        self.assertEqual(r['term_costs']['absent_third_exposure'],'0')

    def test_unrelated_scope_length_dilutes_fit_not_run_count(self):
        ev,points,args,path=setup()
        a=Problem(points,(),3,F(16),'ready')
        b=Problem((F(0),F(8)),(),1,F(32),'ready')
        x,_=run_features(a,ev.source,F(0),F(4),C)
        y,_=run_features(b,ev.source,F(0),F(4),C)
        self.assertEqual(x['nonmember_exposure'],2*y['nonmember_exposure'])
        self.assertEqual(x['harmonic_run_count'],y['harmonic_run_count'])


if __name__=='__main__':unittest.main()
