import unittest
from fractions import Fraction as F
from copy import deepcopy
from test_harmony_joint import fixture
from musicanote_harness.harmony_joint import prepare,f
from musicanote_harness.harmony_boundary_contrast import contrast_blocks,contrast_penalty
from musicanote_harness.harmony_multiscale_shadow import analyze,provider
from musicanote_harness.harmony_candidate_explanation import explain_path


def passage(scale=1,transpose=0):
    return fixture([(p+transpose,F(a)*scale,F(b)*scale,str(i))
        for a,b,ps in [(0,1,[48,65,68]),(1,2,[48,62,71])]
        for i,p in enumerate(ps)])


class BoundaryContrastTests(unittest.TestCase):
    def test_synchronized_replacement_has_evidence(self):
        ir=passage();rows,_=prepare(ir);cs=contrast_blocks(rows,ir['measures'])
        self.assertEqual(len(cs),1)
        self.assertEqual(cs[0]['boundary'],F(1))
        penalty,ev=contrast_penalty({'root':2,'pcs':[2,5,8,0]},F(0),F(2),cs)
        self.assertGreater(penalty,0)
        self.assertEqual(ev[0]['left_pitch_classes'],[0,5,8])
        self.assertEqual(ev[0]['right_pitch_classes'],[0,2,11])

    def test_split_not_penalized_and_same_shape_exempt(self):
        ir=passage();rows,_=prepare(ir);cs=contrast_blocks(rows,ir['measures'])
        for a,b,pcs in [(0,1,[0,5,8]),(1,2,[0,2,11]),(0,2,[0,2,5,8,11])]:
            self.assertEqual(contrast_penalty({'root':0,'pcs':pcs},F(a),F(b),cs),(0,[]))

    def test_arpeggio_single_neighbor_and_added_seventh_exempt(self):
        cases=[[(60,0,1,'v'),(64,1,2,'v'),(67,2,3,'v'),(64,3,4,'v')],
            [(48,0,4,'b'),(64,0,4,'i'),(67,0,1,'v'),(69,1,2,'v'),(67,2,4,'v')],
            [(48,0,4,'b'),(64,0,4,'v'),(67,0,4,'i'),(70,2,4,'t')]]
        for specs in cases:
            ir=fixture(specs);rows,_=prepare(ir)
            self.assertEqual(contrast_blocks(rows,ir['measures']),[])

    def test_short_chordal_ornament_exempt(self):
        ir=passage();ir['sounding_events'][3]['span']['end']={'numerator':5,'denominator':4}
        ir['sounding_events'][4]['span']['end']={'numerator':5,'denominator':4}
        ir['sounding_events'][5]['span']['end']={'numerator':5,'denominator':4}
        rows,_=prepare(ir);self.assertEqual(contrast_blocks(rows,ir['measures']),[])

    def test_octave_reattacks_not_change(self):
        ir=fixture([(48,0,F(1,2),'b'),(60,F(1,2),1,'b'),(65,0,1,'v'),(68,0,1,'i')])
        rows,_=prepare(ir);self.assertEqual(contrast_blocks(rows,ir['measures']),[])

    def test_transposition_meter_scaling_invariant(self):
        penalties=[]
        for scale,tr in [(F(1),0),(F(1,2),2)]:
            ir=passage(scale,tr);ir['measures'][0]['time_signature']['beat_type']=int(4/scale)
            rows,_=prepare(ir);cs=contrast_blocks(rows,ir['measures'])
            penalties.append(contrast_penalty({'root':(2+tr)%12,'pcs':[(x+tr)%12 for x in [2,5,8,0]]},F(0),2*scale,cs)[0])
        self.assertEqual(*penalties)

    def test_real_engine_and_ablation_do_not_mutate_core(self):
        ir=passage();before=deepcopy(ir)
        old=analyze(ir,enable_boundary_contrast=False);new=analyze(ir)
        self.assertEqual(ir,before)
        self.assertEqual(len(old['segments']),1)
        self.assertTrue(any(f(s['span']['end'])==1 for s in new['segments']))
        self.assertEqual(new['segments'][0]['selected']['label'],'F:minor')
        self.assertAlmostEqual(explain_path(new)['reconstructed_path_cost'],new['path_cost'])
        self.assertEqual(new,analyze({**ir,'annotations':['garbage'],'phrases':['wrong']}))

    def test_selected_merged_path_cost_reconstruction(self):
        ir=passage();rows,ns=prepare(ir)
        cs=provider(ir['measures'],enable_boundary_contrast=True)(rows,ns,F(0),F(2),F(1))
        self.assertTrue(any(c['boundary_contrast_cost']>0 for c in cs))
        for c in cs:self.assertAlmostEqual(c['cost'],c['pooled_cost']+c['temporal_regret']+c['boundary_contrast_cost'])


if __name__=='__main__':unittest.main()
