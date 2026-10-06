from copy import deepcopy
from fractions import Fraction as F
import unittest

from musicanote_harness import harmony_ordinal_protection_learning as l
from test_harmony_joint_balance_learning import initial, row
from test_harmony_structured_learning import entry, contract


def fit(rows, competitors=()):
    manifest = [entry()]
    return l.fit(rows, list(competitors), initial(), contract(manifest), manifest, 'parent', 'pool')


def protected(r):
    return dict(sample_id=r['sample_id'], active_contrast_id=r['contrast_id'],
                competitor_case_ref='case', competitor_case_sha256='sha')


class OrdinalLearningTests(unittest.TestCase):
    def test_positive_gap_uses_half_gap_capped_by_loss_not_full_margin(self):
        r = row(); r['loss'] = l.q(99); spec = l.policy([r], [protected(r)], initial())
        gap = l.base.gap(r, initial()); self.assertGreater(gap, 0)
        self.assertEqual(l.f(spec['competitors'][0]['hard_floor']), gap/2)
        r['loss'] = l.q(gap/4)
        self.assertEqual(l.f(l.policy([r], [protected(r)], initial())['competitors'][0]['hard_floor']), gap/4)

    def test_nonpositive_gap_repair_is_not_infeasible_hard_guard(self):
        r = row(); k = 'missing_member_fraction'
        r['score_delta'][k] = r['gradient_delta'][k] = l.q(-1)
        m = fit([r], [protected(r)])
        self.assertIsNone(m['policy']['competitors'][0]['hard_floor'])
        self.assertTrue(m['updates']); self.assertEqual(m['after']['protection_floors'], 0)

    def test_updates_and_average_never_cross_any_positive_floor(self):
        keep = row(); keep['loss'] = l.q(99); bad = deepcopy(keep)
        bad['contrast_id'] = 'repair'; bad['sample_id'] = 'other'
        k = 'missing_member_fraction'; bad['score_delta'][k] = bad['gradient_delta'][k] = l.q(-1)
        before = deepcopy([keep, bad]); m = fit([keep, bad], [protected(keep)])
        floors = l.guard([keep, bad], m['policy'])
        for update in m['updates']:
            self.assertTrue(l.safe({k: l.f(v) for k, v in update['weights'].items()}, floors))
        self.assertTrue(l.safe({k: l.f(v) for k, v in m['weights'].items()}, floors))
        self.assertEqual(m['averaging_ticks'], 6); self.assertEqual([keep, bad], before)
        self.assertEqual(m, fit([keep, bad], [protected(keep)]))

    def test_quantized_dyadic_backtracking_rejects_unsafe_steps(self):
        r = row(); start = initial(); k = 'missing_member_fraction'
        proposal = start | {k: start[k]-F(1, 20)}
        floors = [(r, l.base.gap(r, start)-F(1, 10000))]
        new, power = l.guarded_step(start, proposal, l.base.bounds(start), floors)
        self.assertGreater(power, 0); self.assertTrue(l.safe(new, floors))

    def test_guard_uses_partial_score_even_when_whole_gradient_unknown(self):
        r = row(); start = initial(); k = 'missing_member_fraction'
        r['available'][k] = False; r['gradient_delta'][k] = None
        floor = l.base.gap(r, start)-F(1, 10000)
        new, power = l.guarded_step(start, start | {k: start[k]-F(1, 20)},
                                  l.base.bounds(start), [(r, floor)])
        self.assertGreater(power, 0)
        self.assertGreaterEqual(l.base.gap(r, new), floor)

    def test_partial_cost_can_protect_but_unknown_is_not_gradient(self):
        keep = row(); k = 'missing_member_fraction'; keep['available'][k] = False
        keep['gradient_delta'][k] = None; keep['loss'] = l.q(99)
        m = fit([keep], [protected(keep)])
        self.assertEqual(m['weights'], m['initial_weights']); self.assertFalse(m['updates'])
        self.assertEqual(m['after']['protection_floors'], 1)

    def test_fixed_and_unknown_non_grid_values_unchanged(self):
        r = row(); r['loss'] = l.q(99); k = l.base.ledger.context.FEATURES[0]
        r['available'][k] = False; r['gradient_delta'][k] = None; r['score_delta'][k] = l.q(-1)
        m = fit([r])
        self.assertEqual(m['weights'][k], m['initial_weights'][k])
        for k in l.FIXED: self.assertEqual(m['weights'][k], m['initial_weights'][k])
        for k in l.FEATURES:
            self.assertLessEqual(abs(l.f(m['weights'][k])-initial()[k]), l.base.RADIUS)

    def test_missing_duplicate_scope_and_zero_loss_competitors_rejected(self):
        r = row(); p = protected(r)
        for comps in ([p | {'active_contrast_id': 'missing'}], [p, p], [p | {'sample_id': 'wrong'}]):
            with self.assertRaises(ValueError): fit([r], comps)
        r['loss'] = l.q(0)
        with self.assertRaises(ValueError): fit([r], [protected(r)])

    def test_nontrain_and_invalid_unknown_masks_rejected(self):
        r = row()
        with self.assertRaises(ValueError): fit([r | {'entry': entry(split='dev')}])
        k = 'missing_member_fraction'; r['available'][k] = False
        with self.assertRaises(ValueError): fit([r])

    def test_sealed_model_binds_pool_protections_weights_and_research_use(self):
        rows = [row()]; comps = [protected(rows[0])]; m = fit(rows, comps); manifest = [entry()]
        args = (rows, comps, initial(), contract(manifest), manifest, 'parent', 'pool')
        self.assertEqual(l.model_weights(m, *args), {k: l.f(v) for k, v in m['weights'].items()})
        for bad in (m | {'production_deployment': True}, m | {'dev_used': True},
                    m | {'policy': {}}, m | {'weights': {}}):
            with self.assertRaises(ValueError): l.model_weights(bad, *args)
        with self.assertRaises(ValueError): l.model_weights(m, *args[:-1], 'changed')


if __name__ == '__main__': unittest.main()
