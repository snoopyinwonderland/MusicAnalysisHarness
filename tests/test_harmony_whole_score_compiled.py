import itertools
import json
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction as F
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from musicanote_harness import harmony_whole_score_units as original
from musicanote_harness.harmony_whole_score_fast import FastSearch
from musicanote_harness.harmony_whole_score_compiled import CompiledSearch,WeightedPrefix,infer
from musicanote_harness.harmony_whole_score_phases import Telemetry,infer as measured
from musicanote_harness.harmony_root_context_scoring import RootReturnContext
from musicanote_harness.harmony_temporal_scoring import beat_extent
from test_harmony_whole_score_fast import prepare,C,G,C7,G7,FUNC64
from test_harmony_bounded_recovery import fixture
from test_harmony_whole_score import problem
from test_harmony_root_context_scoring import returning


class CompiledTests(unittest.TestCase):
    def test_weighted_prefix_exact_positive_negative_empty(self):
        table={'a':[F(),F(1,3),F(2,3)],'b':[F(),F(2,7),F(6,7)]}
        for weight in (F(2651,125000),F(-532151,1000000)):
            p=WeightedPrefix(table,weight,3)
            for i,j in itertools.combinations(range(3),2):
                for members in ((),('a',),('a','b'),('unknown',)):
                    self.assertEqual(p.nonmembers(i,j,members),sum(
                        ((v[j]-v[i])*weight for t,v in table.items() if t not in members),F()))
        self.assertEqual(WeightedPrefix({},F(1,2),3).nonmembers(0,2,()),0)

    def test_all_span_costs_meter_roles_and_unknown(self):
        cases=[fixture(),returning(),fixture([('C3',0,4,'b'),('E3',0,4,'i'),('G3',0,4,'j'),
            ('C4',0,F(1,2),'lead'),('D4',F(1,2),1,'lead'),('E4',1,4,'lead')]),
            fixture([('C3',0,4,'b'),('G3',1,4,'i'),('F4',0,3,'lead'),('E4',3,4,'lead')]),
            fixture([('C3',0,8,'b'),('E3',0,3,'i'),('G3',1,8,'j'),
                ('B-4',F(1,3),F(2,3),'lead'),('D4',4,5,'lead')],end=8)]
        cases[-1]['measures'][0]['time_signature'].update(beats=6,beat_type=8)
        cases[-1]['measures'][1]['time_signature'].update(beats=3,beat_type=4)
        cases[-1]['measures'][0]['key_signature']={'fifths':0}
        for ir in cases:
            p,ev,args=prepare(ir)
            for unknown in (False,True):
                if unknown:ev.source.events=tuple(replace(e,pitch=None) if n==0 else e for n,e in enumerate(ev.source.events))
                old=FastSearch(p,ev,original.model_weights(),**args)
                new=CompiledSearch(p,ev,original.model_weights(),**args)
                for i,j in itertools.combinations(range(len(p.points)),2):
                    for sig in (C,G,C7,G7,FUNC64,(None,C[1])):
                        self.assertEqual(old.run_cost(i,j,sig),new.run_cost(i,j,sig),(i,j,sig,unknown))
                    self.assertEqual(new.index.context.extent(p.points[i],p.points[j]),beat_extent(ev.source,p.points[i],p.points[j]))

    def test_root_support_receipts_lowest_boundary_and_barriers(self):
        for ir in (returning(),returning(True),fixture()):
            p,ev,args=prepare(ir)
            for changed in ({},dict(history_gate=lambda a,b:False),dict(context_barriers=(F(1),))):
                old=RootReturnContext(ev,**(args|changed))
                new=CompiledSearch(p,ev,original.model_weights(),**args).index.context
                # Private context changes only this synthetic test instance.
                for k,v in changed.items():setattr(new,'barriers' if k=='context_barriers' else k,v)
                for a,b in itertools.combinations(p.points,2):
                    for sig in (C,G,G7):self.assertEqual(old.support(a,b,sig),new.support(a,b,sig))
                for r in ev.rows:
                    for t in p.points:
                        for before in (False,True):
                            self.assertEqual(old.lowest(r,t,before=before),new.lowest(r,t,before=before))

    def test_identical_frontiers_budget_and_direct_winner(self):
        p,ev,batches=problem()
        for budget in (1,2_000_000):
            old=FastSearch(p,ev,original.model_weights(),beam_width=2,operations=budget)
            new=CompiledSearch(p,ev,original.model_weights(),beam_width=2,operations=budget)
            for batch in batches:
                old.consume(batch);new.consume(batch)
                self.assertEqual(old.frontier,new.frontier);self.assertEqual(old.operations,new.operations)
                self.assertEqual(old.discarded,new.discarded)
                if old.status!='pending':break
            self.assertEqual(old.finish(),new.finish())

    def test_full_catalogs_cost_features_source_and_phase_receipt(self):
        ir=fixture();before=deepcopy(ir)
        with TemporaryDirectory() as d:
            telemetry=Telemetry(Path(d)/'phase.json')
            a=measured(ir,F(4),telemetry);b=infer(ir,F(4))
            self.assertEqual(a[0],b[0]);self.assertEqual(a[2],b[2])
            for field in ('selected_path','page_inventory','score_cost','feature_values','feature_availability',
                          'actual_harmonic_runs','states_discarded','operations'):
                self.assertEqual(a[1][field],b[1][field])
            self.assertEqual(ir,before)
            receipt=json.loads((Path(d)/'phase.json').read_text())
            self.assertFalse(receipt['partial_prediction_submitted']);self.assertEqual(receipt['active'],[])
            self.assertIn('legacy_full_features',receipt['completed_seconds'])


if __name__=='__main__':unittest.main()
