import copy
import unittest
from musicanote_harness.sixth_degree_evidence import assess_transition


def snap(prefix,*notes):
    return [{'event_id':prefix+str(i),'pitch':p} for i,p in enumerate(notes)]


class SixthDegreeTest(unittest.TestCase):
    def setUp(self):
        self.vi=snap('a',('A',0,2),('C',0,4),('E',0,4))
        self.iv6=snap('b',('A',0,2),('C',0,4),('F',0,4))
        self.v=snap('c',('G',0,2),('B',0,3),('D',0,4))

    def test_same_bass_different_shape(self):
        r=assess_transition(self.vi,self.iv6,'C')
        self.assertTrue(r['relations']['vi_to_iv6_same_lowest_pitch_surface'])
        self.assertIsNone(r['cadence'])
        self.assertEqual(r['same_voice_connection'],'unassessed')

    def test_vi_v_major_not_phrygian(self):
        r=assess_transition(self.vi,self.v,'C')
        self.assertTrue(r['relations']['sixth_degree_bass_to_root_dominant_surface'])
        self.assertFalse(r['relations']['minor_iv6_v_phrygian_surface'])

    def test_minor_phrygian_geometry_not_cadence(self):
        a=snap('a',('A',-1,2),('C',0,4),('F',0,4))
        r=assess_transition(a,self.v,'C',mode='minor')
        self.assertTrue(r['relations']['minor_iv6_v_phrygian_surface'])
        self.assertIsNone(r['cadence']); self.assertIsNone(r['functional_verdict'])

    def test_minor_raised_sixth_vs_augmented_second(self):
        dest=snap('c',('B',0,2),('D',0,4),('G',0,4))
        r=assess_transition(self.iv6,dest,'C',mode='minor')
        self.assertTrue(r['relations']['minor_raised_iv6_to_inverted_dominant_surface'])
        self.assertFalse(r['minor_lowered6_to_leading_tone_augmented_second_observation'])
        a=snap('a',('A',-1,2),('C',0,4),('E',-1,4))
        r=assess_transition(a,dest,'C',mode='minor')
        self.assertTrue(r['minor_lowered6_to_leading_tone_augmented_second_observation'])

    def test_minor_vi_iio_observed_not_forbidden(self):
        a=snap('a',('A',-1,2),('C',0,4),('E',-1,4))
        b=snap('b',('D',0,3),('F',0,3),('A',-1,3))
        self.assertTrue(assess_transition(a,b,'C',mode='minor')['relations']['vi_to_root_supertonic_surface'])

    def test_spelling_missing_extra_notes_abstain(self):
        for a in (self.vi[:-1], self.vi+snap('extra',('G',0,4)),
                  snap('a',('G',2,2),('C',0,4),('E',0,4))):
            self.assertEqual(assess_transition(a,self.v,'C')['observations'][0]['complete_surface_candidates'],[])

    def test_transposed_minor(self):
        a=snap('a',('B',-1,2),('D',0,4),('G',0,4))
        b=snap('b',('A',0,2),('C',1,4),('E',0,4))
        self.assertTrue(assess_transition(a,b,'D',mode='minor')['relations']['minor_iv6_v_phrygian_surface'])

    def test_input_not_mutated(self):
        saved=copy.deepcopy(self.vi)
        assess_transition(self.vi,self.iv6,'C'); self.assertEqual(self.vi,saved)
        self.assertTrue(assess_transition([],self.v,'C')['observations'][0]['empty_snapshot'])

    def test_duplicate_and_changed_event(self):
        with self.assertRaises(ValueError): assess_transition(self.vi+[self.vi[0]],self.v,'C')
        b=copy.deepcopy(self.v); b[0]['event_id']='a0'
        with self.assertRaises(ValueError): assess_transition(self.vi,b,'C')
