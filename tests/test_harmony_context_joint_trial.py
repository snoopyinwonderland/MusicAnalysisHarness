from copy import deepcopy
from fractions import Fraction as F
import unittest
from musicanote_harness import harmony_context_joint_trial as trial
from musicanote_harness import harmony_context_joint_decoder as joint
from musicanote_harness import harmony_context_competition_v2 as context
from test_harmony_context_joint_decoder import toy, scorer, paths


class JointTrialTests(unittest.TestCase):
    def test_stress_inventory_is_source_distinct_and_label_independent(self):
        packets = [{'original_edge_count': e, 'sample_id': i, 'source_ir_content_sha256': s,
                    'reference': 'not a selection field', 'work_title': 'unused'}
                   for e, i, s in ((10, 'b', 'src1'), (10, 'a', 'src1'), (17, 'c', 'src2'),
                                   (20, 'd', 'src3'), (101, 'e', 'src4'))]
        self.assertEqual(trial.select_stress(packets, 2), ['a', 'c'])
        self.assertEqual(trial.select_stress(list(reversed(packets))), ['a', 'c', 'd'])
        for p in packets: p['reference'] = 'different'; p['work_title'] = 'different'
        self.assertEqual(trial.select_stress(packets, 2), ['a', 'c'])

    def test_stress_coefficients_are_exact_fixed_numerical_inputs_not_fit(self):
        self.assertEqual(trial.STRESS, {k: F(1 if i % 2 == 0 else -1, 8) for i, k in enumerate(joint.FEATURES)})
        self.assertNotEqual(trial.STRESS, joint.ZERO)

    def test_replay_full_source_profiles_and_detect_tampering(self):
        graph, ev, _ = toy(cap=2); sc = scorer(graph, ev, extra=trial.STRESS)
        for ids in paths(graph):
            r = sc.path_receipt(ids); p = context.observe_path(graph, ev, ids, context=sc.context)
            trial.check_profile(r, p)
            changed = deepcopy(p); changed['observed_feature_sums'][joint.FEATURES[0]] = joint.q(999)
            with self.assertRaises(ValueError): trial.check_profile(r, changed)

    def test_target_path_provenance_is_not_declared_blind(self):
        graph, ev, _ = toy(cap=1); sc = scorer(graph, ev)
        r = sc.path_receipt(paths(graph)[0], target=True)
        self.assertTrue(r['target_path_created_using_labels'])
        self.assertTrue(r['legacy']['source_labels_used_to_create_this_path'])
        self.assertFalse(r['source_labels_used'])  # feature computation remains label-blind

    def test_unknown_partial_observation_cannot_be_scored_as_complete(self):
        graph, ev, _ = toy(cap=3); ev.rows[1]['identity'] = None; ev.rows[1]['clock_valid'] = False
        sc = scorer(graph, ev, extra=trial.STRESS)
        for ids in paths(graph):
            p = context.observe_path(graph, ev, ids, context=sc.context); r = sc.path_receipt(ids)
            trial.check_profile(r, p)
            self.assertEqual(r['cost'], joint.q(sc.score_path(ids)))


if __name__ == '__main__': unittest.main()
