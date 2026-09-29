from copy import deepcopy
from fractions import Fraction as F
import unittest
from test_harmony_joint import fixture
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_figure_evidence import observe
from musicanote_harness.harmony_boundary_ownership import review
from musicanote_harness.harmony_multiscale_shadow import analyze
from test_harmony_boundary_ownership import score


def patterned(second=(53,49,56,53), scale=F(1), transpose=0):
    notes=[(p+transpose, (a+F(i,4))*scale, (a+F(i+1,4))*scale, 'voice')
           for a,ns in [(0,(56,50,59,56)),(3,second)] for i,p in enumerate(ns)]
    ir=fixture(notes)
    ir['measures'][0].update(actual_duration_quarter=q(4*scale), time_signature={'beat_type':int(4/scale)})
    return ir


class FigureEvidenceTests(unittest.TestCase):
    def test_rhythm_and_weak_variation_with_internal_boundary(self):
        ir=patterned();r=observe(ir,{'start':q(0),'end':q(4)},[q(F(1,2)),q(3)])
        m=r['rhythmic_matches'][0]
        self.assertTrue(m['weak_pitch_variation_compatible'])
        self.assertEqual(m['interval_errors_semitones'],[2,2,0])
        self.assertEqual(m['split_by_selected_boundaries'],[{'boundary':q(F(1,2)),'cell':'earlier'}])
        self.assertFalse(r['used_for_selection'])

    def test_same_rhythm_different_shape_is_not_weak_variation(self):
        r=observe(patterned((53,57,64,67)),{'start':q(0),'end':q(4)})
        self.assertTrue(r['rhythmic_matches'][0]['attack_rhythm_exact'])
        self.assertFalse(r['rhythmic_matches'][0]['weak_pitch_variation_compatible'])

    def test_unknown_voices_not_combined(self):
        ir=patterned()
        for n in ir['note_events']:n['voice_id']=None
        self.assertEqual(observe(ir,{'start':q(0),'end':q(4)})['cells'],[])

    def test_separate_voices_not_matched(self):
        ir=patterned()
        for n in ir['note_events'][4:]:n['voice_id']='other'
        self.assertEqual(observe(ir,{'start':q(0),'end':q(4)})['rhythmic_matches'],[])

    def test_meter_relative_and_transposition_invariance(self):
        for tr,scale in [(0,F(1)),(2,F(1)),(0,F(1,2))]:
            r=observe(patterned(scale=scale,transpose=tr),{'start':q(0),'end':q(4*scale)})
            self.assertEqual(r['rhythmic_matches'][0]['interval_errors_semitones'],[2,2,0])

    def test_no_context_overread(self):
        ir=patterned()
        self.assertEqual(observe(ir,{'start':q(0),'end':q(F(7,2))})['rhythmic_matches'],[])

    def test_bass_continuation_not_new_attack(self):
        ir=fixture([(36,0,4,'bass'),(60,0,1,'v'),(64,1,2,'v')])
        b=observe(ir,{'start':q(0),'end':q(4)},[q(1)])['bass_boundaries'][0]
        self.assertEqual(b['new_lowest_attack_refs'],[])
        self.assertEqual(b['continuing_lowest_refs'],['s0'])
        self.assertEqual(b['motion_semitones'],0)

    def test_diagnostics_observation_does_not_change_output(self):
        ir=score();r=analyze(ir);before=deepcopy((ir,r));log=[]
        self.assertEqual(review(ir,r),review(ir,r,diagnostics=log))
        self.assertEqual((ir,r),before)
        self.assertEqual(sum(x['reason']=='accepted_alternative' for x in log),1)
        eligible=sum(len(x.get('considered_onsets',[])) for x in log if x['kind']=='boundary')
        self.assertEqual(eligible,sum(x['kind']=='onset' for x in log))

    def test_figure_input_immutable_labels_ignored(self):
        ir=patterned();before=deepcopy(ir);s={'start':q(0),'end':q(4)}
        r=observe(ir,s)
        self.assertEqual(ir,before)
        self.assertEqual(r,observe({**ir,'annotations':['wrong'],'phrases':['wrong']},s))


if __name__=='__main__':unittest.main()
