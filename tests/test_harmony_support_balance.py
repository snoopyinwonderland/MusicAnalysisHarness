from copy import deepcopy
from dataclasses import replace
from fractions import Fraction as F
import random
import unittest

from musicanote_harness import harmony_support_balance as s
from test_harmony_bounded_recovery import fixture
from test_harmony_exact_frontier import problem
from test_harmony_functional_scoring import C,G,G7


class SupportBalanceTests(unittest.TestCase):
    def test_roles_separate_third_altered_fifth_and_seventh(self):
        self.assertEqual(s.roles(C),(("E",0),None,None))
        self.assertEqual(s.roles(G7),(("B",0),None,("F",0)))
        diminished=(("E",0),(("B",-1),("E",0),("G",0)))
        self.assertEqual(s.roles(diminished),(("G",0),("B",-1),None))
        self.assertIsNone(s.roles((None,C[1])))

    def test_missing_seventh_not_averaged_with_observed_third(self):
        graph,ev=problem(fixture([('G3',0,4,'a'),('B3',0,4,'b')]))
        values,rows=s.support_features(graph,ev.source,F(),F(4),G7)
        self.assertEqual(values['absent_third_exposure'],0)
        self.assertEqual(values['absent_seventh_exposure'],1)
        self.assertEqual(values['absent_altered_fifth_exposure'],0)
        self.assertFalse(rows[0]['confirmed_nct'])
        self.assertFalse(rows[0]['omission_prohibited'])

    def test_duration_uses_full_sound_but_counts_only_run_intersection(self):
        graph,ev=problem(fixture([('C3',0,4,'b'),('D4',0,2,'l')]))
        v,_=s.support_features(graph,ev.source,F(1),F(2),C)
        self.assertEqual(v['durable_nonmember_exposure'],F(1,6))

    def test_compound_meter_relative_duration(self):
        ir=fixture([('C3',0,4,'b'),('D4',0,1,'l')])
        graph,ev=problem(ir)
        ev.source.measures=tuple((a,(6,8),key) for a,meter,key in ev.source.measures)
        ev.source._metric_cache.clear()
        self.assertEqual(s.support_features(graph,ev.source,F(),F(4),C)[0]['durable_nonmember_exposure'],0)

    def test_unknown_meter_or_pitch_remains_unavailable(self):
        graph,ev=problem()
        ev.source.measures=();ev.source._measure_times=();ev.source._metric_cache.clear()
        self.assertIsNone(s.support_features(graph,ev.source,F(),F(4),C)[0]['durable_nonmember_exposure'])
        ev.source.events=tuple(replace(e,pitch=None) for e in ev.source.events)
        self.assertTrue(all(v is None for v in s.support_features(graph,ev.source,F(),F(4),C)[0].values()))

    def test_direct_and_indexed_values_every_span(self):
        graph,ev=problem();scorer=s.Scorer(graph,ev)
        for i,a in enumerate(graph.points):
            for b in graph.points[i+1:]:
                for sig in {e.signature for e in graph.edges}:
                    self.assertEqual(s.support_features(graph,ev.source,a,b,sig)[0],
                                     s.support_features(graph,ev.source,a,b,sig,index=scorer.index)[0])

    def test_zero_coefficients_preserve_existing_control(self):
        ir=fixture();before=deepcopy(ir);graph,ev=problem(ir)
        old=s.prior.decode(graph,ev,arm='control');new=s.Scorer(graph,ev).decode()
        self.assertEqual(new['selected']['score_cost'],old['selected']['score_cost'])
        self.assertEqual(new['selected']['segments'],old['selected']['segments'])
        self.assertEqual(ir,before)

    def test_direct_train_backend_does_not_insert_meter_grid_points(self):
        graph,ev=problem();before=graph.points
        scorer=s.Scorer(graph,ev,build_index=False)
        ids=(next(e.group_id for e in graph.edges if e.start==0 and e.end==4 and e.signature==C),)
        self.assertEqual(scorer.path_features(ids),s.Scorer(graph,ev).path_features(ids))
        with self.assertRaisesRegex(ValueError,'index_not_built'):scorer.path_features(ids,indexed=True)
        self.assertEqual(graph.points,before)

    def test_same_signature_raw_subdivisions_do_not_add_missing_penalties(self):
        graph,ev=problem();by={(e.start,e.end,e.signature):e.group_id for e in graph.edges}
        whole=(by[F(),F(4),C],)
        split=(by[F(),F(1),C],by[F(1),F(2),C],by[F(2),F(4),C])
        scorer=s.Scorer(graph,ev,{k:F(1,2) for k in s.FEATURES})
        self.assertEqual(scorer.path_features(whole),scorer.path_features(split))
        self.assertEqual(scorer.score_path(whole),scorer.score_path(split))

    def test_invalid_coefficient_types_and_bounds_rejected(self):
        for value in (0.1,True,F(-1),F(2)):
            with self.assertRaises(ValueError):s.coefficients(s.ZERO|{s.FEATURES[0]:value})
        with self.assertRaises(ValueError):s.coefficients({})

    def test_exact_joint_minimum_with_nonzero_coefficients(self):
        graph,ev=problem();rng=random.Random(6701)
        for _ in range(8):
            tiny=replace(graph,edges=tuple(e for e in graph.edges if e.signature in (C,G,G7) and rng.random()<.7),max_segments=3)
            scorer=s.Scorer(tiny,ev,{k:F(rng.randrange(4),4) for k in s.FEATURES});paths=[]
            def visit(i,ids):
                if i==len(tiny.points)-1:paths.append((scorer.score_path(ids),ids));return
                if len(ids)>=tiny.max_segments:return
                for edge in tiny.edges:
                    if edge.start_index==i:visit(edge.end_index,ids+(edge.group_id,))
            visit(0,());result=scorer.decode()
            if not paths:self.assertIsNone(result['selected']);continue
            selected=result['selected'];ids=tuple(x['semantic_group_ref'] for x in selected['segments'])
            self.assertEqual((s.f(selected['score_cost']),ids),min(paths))

