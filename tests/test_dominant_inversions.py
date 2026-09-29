import unittest
from musicanote_harness.tonic_dominant_evidence import assess_bass_path


class DominantInversionTest(unittest.TestCase):
    def assess(self,p,c,tonic='C',mode='major'):
        return assess_bass_path(p,c,['a','b','c'],tonic,mode=mode)

    def test_v65_neighbor(self):
        r=self.assess([('C',0,3),('B',0,2),('C',0,3)],['I','V65','I'])
        self.assertEqual(r['middle_role_candidate'],'neighboring_dominant_seventh_candidate')
        self.assertEqual(r['bass_resolution_evidence'][0]['type'],'leading_tone_bass_step_up')

    def test_v43_passing_both_directions(self):
        p=[('C',0,3),('D',0,3),('E',0,3)];c=['I','V43','I6']
        for ps,cs in [(p,c),(p[::-1],c[::-1])]:
            r=self.assess(ps,cs)
            self.assertEqual(r['middle_role_candidate'],'passing_dominant_seventh_candidate')
            self.assertEqual(r['upper_voice_support'],'unassessed')

    def test_v42_passing(self):
        r=self.assess([('G',0,3),('F',0,3),('E',0,3)],['V','V42','I6'])
        self.assertEqual(r['middle_role_candidate'],'passing_dominant_seventh_candidate')
        self.assertEqual(r['bass_resolution_evidence'][0]['type'],'chordal_seventh_bass_step_down')

    def test_v42_minor_neighbor(self):
        r=self.assess([('C',0,3),('D',0,3),('C',0,3)],['i6','V42','i6'],'A','minor')
        self.assertEqual(r['middle_role_candidate'],'neighboring_dominant_seventh_candidate')
        self.assertIsNone(r['cadence'])

    def test_wrong_destination_not_forced(self):
        r=self.assess([('G',0,3),('F',0,3),('C',0,3)],['V7','V42','I'])
        self.assertEqual(r['bass_resolution_evidence'],[])
        self.assertIsNone(r['middle_role_candidate'])

    def test_expansion_keeps_7th_family(self):
        r=self.assess([('G',0,3),('F',0,3),('E',0,3)],['V7','V42','I6'])
        self.assertEqual(len(r['expansion_candidates']),1)
        self.assertFalse(r['harmony_verified'])


if __name__ == '__main__':unittest.main()
