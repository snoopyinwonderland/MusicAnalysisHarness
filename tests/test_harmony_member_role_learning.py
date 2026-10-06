from copy import deepcopy
from fractions import Fraction as F
import unittest

from musicanote_harness import harmony_member_role_learning as l
from test_harmony_structured_learning import entry, contract

s = l.score


def frozen():
    return l.sealed.s.initial_weights(l.sealed.s.fresh.timing.ZERO), dict(l.sealed.joint.ZERO)


def row():
    delta = {k: s.q(F(1) if i == 0 else F()) for i, k in enumerate(s.FEATURES)}
    return {'entry': entry(), 'sample_id': 'a', 'contrast_id': 'c', 'score_delta': delta,
        'gradient_delta': deepcopy(delta), 'available': dict.fromkeys(s.FEATURES, True),
        'frozen33_gap': s.q(0), 'loss': s.q(F(1, 4))}


def fit(rows):
    manifest = [entry()]
    return l.fit(rows, *frozen(), contract(manifest), manifest, 'parent', 'pool')


class MemberRoleLearningTests(unittest.TestCase):
    def test_exact_deterministic_freezes_old33_and_all_visit_average(self):
        rows = [row()]; before = deepcopy(rows); m = fit(rows)
        self.assertEqual(m, fit(rows)); self.assertEqual(rows, before)
        old26, old7 = frozen()
        self.assertEqual(m['frozen26'], {k: s.q(v) for k, v in old26.items()})
        self.assertEqual(m['frozen7'], {k: s.q(v) for k, v in old7.items()})
        self.assertEqual(m['averaging_ticks'], 3); self.assertGreater(s.f(m['weights'][s.FEATURES[0]]), 0)
        self.assertLess(s.f(m['margin_sum_after']), s.f(m['margin_sum_before']))

    def test_unknown_dimension_never_drives_gradient(self):
        r = row(); k = s.FEATURES[0]; r['available'][k] = False; r['gradient_delta'][k] = None
        m = fit([r]); self.assertEqual(m['updates'], [])
        self.assertEqual(m['weights'], {k: s.q(0) for k in s.FEATURES})

    def test_known_local_partial_score_is_not_unknown_observation(self):
        r = row(); a, b = s.FEATURES
        r['available'][a] = False; r['gradient_delta'][a] = None; r['score_delta'][a] = s.q(99)
        r['score_delta'][b] = r['gradient_delta'][b] = s.q(1)
        self.assertEqual(l.gap(r, {a: F(1, 10), b: F(1, 4)}), F(203, 20))
        self.assertEqual(fit([r])['weights'][a], s.q(0))

    def test_zero_loss_protection_and_signed_bound(self):
        r = row(); r['contrast_id'] = 'z'; r['loss'] = s.q(0)
        self.assertEqual(fit([row(), r])['averaging_ticks'], 6)
        self.assertEqual(fit([r])['updates'], [])
        r['frozen33_gap'] = s.q(-50); r['score_delta'][s.FEATURES[0]] = s.q(-100)
        r['gradient_delta'] = deepcopy(r['score_delta']); m = fit([r])
        self.assertLess(s.f(m['weights'][s.FEATURES[0]]), 0)
        self.assertTrue(all(abs(s.f(v)) <= l.BOUND for v in m['weights'].values()))

    def test_nontrain_unapproved_and_mutated_entry_rejected(self):
        manifest = [entry(), entry('dev', 'dev')]; c = contract(manifest)
        for e in (manifest[1], entry('absent'), entry() | {'changed': True}):
            with self.assertRaises(ValueError): l.fit([row() | {'entry': e}], *frozen(), c, manifest, 'parent', 'pool')

    def test_bad_vectors_duplicate_empty_and_negative_loss(self):
        r = row(); k = s.FEATURES[0]
        for bad in (r | {'available': {}}, r | {'loss': s.q(-1)},
                    r | {'gradient_delta': r['gradient_delta'] | {k: None}},
                    r | {'available': r['available'] | {k: False}},
                    r | {'score_delta': r['score_delta'] | {k: s.q(2)}}):
            with self.assertRaises(ValueError): fit([bad])
        with self.assertRaises(ValueError): fit([r, r])
        with self.assertRaises(ValueError): fit([])

    def test_model_licenses_content_and_frozen_weights_bound(self):
        manifest = [entry()]; c = contract(manifest); m = fit([row()]); old26, old7 = frozen()
        self.assertEqual(l.model_weights(m, old26, old7, c, manifest, 'parent', 'pool'), {k: s.f(v) for k, v in m['weights'].items()})
        for bad in (m | {'production_deployment': True}, m | {'dev_used': True}, m | {'weights': {}}):
            with self.assertRaises(ValueError): l.model_weights(bad, old26, old7, c, manifest, 'parent', 'pool')
        changed = old7 | {next(iter(old7)): F(1, 10)}
        with self.assertRaises(ValueError): l.model_weights(m, old26, changed, c, manifest, 'parent', 'pool')
        with self.assertRaises(ValueError): l.model_weights(m, old26, old7, c, manifest, 'parent', 'changed_pool')
        c['restrictions']['commercial_use'] = True
        with self.assertRaises(ValueError): l.model_weights(m, old26, old7, c, manifest, 'parent', 'pool')


if __name__ == '__main__': unittest.main()
