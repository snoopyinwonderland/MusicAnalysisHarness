import hashlib
import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree as ET

from jsonschema import Draft202012Validator
from musicanote_harness.dcml_import import parse_score_without_imported_harmony
from musicanote_harness.canonical import CanonicalIRBuilder
from musicanote_harness.formal_ir import FormalIRAdapter, q
from musicanote_harness.source_locator_revision import revise, validate_revision
from musicanote_harness import source_locator_revision as module


SCHEMA = Path(__file__).resolve().parents[1] / 'MUSICANOTE_Canonical_Music_IR/schemas/canonical_music_ir.schema.json'
XML = '''<score-partwise version="4.0"><part-list><score-part id="P1"><part-name>Piano</part-name></score-part></part-list>
<part id="P1"><measure number="1"><attributes><divisions>4</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes>
<note><pitch><step>C</step><octave>4</octave></pitch><duration>4</duration><voice>1</voice><type>quarter</type><stem>up</stem></note>
<note><pitch><step>D</step><alter>1</alter><octave>4</octave></pitch><duration>2</duration><voice>1</voice><type>eighth</type><accidental>sharp</accidental><stem>down</stem><beam number="1">begin</beam><notations><slur number="1" type="start"/></notations></note>
<note><pitch><step>E</step><octave>4</octave></pitch><duration>2</duration><voice>1</voice><type>eighth</type><stem>down</stem><beam number="1">end</beam><notations><articulations><staccato/></articulations><slur number="1" type="stop"/></notations></note>
<note><grace slash="yes"/><pitch><step>A</step><octave>4</octave></pitch><voice>1</voice><type>16th</type></note>
<note><pitch><step>F</step><octave>4</octave></pitch><duration>8</duration><voice>1</voice><type>half</type><notations><fermata/></notations></note>
</measure><measure number="2"><note><pitch><step>C</step><octave>4</octave></pitch><duration>8</duration><tie type="start"/><voice>1</voice><type>half</type></note>
<note><pitch><step>C</step><octave>4</octave></pitch><duration>8</duration><tie type="stop"/><voice>1</voice><type>half</type></note>
</measure><measure number="3"><note><rest/><duration>16</duration><voice>1</voice><type>whole</type></note></measure></part></score-partwise>'''


def short_xml(notes):
    return '''<score-partwise version="4.0"><part-list><score-part id="P1"><part-name>Piano</part-name></score-part></part-list>
<part id="P1"><measure number="1"><attributes><divisions>4</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes>''' + notes + '</measure></part></score-partwise>'


class SourceLocatorRevisionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.counter = 0
        self.source, self.old = self.make(XML)
        self.validator = Draft202012Validator(json.loads(SCHEMA.read_text(encoding='utf-8')))

    def make(self, xml):
        self.counter += 1
        source = Path(self.temp.name) / ('fixture-' + str(self.counter) + '.musicxml')
        source.write_text(xml, encoding='utf-8')
        score, _, _ = parse_score_without_imported_harmony(source)
        old = FormalIRAdapter().convert(CanonicalIRBuilder().build(score, source), source)
        return source, old

    def ready(self, old=None, source=None):
        old = self.old if old is None else old; source = self.source if source is None else source
        candidate, report = revise(old, source)
        self.assertEqual(report['status'], 'candidate_ready', report)
        self.assertIsNotNone(candidate); self.validator.validate(candidate)
        validate_revision(old, candidate)
        return candidate, report

    def duplicate_printed_fixture(self, same_pitch):
        first = '<note><pitch><step>C</step><octave>4</octave></pitch><duration>16</duration><voice>1</voice><type>whole</type></note>'
        second = first if same_pitch else first.replace('<step>C</step>', '<step>E</step>')
        xml = short_xml(first).replace('</measure></part>',
              '</measure><measure number="2">' + second + '</measure></part>')
        source, old = self.make(xml)
        # Keep independent, stable measure IDs from a valid two-measure fixture;
        # simulate a legacy source whose printed labels are both "1".
        source.write_text(xml.replace('<measure number="2">', '<measure number="1">'), encoding='utf-8')
        old['source_files'][0]['sha256'] = hashlib.sha256(source.read_bytes()).hexdigest()
        for measure in old['measures']: measure['printed_measure_number'] = '1'
        for ref in old['source_references']: ref['source_measure_number'] = '1'
        self.validator.validate(old)
        return source, old

    def test_success_preserves_source_old_and_all_core_entities(self):
        before = deepcopy(self.old); raw = self.source.read_bytes()
        candidate, _ = self.ready()
        self.assertNotEqual(candidate['ir_document_id'], self.old['ir_document_id'])
        for key in ('score', 'source_files', 'parts', 'staves', 'voices', 'measures', 'rest_events',
                    'sounding_events', 'tie_chains', 'attack_events', 'chord_onset_groups',
                    'extensions', 'parser_manifest', 'validation_summary'):
            with self.subTest(key=key): self.assertEqual(candidate[key], self.old[key])
        self.assertEqual(self.old, before); self.assertEqual(self.source.read_bytes(), raw)

    def test_before_missing_locator_after_exact_for_all_notes(self):
        _, report = self.ready()
        ids = {note['note_id'] for note in self.old['note_events']}
        self.assertEqual(set(report['before_checks']), ids); self.assertEqual(set(report['after_checks']), ids)
        self.assertTrue(all(row['status'] == 'missing_locator' for row in report['before_checks'].values()))
        self.assertTrue(all(row['status'] == 'exact' for row in report['after_checks'].values()))

    def test_locator_fields_match_physical_note_ordinal_and_raw_lane(self):
        candidate, _ = self.ready(); refs = {ref['source_ref_id']: ref for ref in candidate['source_references']}
        first_measure = [note for note in candidate['note_events'] if note['measure_id'] == candidate['measures'][0]['measure_id']]
        for note in first_measure:
            ref = refs[note['source_ref_id']]
            self.assertEqual(ref['source_part_id'], 'P1'); self.assertEqual(ref['source_voice'], '1')
            self.assertEqual(ref['source_staff'], 1); self.assertEqual(ref['source_measure_number'], '1')
            self.assertEqual(ref['source_xpath'], '/score-partwise/part[1]/measure[1]/note[' + str(ref['source_element_index'] + 1) + ']')
        self.assertEqual(sorted(refs[note['source_ref_id']]['source_element_index'] for note in first_measure), list(range(5)))

    def test_stale_xpath_is_repaired_not_used_as_mapping_fallback(self):
        refs = {ref['source_ref_id']: ref for ref in self.old['source_references']}
        for note in self.old['note_events']:
            refs[note['source_ref_id']]['source_xpath'] = '/score-partwise/part[1]/measure[1]/note[1]'
        candidate, report = self.ready()
        self.assertTrue(any(row['status'] == 'mismatch' for row in report['before_checks'].values()))
        self.assertTrue(all(row['status'] == 'exact' for row in report['after_checks'].values()))
        self.assertEqual(len({ref['source_xpath'] for ref in candidate['source_references'] if ref['source_xpath']}), len(candidate['note_events']))

    def test_notation_fields_and_grace_slash_are_source_observations(self):
        candidate, _ = self.ready()
        ds = next(note for note in candidate['note_events'] if note['written_pitch']['step'] == 'D')
        e = next(note for note in candidate['note_events'] if note['written_pitch']['step'] == 'E')
        f_note = next(note for note in candidate['note_events'] if note['written_pitch']['step'] == 'F')
        grace = next(note for note in candidate['note_events'] if note['grace']['is_grace'])
        self.assertEqual(ds['notation']['accidental_display'], 'sharp')
        self.assertEqual(ds['notation']['stem'], 'down')
        self.assertEqual(ds['notation']['beams'], [{'number': '1', 'value': 'begin'}])
        self.assertIn('staccato', e['notation']['articulations'])
        self.assertEqual(ds['notation']['slurs'], [{'number': '1', 'type': 'start'}])
        self.assertTrue(f_note['notation']['fermata']); self.assertTrue(grace['grace']['slash'])

    def test_note_core_pitch_time_voice_tie_and_grace_role_unchanged(self):
        candidate, _ = self.ready(); old_by_id = {note['note_id']: note for note in self.old['note_events']}
        for note in candidate['note_events']:
            previous = old_by_id[note['note_id']]
            for key in set(previous) - {'notation', 'grace'}:
                with self.subTest(note=note['note_id'], key=key): self.assertEqual(note[key], previous[key])
            self.assertEqual({key: value for key, value in note['grace'].items() if key != 'slash'},
                             {key: value for key, value in previous['grace'].items() if key != 'slash'})

    def test_changed_ids_report_actual_note_and_ref_diffs(self):
        candidate, report = self.ready()
        old_notes = {note['note_id']: note for note in self.old['note_events']}
        old_refs = {ref['source_ref_id']: ref for ref in self.old['source_references']}
        self.assertEqual(set(report['changed_note_ids']), {note['note_id'] for note in candidate['note_events']
                                                        if note != old_notes[note['note_id']]})
        self.assertEqual(set(report['changed_source_ref_ids']), {ref['source_ref_id'] for ref in candidate['source_references']
                                                              if ref != old_refs[ref['source_ref_id']]})

    def test_revision_deterministic_and_return_mutation_cannot_touch_old(self):
        first, report1 = self.ready(); second, report2 = self.ready(); before = deepcopy(self.old)
        self.assertEqual(first, second); self.assertEqual(report1, report2); json.dumps((first, report1))
        first['note_events'][0]['notation']['stem'] = 'changed'
        first['source_references'][0]['source_xpath'] = 'changed'
        self.assertEqual(self.old, before)

    def test_source_hash_mismatch_raises_before_mapping(self):
        self.source.write_bytes(self.source.read_bytes() + b'\n<!--changed-->')
        before = deepcopy(self.old)
        with self.assertRaisesRegex(ValueError, 'source_hash_mismatch'): revise(self.old, self.source)
        self.assertEqual(self.old, before)

    def test_old_source_digest_mismatch_is_rejected(self):
        self.old['source_files'][0]['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'source_hash_mismatch'): revise(self.old, self.source)

    def test_duplicate_note_ids_fail_without_mutation(self):
        self.old['note_events'][1]['note_id'] = self.old['note_events'][0]['note_id']; before = deepcopy(self.old)
        with self.assertRaises(ValueError): revise(self.old, self.source)
        self.assertEqual(self.old, before)

    def test_duplicate_source_ref_ids_fail_without_mutation(self):
        self.old['source_references'].append(deepcopy(self.old['source_references'][0])); before = deepcopy(self.old)
        with self.assertRaises(ValueError): revise(self.old, self.source)
        self.assertEqual(self.old, before)

    def test_wrong_note_geometry_blocked_even_with_plausible_stale_xpath(self):
        for kind in ('duration', 'onset', 'pitch', 'tie', 'grace'):
            old = deepcopy(self.old); note = old['note_events'][0]
            ref = next(ref for ref in old['source_references'] if ref['source_ref_id'] == note['source_ref_id'])
            ref['source_xpath'] = '/score-partwise/part[1]/measure[1]/note[1]'
            if kind == 'duration': note['notated_duration_quarter'] = q(2)
            elif kind == 'onset': note['onset_in_measure'] = q('1/3')
            elif kind == 'pitch': note['written_pitch']['octave'] += 1
            elif kind == 'tie': note['tie_role'] = 'stop'
            else: note['grace']['is_grace'] = True
            before = deepcopy(old)
            with self.subTest(kind=kind):
                candidate, report = revise(old, self.source)
                self.assertIsNone(candidate); self.assertEqual(report['status'], 'blocked'); self.assertTrue(report['blockers'])
                self.assertEqual(old, before)

    def test_identical_unison_same_lane_ambiguous_despite_stale_locators(self):
        source, old = self.make(short_xml('''<note><pitch><step>D</step><octave>4</octave></pitch><duration>4</duration><voice>1</voice><type>quarter</type></note>
<backup><duration>4</duration></backup><note><pitch><step>D</step><octave>4</octave></pitch><duration>4</duration><voice>1</voice><type>quarter</type></note>'''))
        for index, ref in enumerate(old['source_references'], 1):
            ref['source_xpath'] = '/score-partwise/part[1]/measure[1]/note[' + str(index) + ']'
        candidate, report = revise(old, source)
        self.assertIsNone(candidate); self.assertEqual(report['status'], 'blocked'); self.assertTrue(report['blockers'])

    def test_identical_sequential_graces_ambiguous_not_order_tiebroken(self):
        source, old = self.make(short_xml('''<note><grace/><pitch><step>D</step><octave>4</octave></pitch><voice>1</voice><type>eighth</type></note>
<note><grace/><pitch><step>D</step><octave>4</octave></pitch><voice>1</voice><type>eighth</type></note>
<note><pitch><step>E</step><octave>4</octave></pitch><duration>4</duration><voice>1</voice><type>quarter</type></note>'''))
        candidate, report = revise(old, source)
        self.assertIsNone(candidate); self.assertEqual(report['status'], 'blocked'); self.assertTrue(report['blockers'])

    def test_grace_and_principal_same_pitch_same_onset_not_swapped(self):
        source, old = self.make(short_xml('''<note><grace slash="yes"/><pitch><step>D</step><octave>4</octave></pitch><voice>1</voice><type>eighth</type></note>
<note><pitch><step>D</step><octave>4</octave></pitch><duration>4</duration><voice>1</voice><type>quarter</type></note>'''))
        candidate, report = self.ready(old, source)
        refs = {ref['source_ref_id']: ref for ref in candidate['source_references']}
        for note in candidate['note_events']:
            expected = 1 if note['grace']['is_grace'] else 2
            self.assertTrue(refs[note['source_ref_id']]['source_xpath'].endswith('/note[' + str(expected) + ']'))
            self.assertEqual(report['after_checks'][note['note_id']]['status'], 'exact')

    def test_exact_triplet_duration_not_rounded_for_locator_mapping(self):
        source, old = self.make(short_xml('''<note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice><type>16th</type></note>''').replace('<divisions>4</divisions>', '<divisions>3</divisions>').replace('<type>16th</type>', '<type>eighth</type><time-modification><actual-notes>3</actual-notes><normal-notes>2</normal-notes></time-modification>'))
        candidate, report = self.ready(old, source)
        self.assertEqual(candidate['note_events'][0]['notated_duration_quarter'], q('1/3'))
        self.assertEqual(report['after_checks'][candidate['note_events'][0]['note_id']]['status'], 'exact')

    def test_rest_and_unrelated_ref_content_not_rewritten(self):
        candidate, _ = self.ready(); rest_ids = {rest['source_ref_id'] for rest in self.old['rest_events']}
        old_refs = {ref['source_ref_id']: ref for ref in self.old['source_references']}
        self.assertTrue(rest_ids)
        for ref in candidate['source_references']:
            if ref['source_ref_id'] in rest_ids: self.assertEqual(ref, old_refs[ref['source_ref_id']])

    def test_validate_revision_rejects_core_and_ref_changes_independently(self):
        candidate, _ = self.ready()
        mutations = {
            'score': lambda ir: ir['score'].__setitem__('title', 'different'),
            'duration': lambda ir: ir['note_events'][0].__setitem__('notated_duration_quarter', q(2)),
            'onset': lambda ir: ir['note_events'][0].__setitem__('onset_in_measure', q(1)),
            'global': lambda ir: ir['note_events'][0].__setitem__('global_onset_quarter', q(1)),
            'voice': lambda ir: ir['note_events'][0].__setitem__('voice_id', 'other-voice'),
            'written_pitch': lambda ir: ir['note_events'][0]['written_pitch'].__setitem__('octave', 5),
            'concert_pitch': lambda ir: ir['note_events'][0]['concert_pitch'].__setitem__('octave', 5),
            'tie': lambda ir: ir['note_events'][0].__setitem__('tie_role', 'start'),
            'grace_role': lambda ir: ir['note_events'][0]['grace'].__setitem__('is_grace', True),
            'grace_anchor': lambda ir: ir['note_events'][0]['grace'].__setitem__('anchor_note_id', 'different'),
            'note_id': lambda ir: ir['note_events'][0].__setitem__('note_id', 'different'),
            'source_ref_id': lambda ir: ir['note_events'][0].__setitem__('source_ref_id', 'different'),
            'source_file': lambda ir: ir['source_files'][0].__setitem__('original_name', 'different'),
            'ref_hash': lambda ir: ir['source_references'][0].__setitem__('local_fingerprint', 'different'),
            'ref_identity': lambda ir: ir['source_references'][0].__setitem__('source_ref_id', 'different'),
            'meter': lambda ir: ir['measures'][0]['time_signature'].__setitem__('beats', 3),
            'sounds': lambda ir: ir['sounding_events'][0]['span'].__setitem__('end', q(9)),
            'attacks': lambda ir: ir['attack_events'][0].__setitem__('global_onset_quarter', q(9)),
            'voices': lambda ir: ir['voices'][0].__setitem__('source_voice_number', '9'),
            'extensions': lambda ir: ir['extensions'].append({'name': 'test', 'payload': {}}),
        }
        for key, mutate in mutations.items():
            changed = deepcopy(candidate); mutate(changed)
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'forbidden_revision_change'):
                validate_revision(self.old, changed)

    def test_validate_revision_forbids_arbitrary_note_notation_analysis(self):
        candidate, _ = self.ready(); candidate['note_events'][0]['notation']['roman_numeral'] = 'V7'
        with self.assertRaisesRegex(ValueError, 'forbidden_revision_change'): validate_revision(self.old, candidate)

    def test_source_namespace_supported_without_changing_source(self):
        # The existing music21 loader cannot ingest a namespaced root. Exercise
        # this revision's raw namespace handling with equivalent full IR instead.
        source = Path(self.temp.name) / 'namespaced.musicxml'
        source.write_text(XML.replace('<score-partwise version="4.0">',
                          '<score-partwise xmlns="http://www.musicxml.org/ns/musicxml" version="4.0">'), encoding='utf-8')
        old = deepcopy(self.old); old['source_files'][0]['sha256'] = hashlib.sha256(source.read_bytes()).hexdigest()
        before = source.read_bytes(); self.ready(old, source)
        self.assertEqual(source.read_bytes(), before)

    def test_missing_shared_or_wrong_file_note_references_rejected_upfront(self):
        for kind in ('missing', 'shared', 'wrong-file'):
            old = deepcopy(self.old)
            if kind == 'missing': old['note_events'][0]['source_ref_id'] = 'missing'
            elif kind == 'shared': old['note_events'][1]['source_ref_id'] = old['note_events'][0]['source_ref_id']
            else:
                ref = next(ref for ref in old['source_references']
                           if ref['source_ref_id'] == old['note_events'][0]['source_ref_id'])
                ref['source_file_id'] = 'wrong-file'
            before = deepcopy(old)
            with self.subTest(kind=kind), self.assertRaises(ValueError): revise(old, self.source)
            self.assertEqual(old, before)

    def test_independent_geometry_recheck_blocks_falsely_complete_mapper(self):
        before = deepcopy(self.old); actual_mapper = module.musicxml_with_canonical_ids
        def swapped(source, ir):
            mapped, report = actual_mapper(source, ir)
            root = ET.fromstring(mapped); notes = list(root.iter('note'))
            first, second = notes[0].get('id'), notes[1].get('id')
            notes[0].set('id', second); notes[1].set('id', first)
            self.assertTrue(report['complete'])
            return ET.tostring(root, encoding='unicode'), report
        with patch.object(module, 'musicxml_with_canonical_ids', side_effect=swapped):
            candidate, report = revise(self.old, self.source)
        self.assertIsNone(candidate); self.assertEqual(report['status'], 'blocked')
        self.assertIn('independent_source_note_geometry_mismatch', report['blockers'])
        self.assertTrue(any(row['status'] == 'mismatch' for row in report['after_checks'].values()))
        self.assertEqual(self.old, before)

    def test_source_mutation_during_computation_blocks_candidate(self):
        before = deepcopy(self.old); actual_mapper = module.musicxml_with_canonical_ids
        def changed(source, ir):
            # Simulates an outside writer after the initial immutable snapshot.
            self.source.write_bytes(self.source.read_bytes() + b'\n<!--external-change-->')
            return actual_mapper(source, ir)
        with patch.object(module, 'musicxml_with_canonical_ids', side_effect=changed):
            candidate, report = revise(self.old, self.source)
        self.assertIsNone(candidate); self.assertEqual(report['status'], 'blocked')
        self.assertIn('source_changed_during_revision', report['blockers'])
        self.assertEqual(self.old, before)

    def test_unique_geometry_preserves_legacy_voice_and_unrelated_notation(self):
        self.old['voices'][0]['source_voice_number'] = '9'
        self.old['note_events'][0]['notation']['legacy_expression'] = {'text': 'keep exactly'}
        before = deepcopy(self.old); candidate, report = self.ready()
        self.assertEqual(candidate['voices'], self.old['voices'])
        self.assertEqual(candidate['note_events'][0]['voice_id'], self.old['note_events'][0]['voice_id'])
        self.assertEqual(candidate['note_events'][0]['notation']['legacy_expression'], {'text': 'keep exactly'})
        note_ref = candidate['note_events'][0]['source_ref_id']
        self.assertEqual(next(ref for ref in candidate['source_references'] if ref['source_ref_id'] == note_ref)['source_voice'], '1')
        self.assertTrue(report['mapping']['voice_hint_disagreements'])
        self.assertEqual(self.old, before)

    def test_validate_revision_rejects_bool_to_int_in_immutable_metadata(self):
        self.old['score']['metadata']['flag'] = True
        candidate, _ = self.ready(); before = module.canonical_bytes(self.old)
        candidate['score']['metadata']['flag'] = 1
        # Python dict equality alone considers True and 1 equal.
        self.assertEqual(candidate['score']['metadata'], self.old['score']['metadata'])
        with self.assertRaisesRegex(ValueError, 'forbidden_revision_change'):
            validate_revision(self.old, candidate)
        self.assertEqual(module.canonical_bytes(self.old), before)

    def test_validate_revision_rejects_float_to_int_in_immutable_metadata(self):
        self.old['score']['metadata']['value'] = 1.0
        candidate, _ = self.ready(); before = module.canonical_bytes(self.old)
        candidate['score']['metadata']['value'] = 1
        self.assertEqual(candidate['score']['metadata'], self.old['score']['metadata'])
        with self.assertRaisesRegex(ValueError, 'forbidden_revision_change'):
            validate_revision(self.old, candidate)
        self.assertEqual(module.canonical_bytes(self.old), before)

    def test_changes_distinguishes_missing_and_null_with_exact_pointers(self):
        cases = [({}, {'a/b~c': None}, False, True),
                 ({'a/b~c': None}, {}, True, False)]
        for old, new, before_present, after_present in cases:
            before = (module.canonical_bytes(old), module.canonical_bytes(new))
            with self.subTest(before_present=before_present):
                self.assertEqual(module.changes(old, new), [{
                    'pointer': '/a~1b~0c', 'before_present': before_present,
                    'after_present': after_present, 'before': None, 'after': None,
                }])
                self.assertEqual((module.canonical_bytes(old), module.canonical_bytes(new)), before)
        self.assertEqual(module.changes({'value': None}, {'value': None}), [])

    def test_changes_distinguishes_bool_int_and_float_in_nested_values(self):
        for old_value, new_value in ((True, 1), (1, True), (1.0, 1), (1, 1.0)):
            old = {'nested': [old_value]}; new = {'nested': [new_value]}
            before = (module.canonical_bytes(old), module.canonical_bytes(new))
            with self.subTest(old_type=type(old_value).__name__, new_type=type(new_value).__name__):
                changes = module.changes(old, new)
                self.assertEqual(len(changes), 1)
                self.assertEqual(changes[0]['pointer'], '/nested/0')
                self.assertTrue(changes[0]['before_present']); self.assertTrue(changes[0]['after_present'])
                self.assertIs(type(changes[0]['before']), type(old_value))
                self.assertIs(type(changes[0]['after']), type(new_value))
                self.assertEqual((module.canonical_bytes(old), module.canonical_bytes(new)), before)

    def test_malformed_source_with_matching_hash_blocks_without_mutation(self):
        malformed = b'<score-partwise version="4.0"><part'
        self.source.write_bytes(malformed)
        self.old['source_files'][0]['sha256'] = hashlib.sha256(malformed).hexdigest()
        before = module.canonical_bytes(self.old); self.validator.validate(self.old)
        with patch.object(module, 'musicxml_with_canonical_ids') as mapper:
            candidate, report = revise(self.old, self.source)
        self.assertIsNone(candidate); self.assertEqual(report['status'], 'blocked')
        self.assertTrue(report['blockers']); self.assertEqual(report['before_checks'], {})
        self.assertEqual(report['after_checks'], {}); mapper.assert_not_called()
        self.assertEqual(module.canonical_bytes(self.old), before)
        self.assertEqual(self.source.read_bytes(), malformed); json.dumps(report)

    def test_mapper_mutating_private_ir_cannot_change_parent_or_candidate_core(self):
        expected, _ = self.ready(); before = module.canonical_bytes(self.old)
        raw = self.source.read_bytes(); actual_mapper = module.musicxml_with_canonical_ids
        def mutating_mapper(source, ir):
            self.assertIsNot(ir, self.old)
            self.assertIsNot(ir['score']['metadata'], self.old['score']['metadata'])
            self.assertIsNot(ir['note_events'][0]['written_pitch'], self.old['note_events'][0]['written_pitch'])
            mapped, report = actual_mapper(source, ir)
            ir['score']['metadata']['mapper_only'] = {'flag': True}
            ir['note_events'][0]['note_id'] = 'mapper-only-id'
            ir['note_events'][0]['written_pitch']['step'] = 'B'
            ir['source_references'][0]['source_ref_id'] = 'mapper-only-ref'
            return mapped, report
        with patch.object(module, 'musicxml_with_canonical_ids', side_effect=mutating_mapper):
            candidate, report = self.ready()
        self.assertEqual(module.canonical_bytes(candidate), module.canonical_bytes(expected))
        self.assertEqual(module.canonical_bytes(self.old), before)
        self.assertEqual(self.source.read_bytes(), raw); json.dumps((candidate, report))

    def test_duplicate_printed_numbers_identical_geometry_not_order_tiebroken(self):
        source, old = self.duplicate_printed_fixture(same_pitch=True)
        refs = {ref['source_ref_id']: ref for ref in old['source_references']}
        for index, note in enumerate(old['note_events'], 1):
            refs[note['source_ref_id']]['source_xpath'] = '/score-partwise/part[1]/measure[' + str(index) + ']/note[1]'
        before = module.canonical_bytes(old); raw = source.read_bytes()
        candidate, report = revise(old, source)
        self.assertIsNone(candidate); self.assertEqual(report['status'], 'blocked')
        self.assertFalse(report['mapping']['complete'])
        self.assertIn('incomplete_or_ambiguous_note_mapping', report['blockers'])
        self.assertEqual(report['after_checks'], {})
        self.assertEqual(module.canonical_bytes(old), before); self.assertEqual(source.read_bytes(), raw)

    def test_duplicate_printed_numbers_unique_geometry_rechecked_by_physical_order(self):
        source, old = self.duplicate_printed_fixture(same_pitch=False)
        before = module.canonical_bytes(old); candidate, report = self.ready(old, source)
        refs = {ref['source_ref_id']: ref for ref in candidate['source_references']}
        self.assertTrue(report['mapping']['complete'])
        self.assertEqual(len({m['measure_id'] for m in old['measures']}), 2)
        self.assertEqual([m['printed_measure_number'] for m in candidate['measures']], ['1', '1'])
        for index, note in enumerate(candidate['note_events'], 1):
            self.assertEqual(refs[note['source_ref_id']]['source_xpath'],
                             '/score-partwise/part[1]/measure[' + str(index) + ']/note[1]')
            self.assertTrue(report['after_checks'][note['note_id']]['checks']['physical_measure'])
        self.assertEqual(module.canonical_bytes(old), before)

    def test_independent_physical_order_rejects_unique_mapping_with_duplicate_printed_numbers(self):
        source, old = self.duplicate_printed_fixture(same_pitch=False)
        first, second = old['measures']
        first['sequential_measure_index'], second['sequential_measure_index'] = (
            second['sequential_measure_index'], first['sequential_measure_index'])
        before = module.canonical_bytes(old); raw = source.read_bytes()
        candidate, report = revise(old, source)
        self.assertIsNone(candidate); self.assertEqual(report['status'], 'blocked')
        self.assertTrue(report['mapping']['complete'])
        self.assertIn('independent_source_note_geometry_mismatch', report['blockers'])
        self.assertTrue(all(row['status'] == 'mismatch' for row in report['after_checks'].values()))
        self.assertTrue(all(not row['checks']['physical_measure'] for row in report['after_checks'].values()))
        self.assertEqual(module.canonical_bytes(old), before); self.assertEqual(source.read_bytes(), raw)


if __name__ == '__main__': unittest.main()
