import json
import unittest
from copy import deepcopy
from unittest.mock import patch

from test_harmony_open_candidates import score
from test_harmony_progression_multivoice import fixture
from test_harmony_distributed_resolution import fixture as delayed_fixture
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_reading_voice_context import voice_links
from musicanote_harness.harmony_progression_resolution import analyze as resolution
from musicanote_harness.harmony_candidate_relation_survey import run as survey
from musicanote_harness import harmony_candidate_relation_survey as survey_module
from musicanote_harness import harmony_voice_geometry_cache as module
from musicanote_harness.harmony_voice_geometry_cache import VoiceGeometryCache, fingerprint


def span(a=0, b=3):
    return {'start': q(a), 'end': q(b)}


def simple():
    return score([('C4', 0, 1, 'v'), ('D4', 1, 2, 'v'), ('E4', 2, 3, 'v')])


def repeated_candidates(count):
    result, path, ir = fixture(return_ir=True)
    edge = result['edges'][path[1]['edge']]
    original = deepcopy(edge['readings'][1])
    edge['readings'] = [edge['readings'][0]]
    for index in range(count):
        reading = deepcopy(original)
        reading['candidate_ref'] = 'origin-' + str(index)
        edge['readings'].append(reading)
    return result, ir


class VoiceGeometryCacheTests(unittest.TestCase):
    def assert_cached_equal(self, ir, bounds):
        before = deepcopy(ir); cache = VoiceGeometryCache(ir)
        expected = voice_links(ir, bounds)
        self.assertEqual(voice_links(ir, bounds, geometry_cache=cache), expected)
        self.assertEqual(voice_links(ir, bounds, geometry_cache=cache), expected)
        self.assertEqual(ir, before)
        self.assertEqual(cache.stats()['prepares'], 1)
        self.assertEqual(cache.stats()['span_hits'], 1)
        self.assertFalse(cache.stats()['harmonic_results_cached'])
        return expected

    def test_cached_uncached_whole_object_equal_reuse(self):
        a = self.assert_cached_equal(simple(), span())
        self.assertEqual(len(a['links']), 2)

    def test_equivalent_fraction_key_reattaches_individual_metadata(self):
        ir = simple(); cache = VoiceGeometryCache(ir)
        one = {'start': {'numerator': 0, 'denominator': 2},
               'end': {'numerator': 6, 'denominator': 2}, 'display': 'original'}
        two = {**span(), 'display': {'label': 'new'}, 'source_ref': 'second'}
        a = cache.voice_links(ir, one); b = cache.voice_links(ir, two)
        self.assertEqual(a['context_span'], one)
        self.assertEqual(b['context_span'], two)
        self.assertEqual(b, voice_links(ir, two))
        self.assertEqual(cache.stats()['span_misses'], 1)
        self.assertEqual(cache.stats()['span_hits'], 1)

    def test_returned_nested_mutation_cannot_poison_cache_or_ir(self):
        ir = simple(); before = deepcopy(ir); cache = VoiceGeometryCache(ir)
        a = cache.voice_links(ir, span()); original = deepcopy(a)
        a['links'][0]['source_pitch']['step'] = 'G'
        a['links'][0]['source_refs'].append('made-up')
        a['abstentions']['made-up'] = 99
        a['context_span']['end'] = q(999)
        self.assertEqual(cache.voice_links(ir, span()), original)
        self.assertEqual(ir, before)

    def test_request_span_mutation_does_not_mutate_stored_span(self):
        ir = simple(); cache = VoiceGeometryCache(ir); bounds = span()
        a = cache.voice_links(ir, bounds); bounds['end'] = q(2); bounds['new'] = True
        self.assertEqual(a['context_span'], span())
        self.assertEqual(cache.voice_links(ir, span()), voice_links(ir, span()))

    def test_complete_ir_fingerprint_pitch_time_source_voice_barline_metadata(self):
        for kind in ('pitch', 'time', 'source', 'voice', 'barline', 'metadata'):
            ir = simple(); cache = VoiceGeometryCache(ir); cache.voice_links(ir, span())
            if kind == 'pitch': ir['sounding_events'][0]['pitch']['midi_pitch'] += 1
            elif kind == 'time': ir['sounding_events'][0]['span']['end'] = q('3/2')
            elif kind == 'source': ir['sounding_events'][0]['source_note_ids'] = ['missing']
            elif kind == 'voice': ir['note_events'][0]['voice_id'] = 'other'
            elif kind == 'barline': ir['measures'][0]['repeat_barline'] = {'repeat_direction': 'backward'}
            else: ir['metadata'] = {'title': 'changed'}
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, 'geometry_cache_ir_changed'):
                cache.voice_links(ir, span())

    def test_equivalent_deep_copy_allowed_outside_scope(self):
        ir = simple(); cache = VoiceGeometryCache(ir)
        self.assertEqual(cache.voice_links(deepcopy(ir), span()), voice_links(ir, span()))
        self.assertEqual(cache.stats()['ir_sha256'], fingerprint(ir))

    def test_scope_same_object_only_and_rechecks_entry(self):
        ir = simple(); cache = VoiceGeometryCache(ir)
        with cache.scope(ir):
            self.assertEqual(cache.voice_links(ir, span()), voice_links(ir, span()))
            with self.assertRaisesRegex(ValueError, 'scope_input_mismatch'):
                cache.voice_links(deepcopy(ir), span())
        ir['metadata'] = {'changed': True}
        with self.assertRaisesRegex(ValueError, 'geometry_cache_ir_changed'):
            with cache.scope(ir): pass

    def test_scope_exit_detects_mid_session_mutation_and_is_not_left_bound(self):
        ir = simple(); original = deepcopy(ir); cache = VoiceGeometryCache(ir)
        with self.assertRaisesRegex(ValueError, 'geometry_cache_ir_changed'):
            with cache.scope(ir):
                cache.voice_links(ir, span())
                ir['sounding_events'][0]['pitch']['midi_pitch'] += 1
                # Fast scoped lookup reads private immutable snapshot; exit invalidates the computation.
                self.assertEqual(cache.voice_links(ir, span()), voice_links(original, span()))
        ir.clear(); ir.update(original)
        with cache.scope(ir): self.assertEqual(cache.voice_links(ir, span()), voice_links(ir, span()))

    def test_scope_exception_cleanup_and_nested_scope_guard(self):
        ir = simple(); cache = VoiceGeometryCache(ir)
        with self.assertRaisesRegex(RuntimeError, 'test_failure'):
            with cache.scope(ir):
                with self.assertRaisesRegex(ValueError, 'nested_scope'):
                    with cache.scope(ir): pass
                raise RuntimeError('test_failure')
        with cache.scope(ir): cache.voice_links(ir, span())

    def test_lru_access_order_and_size_limit(self):
        ir = simple(); cache = VoiceGeometryCache(ir, max_spans=2)
        for bounds in (span(0, 1), span(1, 2), span(0, 1), span(2, 3), span(0, 1), span(1, 2)):
            self.assertEqual(cache.voice_links(ir, bounds), voice_links(ir, bounds))
        a = cache.stats()
        self.assertEqual(a['prepares'], 1); self.assertEqual(a['cached_spans'], 2)
        self.assertEqual(a['span_hits'], 2); self.assertEqual(a['span_misses'], 4)
        self.assertEqual(a['evictions'], 2); self.assertEqual(a['max_spans'], 2)

    def test_version_identity_includes_prepare_geometry_and_cache_versions(self):
        ir = simple(); cache = VoiceGeometryCache(ir)
        self.assertEqual(cache.stats()['geometry_versions'],
                         [module.VERSION, module.GEOMETRY_VERSION, module.PREPARE_VERSION])
        with patch.object(module, 'GEOMETRY_VERSION', 'test-new-geometry'):
            alternate = VoiceGeometryCache(ir)
            self.assertIn('test-new-geometry', alternate.stats()['geometry_versions'])
            self.assertEqual(alternate.voice_links(ir, span()), cache.voice_links(ir, span()))

    def test_invalid_size_and_span_preserve_uncached_error(self):
        ir = simple()
        for size in (0, -1, True, 1.5):
            with self.assertRaisesRegex(ValueError, 'invalid_geometry_cache_size'): VoiceGeometryCache(ir, size)
        for bounds in (span(-1, 2), span(2, 1)):
            cache = VoiceGeometryCache(ir)
            with self.assertRaisesRegex(ValueError, 'invalid_context_span'): cache.voice_links(ir, bounds)
            with self.assertRaisesRegex(ValueError, 'invalid_context_span'): voice_links(ir, bounds)
        self.assert_cached_equal(ir, span(1, 1))

    def test_lazy_snapshot_preparation_zero_work_until_first_query(self):
        ir = simple()
        with patch.object(module, 'prepare_voice_geometry', wraps=module.prepare_voice_geometry) as prepare:
            cache = VoiceGeometryCache(ir)
            with cache.scope(ir): pass
            prepare.assert_not_called()
            cache.voice_links(ir, span())
            cache.voice_links(ir, span(1, 2))
            self.assertEqual(prepare.call_count, 1)

    def test_external_overlap_not_clipped_into_false_direct_voice_link(self):
        ir = score([('C4', 0, 2, 'v'), ('B3', 0, 1, 'v'), ('D4', 2, 3, 'v')])
        a = self.assert_cached_equal(ir, span('3/2', '5/2'))
        self.assertFalse(a['links'])
        self.assertIn('polyphonic_source_voice', a['abstentions'])

    def test_successor_outside_context_stays_visible_as_abstention(self):
        a = self.assert_cached_equal(simple(), span(0, 2))
        self.assertEqual(a['abstentions']['successor_outside_context'], 1)
        self.assertEqual(len(a['links']), 1)

    def test_cross_staff_same_voice_link_unchanged(self):
        ir = simple()
        for i, note in enumerate(ir['note_events']): note['staff_id'] = 'staff-' + str(i % 2)
        a = self.assert_cached_equal(ir, span())
        self.assertEqual(len(a['links']), 2)

    def test_tie_source_notes_cross_voice_not_invented_as_single_lane(self):
        for changed in (False, True):
            ir = simple(); continued = deepcopy(ir['note_events'][0]); continued['note_id'] = 'tie-continuation'
            continued['staff_id'] = 'other-staff'
            if changed: continued['voice_id'] = 'other-voice'
            ir['note_events'].append(continued)
            ir['sounding_events'][0]['source_note_ids'].append(continued['note_id'])
            with self.subTest(cross_voice=changed):
                a = self.assert_cached_equal(ir, span())
                if changed:
                    self.assertIn('missing_or_cross_voice_source_identity', a['abstentions'])
                    self.assertFalse(any('s0' in link['source_refs'] for link in a['links']))
                else: self.assertTrue(any(link['source_refs'] == ['s0', 's1'] for link in a['links']))

    def test_chord_and_grace_geometry_same_without_pitch_guess(self):
        ir = score([('C4', 0, 1, 'v'), ('E4', 0, 1, 'v'), ('D4', 1, 2, 'v'),
                    ('G4', '1/2', '1/2', 'v'), ('F4', 2, 3, 'v')])
        a = self.assert_cached_equal(ir, span())
        self.assertIn('polyphonic_source_voice', a['abstentions'])
        self.assertFalse(any('s3' in link['source_refs'] for link in a['links']))

    def test_assignment_specific_results_not_cached_as_harmonic_answers(self):
        r, path, ir = fixture(return_ir=True); saved = deepcopy((r, ir)); cache = VoiceGeometryCache(ir)
        for assignment in ('none', 'linked'):
            expected = resolution(r, path, assignment, ir=ir)
            self.assertEqual(resolution(r, path, assignment, ir=ir, geometry_cache=cache), expected)
        self.assertGreaterEqual(cache.stats()['span_hits'], 1)
        self.assertEqual((r, ir), saved)

    def test_survey_cached_and_uncached_preserve_duplicate_origins_and_blockers(self):
        for blocked in (False, True):
            r, path, ir = fixture(return_ir=True)
            duplicate = deepcopy(r['edges'][path[1]['edge']]['readings'][1])
            duplicate['candidate_ref'] = 'other-origin'; r['edges'][path[1]['edge']]['readings'].append(duplicate)
            if blocked: r['edges'][path[0]['edge']]['readings'][0]['abstention_reasons'] = ['blocked']
            saved = deepcopy((r, ir)); cache = VoiceGeometryCache(ir)
            for temporal in (False, True):
                expected = survey(r, ir, temporal=temporal, use_geometry_cache=False)
                actual = survey(r, ir, temporal=temporal, geometry_cache=cache)
                self.assertEqual(actual, expected)
                self.assertEqual({v['target_candidate_ref'] for v in actual['results']}, {'1', 'other-origin'})
            self.assertEqual((r, ir), saved)
            self.assertGreaterEqual(cache.stats()['span_hits'], 3)

    def test_delayed_resolution_survey_whole_object_equivalent(self):
        r, _, ir = delayed_fixture(); cache = VoiceGeometryCache(ir)
        self.assertEqual(survey(r, ir, temporal=True, geometry_cache=cache),
                         survey(r, ir, temporal=True, use_geometry_cache=False))
        self.assertEqual(cache.stats()['prepares'], 1)

    def test_budget_no_pruning_before_cache_construction_or_preparation(self):
        r, path, ir = fixture(return_ir=True)
        r['edges'][path[1]['edge']]['readings'].append(deepcopy(r['edges'][path[1]['edge']]['readings'][1]))
        with patch.object(module, 'VoiceGeometryCache', side_effect=AssertionError('must_not_construct')):
            a = survey(r, ir, max_pairs=1)
        cache = VoiceGeometryCache(ir)
        with patch.object(module, 'prepare_voice_geometry', side_effect=AssertionError('must_not_prepare')):
            b = survey(r, ir, max_pairs=1, geometry_cache=cache)
        expected = survey(r, ir, max_pairs=1, use_geometry_cache=False)
        self.assertEqual(a, expected); self.assertEqual(b, expected)
        self.assertEqual(b['results'], [])
        self.assertEqual(cache.stats()['prepares'], 0)

    def test_wrong_ir_identity_precedes_geometry_preparation(self):
        r, _, ir = fixture(return_ir=True); ir = deepcopy(ir)
        ir['sounding_events'][0]['pitch']['midi_pitch'] += 1
        cache = VoiceGeometryCache(ir)
        with patch.object(module, 'prepare_voice_geometry', side_effect=AssertionError('must_not_prepare')):
            with self.assertRaisesRegex(ValueError, 'identity_mismatch'):
                survey(r, ir, geometry_cache=cache)
        self.assertEqual(cache.stats()['prepares'], 0)
        with self.assertRaisesRegex(ValueError, 'identity_mismatch'):
            survey(r, ir, use_geometry_cache=False)

    def test_grace_survey_unsupported_refs_same_with_and_without_cache(self):
        r, _, ir = fixture(return_ir=True)
        grace = deepcopy(ir['sounding_events'][0]); grace['sounding_event_id'] = 'zero'
        grace['span'] = span('1/2', '1/2')
        ir['sounding_events'].append(grace); r['events'] = deepcopy(ir['sounding_events'])
        expected = survey(r, ir, temporal=True, use_geometry_cache=False)
        actual = survey(r, ir, temporal=True)
        self.assertEqual(actual, expected)
        self.assertEqual(actual['results'][0]['unsupported_event_refs'], ['zero'])

    def test_survey_flag_and_conflicting_options_guard(self):
        r, _, ir = fixture(return_ir=True); cache = VoiceGeometryCache(ir)
        with self.assertRaisesRegex(ValueError, 'invalid_geometry_cache_flag'): survey(r, ir, use_geometry_cache='yes')
        with self.assertRaisesRegex(ValueError, 'conflicting_geometry_cache_options'):
            survey(r, ir, geometry_cache=cache, use_geometry_cache=False)


