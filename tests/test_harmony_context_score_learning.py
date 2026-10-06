from copy import deepcopy
from fractions import Fraction as F
import unittest

from musicanote_harness import harmony_context_score_learning as l
from test_harmony_structured_learning import entry, contract

s, joint = l.s, l.joint


def frozen(): return s.initial_weights(s.fresh.timing.ZERO)


def row():
    delta = {k: s.q(F(1) if i == 0 else F()) for i, k in enumerate(joint.FEATURES)}
    return {'entry': entry(), 'sample_id': 'a', 'contrast_id': 'c',
        'score_delta': delta, 'gradient_delta': deepcopy(delta),
        'available': dict.fromkeys(joint.FEATURES, True), 'legacy_gap': s.q(0), 'loss': s.q(F(1, 4))}


def fit(rows):
    manifest = [entry()]
    return l.fit(rows, frozen(), contract(manifest), manifest, 'parent', 'pool')


class ContextLearningTests(unittest.TestCase):
    def test_exact_deterministic_and_old_26_not_changed(self):
        rows = [row()]; before = deepcopy(rows); w = frozen(); old = dict(w)
        m = fit(rows); self.assertEqual(m, fit(rows)); self.assertEqual(rows, before); self.assertEqual(w, old)
        self.assertEqual(m['frozen_existing_weights'], {k: s.q(v) for k, v in old.items()})
        self.assertGreater(s.f(m['weights'][joint.FEATURES[0]]), 0)
        self.assertEqual(m['averaging_ticks'], 3)
        self.assertLess(s.f(m['margin_violation_sum_after']), s.f(m['margin_violation_sum_before']))
        self.assertFalse(m['fresh_adversary_search_during_fit']); self.assertFalse(m['dev_labels_used'])

    def test_unknown_dimension_has_null_gradient_not_partial_value(self):
        r = row(); k = joint.FEATURES[0]; r['available'][k] = False; r['gradient_delta'][k] = None
        m = fit([r]); self.assertEqual(m['updates'], []); self.assertEqual(m['weights'], {k: s.q(0) for k in joint.FEATURES})
        self.assertEqual(m['epochs'][0]['statuses']['known_feature_collision'], 1)

    def test_partial_known_local_sum_can_contribute_score_not_gradient(self):
        r = row(); a, b = joint.FEATURES[:2]
        r['available'][a] = False; r['gradient_delta'][a] = None
        r['score_delta'][a] = s.q(99); r['score_delta'][b] = r['gradient_delta'][b] = s.q(1)
        self.assertEqual(l.gap(r, joint.ZERO | {a: F(1, 10), b: F(1, 4)}), F(203, 20))
        m = fit([r]); self.assertEqual(m['weights'][a], s.q(0)); self.assertGreater(s.f(m['weights'][b]), 0)

    def test_zero_loss_protection_rows_and_every_visit_average(self):
        r = row(); r['contrast_id'] = 'z'; r['loss'] = s.q(0)
        m = fit([row(), r]); self.assertEqual(m['averaging_ticks'], 6)
        self.assertGreater(m['epochs'][0]['statuses']['margin_satisfied'], 0)
        self.assertEqual(fit([r])['updates'], [])

    def test_signed_training_projection_and_quantization(self):
        r = row(); r['legacy_gap'] = s.q(-50); r['score_delta'][joint.FEATURES[0]] = s.q(-100)
        r['gradient_delta'] = deepcopy(r['score_delta'])
        m = fit([r])
        for k, v in m['weights'].items(): self.assertLessEqual(abs(s.f(v)), l.BOUND)
        self.assertLess(s.f(m['weights'][joint.FEATURES[0]]), 0)

    def test_nontrain_unapproved_and_entry_mutation_rejected_before_updates(self):
        manifest = [entry(), entry('dev', 'dev')]; c = contract(manifest)
        for e in (manifest[1], entry('absent'), entry() | {'changed': True}):
            with self.assertRaises(ValueError): l.fit([row() | {'entry': e}], frozen(), c, manifest, 'parent', 'pool')

    def test_bad_vectors_duplicate_empty_and_negative_loss(self):
        r = row(); k = joint.FEATURES[0]
        bad = [r | {'available': {}}, r | {'loss': s.q(-1)},
            r | {'gradient_delta': r['gradient_delta'] | {k: None}},
            r | {'available': r['available'] | {k: False}},
            r | {'score_delta': r['score_delta'] | {k: s.q(2)}}]
        for x in bad:
            with self.assertRaises(ValueError): fit([x])
        with self.assertRaises(ValueError): fit([r, r])
        with self.assertRaises(ValueError): fit([])

    def test_model_rights_frozen_weights_pool_and_content_binding(self):
        manifest = [entry()]; c = contract(manifest); m = fit([row()])
        w = l.model_weights(m, frozen(), c, manifest, 'parent', 'pool')
        self.assertEqual(w, {k: s.f(v) for k, v in m['weights'].items()})
        for bad in (m | {'production_deployment': True}, m | {'dev_labels_used': True}, m | {'weights': {}}):
            with self.assertRaises(ValueError): l.model_weights(bad, frozen(), c, manifest, 'parent', 'pool')
        with self.assertRaises(ValueError): l.model_weights(m, frozen(), c, manifest, 'parent', 'wrong_pool')
        changed = frozen(); changed['extra_member_complexity'] /= 2
        with self.assertRaises(ValueError): l.model_weights(m, changed, c, manifest, 'parent', 'pool')
        c['restrictions']['commercial_use'] = True
        with self.assertRaises(ValueError): l.model_weights(m, frozen(), c, manifest, 'parent', 'pool')


if __name__ == '__main__': unittest.main()
