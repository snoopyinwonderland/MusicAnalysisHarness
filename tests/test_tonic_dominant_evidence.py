import unittest
from musicanote_harness.tonic_dominant_evidence import assess_path


class TonicDominantTest(unittest.TestCase):
    def test_supported_passing_not_nct(self):
        r=assess_path([('E',0,4),('D',0,4),('C',0,4)],['I','V','I'],['a','b','c'],'C')
        self.assertEqual(r['melodic_geometry']['pattern'],'passing_geometry')
        self.assertTrue(all(s['member_under_candidate'] for s in r['supports']))
        self.assertIsNone(r['cadence'])

    def test_same_melody_different_hypothesis(self):
        r=assess_path([('E',0,4),('D',0,4),('C',0,4)],['I']*3,['a','b','c'],'C')
        self.assertFalse(r['supports'][1]['member_under_candidate'])
        self.assertIsNone(r['supports'][1]['nct_label'])

    def test_seventh_is_supported_neighbor(self):
        r=assess_path([('E',0,4),('F',0,4),('E',0,4)],['I','V7','I'],['a','b','c'],'C')
        self.assertEqual(r['melodic_geometry']['pattern'],'neighbor_geometry')
        self.assertEqual(r['supports'][1]['chord_factor_under_candidate'],7)
        self.assertTrue(r['transitions'][1]['seventh_step_down_to_tonic_third'])

    def test_minor_leading_tone(self):
        for alter,expected in [(1,True),(0,False)]:
            r=assess_path([('A',0,4),('G',alter,4),('A',0,4)],['i','V','i'],['a','b','c'],'A',mode='minor')
            self.assertEqual(r['transitions'][1]['leading_tone_step_up_to_tonic'],expected)

    def test_transposed(self):
        r=assess_path([('A',1,4),('B',0,4),('A',1,4)],['I','V7','I'],['a','b','c'],'F',1)
        self.assertTrue(r['transitions'][1]['seventh_step_down_to_tonic_third'])

    def test_inner_voice_leap_not_declared_invalid(self):
        r=assess_path([('G',0,4),('B',0,4),('G',0,4)],['I','V','I'],['a','b','c'],'C')
        self.assertFalse(r['transitions'][1]['leading_tone_step_up_to_tonic'])
        self.assertTrue(r['supports'][2]['member_under_candidate'])
        self.assertFalse(r['harmony_verified'])

    def test_invalid_inputs(self):
        p=[('C',0,4)]*3
        with self.assertRaises(ValueError):assess_path(p,['I','II','I'],['a','b','c'],'C')
        with self.assertRaises(ValueError):assess_path(p,['I']*3,['a']*3,'C')


if __name__ == '__main__':unittest.main()
