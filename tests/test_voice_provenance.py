import unittest
import tempfile
from pathlib import Path
from music21 import stream, note, chord, converter
from musicanote_harness.canonical import _voice_id, CanonicalIRBuilder
from musicanote_harness.voice_provenance import containing_voice, parser_voice_inventory, assess


class VoiceProvenanceTest(unittest.TestCase):
    def score(self):
        s = stream.Score(); p = stream.Part(id='P1'); s.append(p)
        m = stream.Measure(number=1)
        for v in ('1', '2'):
            voice = stream.Voice(id=v); voice.append(note.Note('C4', quarterLength=4)); m.insert(0, voice)
        p.append(m)
        m = stream.Measure(number=2); n = note.Note('D4', quarterLength=4); m.append(n); p.append(m)
        return s, p, n

    def test_previous_measure_voice_leak_reproduced(self):
        s, p, n = self.score()
        list(p.recurse().notesAndRests)
        self.assertEqual(_voice_id(n), '2')
        self.assertEqual(containing_voice(n), {'voice': None, 'basis': 'no_voice_container_in_measure'})

    def test_explicit_voice(self):
        v = stream.Voice(id='6'); n = note.Note(); v.append(n)
        self.assertEqual(containing_voice(n)['voice'], '6')

    def test_rest(self):
        m = stream.Measure(); r = note.Rest(); m.append(r)
        self.assertIsNone(containing_voice(r)['voice'])

    def test_chord_uses_container_not_member_context(self):
        s = stream.Score(); p = stream.Part(id='P1'); s.append(p)
        m = stream.Measure(number=1); p.append(m)
        v = stream.Voice(id='5'); m.insert(0, v); v.append(chord.Chord(['C4', 'E4']))
        rows = parser_voice_inventory(s)
        self.assertEqual(len(rows), 2)
        self.assertEqual({r['voice'] for r in rows.values()}, {'5'})

    def test_detached_not_guessed(self):
        self.assertEqual(containing_voice(note.Note())['basis'], 'no_voice_container')

    def test_unnamed_voice_not_object_address(self):
        v = stream.Voice(); n = note.Note(); v.append(n)
        self.assertIsNone(containing_voice(n)['voice'])

    def test_nested_stream(self):
        v = stream.Voice(id='3'); inner = stream.Stream(); v.append(inner)
        n = note.Note(); inner.append(n)
        self.assertEqual(containing_voice(n)['voice'], '3')

    def test_unverified_never_proposes_voice(self):
        result = assess('2', {'voice': None, 'basis': 'no_voice_container_in_measure'}, '1', False)
        self.assertIsNone(result['proposed_source_voice'])

    def test_verified_xml_not_context_is_proposal_source(self):
        result = assess('2', {'voice': None, 'basis': 'no_voice_container_in_measure'}, '1', True)
        self.assertEqual(result['category'], 'context_voice_without_container')
        self.assertTrue(result['legacy_xml_disagreement'])
        self.assertEqual(result['proposed_source_voice'], '1')

    def test_missing_xml_voice_not_defaulted_to_one(self):
        result = assess('voice_0', {'voice': None, 'basis': 'no_voice_container_in_measure'}, None, True)
        self.assertIsNone(result['proposed_source_voice'])

    def test_explicit_conflict_not_hidden(self):
        self.assertEqual(assess('2', {'voice': '2', 'basis': 'containing_voice'}, '1', True)['category'],
                         'explicit_container_xml_conflict')

    def test_deterministic_inventory(self):
        s, _, _ = self.score()
        self.assertEqual(parser_voice_inventory(s), parser_voice_inventory(s))

    def test_musicxml_single_voice_loses_container_not_xml_label(self):
        xml = '''<score-partwise version="4.0"><part-list><score-part id="P1">
        <part-name>Piano</part-name></score-part></part-list><part id="P1">
        <measure number="1"><attributes><divisions>1</divisions>
        <time><beats>4</beats><beat-type>4</beat-type></time></attributes>
        <note><pitch><step>C</step><octave>4</octave></pitch><duration>4</duration><voice>1</voice></note>
        <backup><duration>4</duration></backup>
        <note><pitch><step>E</step><octave>3</octave></pitch><duration>4</duration><voice>2</voice></note>
        </measure><measure number="2">
        <note><pitch><step>D</step><octave>4</octave></pitch><duration>4</duration><voice>1</voice></note>
        </measure></part></score-partwise>'''
        s = converter.parseData(xml, format='musicxml')
        notes = list(s.parts[0].recurse().notes)
        n = notes[-1]
        self.assertIsInstance(n.activeSite, stream.Measure)
        self.assertEqual(_voice_id(n), '2')
        self.assertIsNone(containing_voice(n)['voice'])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'fixture.musicxml'; path.write_text(xml, encoding='utf-8')
            before = CanonicalIRBuilder().build(s, path)
            observations = parser_voice_inventory(s)
            after = CanonicalIRBuilder().build(s, path)
        self.assertEqual(before, after)
        self.assertEqual(set(observations), {r['segment_id'] for r in before['notated_note_segments']})

    def test_separate_parts_keep_independent_voice_scopes(self):
        s = stream.Score()
        for pid in ('P1', 'P2'):
            p = stream.Part(id=pid); s.append(p); m = stream.Measure(number=1); p.append(m)
            v = stream.Voice(id='1'); m.insert(0, v); v.append(note.Note('C4'))
        self.assertEqual(len(parser_voice_inventory(s)), 2)

    def test_duplicate_part_labels_preserve_distinct_fingerprints(self):
        s = stream.Score()
        for _ in range(2):
            p = stream.Part(id='Piano'); s.append(p); m = stream.Measure(number=1); p.append(m)
            m.append(note.Note('C4'))
        self.assertEqual(len(parser_voice_inventory(s)), 2)

    def test_score_boundary_does_not_search_other_part(self):
        p = stream.Part(); n = note.Note(); p.append(n)
        self.assertEqual(containing_voice(n)['basis'], 'no_voice_container')


if __name__ == '__main__':
    unittest.main()
