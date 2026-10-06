from copy import deepcopy
from fractions import Fraction as F
import json
import unittest

from musicanote_harness import harmony_arrangement_reference as c


def q(v): return c.rational(F(v))


def fixture():
    signature = [['F', 1], [['A', 0], ['C', 1], ['F', 1]]]
    graph = {'max_segments': 3, 'edges': [
        {'group_id': 'a', 'start': q(0), 'end': q(F(1, 3)), 'signature': signature, 'source_event_ids': ['s']},
        {'group_id': 'b', 'start': q(F(1, 3)), 'end': q(1), 'signature': signature, 'source_event_ids': ['s']}]}
    ir = {'score': {'score_id': 'score'}, 'ir_document_id': 'ir', 'note_events': [{'note_id': 'n1'}, {'note_id': 'n2'}],
          'sounding_events': [{'sounding_event_id': 's', 'source_note_ids': ['n1', 'n2'],
                               'span': {'start': q(0), 'end': q(1)}}]}
    receipt = {'existing_path_ids': ['a', 'b'], 'cost': q(F(1, 5)), 'source_labels_used': False,
               'target_path_created_using_labels': False}
    binding = {'verified': True, 'case_sha256': '1'*64, 'model_sha256': '2'*64,
               'scope_artifact_sha256': '3'*64, 'whole_musicxml_sha256': '4'*64, 'whole_ir_sha256': '5'*64}
    packet = {'sample_id': 'sample', 'sample_span': {'start': q(0), 'end': q(1)}, 'model_sha256': '2'*64,
              'original_scope_sha256': '3'*64, 'source_clock_gate': {'accepted': True},
              'source_labels_used_for_inference': False,
              'full_source_paths': {'whole_musicxml_sha256': '4'*64, 'working_ir_sha256': '5'*64},
              'post_search_cost_receipts': {'fresh': deepcopy(receipt), 'previous_context': deepcopy(receipt),
                  'stored_target': receipt | {'secret': 'ORACLE_LABEL', 'target_path_created_using_labels': True}},
              'evaluation': {'label': 'ORACLE_LABEL'},
              'result': {'status': 'exact', 'selected': {'segments': [{'semantic_group_ref': 'a'}, {'semantic_group_ref': 'b'}],
                       'score_cost': q(F(1, 5)), 'source_labels_used_for_selection': False}}}
    return packet, graph, ir, binding


def build():
    p, g, ir, b = fixture(); return c.build(p, g, ir, binding=b)


