import unittest
from musicanote_harness.tonic_dominant_evidence import assess_bass_path


class FirstInversionTest(unittest.TestCase):
    def run_path(self,pitches,labels,tonic='C',mode='major'):
        return assess_bass_path(pitches,labels,['a','b','c'],tonic,mode=mode)

    def test_neighbor_v6(self):
        r=self.run_path([('C',0,3),('B',0,2),('C',0,3)],['I','V6','I'])
        self.assertEqual(r['middle_role_candidate'],'neighboring_dominant_candidate')
        self.assertIsNone(r['cadence'])

    def test_passing_vii6_both_directions(self):
        p=[('C',0,3),('D',0,3),('E',0,3)];labels=['I','viio6','I6']
        for ps,ls in [(p,labels),(p[::-1],labels[::-1])]:
            self.assertEqual(self.run_path(ps,ls)['middle_role_candidate'],'passing_leading_tone_chord_candidate')

    def test_same_family_not_new_function(self):
        r=self.run_path([('C',0,3),('E',0,3),('G',0,3)],['I','I6','V'])
        self.assertEqual(len(r['expansion_candidates']),1)
        self.assertFalse(r['harmony_verified'])

    def test_wrong_bass_and_register_reject_role(self):
        for mid in [('G',0,2),('B',0,3)]:
            r=self.run_path([('C',0,3),mid,('C',0,3)],['I','V6','I'])
            self.assertIsNone(r['middle_role_candidate'])

    def test_minor_third_and_leading_tone(self):
        r=self.run_path([('A',0,2),('B',0,2),('C',0,3)],['i','viio6','i6'],'A','minor')
        self.assertEqual(r['middle_role_candidate'],'passing_leading_tone_chord_candidate')
        r=self.run_path([('A',0,2),('G',0,2),('A',0,2)],['i','V6','i'],'A','minor')
        self.assertFalse(r['bass_observations'][1]['bass_matches_candidate'])

    def test_not_major_vii_or_unknown_label(self):
        with self.assertRaises(ValueError):
            self.run_path([('C',0,3)]*3,['I','VII6','I'])

    def test_transposed(self):
        r=self.run_path([('G',0,3),('A',0,3),('B',0,3)],['I','viio6','I6'],'G')
        self.assertEqual(r['middle_role_candidate'],'passing_leading_tone_chord_candidate')


if __name__ == '__main__':unittest.main()
