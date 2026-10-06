from copy import deepcopy
from fractions import Fraction as F
import unittest

from musicanote_harness import harmony_adversarial_score_learning as l
from test_harmony_online_score_learning import initial, scope
from test_harmony_structured_learning import entry, contract

s = l.s


def observed(weights, *, available=True, loss=F(1, 4)):
    delta = dict.fromkeys(s.FEATURES, F()); delta['extra_member_complexity'] = F(-1)
    gap = s.feature_cost(delta, weights)
    return {'resource_abstention': False, 'negative_kind': l.NEGATIVE,
        'source_labels_used_for_negative_selection': True, 'target_training_reference_labels_used': True,
        'analysis_export_allowed': False, 'feature_delta': {k: s.q(v) for k, v in delta.items()},
        'feature_available': dict.fromkeys(s.FEATURES, available), 'loss': s.q(loss),
        'negative_cost': s.q(F(1)+gap), 'target_cost': s.q(F(1)), 'margin_violation': s.q(loss-gap),
        'ordinary_correct_positive_margin': True}


class AdversarialLearningTests(unittest.TestCase):
    def fit(self, visit, rows=None):
        m = [entry()]
        return l.fit(rows or [scope()], initial(), contract(m), m, 'parent', visit)

    def test_current_exact_adversary_every_visit_and_correct_ordinary_still_updates(self):
        seen = []
        def visit(r, w, epoch):
            seen.append(w['extra_member_complexity']); return observed(w)
        model = self.fit(visit)
        self.assertEqual(len(seen), 3); self.assertGreater(seen[0], seen[1]); self.assertGreater(seen[1], seen[2])
        self.assertEqual([v['update']['status'] for v in model['visits']], ['updated']*3)
        self.assertTrue(model['configuration']['loss_augmented_search']); self.assertFalse(model['ordinary_correct_scopes_exempted'])
        average = sum((s.f(v['weights_after']['extra_member_complexity']) for v in model['visits']), F())/3
        self.assertEqual(s.f(model['weights']['extra_member_complexity']), l.online.quantize(average))

    def test_abstention_no_update_still_contributes_to_average(self):
        model = self.fit(lambda r, w, epoch: {'resource_abstention': True} if epoch == 2 else observed(w))
        self.assertEqual(model['visits'][1]['update']['status'], 'resource_abstention_no_update')
        self.assertEqual(model['visits'][1]['weights_before'], model['visits'][1]['weights_after'])
        self.assertEqual(model['averaging_ticks'], 3)

    def test_unavailable_dimensions_do_not_train(self):
        model = self.fit(lambda r, w, epoch: observed(w, available=False))
        self.assertEqual(model['weights'], model['initial_weights'])
        self.assertEqual([v['update']['status'] for v in model['visits']], ['known_feature_collision']*3)

    def test_fixed_terms_initial_trust_box_and_source_scopes_preserved(self):
        rows = [scope()]; before = deepcopy(rows)
        model = self.fit(lambda r, w, epoch: observed(w), rows)
        for k in s.FIXED: self.assertEqual(model['weights'][k], model['initial_weights'][k])
        for k, v in model['weights'].items():
            lo, hi = l.online.trust_bounds(initial())[k]; self.assertTrue(lo <= s.f(v) <= hi)
        self.assertEqual(rows, before)

    def test_wrong_objective_flags_costs_margin_partial_gradient_rejected(self):
        base = observed(initial())
        for value in (base | {'negative_kind': 'ordinary'}, base | {'analysis_export_allowed': True},
                base | {'source_labels_used_for_negative_selection': False}, base | {'negative_cost': s.q(10)},
                base | {'margin_violation': s.q(10)}, base | {'resource_abstention': True}):
            with self.assertRaises(ValueError): self.fit(lambda *args: value)

    def test_duplicate_dev_or_unapproved_rejected(self):
        m = [entry(), entry('dev', 'dev')]
        for rows in ([scope(), scope()], [scope(e=m[1])], [scope(e=entry('absent'))]):
            with self.assertRaises(ValueError):
                l.fit(rows, initial(), contract(m), m, 'parent', lambda r, w, epoch: observed(w))

    def test_callback_cannot_mutate_learning_weights(self):
        def visit(r, w, epoch):
            value = observed(w); w['extra_member_complexity'] = F(999); return value
        model = self.fit(visit)
        self.assertLess(s.f(model['weights']['extra_member_complexity']), F(1, 10))

    def test_determinism_model_tampering_rights_and_initial_binding(self):
        m = [entry()]; c = contract(m); model = self.fit(lambda r, w, epoch: observed(w))
        self.assertEqual(model, self.fit(lambda r, w, epoch: observed(w)))
        self.assertEqual(l.model_weights(model, initial(), c, m, 'parent'), {k: s.f(v) for k, v in model['weights'].items()})
        for bad in (model | {'weights': {}}, model | {'dev_labels_used': True}, model | {'analysis_export_allowed': True}):
            with self.assertRaises(ValueError): l.model_weights(bad, initial(), c, m, 'parent')
        with self.assertRaises(ValueError): l.model_weights(model, initial() | {'extra_member_complexity': F(1, 5)}, c, m, 'parent')
        c['restrictions']['commercial_use'] = True
        with self.assertRaises(ValueError): l.model_weights(model, initial(), c, m, 'parent')


if __name__ == '__main__': unittest.main()
