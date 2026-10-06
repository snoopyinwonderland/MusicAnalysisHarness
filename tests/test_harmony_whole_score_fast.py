import itertools
import unittest
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction as F

from musicanote_harness import harmony_whole_score_units as original
from musicanote_harness.harmony_whole_score_fast import FastBeatIndex,FastSearch,sweep,infer
from musicanote_harness.harmony_whole_score_diagnosis import evidence
from musicanote_harness.harmony_scored_decoder import Problem
from musicanote_harness.harmony_functional_scoring import pair_features
from musicanote_harness.harmony_progression_search import _hash
from test_harmony_bounded_recovery import fixture
from test_harmony_whole_score import problem,C,G

C7=(('C',0),(('B',-1),('C',0),('E',0),('G',0)))
G7=(('G',0),(('B',0),('D',0),('F',0),('G',0)))
FUNC64=(('G',0),C[1])


def prepare(ir):
    total=F(ir['score']['duration_quarters']['numerator'],ir['score']['duration_quarters']['denominator'])
    ev,points,_,args=evidence(ir,total)
    p=Problem(points,(),len(points)-1,sum((e.end-e.start for e in ev.source.events),F()),'ready')
    return p,ev,args


class PerformanceTests(unittest.TestCase):
    def test_sweep_exact_half_open_order(self):
        events=((0,2,'a'),(1,3,'b'),(2,3,'c'))
        cells=sweep(events,(0,1,2,3),lambda r:r[0],lambda r:r[1])
        self.assertEqual(cells,((events[0],),(events[0],events[1]),(events[1],events[2])))
        with self.assertRaisesRegex(ValueError,'missing_source_boundary'):
            sweep(events,(0,3),lambda r:r[0],lambda r:r[1])
        with self.assertRaisesRegex(ValueError,'nonpositive'):
            sweep(((1,1),),(0,1,2),lambda r:r[0],lambda r:r[1])

    def test_raw_indexes_and_converted_values_match_all_spans(self):
        examples=[fixture(),fixture([('C3',0,8,'b'),('E3',0,3,'i'),
            ('G3',1,8,'j'),('B-4',F(1,3),F(2,3),'lead'),('D4',4,5,'lead')],end=8)]
        examples[1]['measures'][0]['time_signature'].update(beats=6,beat_type=8)
        examples[1]['measures'][1]['time_signature'].update(beats=3,beat_type=4)
        examples[1]['measures'][0]['key_signature']={'fifths':0}
        for ir in examples:
            p,ev,args=prepare(ir);slow=original.UnitSearch(p,ev,original.model_weights(),**args)
            fast=FastSearch(p,ev,original.model_weights(),**args)
            for name in ('exposure','metric_exposure','durable','lowest','foreign','beats','unknown',
                         'metric_bad','durable_bad','bass_bad','key_bad'):
                self.assertEqual(getattr(slow.units,name),getattr(fast.units,name),name)
            for i,j in itertools.combinations(range(len(p.points)),2):
                a,b=p.points[i],p.points[j]
                for sig in (C,G,C7,G7,FUNC64):
                    old=original.applicability(slow.index.features(a,b,sig)[0])|{
                        'functional_role_complexity':F(int(original.six_four_surface(sig) is not None))}
                    new=original.applicability(fast.index.features(a,b,sig)[0])|{
                        'functional_role_complexity':F(int(original.six_four_surface(sig) is not None))}
                    self.assertEqual(slow.units.convert(old,a,b,sig),fast.units.convert(new,a,b,sig),(a,b,sig))
                    self.assertEqual(slow.run_cost(i,j,sig),fast.run_cost(i,j,sig))

    def test_unknown_spelling_projection_matches(self):
        p,ev,args=prepare(fixture())
        ev.source.events=tuple(replace(e,pitch=None) if i==0 else e for i,e in enumerate(ev.source.events))
        slow=original.UnitSearch(p,ev,original.model_weights(),**args)
        fast=FastSearch(p,ev,original.model_weights(),**args)
        for i,j in itertools.combinations(range(len(p.points)),2):
            for sig in (C,G):self.assertEqual(slow.run_cost(i,j,sig),fast.run_cost(i,j,sig))

    def test_conditional_passing_and_prepared_delay_match(self):
        cases=[fixture(),fixture([('C3',0,4,'b'),('G3',0,4,'i'),
            ('F4',0,2,'lead'),('E4',2,4,'lead')])]
        for ir in cases:
            p,ev,args=prepare(ir);slow=original.UnitSearch(p,ev,original.model_weights(),**args)
            fast=FastSearch(p,ev,original.model_weights(),**args)
            for i,j in itertools.combinations(range(len(p.points)),2):
                for sig in (C,G,G7):self.assertEqual(slow.run_cost(i,j,sig),fast.run_cost(i,j,sig))

    def test_positive_pair_costs_and_receipts_match(self):
        examples=[fixture([('G3',0,2,'b'),('C3',2,4,'b'),('B3',0,2,'i'),
            ('C4',2,4,'i'),('D4',0,2,'j'),('E4',2,4,'j'),('F4',0,2,'k'),('E4',2,4,'k')]),
            fixture([('G3',0,2,'b'),('G3',2,4,'b'),('C4',0,2,'i'),('B3',2,4,'i'),
                ('E4',0,2,'j'),('D4',2,4,'j'),('G4',0,2,'k'),('F4',2,4,'k')])]
        nonzero=0
        for ir in examples:
            p,ev,args=prepare(ir);slow=original.UnitSearch(p,ev,original.model_weights(),**args)
            fast=FastSearch(p,ev,original.model_weights(),**args)
            for left,right in itertools.product((C,G,C7,G7,FUNC64),repeat=2):
                self.assertEqual(slow.pair_cost(0,1,left,right),fast.pair_cost(0,1,left,right))
                expected=pair_features(ev,p.points[0],p.points[1],p.points[2],left,right)
                actual=fast.bound_pair(fast.pair_ev,p.points[0],p.points[1],p.points[2],left,right)
                self.assertEqual(expected,actual)
                nonzero+=bool(any(expected[0].values()))
        self.assertGreater(nonzero,0)

    def test_search_frontiers_costs_ids_and_loss_identical(self):
        p,ev,batches=problem();slow=original.UnitSearch(p,ev,original.model_weights(),beam_width=2)
        fast=FastSearch(p,ev,original.model_weights(),beam_width=2)
        for batch in batches:
            slow.consume(batch);fast.consume(batch)
            self.assertEqual(slow.frontier,fast.frontier)
            self.assertEqual(slow.discarded,fast.discarded)
            self.assertEqual(slow.operations,fast.operations)
        self.assertEqual(slow.finish(),fast.finish())

    def test_full_inference_catalogs_source_and_path_identical(self):
        ir=fixture();before=deepcopy(ir)
        expected=original.infer(ir,F(4));actual=infer(ir,F(4))
        self.assertEqual(expected[0],actual[0]);self.assertEqual(_hash(expected[2]),_hash(actual[2]))
        for field in ('selected_path','page_inventory','score_cost','feature_values','feature_availability',
                      'actual_harmonic_runs','states_discarded','operations'):
            self.assertEqual(expected[1][field],actual[1][field],field)
        self.assertTrue(actual[1]['independently_rescored']);self.assertEqual(ir,before)
        self.assertGreater(actual[1]['window_reuse']['cache_hits'],0)
        self.assertFalse(actual[1]['optimization_changes_score_semantics'])

    def test_no_partial_submission(self):
        p,ev,batches=problem();fast=FastSearch(p,ev,original.model_weights(),operations=1)
        fast.consume(batches[0]);self.assertIsNone(fast.finish()['selected'])
        self.assertEqual(fast.finish()['status'],'operation_budget_abstention')


if __name__=='__main__':unittest.main()
