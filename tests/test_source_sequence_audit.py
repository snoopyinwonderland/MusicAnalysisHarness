import tempfile
import unittest
from pathlib import Path
from musicanote_harness.source_sequence_audit import token, xml_rows, parser_rows, match_sequences
from musicanote_harness.dcml_import import parse_score_without_imported_harmony
from musicanote_harness.canonical import CanonicalIRBuilder
from musicanote_harness.formal_ir import FormalIRAdapter


def row(fingerprint, pitch='C', voice='1', onset=0):
    return {'fingerprint': fingerprint, 'xpath': fingerprint, 'part': 'P1', 'measure_index': 1,
            'staff': '1', 'voice': voice, 'global_onset': str(onset),
            'token': token(onset, 0, (pitch, '0', 4), True, 'none')}


class SourceSequenceTest(unittest.TestCase):
    def test_repeated_grace_occurrence_order_retained(self):
        parsed = [row('a'), row('b', 'D'), row('c')]
        xml = [row('xpath1'), row('xpath2', 'D'), row('xpath3')]
        matches, rejected = match_sequences(parsed, xml)
        self.assertEqual([(p['fingerprint'], r['xpath']) for p, r in matches],
                         [('a', 'xpath1'), ('b', 'xpath2'), ('c', 'xpath3')])
        self.assertFalse(rejected)

    def test_reordered_sequence_is_not_matched_by_pitch(self):
        matches, rejected = match_sequences([row('a'), row('b', 'D')], [row('x', 'D'), row('y')])
        self.assertFalse(matches); self.assertEqual(len(rejected), 2)

    def test_missing_event_abstains_for_whole_lane(self):
        matches, rejected = match_sequences([row('a')], [row('x'), row('y')])
        self.assertFalse(matches); self.assertEqual(len(rejected), 1)

    def test_unknown_voice_multiple_lanes_abstains(self):
        matches, rejected = match_sequences([row('a', voice=None)], [row('x'), row('y', voice='2')])
        self.assertFalse(matches); self.assertEqual(rejected[0]['reason'], 'ambiguous_or_missing_source_lane')

    def test_unknown_voice_one_lane_can_match(self):
        self.assertEqual(len(match_sequences([row('a', voice=None)], [row('x')])[0]), 1)

    def test_global_time_mismatch_abstains(self):
        p = row('a'); p['global_onset'] = '4'
        self.assertEqual(match_sequences([p], [row('x')])[1][0]['reason'], 'global_timeline_mismatch')

    def test_tie_role_difference_abstains(self):
        p = row('a'); p['token'] = token(0, 0, ('C', '0', 4), True, 'start')
        self.assertFalse(match_sequences([p], [row('x')])[0])

    def test_duration_difference_abstains(self):
        p = row('a'); p['token'] = token(0, '1/3', ('C', '0', 4), True, 'none')
        self.assertFalse(match_sequences([p], [row('x')])[0])

    def test_rest_distinct_from_note(self):
        p = row('a'); p['token'] = token(0, 0, None, True, 'none')
        self.assertFalse(match_sequences([p], [row('x')])[0])

    def test_enharmonic_spelling_not_collapsed(self):
        p = row('a'); p['token'] = token(0, 0, ('B', '1', 3), True, 'none')
        self.assertFalse(match_sequences([p], [row('x')])[0])

    def test_special_measure_and_grace_replay(self):
        xml = '''<score-partwise version="4.0"><part-list><score-part id="P1">
        <part-name>Piano</part-name></score-part></part-list><part id="P1">
        <measure number="1"><attributes><divisions>3</divisions>
        <time><beats>4</beats><beat-type>4</beat-type></time></attributes>
        <note><pitch><step>C</step><octave>4</octave></pitch><duration>9</duration><voice>1</voice></note>
        </measure><measure number="X1" implicit="yes">
        <note><grace slash="yes"/><pitch><step>D</step><octave>4</octave></pitch><voice>1</voice><type>eighth</type></note>
        <note><grace slash="yes"/><pitch><step>D</step><octave>4</octave></pitch><voice>1</voice><type>eighth</type></note>
        <note><pitch><step>E</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice></note>
        <note><rest/><duration>2</duration><voice>1</voice></note>
        </measure></part></score-partwise>'''
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'fixture.musicxml'; path.write_text(xml, encoding='utf-8')
            s, _, mapping = parse_score_without_imported_harmony(path)
            parsed = parser_rows(s, mapping); original, measures = xml_rows(path)
            matches, rejected = match_sequences(parsed, original)
            legacy = CanonicalIRBuilder().build(s, path)
            ir = FormalIRAdapter().convert(legacy, path)
        self.assertFalse(rejected); self.assertEqual(len(matches), 5)
        self.assertEqual(measures[('P1', 2)]['label'], 'X1')
        self.assertEqual(measures[('P1', 2)]['start'], '3')
        self.assertEqual([r['source_note_ordinal'] for _, r in matches if r['measure_index'] == 2], [1, 2, 3, 4])
        refs = {r['local_fingerprint']: r for r in ir['source_references']}
        self.assertEqual(set(refs), {p['fingerprint'] for p in parsed})


if __name__ == '__main__':
    unittest.main()
