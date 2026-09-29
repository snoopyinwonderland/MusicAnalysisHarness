from copy import deepcopy
import unittest
from musicanote_harness.voice_tie_impact import impact, source_tie_graph


def segment(sid, start, end, voice, role):
    return {'segment_id': sid, 'part_id': 'P1', 'staff_id': '1', 'voice_id': voice,
            'measure': 1 if start == '0' else 2, 'onset_ql': start, 'end_ql': end,
            'pitch_spelling': 'C4', 'midi': 60, 'tie_role': role}


class VoiceTieImpactTest(unittest.TestCase):
    def test_voice_correction_can_restore_chain_without_changing_ids(self):
        notes = [segment('a', '0', '4', '2', 'start'), segment('b', '4', '5', '1', 'stop')]
        original = deepcopy(notes)
        r = impact(notes, {'a': '1', 'b': '1'})
        self.assertEqual(len(r['before']), 2); self.assertEqual(len(r['after']), 1)
        self.assertEqual(r['after'][0]['segment_ids'], ['a', 'b'])
        self.assertFalse(r['after_chain_problems']); self.assertEqual(notes, original)

    def test_gap_not_silently_accepted(self):
        notes = [segment('a', '0', '1', '2', 'start'), segment('b', '4', '5', '1', 'stop')]
        r = impact(notes, {'a': '1', 'b': '1'})
        self.assertIn('noncontiguous', r['after_chain_problems'][0]['reasons'])

    def test_different_source_voices_split_false_chain(self):
        notes = [segment('a', '0', '4', '2', 'start'), segment('b', '4', '5', '2', 'stop')]
        r = impact(notes, {'a': '1', 'b': '2'})
        self.assertEqual(len(r['before']), 1); self.assertEqual(len(r['after']), 2)

    def test_no_tie_does_not_merge_repeated_pitch(self):
        notes = [segment('a', '0', '1', '2', 'none'), segment('b', '1', '2', '1', 'none')]
        self.assertEqual(len(impact(notes, {'a': '1', 'b': '1'})['after']), 2)

    def test_unknown_xml_voice_blocks(self):
        with self.assertRaisesRegex(ValueError, 'unknown_source_voice'):
            impact([segment('a', '0', '1', '2', 'none')], {'a': None})

    def test_source_graph_preserves_unique_cross_voice_tie(self):
        r = source_tie_graph([segment('a', '0', '1', '2', 'start'), segment('b', '1', '2', '1', 'stop')])
        self.assertEqual(r['sounds'][0]['segment_ids'], ['a', 'b'])
        self.assertTrue(r['edges'][0]['voice_changed']); self.assertFalse(r['issues'])

    def test_source_graph_rejects_gap(self):
        r = source_tie_graph([segment('a', '0', '1', '2', 'start'), segment('b', '2', '3', '1', 'stop')])
        self.assertEqual(len(r['sounds']), 2); self.assertEqual(len(r['issues']), 2)

    def test_source_graph_unison_ambiguity_abstains_even_same_voice(self):
        r = source_tie_graph([segment('a', '0', '1', '1', 'start'), segment('b', '0', '1', '2', 'start'),
                              segment('c', '1', '2', '1', 'stop')])
        self.assertFalse(r['edges']); self.assertEqual(len(r['sounds']), 3)

    def test_source_graph_no_tie_across_parts(self):
        a = segment('a', '0', '1', '1', 'start'); b = segment('b', '1', '2', '1', 'stop'); b['part_id'] = 'P2'
        self.assertFalse(source_tie_graph([a, b])['edges'])

    def test_source_graph_cross_staff_unique(self):
        a = segment('a', '0', '1', '1', 'start'); b = segment('b', '1', '2', '1', 'stop'); b['staff_id'] = '2'
        self.assertTrue(source_tie_graph([a, b])['edges'][0]['staff_changed'])

    def test_source_graph_continue_and_zero_grace_no_cycle(self):
        rows = [segment('a', '0', '1', '1', 'start'), segment('b', '1', '2', '2', 'continue'),
                segment('c', '2', '3', '1', 'stop'), segment('g', '3', '3', '1', 'continue')]
        r = source_tie_graph(rows)
        self.assertEqual(r['sounds'][0]['segment_ids'], ['a', 'b', 'c'])
        self.assertEqual(len(r['sounds']), 2)

    def test_zero_grace_tie_cannot_be_bypassed_by_normal_notes(self):
        rows = [segment('a', '0', '2', '1', 'start'), segment('g1', '2', '2', '1', 'stop'),
                segment('g2', '2', '2', '1', 'start'), segment('b', '2', '3', '1', 'stop')]
        r = source_tie_graph(rows)
        self.assertFalse(r['edges']); self.assertEqual(len(r['issues']), 4)
        self.assertEqual(r['grace_barriers'], [['P1', 'C4', '2']])


if __name__ == '__main__': unittest.main()
