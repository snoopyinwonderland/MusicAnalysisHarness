from copy import deepcopy
from fractions import Fraction as F
import unittest

from musicanote_harness import harmony_online_score_learning as l
from test_harmony_structured_learning import entry, contract

s = l.s


def initial(): return s.initial_weights(s.fresh.timing.ZERO)


def scope(sample='a', e=None):
    e = e or entry()
    return {'sample_id': sample, 'entry': e, 'work_family_id': e['work_family_id'], 'split': e['split']}


def observation(loss=F(1, 4), feature='extra_member_complexity', delta=F(-1), available=True):
    values = dict.fromkeys(s.FEATURES, F()); values[feature] = delta
    mask = dict.fromkeys(s.FEATURES, True); mask[feature] = available
    return {'resource_abstention': False, 'feature_delta': {k: s.q(v) for k, v in values.items()},
        'feature_available': mask, 'loss': s.q(loss)}


class OnlineLearningTests(unittest.TestCase):
    def fit(self, visit, rows=None):
        m = [entry()]
        return l.fit(rows or [scope()], initial(), contract(m), m, 'parent', visit)

    def test_refresh_each_visit_uses_current_weights_and_all_epochs_average(self):
        observed = []
        def visit(r, w, epoch):
            observed.append((epoch, w['extra_member_complexity']))
            return observation()
        model = self.fit(visit)
        self.assertEqual(len(observed), 3)
        self.assertGreater(observed[0][1], observed[1][1])
        self.assertGreater(observed[1][1], observed[2][1])
        expected = l.quantize(sum(s.f(v['weights_after']['extra_member_complexity']) for v in model['visits'])/3)
        self.assertEqual(s.f(model['weights']['extra_member_complexity']), expected)
        self.assertFalse(model['configuration']['loss_augmented_search'])
        self.assertEqual(model['averaging_ticks'], 3)

    def test_previously_correct_scope_is_revisited_and_can_become_a_negative(self):
        def visit(r, w, epoch): return observation(F() if epoch == 1 else F(1, 4))
        model = self.fit(visit)
        self.assertEqual(model['visits'][0]['update']['status'], 'current_winner_reference_agreement')
        self.assertEqual(model['visits'][1]['update']['status'], 'updated')
        self.assertEqual(model['training_samples'], 1)

    def test_trust_box_prevents_complexity_collapse_and_preserves_fixed_terms(self):
        w = initial(); a = dict(w)
        for _ in range(100):
            d = dict.fromkeys(s.FEATURES, F()); d['extra_member_complexity'] = F(1)
            a, _ = l.update(a, w, d, dict.fromkeys(s.FEATURES, True), F(2))
        self.assertEqual(a['extra_member_complexity'], F(1, 5))
        for k in s.FIXED: self.assertEqual(a[k], w[k])
        self.assertEqual(l.trust_bounds(w)['conditional_step_ornament_exposure'], (F(-1), F(-1, 4)))

    def test_unavailable_gradient_and_resource_abstention_do_not_update(self):
        model = self.fit(lambda *args: observation(available=False))
        self.assertEqual(model['weights'], model['initial_weights'])
        self.assertEqual(model['visits'][0]['update']['status'], 'known_feature_collision')
        abstained = self.fit(lambda *args: {'resource_abstention': True})
        self.assertEqual(abstained['weights'], abstained['initial_weights'])
        self.assertEqual(abstained['epochs'][0]['statuses']['resource_abstention_no_update'], 1)

    def test_callback_cannot_mutate_weights_and_input_is_preserved(self):
        rows = [scope()]; before = deepcopy(rows)
        def visit(r, w, epoch):
            w['extra_member_complexity'] = F(999)
            return observation(F())
        model = self.fit(visit, rows)
        self.assertEqual(model['weights'], model['initial_weights']); self.assertEqual(rows, before)

    def test_duplicate_dev_unapproved_and_entry_change_are_rejected(self):
        m = [entry(), entry('dev', 'dev')]; c = contract(m)
        for rows in ([scope(), scope()], [scope(e=m[1])], [scope(e=entry('absent'))],
                     [scope(e=entry() | {'title': 'changed'})], [scope() | {'split': 'dev'}]):
            with self.assertRaises(ValueError):
                l.fit(rows, initial(), c, m, 'parent', lambda *args: observation())
        with self.assertRaises(ValueError): l.fit([], initial(), c, m, 'parent', lambda *args: observation())

    def test_deterministic_model_validation_tampering_and_rights(self):
        m = [entry()]; c = contract(m)
        model = self.fit(lambda *args: observation())
        self.assertEqual(model, self.fit(lambda *args: observation()))
        self.assertLess(l.model_weights(model, initial(), c, m, 'parent')['extra_member_complexity'], F(1, 10))
        for bad in (model | {'weights': {}}, model | {'dev_labels_used': True}, model | {'production_deployment': True}):
            with self.assertRaises(ValueError): l.model_weights(bad, initial(), c, m, 'parent')
        c['restrictions']['commercial_use'] = True
        with self.assertRaises(ValueError): l.fit([scope()], initial(), c, m, 'parent', lambda *args: observation())

    def test_rational_trust_box_quantizes_inwards(self):
        self.assertLessEqual(l.project(F(2, 3), (F(1, 6), F(2, 3))), F(2, 3))
        self.assertGreaterEqual(l.project(F(1, 6), (F(1, 6), F(2, 3))), F(1, 6))
        with self.assertRaises(ValueError): l.project(F(), (F(1, 3), F(1, 3)))

    def test_invalid_availability_loss_and_out_of_box_are_rejected(self):
        w = initial(); d = dict.fromkeys(s.FEATURES, F()); a = dict.fromkeys(s.FEATURES, True)
        for mask, loss in (({}, F(1)), (a | {'nonmember_exposure': None}, F(1)), (a, F(-1)), (a, .1)):
            with self.assertRaises(ValueError): l.update(w, w, d, mask, loss)
        with self.assertRaises(ValueError): l.update(w | {'extra_member_complexity': F(1)}, w, d, a, F(1))
