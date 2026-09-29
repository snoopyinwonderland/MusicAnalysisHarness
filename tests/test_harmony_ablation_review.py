import copy
from fractions import Fraction as F
import tempfile
import unittest
from test_harmony_joint import fixture
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_joint import prepare
from musicanote_harness.harmony_temporal_shadow import analyze as temporal
from musicanote_harness.harmony_multiscale_shadow import analyze, provider
from musicanote_harness.harmony_ablation_review import ARMS, replay_matches, rescore_path, build
from musicanote_harness.harmony_ablation_diagnostics import clip_path


class AblationTests(unittest.TestCase):
    def test_switch_type_guard(self):
        for value in (0, 1, 'false', None):
            with self.assertRaises(ValueError):
                provider(enable_distributed=value)

    def test_no_supplements_replays_temporal(self):
        specs = [(54, 0, 1, 'b'), (58, 0, 1, 'v'), (64, 0, 1, 't'),
                 (60, 1, 2, 'v'), (53, 2, 3, 'b'), (56, 2, 3, 't')]
        ir = fixture(specs); span = {'start': q(0), 'end': q(3)}
        self.assertTrue(replay_matches(temporal(ir, cell_divisions=2, analysis_span=span),
                                     analyze(ir, analysis_span=span, **ARMS['none'])))

    def test_missing_fifth_requires_fifth_switch(self):
        ir = fixture([(54, 0, 2, 'b'), (58, 0, 2, 'v'), (64, 0, 2, 't')])
        rows, neighbors = prepare(ir)
        for arm, switches in ARMS.items():
            choices = provider(ir['measures'], **switches)(rows, neighbors, F(0), F(2), F(1), limit=None)
            evidence = next(c for c in choices if c['label'] == 'F#:dominant7')['temporal_evidence']
            self.assertEqual(bool(evidence), switches['enable_missing_fifth'], arm)

    def test_distributed_complete_requires_distributed_switch(self):
        ir = fixture([(60, 0, 1, 'v'), (53, 1, 2, 'b'), (56, 1, 2, 't')])
        rows, neighbors = prepare(ir)
        for arm, switches in ARMS.items():
            choices = provider(ir['measures'], **switches)(rows, neighbors, F(0), F(2), F(1), limit=None)
            evidence = next(c for c in choices if c['label'] == 'F:minor')['temporal_evidence']
            self.assertEqual(bool(evidence), switches['enable_distributed'], arm)

    def test_distributed_missing_fifth_requires_both(self):
        ir = fixture([(54, 0, 1, 'b'), (58, 1, 2, 'v'), (64, 1, 2, 't')])
        rows, neighbors = prepare(ir)
        for arm, switches in ARMS.items():
            choices = provider(ir['measures'], **switches)(rows, neighbors, F(0), F(2), F(1), limit=None)
            evidence = next(c for c in choices if c['label'] == 'F#:dominant7')['temporal_evidence']
            self.assertEqual(bool(evidence), arm == 'both', arm)

    def test_same_path_cost_reconstruction_and_no_mutation(self):
        ir = fixture([(p, a, b, str(i)) for a, b, ps in [(0, 1, [54, 58, 64]), (1, 2, [47, 50, 54])] for i, p in enumerate(ps)])
        span = {'start': q(0), 'end': q(2)}
        for switches in ARMS.values():
            result = analyze(ir, analysis_span=span, **switches)
            original = copy.deepcopy((ir, result))
            cost = rescore_path(ir, result, switches)
            self.assertAlmostEqual(cost['total_cost'], result['path_cost'])
            self.assertEqual((ir, result), original)
            self.assertTrue(cost['all_segments_in_top_five'])

    def test_replay_does_not_accept_same_labels_with_different_boundaries(self):
        ir = fixture([(60, 0, 2, 'v'), (64, 0, 2, 'm'), (67, 0, 2, 'b')])
        original = analyze(ir, analysis_span={'start': q(0), 'end': q(2)})
        changed = copy.deepcopy(original); changed['segments'][0]['span']['end'] = q(1)
        self.assertFalse(replay_matches(original, changed))
        changed = copy.deepcopy(original); changed['path_cost'] += .01
        self.assertFalse(replay_matches(original, changed))

    def test_existing_output_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, 'output_exists'):
                build('missing', 'missing', 'missing', folder)

    def test_clip_path_does_not_crop_ties_or_mutate_inputs(self):
        ir = fixture([(60, 0, 4, 'v'), (64, 0, 4, 'm'), (67, 0, 4, 'b')])
        result = analyze(ir, analysis_span={'start': q(0), 'end': q(4)})
        original = copy.deepcopy((ir, result))
        clipped = clip_path(result, {'start': q(1), 'end': q(3)}, ir['measures'])
        self.assertEqual(clipped['segments'][0]['span'], {'start': q(1), 'end': q(3)})
        self.assertEqual((ir, result), original)
        self.assertEqual(rescore_path(ir, clipped, ARMS['both'])['total_cost'], .15)
        with self.assertRaisesRegex(ValueError, 'contained'):
            clip_path(result, {'start': q(0), 'end': q(5)}, ir['measures'])

    def test_clipped_path_can_lose_proposal_eligibility(self):
        ir = fixture([(60, 0, 1, 'v'), (64, 1, 2, 'v'), (67, 2, 3, 'v')])
        result = analyze(ir, analysis_span={'start': q(0), 'end': q(3)})
        clipped = clip_path(result, {'start': q(0), 'end': q(1)}, ir['measures'])
        with self.assertRaisesRegex(ValueError, 'not_proposed'):
            rescore_path(ir, clipped, ARMS['both'])


if __name__ == '__main__':
    unittest.main()
