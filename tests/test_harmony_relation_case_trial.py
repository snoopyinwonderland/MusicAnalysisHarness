import unittest
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import gzip

from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_relation_case_trial import source_index, trace_note, context, run, witness_note_refs
from musicanote_harness import harmony_geometry_cache_trial as cached_trial
from test_harmony_geometry_cache_trial import reference
from test_harmony_breadth_trial import write_json


XML = b'''<score-partwise version="4.0"><part id="P1"><measure number="0">
<attributes><divisions>3</divisions></attributes>
<note><pitch><step>F</step><alter>1</alter><octave>4</octave></pitch><duration>1</duration><voice>2</voice><staff>1</staff></note>
</measure><measure number="2"><note><pitch><step>G</step><octave>4</octave></pitch><duration>3</duration><voice>2</voice></note></measure>
</part></score-partwise>'''


def fixture():
    note = {'note_id': 'n1', 'source_ref_id': 'r1', 'global_onset_quarter': q(0),
            'notated_duration_quarter': q('1/3'), 'grace': {'is_grace': False},
            'written_pitch': {'step': 'F', 'alter': q(1), 'octave': 4, 'midi_pitch': 66}}
    refs = {'r1': {'source_ref_id': 'r1', 'source_xpath': '/score-partwise/part[1]/measure[1]/note[1]',
            'source_part_id': 'P1', 'source_measure_number': '0', 'source_voice': '2',
            'source_staff': 1, 'source_element_index': 0}}
    return note, refs, source_index(XML)


class SourceContextTests(unittest.TestCase):
    def test_exact_source_fields_and_fractional_duration(self):
        row = trace_note(*fixture())
        self.assertEqual(row['status'], 'source_note_fields_rechecked')
        self.assertEqual(row['observed_notated_duration_quarter'], q('1/3'))
        self.assertFalse(row['xml_onset_reparsed'])
        self.assertFalse(row['concert_pitch_verified'])

    def test_element_index_is_note_ordinal_not_xml_child(self):
        note, refs, index = fixture()
        refs['r1']['source_element_index'] = 1
        self.assertEqual(trace_note(note, refs, index)['status'], 'source_note_field_mismatch')

    def test_inherited_divisions_remains_exact(self):
        index = source_index(XML)
        self.assertEqual(index['/score-partwise/part[1]/measure[2]/note[1]']['divisions'], Fraction(3))

    def test_namespace_source_index(self):
        xml = XML.replace(b'<score-partwise version=', b'<score-partwise xmlns="urn:musicxml" version=')
        self.assertEqual(set(source_index(xml)), set(source_index(XML)))

    def test_written_pitch_is_not_midi_only(self):
        note, refs, index = fixture()
        note['written_pitch'].update(step='G', alter=q(-1))
        row = trace_note(note, refs, index)
        self.assertEqual(row['status'], 'source_note_field_mismatch')
        self.assertFalse(row['checks']['written_pitch'])

    def test_wrong_duration_is_visible(self):
        note, refs, index = fixture(); note['notated_duration_quarter'] = q(1)
        self.assertEqual(trace_note(note, refs, index)['status'], 'source_note_field_mismatch')

    def test_missing_locator_is_not_guessed_by_pitch(self):
        note, refs, index = fixture(); refs['r1']['source_xpath'] = '/bad'
        self.assertEqual(trace_note(note, refs, index)['status'], 'unresolved_locator')

    def test_missing_reference_is_preserved(self):
        note, refs, index = fixture()
        self.assertEqual(trace_note(note, {}, index)['status'], 'unresolved_locator')

    def test_source_microtone_is_not_folded(self):
        note, refs, index = fixture()
        index = source_index(XML.replace(b'<alter>1</alter>', b'<alter>0.5</alter>'))
        self.assertEqual(trace_note(note, refs, index)['status'], 'source_note_probe_unsupported')

    def test_empty_duration_is_not_zero(self):
        note, refs, index = fixture()
        index = source_index(XML.replace(b'<duration>1</duration>', b'<duration/>'))
        self.assertIn('missing_duration', trace_note(note, refs, index)['unsupported'])

    def test_divisions_missing_is_not_defaulted(self):
        note, refs, index = fixture()
        index = source_index(XML.replace(b'<attributes><divisions>3</divisions></attributes>', b''))
        self.assertIn('missing_or_invalid_divisions', trace_note(note, refs, index)['unsupported'])

    def test_grace_without_duration_is_zero_not_bad_xml(self):
        note, refs, index = fixture()
        index = source_index(XML.replace(b'<duration>1</duration>', b'<grace slash="yes"/>'))
        note['grace']['is_grace'] = True; note['notated_duration_quarter'] = q(0)
        self.assertEqual(trace_note(note, refs, index)['status'], 'source_note_fields_rechecked')

    def test_duplicate_source_fields_rejected(self):
        with self.assertRaisesRegex(ValueError, 'duplicate_xml_voice'):
            source_index(XML.replace(b'<voice>2</voice>', b'<voice>2</voice><voice>3</voice>', 1))

    def test_score_timewise_is_explicitly_unsupported(self):
        with self.assertRaisesRegex(ValueError, 'unsupported_source_layout'):
            source_index(b'<score-timewise/>')

    def test_context_keeps_all_parts_padding_and_whole_tie(self):
        note, refs, index = fixture()
        notes = [{**deepcopy(note), 'note_id': 'n'+str(i), 'global_onset_quarter': q(i)} for i in range(5)]
        ir = {'note_events': notes, 'rest_events': [{'rest_id': 'r', 'global_onset_quarter': q(2),
               'notated_duration_quarter': q(1)}], 'source_references': list(refs.values()),
              'measures': [{'measure_id': 'm'+str(i), 'sequential_measure_index': i,
               'global_start_quarter': q(i), 'actual_duration_quarter': q(1)} for i in range(5)],
              'sounding_events': [{'sounding_event_id': 's1', 'source_note_ids': ['n0', 'n4'],
                 'span': {'start': q(0), 'end': q(5)}}]}
        before = deepcopy(ir)
        value = context(ir, {'start': q(2), 'end': q(3)}, index)
        self.assertEqual(value['span'], {'start': q(1), 'end': q(4)})
        self.assertEqual({n['note_id'] for n in value['note_events']}, {'n0', 'n1', 'n2', 'n3', 'n4'})
        self.assertEqual(value['sounding_events'][0]['span'], {'start': q(0), 'end': q(5)})
        self.assertEqual(len(value['rest_events']), 1)
        self.assertTrue(value['all_parts_preserved']); self.assertFalse(value['event_spans_clipped'])
        self.assertEqual(ir, before)

    def test_existing_output_never_overwritten(self):
        with TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, 'output_exists_no_overwrite'):
                run(Path(tmp)/'missing', Path(tmp)/'missing', Path(tmp))


