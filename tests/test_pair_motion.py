import unittest
from musicanote_harness.counterpoint_evidence import pair_motion


class PairMotionTest(unittest.TestCase):
    def test_parallel_thirds_quality_may_change(self):
        r=pair_motion(('C',0,4),('E',0,4),('D',0,4),('F',0,4))
        self.assertEqual(r['motion'],'parallel')
        self.assertIsNone(r['parallel_perfect_family'])

    def test_contrary_and_oblique(self):
        self.assertEqual(pair_motion(('C',0,3),('G',0,4),('D',0,3),('F',0,4))['motion'],'contrary')
        self.assertEqual(pair_motion(('C',0,3),('G',0,4),('C',0,3),('A',0,4))['motion'],'oblique')

    def test_repeated_fifth_not_parallel_motion(self):
        r=pair_motion(('C',0,4),('G',0,4),('C',0,4),('G',0,4))
        self.assertEqual(r['motion'],'stationary')
        self.assertIsNone(r['parallel_perfect_family'])

    def test_perfect_vs_diminished(self):
        r=pair_motion(('C',0,4),('G',0,4),('D',0,4),('A',-1,4))
        self.assertEqual(r['motion'],'parallel')
        self.assertIsNone(r['parallel_perfect_family'])

    def test_octave_observation_not_violation(self):
        r=pair_motion(('C',0,3),('C',0,4),('D',0,3),('D',0,4))
        self.assertEqual(r['parallel_perfect_family'],'unison_octave')
        self.assertIsNone(r['style_violation'])

    def test_overlap_not_crossing(self):
        r=pair_motion(('C',0,4),('E',0,4),('F',0,4),('A',0,4))
        self.assertTrue(r['lower_above_previous_upper'])
        self.assertFalse(r['crossed_after'])

    def test_crossing_keeps_identity(self):
        r=pair_motion(('C',0,4),('E',0,4),('G',0,4),('D',0,4))
        self.assertTrue(r['crossed_after'])
        self.assertEqual(r['motion'],'contrary')

    def test_similar_arrival(self):
        r=pair_motion(('C',0,3),('B',0,3),('D',0,3),('D',0,4))
        self.assertEqual(r['motion'],'similar')
        self.assertEqual(r['similar_arrival_perfect_family'],'unison_octave')


if __name__ == '__main__':unittest.main()