class ArrangementReferenceTests(unittest.TestCase):
    def test_union_dedup_preserves_exact_time_and_tie_note_ids(self):
        value = build(); self.assertEqual(len(value['hypotheses']), 1)
        h = value['hypotheses'][0]; self.assertEqual(h['source_arms'], ['fresh', 'previous_context'])
        self.assertEqual(len(h['harmonic_runs']), 1)
        run = h['harmonic_runs'][0]; self.assertEqual(run['span'], {'start': q(0), 'end': q(1)})
        self.assertEqual(run['source_note_ids'], ['n1', 'n2'])
        self.assertEqual(run['musicomp_candidate']['root_absolute_tpc'], 6)
        self.assertEqual(run['musicomp_candidate']['tones_absolute_tpc'][0], 6)

    def test_never_exports_reference_labels_or_promotes_candidate(self):
        value = build(); self.assertNotIn('ORACLE_LABEL', json.dumps(value))
        self.assertFalse(value['training_target_or_evaluation_labels_exported'])
        self.assertFalse(value['generation_ready']); self.assertFalse(value['production_adopted'])
        self.assertFalse(value['restrictions']['external_api_transmission'])
        self.assertFalse(value['restrictions']['use_as_hard_harmony_constraints'])
        candidate = value['hypotheses'][0]['harmonic_runs'][0]['musicomp_candidate']
        for k in ('bass_absolute_tpc', 'key', 'rn', 'function', 'margin'): self.assertIsNone(candidate[k])
        self.assertFalse(candidate['chordspan_ready'])

    def test_wall_limit_never_promotes_old_alternative(self):
        p, g, ir, b = fixture(); del p['post_search_cost_receipts']['fresh']
        p['result'] = {'status': 'wall_limit', 'selected': None}
        value = c.build(p, g, ir, binding=b)
        self.assertTrue(value['unresolved']); self.assertIsNone(value['research_selected_hypothesis_id'])
        self.assertEqual(len(value['hypotheses']), 1)

    def test_different_model_or_source_produces_different_hypothesis_id(self):
        original = build()['research_selected_hypothesis_id']
        p, g, ir, b = fixture(); p['model_sha256'] = b['model_sha256'] = '6'*64
        self.assertNotEqual(original, c.build(p, g, ir, binding=b)['research_selected_hypothesis_id'])

    def test_enharmonic_spelling_and_double_accidentals_not_lost(self):
        self.assertEqual(c.absolute_tpc(c.spelling(['F', 1])), 6)
        self.assertEqual(c.absolute_tpc(c.spelling(['G', -1])), -6)
        self.assertEqual(c.absolute_tpc(c.spelling(['C', 2])), 14)
        with self.assertRaises(ValueError): c.absolute_tpc({'step': 'C', 'alter': q(F(1, 2))})

    def test_functional_root_not_inserted_into_literal_members(self):
        p, g, ir, b = fixture()
        for e in g['edges']: e['signature'] = [['C', 0], [['F', 0], ['A', 0], ['C', 1]]]
        candidate = c.build(p, g, ir, binding=b)['hypotheses'][0]['harmonic_runs'][0]['musicomp_candidate']
        self.assertEqual(candidate['root_absolute_tpc'], 0)
        self.assertNotIn(0, candidate['tones_absolute_tpc']); self.assertFalse(candidate['root_is_literal_member'])

    def test_missing_source_id_note_id_or_nonoverlap_rejected(self):
        for mode in ('sound', 'note', 'time'):
            p, g, ir, b = fixture()
            if mode == 'sound': ir['sounding_events'] = []
            elif mode == 'note': ir['note_events'] = []
            else: ir['sounding_events'][0]['span'] = {'start': q(1), 'end': q(2)}
            with self.assertRaises(ValueError): c.build(p, g, ir, binding=b)

    def test_noncontiguous_or_incomplete_or_duplicate_path_rejected(self):
        for ids in (['a'], ['b', 'a'], ['a', 'a'], ['missing']):
            p, g, ir, b = fixture(); p['post_search_cost_receipts']['fresh']['existing_path_ids'] = ids
            with self.assertRaises(ValueError): c.build(p, g, ir, binding=b)

    def test_invalid_rational_and_scope_rejected(self):
        for value in (1.0, {'numerator': True, 'denominator': 1}, {'numerator': 1, 'denominator': 0}):
            with self.assertRaises(ValueError): c.fraction(value)
        with self.assertRaises(ValueError): c.span({'start': q(1), 'end': q(1)})

    def test_label_conditioned_selection_and_source_clock_rejected(self):
        p, g, ir, b = fixture(); p['post_search_cost_receipts']['fresh']['target_path_created_using_labels'] = True
        with self.assertRaises(ValueError): c.build(p, g, ir, binding=b)
        p, g, ir, b = fixture(); p['source_clock_gate']['accepted'] = False
        with self.assertRaises(ValueError): c.build(p, g, ir, binding=b)
        p, g, ir, b = fixture(); p['result']['selected']['source_labels_used_for_selection'] = True
        with self.assertRaises(ValueError): c.build(p, g, ir, binding=b)

    def test_sha_binding_and_selected_receipt_consistency_rejected(self):
        p, g, ir, b = fixture()
        for bad in (b | {'verified': False}, b | {'model_sha256': '0'*64}, b | {'case_sha256': 'bad'}):
            with self.assertRaises(ValueError): c.build(p, g, ir, binding=bad)
        p['result']['selected']['score_cost'] = q(9)
        with self.assertRaises(ValueError): c.build(p, g, ir, binding=b)

    def test_union_score_disagreement_rejected_and_inputs_immutable(self):
        p, g, ir, b = fixture(); before = deepcopy((p, g, ir, b))
        c.build(p, g, ir, binding=b); self.assertEqual((p, g, ir, b), before)
        p['post_search_cost_receipts']['previous_context']['cost'] = q(9)
        with self.assertRaises(ValueError): c.build(p, g, ir, binding=b)


if __name__ == '__main__': unittest.main()
