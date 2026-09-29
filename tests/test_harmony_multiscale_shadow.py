import copy
from fractions import Fraction as F
import unittest
from test_harmony_joint import fixture
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_joint import prepare
from musicanote_harness.harmony_temporal_shadow import provider as previous_provider
from musicanote_harness.harmony_multiscale_shadow import analyze, provider, shape_reason


def scored(specs):
    ir = fixture(specs)
    rows, neighbors = prepare(ir)
    return {c['label']: c for c in provider(ir['measures'])(rows, neighbors, F(0), F(2), F(1), limit=None)}


class MultiscaleTests(unittest.TestCase):
    def test_distributed_triad_evidence_and_no_double_count(self):
        result = scored([(60, 0, 1, 'v'), (53, 1, 2, 'b'), (56, 1, 2, 'v')])
        evidence = result['F:minor']['temporal_evidence']
        self.assertEqual(len(evidence), 4)
        self.assertEqual(sum(e['weight'] for e in evidence), 1)
        self.assertTrue(all(e['reason'] == 'supplemental_distributed_window' for e in evidence))
        self.assertTrue(all('F:minor' in [s['label'] for s in e['qualifying_best_shapes']] for e in evidence))

    def test_missing_only_fifth_support(self):
        result = scored([(54, 0, 2, 'b'), (58, 0, 2, 'm'), (64, 0, 2, 't')])
        self.assertTrue(all(any(s['reason'] == 'seventh_missing_only_fifth' for s in e['qualifying_best_shapes'])
                            for e in result['F#:dominant7']['temporal_evidence']))
        self.assertGreater(result['F#:major']['temporal_regret'], 0)

    def test_do_not_waive_third_root_or_diminished_fifth(self):
        c = {'root': 0, 'pcs': [0, 4, 7, 10], 'label': 'C:dominant7'}
        for observed in ({0, 7, 10}, {4, 7, 10}, {0, 4}, {0, 4, 9, 10}):
            self.assertIsNone(shape_reason(c, observed))
        self.assertIsNone(shape_reason({'root': 0, 'pcs': [0, 3, 6, 10], 'label': 'C:half-diminished7'}, {0, 3, 10}))

    def test_silence_blocks_distributed_accumulation(self):
        result = scored([(60, 0, F(1, 2), 'v'), (53, 1, 2, 'b'), (56, 1, 2, 'v')])
        self.assertEqual(result['F:minor']['temporal_evidence'], [])

    def test_complete_cells_match_previous_costs(self):
        ir = fixture([(p, a, b, str(i)) for a, b, ps in [(0, 1, [48, 52, 55]), (1, 2, [55, 59, 62, 65])] for i, p in enumerate(ps)])
        rows, neighbors = prepare(ir)
        args = (rows, neighbors, F(0), F(2), F(1))
        old = {c['label']: c['cost'] for c in previous_provider(cell_divisions=2, measures=ir['measures'])(*args, limit=None)}
        new = {c['label']: c['cost'] for c in provider(ir['measures'])(*args, limit=None)}
        self.assertEqual(old, new)

    def test_clear_change_and_short_seventh_kept(self):
        specs = [(p, a, b, str(i)) for a, b, ps in [(0, 1, [48, 52, 55]), (1, F(3, 2), [55, 59, 62, 65]), (F(3, 2), 4, [48, 52, 55])] for i, p in enumerate(ps)]
        self.assertIn('G:dominant7', [s['selected']['label'] for s in analyze(fixture(specs))['segments']])

    def test_neighbor_and_arpeggio_not_forced_apart(self):
        for specs in [[(60, 0, 1, 'v'), (64, 1, 2, 'v'), (67, 2, 3, 'v'), (64, 3, 4, 'v')],
                      [(48, 0, 4, 'b'), (64, 0, 4, 'i'), (67, 0, 1, 'v'), (69, 1, F(5, 4), 'v'), (67, F(5, 4), 4, 'v')]]:
            self.assertEqual(len(analyze(fixture(specs))['segments']), 1)

    def test_transposition_and_time_scaling(self):
        specs = [(60, 0, 1, 'v'), (53, 1, 2, 'b'), (56, 1, 2, 'v')]
        first = scored(specs)['F:minor']
        ir = fixture([(p+2, F(a, 2), F(b, 2), v) for p, a, b, v in specs])
        ir['measures'][0]['time_signature']['beat_type'] = 8
        rows, neighbors = prepare(ir)
        scaled = {c['label']: c for c in provider(ir['measures'])(rows, neighbors, F(0), F(1), F(1, 2), limit=None)}['G:minor']
        self.assertEqual(first['cost'], scaled['cost'])
        self.assertEqual([e['weight'] for e in first['temporal_evidence']], [e['weight'] for e in scaled['temporal_evidence']])

    def test_measure_and_meter_boundaries_not_crossed(self):
        ir = fixture([(60, 0, 1, 'v'), (53, 1, 2, 'b'), (56, 1, 2, 'v')])
        ir['measures'].append({'global_start_quarter': q(1), 'time_signature': {'beat_type': 8}})
        rows, neighbors = prepare(ir)
        result = provider(ir['measures'])(rows, neighbors, F(0), F(2), F(1), limit=None)
        self.assertTrue(all(c['temporal_evidence'] == [] for c in result))

    def test_inputs_unchanged_annotations_ignored_tie_attack_preserved(self):
        ir = fixture([(60, 0, 4, 'v'), (64, 0, 4, 'm'), (67, 0, 4, 'b')])
        ir['note_events'].append({'note_id': 'tied_continuation', 'voice_id': 'v'})
        original = copy.deepcopy(ir)
        out = analyze(ir)
        self.assertEqual(ir, original)
        self.assertEqual(out, analyze({**ir, 'annotations': ['WRONG'], 'phrases': ['wrong']}))
        self.assertEqual(len(out['segments']), 1)
        self.assertTrue(all(e['event_refs'] == ['s0', 's1', 's2'] for e in out['segments'][0]['selected']['temporal_evidence']))

    def test_empty(self):
        self.assertEqual(analyze({'sounding_events': []})['segments'], [])


if __name__ == '__main__':
    unittest.main()
