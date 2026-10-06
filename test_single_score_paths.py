import copy
import unittest
from single_score_paths import paths
from test_single_score_melody_review import note


class PathTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(paths([])['candidates'], [])

    def test_fixed_voice_retains_gap_and_source(self):
        ns = [note(0, 72), note(1, 60), note(2, 74)]
        ns[1]['voice'] = '2'
        original = copy.deepcopy(ns)
        r = paths(ns)
        voice = next(c for c in r['candidates'] if c['name'] == 'source-voice-1')
        self.assertEqual(voice['eventIds'], ['0', '2'])
        self.assertEqual(voice['transitions'][0]['gapQuarters'], '1')
        self.assertEqual(ns, original)
        self.assertTrue(all(not c['selected'] for c in r['candidates']))

    def test_continuity_can_reject_isolated_chord_top(self):
        ns = [note(0, 72), note(1, 74), note(1, 96), note(2, 76)]
        ns[2]['id'] = 'high'
        r = paths(ns)
        low_register = next(c for c in r['candidates'] if c['name'] == 'continuity-register-0.15')
        self.assertNotIn('high', low_register['eventIds'])
        self.assertIn('high', r['candidates'][0]['eventIds'])
        self.assertEqual(r, paths(ns))

    def test_tie_is_not_rearticulated(self):
        ns = [note(0, 72, ties=['start']), note(1, 72, ties=['stop']), note(2, 74)]
        r = paths(ns)
        self.assertEqual(r['candidates'][0]['eventIds'], ['0', '2'])
        self.assertEqual(r['sounding'][0]['sourceIds'], ['0', '1'])


if __name__ == '__main__':
    unittest.main()