class GeometryCacheCostGuardTests(unittest.TestCase):
    def test_exact_reuse_threshold_not_raw_query_count(self):
        self.assertEqual(survey_module.MINIMUM_GEOMETRY_SPAN_REUSES, 16)
        for count, enabled in ((1, False), (16, False), (17, True), (18, True)):
            result, _ = repeated_candidates(count); saved = deepcopy(result)
            with self.subTest(count=count):
                policy = survey_module.geometry_cache_policy(result)
                self.assertEqual(policy, {
                    'enabled': enabled, 'planned_queries': count, 'unique_context_spans': 1,
                    'repeated_span_queries': count - 1, 'minimum_span_reuses': 16,
                    'selection_uses_harmonic_labels': False, 'queries_removed': 0})
                self.assertEqual(result, saved)

    def test_many_unique_spans_do_not_enable_cache(self):
        result = {'edges': []}; pairs = []
        for index in range(20):
            result['edges'].extend([{'span': span(index, index + 1)},
                                    {'span': span(index + 1, index + 2)}])
            pairs.append({'source': {'edge': 2 * index}, 'target': {'edge': 2 * index + 1}})
        policy = survey_module.geometry_cache_policy(result, {'pairs': pairs})
        self.assertFalse(policy['enabled'])
        self.assertEqual(policy['planned_queries'], 20)
        self.assertEqual(policy['unique_context_spans'], 20)
        self.assertEqual(policy['repeated_span_queries'], 0)
        self.assertEqual(policy['queries_removed'], 0)

    def test_rational_equivalent_span_keys_ignore_display_metadata(self):
        result = {'edges': []}; pairs = []
        for index in range(17):
            denominator = index + 1
            result['edges'].extend([
                {'span': {'start': {'numerator': denominator, 'denominator': 3 * denominator},
                          'end': q(1), 'display': 'left-' + str(index)}},
                {'span': {'start': q(1),
                          'end': {'numerator': 7 * denominator, 'denominator': 3 * denominator},
                          'display': {'source': index}}}])
            pairs.append({'source': {'edge': 2 * index}, 'target': {'edge': 2 * index + 1}})
        before = deepcopy(result)
        policy = survey_module.geometry_cache_policy(result, {'pairs': pairs})
        self.assertTrue(policy['enabled'])
        self.assertEqual(policy['unique_context_spans'], 1)
        self.assertEqual(policy['repeated_span_queries'], 16)
        self.assertEqual(result, before)

    def test_supplied_plan_uses_only_span_geometry_not_labels_or_readings(self):
        result, _ = repeated_candidates(17)
        planned = survey_module.plan(result); expected = survey_module.geometry_cache_policy(result, planned)
        # With a frozen query plan, the cost guard cannot need candidate shape or labels.
        for edge in result['edges']:
            del edge['readings']
            edge['source_annotation_label'] = object()
            edge['human_harmony_label'] = object()
        with patch.object(survey_module, 'plan', side_effect=AssertionError('must_not_replan')):
            self.assertEqual(survey_module.geometry_cache_policy(result, planned), expected)

    def test_implicit_plan_and_label_changes_do_not_change_cost_decision(self):
        result, _ = repeated_candidates(17)
        expected_plan = survey_module.plan(result)
        expected = survey_module.geometry_cache_policy(result, expected_plan)
        result['source_labels'] = {'answer': 'do not use'}
        for edge in result['edges']:
            for reading in edge['readings']:
                reading['label'] = 'arbitrary human verdict'
                reading['roman_numeral'] = 'not a geometry feature'
        self.assertEqual(survey_module.plan(result), expected_plan)
        self.assertEqual(survey_module.geometry_cache_policy(result), expected)
        self.assertFalse(expected_plan['source_labels_used'])

    def test_low_reuse_default_does_not_construct_cache_and_preserves_json(self):
        result, ir = repeated_candidates(16); before = deepcopy((result, ir))
        expected = survey(result, ir, temporal=True, use_geometry_cache=False)
        with patch.object(module, 'VoiceGeometryCache', side_effect=AssertionError('must_not_construct')):
            actual = survey(result, ir, temporal=True)
        self.assertEqual(json.dumps(actual, sort_keys=True), json.dumps(expected, sort_keys=True))
        self.assertEqual(len(actual['results']), 16)
        self.assertEqual((result, ir), before)

    def test_high_reuse_default_constructs_once_with_same_json_and_all_origins(self):
        for temporal in (False, True):
            result, ir = repeated_candidates(17)
            result['edges'][2]['readings'][3]['abstention_reasons'] = ['blocked-origin']
            before = deepcopy((result, ir)); created = []
            expected = survey(result, ir, temporal=temporal, use_geometry_cache=False)
            def construct(*args, **kwargs):
                cache = VoiceGeometryCache(*args, **kwargs); created.append(cache); return cache
            with self.subTest(temporal=temporal), patch.object(module, 'VoiceGeometryCache', side_effect=construct):
                actual = survey(result, ir, temporal=temporal)
            self.assertEqual(json.dumps(actual, sort_keys=True), json.dumps(expected, sort_keys=True))
            self.assertEqual(len(created), 1)
            self.assertEqual(created[0].stats()['prepares'], 1)
            self.assertGreaterEqual(created[0].stats()['span_hits'], 15)
            self.assertEqual(len(actual['results']), 17)
            self.assertEqual({item['target_candidate_ref'] for item in actual['results']},
                             {'origin-' + str(index) for index in range(17)})
            self.assertEqual((result, ir), before)

    def test_explicit_cache_forces_low_reuse_without_automatic_policy(self):
        result, ir = repeated_candidates(1); cache = VoiceGeometryCache(ir)
        expected = survey(result, ir, use_geometry_cache=False)
        with patch.object(survey_module, 'geometry_cache_policy', side_effect=AssertionError('must_not_gate_explicit_cache')):
            self.assertEqual(survey(result, ir, geometry_cache=cache), expected)
            self.assertEqual(survey(result, ir, geometry_cache=cache), expected)
        self.assertEqual(cache.stats()['prepares'], 1)
        self.assertEqual(cache.stats()['span_hits'], 1)

    def test_disabled_high_reuse_does_not_call_cost_policy_or_construct_cache(self):
        result, ir = repeated_candidates(17)
        expected = survey(result, ir, use_geometry_cache=False)
        with patch.object(survey_module, 'geometry_cache_policy', side_effect=AssertionError('disabled')):
            with patch.object(module, 'VoiceGeometryCache', side_effect=AssertionError('must_not_construct')):
                self.assertEqual(survey(result, ir, use_geometry_cache=False), expected)

    def test_high_reuse_pair_budget_abstains_before_policy_without_pruning(self):
        result, ir = repeated_candidates(17)
        expected = survey(result, ir, max_pairs=16, use_geometry_cache=False)
        with patch.object(survey_module, 'geometry_cache_policy', side_effect=AssertionError('must_not_gate')):
            with patch.object(module, 'VoiceGeometryCache', side_effect=AssertionError('must_not_construct')):
                self.assertEqual(survey(result, ir, max_pairs=16), expected)
        self.assertEqual(expected['status'], 'pair_budget_abstention_no_pruning')
        self.assertEqual(len(expected['plan']['pairs']), 17)
        self.assertEqual(expected['results'], [])

    def test_high_reuse_ir_identity_check_still_precedes_geometry_preparation(self):
        result, ir = repeated_candidates(17)
        ir = deepcopy(ir); ir['sounding_events'][0]['pitch']['midi_pitch'] += 1
        with patch.object(module, 'prepare_voice_geometry', side_effect=AssertionError('must_not_prepare')):
            with self.assertRaisesRegex(ValueError, 'identity_mismatch'):
                survey(result, ir)
        with self.assertRaisesRegex(ValueError, 'identity_mismatch'):
            survey(result, ir, use_geometry_cache=False)

    def test_nonready_and_empty_plans_do_not_invoke_cost_guard(self):
        result, ir = repeated_candidates(1)
        for status in ('upstream_abstention', 'ready'):
            test_result = deepcopy(result); test_result['status'] = status
            if status == 'ready':
                for edge in test_result['edges']: edge['readings'] = []
            with self.subTest(status=status), patch.object(survey_module, 'geometry_cache_policy',
                                                         side_effect=AssertionError('must_not_gate')):
                self.assertEqual(survey(test_result, ir),
                                 survey(test_result, ir, use_geometry_cache=False))


if __name__ == '__main__': unittest.main()
