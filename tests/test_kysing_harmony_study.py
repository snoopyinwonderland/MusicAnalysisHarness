import unittest
from musicanote_harness.kysing_harmony_study import analyze


class HarmonyStudyTest(unittest.TestCase):
    def test_incomplete_single_note_is_not_complete_tonic(self):
        frames = [{'frame_id':'a','time':{'numerator':0,'denominator':1},'features':{'active_pitch_classes':['0']}}]
        result = analyze(frames)
        self.assertIsNone(result[0]['confidence'])
        self.assertIsNone(result[0]['selected_hypothesis'])
        for h in result[0]['hypotheses']:
            self.assertFalse(h['dominant_to_tonic_candidate'])
            self.assertTrue(all(not c['complete_template'] for c in h['chord_candidates']))

    def test_extra_lyric_fields_do_not_affect_analysis(self):
        frames = [{'frame_id':'a','time':{'numerator':0,'denominator':1},'features':{'active_pitch_classes':['0','4','7']}}]
        before = analyze(frames)
        frames[0]['lyrics'] = 'Hello, 世界'
        self.assertEqual(before, analyze(frames))
