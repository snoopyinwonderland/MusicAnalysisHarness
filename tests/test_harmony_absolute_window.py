import copy
from fractions import Fraction as F
import unittest
from unittest.mock import patch
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_joint import analyze_joint, candidates, f
from musicanote_harness.harmony_temporal_shadow import analyze, provider
from musicanote_harness.harmony_review_comparison import compare_outputs, target_segments
from test_harmony_joint import fixture


def span(a,b):return {'start':q(a),'end':q(b)}


class AbsoluteWindowTests(unittest.TestCase):
    def test_preserves_carried_sound_and_external_neighbors(self):
        ir=fixture([(60,0,1,'v'),(62,1,F(3,2),'v'),(64,F(3,2),4,'v'),(48,0,4,'b')])
        original=copy.deepcopy(ir);seen=[]
        def choose(rows,neighbors,a,b,beat):
            seen.append((rows,neighbors))
            return candidates(rows,neighbors,a,b,beat)
        analyze_joint(ir,candidate_provider=choose,analysis_span=span(1,F(3,2)))
        rows,neighbors=seen[0]
        self.assertEqual(next(r for r in rows if r['id']=='s3')['start'],0)
        self.assertEqual(next(r for r in rows if r['id']=='s3')['end'],4)
        self.assertEqual([r['id'] for r in neighbors['s1']],['s0','s2'])
        self.assertEqual(ir,original)

    def test_original_measure_grid_not_window_origin(self):
        ir=fixture([(60,0,4,'v')]);pairs=[]
        def choose(rows,neighbors,a,b,beat):
            pairs.append((a,b));return candidates(rows,neighbors,a,b,beat)
        out=analyze_joint(ir,candidate_provider=choose,analysis_span=span(F(1,3),F(7,3)))
        points={t for pair in pairs for t in pair}
        self.assertIn(F(1),points);self.assertIn(F(2),points)
        self.assertNotIn(F(4,3),points)
        self.assertEqual(out['segments'][0]['span']['start'],q(F(1,3)))
        self.assertEqual(out['segments'][-1]['span']['end'],q(F(7,3)))

    def test_requested_silence_and_empty_score(self):
        for ir in [fixture([]),fixture([(60,0,1,'v')])]:
            out=analyze_joint(ir,analysis_span=span(2,4))
            self.assertEqual(out['segments'][0]['selected']['label'],'rest')
            self.assertEqual(out['segments'][-1]['span']['end'],q(4))

    def test_full_window_preserves_default_path(self):
        ir=fixture([(60,0,1,'v'),(64,1,2,'v'),(67,2,4,'v')])
        self.assertEqual(analyze_joint(ir)['segments'],analyze_joint(ir,analysis_span=span(0,4))['segments'])

    def test_invalid_bounds(self):
        for s in [span(-1,1),span(1,1),span(2,1)]:
            with self.assertRaises(ValueError):analyze_joint(fixture([]),analysis_span=s)

    def test_fractional_translation_preserves_temporal_costs(self):
        ir=fixture([(p,a,b,str(i)) for a,b,ps in [(0,1,[60,64,67]),(1,2,[62,65,69])]
                    for i,p in enumerate(ps)])
        delta=F(1,3);shifted=copy.deepcopy(ir)
        for s in shifted['sounding_events']:
            s['span']={k:q(f(v)+delta) for k,v in s['span'].items()}
        shifted['measures'][0]['global_start_quarter']=q(delta)
        a=analyze(ir,cell_divisions=2,analysis_span=span(0,2))
        b=analyze(shifted,cell_divisions=2,analysis_span=span(delta,2+delta))
        self.assertAlmostEqual(a['path_cost'],b['path_cost'])
        self.assertEqual([s['selected']['label'] for s in a['segments']],
                         [s['selected']['label'] for s in b['segments']])
        self.assertEqual([f(s['span']['start']) for s in a['segments']],
                         [f(s['span']['start'])-delta for s in b['segments']])

    def test_temporal_cells_stop_at_meter_change(self):
        measures=[{'global_start_quarter':q(0),'time_signature':{'beat_type':4}},
                  {'global_start_quarter':q(F(3,4)),'time_signature':{'beat_type':8}}]
        calls=[]
        def fake(rows,neighbors,a,b,beat,**kw):
            if kw.get('min_shared_pcs')==0:calls.append((a,b,beat))
            return [{'label':'rest','root':None,'pcs':[],'cost':0}]
        with patch('musicanote_harness.harmony_temporal_shadow.candidates',side_effect=fake):
            provider(cell_divisions=2,measures=measures)([],{},F(0),F(5,4),F(1))
        self.assertEqual(calls,[(F(0),F(1,2),F(1)),(F(1,2),F(3,4),F(1)),
                                (F(3,4),F(1),F(1,2)),(F(1),F(5,4),F(1,2))])

    def test_target_only_no_artificial_edge_boundary(self):
        def seg(a,b,label):return {'span':span(a,b),'selected':{'label':label}}
        old={'segments':[seg(0,4,'C')]}
        new={'segments':[seg(0,1,'X'),seg(1,3,'C'),seg(3,4,'Y')]}
        r=compare_outputs(old,new,target_span=span(1,3))
        self.assertEqual(r['added_boundaries'],[])
        self.assertEqual(r['baseline_segments'],1)
        self.assertFalse(r['label_sequence_changed'])
        projected=target_segments(old,span(1,3))[0]
        self.assertEqual(projected['inferred_absolute_span'],span(0,4))
        self.assertEqual(projected['span'],span(1,3))
        self.assertEqual(old['segments'][0]['span'],span(0,4))
