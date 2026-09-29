import unittest
from musicanote_harness.predominant_evidence import assess_transition


def snap(prefix, *pitches):
    return [{'event_id':prefix+str(i), 'pitch':p} for i,p in enumerate(pitches)]


class PredominantTests(unittest.TestCase):
    def setUp(self):
        self.iv=snap('a',('F',0,3),('A',0,3),('C',0,4))
        self.ii=snap('b',('F',0,3),('A',0,3),('D',0,4))
        self.v=snap('c',('G',0,2),('B',0,3),('D',0,4))

    def test_major_and_no_cadence(self):
        r=assess_transition(self.ii,self.v,['ii6','V'],'C')
        self.assertTrue(r['predominant_to_dominant_candidate'])
        self.assertIsNone(r['cadence'])

    def test_same_bass_five_six(self):
        r=assess_transition(self.iv,self.ii,['IV','ii6'],'C')
        self.assertTrue(r['iv_to_ii6_five_six_candidate'])
        self.assertFalse(r['predominant_to_dominant_candidate'])

    def test_sustained_event_v42(self):
        dest=[self.ii[0]]+snap('d',('G',0,3),('B',0,3),('D',0,4))
        r=assess_transition(self.ii,dest,['ii6','V42'],'C')
        self.assertTrue(r['held_bass_harmony_change_candidate'])
        self.assertEqual(r['retained_degree4_event_refs'],['b0'])
        self.assertIsNone(r['nct_label'])

    def test_minor_and_transposition(self):
        a=snap('a',('G',0,3),('B',-1,3),('E',0,4))
        b=snap('b',('A',0,2),('C',1,4),('E',0,4))
        self.assertTrue(assess_transition(a,b,['iio6','V'],'D',mode='minor')['predominant_to_dominant_candidate'])

    def test_extra_note_abstains(self):
        a=self.ii+snap('extra',('E',0,4))
        self.assertFalse(assess_transition(a,self.v,['ii6','V'],'C')['predominant_to_dominant_candidate'])

    def test_wrong_bass_and_spelling_abstain(self):
        a=snap('a',('D',0,3),('F',0,3),('A',0,3))
        self.assertFalse(assess_transition(a,self.v,['ii6','V'],'C')['predominant_to_dominant_candidate'])
        b=snap('wrong',('G',0,2),('C',-1,4),('D',0,4))
        self.assertFalse(assess_transition(self.ii,b,['ii6','V'],'C')['predominant_to_dominant_candidate'])

    def test_bad_references(self):
        with self.assertRaises(ValueError):
            assess_transition(self.ii,[{'event_id':'b0','pitch':('G',0,3)}],['ii6','V'],'C')
        with self.assertRaises(ValueError):
            assess_transition([],self.v,['ii6','V'],'C')