class FrozenRunnerTests(unittest.TestCase):
    def inputs(self, root):
        folder, _, _ = reference(root)
        cached = root/'cache'; cached_trial.run(folder, cached, 0)
        return folder, cached

    def test_actual_frozen_disk_inputs_keep_empty_cohort_and_statuses(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp); folder, cached = self.inputs(root)
            result = run(folder, cached, root/'audit')
            self.assertEqual(result['frozen_surveys_inventoried'], 1)
            self.assertTrue(result['inputs_unchanged']); self.assertTrue(result['snapshots_unchanged'])
            self.assertFalse(result['accuracy_measured']); self.assertFalse(result['source_labels_used'])
            self.assertFalse(result['engine_recomputed']); self.assertFalse(result['gate_changed'])
            self.assertEqual(result['all_query_inventory_count'], sum(len(x['query_inventory']) for x in result['survey_inventory']))
            self.assertEqual(result['actual_delayed_positive'], 'not_seen')

    def test_endpoint_collection_never_appends_temporal_links_to_direct_witness(self):
        from test_harmony_relation_case_audit import case
        from musicanote_harness.harmony_relation_case_audit import audit_pair
        lattice, item, ir = case(delayed=False)
        row = audit_pair(lattice, item, ir)
        self.assertEqual(row['direct']['status'], 'conditional_witness_rechecked')
        self.assertEqual(row['temporal']['status'], 'conditional_witness_rechecked')
        group = {'audits': [row]}; before = deepcopy(group)
        sounds = {s['sounding_event_id']: s for s in ir['sounding_events']}
        endpoints = witness_note_refs(group, sounds)
        self.assertEqual(group, before)
        self.assertEqual(row['direct']['selected_links'], item['query']['links'])
        self.assertEqual(endpoints, {nid for edge in item['query']['links'] for sid in edge for nid in sounds[sid]['source_note_ids']})
        self.assertEqual(witness_note_refs(group, sounds), endpoints)

    def test_cached_artifact_consumed_hash_guard(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp); folder, cached = self.inputs(root)
            row = cached_trial.load(cached/'report.json')['records'][0]
            Path(row['artifact']).write_bytes(b'not the frozen bytes')
            with self.assertRaisesRegex(ValueError, 'consumed_input_hash_mismatch'):
                run(folder, cached, root/'audit')
            self.assertFalse((root/'audit').exists())

    def test_missing_or_duplicate_cached_sample_rejected(self):
        for duplicate in (False, True):
            with TemporaryDirectory() as tmp:
                root = Path(tmp); folder, cached = self.inputs(root)
                report = cached_trial.load(cached/'report.json')
                report['records'] = report['records']*2 if duplicate else []
                write_json(cached/'report.json', report)
                with self.assertRaisesRegex(ValueError, 'cache_sample_coverage_mismatch'):
                    run(folder, cached, root/'audit')

    def test_cache_success_flag_is_not_semantic_equality(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp); folder, cached = self.inputs(root)
            report = cached_trial.load(cached/'report.json'); row = report['records'][0]
            payload = json.loads(gzip.decompress(Path(row['artifact']).read_bytes()))
            payload['relations']['status'] = 'invented-equal'
            Path(row['artifact']).write_bytes(gzip.compress(json.dumps(payload).encode()))
            row['sha256'] = cached_trial.digest(Path(row['artifact']))
            write_json(cached/'report.json', report)
            with self.assertRaisesRegex(ValueError, 'cache_relation_not_equal'):
                run(folder, cached, root/'audit')

    def test_unverified_cache_report_rejected(self):
        for field in ('inputs_unchanged', 'complete', 'source_labels_used', 'accuracy_measured'):
            with TemporaryDirectory() as tmp:
                root = Path(tmp); folder, cached = self.inputs(root)
                report = cached_trial.load(cached/'report.json'); report[field] = not report[field]
                write_json(cached/'report.json', report)
                with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'invalid_cache_reference'):
                    run(folder, cached, root/'audit')

    def test_holdout_reference_stays_protected(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp); folder, cached = self.inputs(root)
            plan = cached_trial.load(folder/'frozen-plan.json')
            plan['packages'][0]['source']['manifest_entry']['split'] = 'holdout'
            write_json(folder/'frozen-plan.json', plan)
            contract = cached_trial.load(folder/'run-contract.json')
            contract['frozen_plan_sha256'] = cached_trial.digest(folder/'frozen-plan.json')
            write_json(folder/'run-contract.json', contract)
            with self.assertRaisesRegex(ValueError, 'protected_or_unauthorized'):
                run(folder, cached, root/'audit')


if __name__ == '__main__': unittest.main()
