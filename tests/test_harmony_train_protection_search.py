from copy import deepcopy
from dataclasses import replace
from fractions import Fraction as F
import random
import unittest

from musicanote_harness import harmony_train_protection_search as t
from musicanote_harness import harmony_joint_balance_trial as trial
from musicanote_harness.harmony_margin_learning import training_loss
from test_harmony_member_role_scoring import toy as parent_toy, paths, C, FM, by_path
from test_harmony_score_balance_ledger import fixture


def toy(notes=None, end=3, **kwargs):
    return parent_toy(notes=notes or [('E4', 0, 1, 'lead'), ('F4', 1, 2, 'lead'),
        ('E4', 2, end, 'lead'), ('C3', 0, end, 'bass')], end=end, **kwargs)


def loss(graph, runs):
    cells = [dict(start=F(a), end=F(b), signature=sig, context='key', available=True)
             for a, b, sig in runs]
    return training_loss(graph, cells)


class ProtectionSearchTests(unittest.TestCase):
    def check_exact(self, graph, ev, weights, gold):
        sc = trial.Scorer(graph, ev, weights); before = deepcopy(weights)
        values = [(sc.score_path(ids), ids) for ids in paths(graph)
                  if t.f(t.path_loss(graph, {'selected': {'segments': [
                      {'semantic_group_ref': x} for x in ids]}}, gold)['total']) > 0]
        result = t.decode(sc, gold, wall_seconds=60)
        self.assertEqual(weights, before)
        if not values:
            self.assertIsNone(result['path_ids'])
            self.assertEqual(result['status'], 'no_positive_loss_path_under_original_cap')
        else:
            self.assertEqual((t.f(result['ordinary_cost']), tuple(result['path_ids'])), min(values))
            self.assertGreater(t.f(result['training_loss']['total']), 0)
            self.assertFalse(result['analysis_export_allowed'])
            self.assertFalse(result['loss_used_as_score'])
            trial.ledger.flatten(result['receipt'], weights)
        self.assertTrue(result['exact_optimum_among_positive_loss_paths'])
        return result

    def test_signed_three_run_costs_match_all_tiny_paths(self):
        graph, ev, _ = toy(end=3, cap=3); rng = random.Random(8701)
        for _ in range(4):
            weights = fixture()[2]
            weights |= {k: rng.choice((F(-1, 3), F(), F(1, 5)))
                        for k in (*trial.ledger.context.FEATURES, *trial.ledger.role.FEATURES)}
            self.check_exact(graph, ev, weights, loss(graph, [(0, 1, C), (1, 3, FM)]))

    def test_all_same_signature_raw_partitions_are_correct_not_negatives(self):
        graph, ev, _ = toy(end=3, signatures=(C,), cap=3)
        self.check_exact(graph, ev, fixture()[2], loss(graph, [(0, 3, C)]))

    def test_error_bit_survives_reconvergence_with_same_last_history(self):
        graph, ev, _ = toy(end=3, cap=3)
        # A cheaper correct path must not erase a wrong path sharing endpoint/history.
        self.check_exact(graph, ev, fixture()[2], loss(graph, [(0, 3, C)]))
        history = ((0, C),)
        states = {(1, history, False): (F(), ('a',)),
                  (2, history, False): (F(1), ('b',)),
                  (2, history, True): (F(2), ('c',))}
        kept, n = t.error_pareto(states)
        self.assertIn((2, history, True), kept); self.assertEqual(n, 1)

    def test_wall_and_operation_limit_never_return_partial_winners(self):
        graph, ev, _ = toy(end=3); gold = loss(graph, [(0, 3, C)])
        for kw in ({'transition_budget': 1}, {'wall_seconds': .1, 'timer': iter(range(100000)).__next__}):
            result = t.decode(trial.Scorer(graph, ev, fixture()[2]), gold, **kw)
            self.assertIsNone(result['path_ids']); self.assertFalse(result['partial_winner_returned'])
            self.assertFalse(result['exact_optimum_among_positive_loss_paths'])

    def test_original_cap_no_candidate_injection_and_missing_complete_reference(self):
        graph, ev, _ = toy(end=3, cap=1)
        self.check_exact(graph, ev, fixture()[2], loss(graph, [(0, 3, C)]))
        bad = replace(loss(graph, [(0, 3, C)]), edge_time_error={})
        with self.assertRaisesRegex(ValueError, 'training_loss_mismatch'):
            t.decode(trial.Scorer(graph, ev, fixture()[2]), bad)
        with self.assertRaises(ValueError):
            training_loss(graph, [dict(start=F(0), end=F(2), signature=C, context='key', available=True)])

    def test_unknown_voice_and_meter_keep_whole_availability_null(self):
        graph, ev, _ = toy(end=3, cap=2)
        sc = trial.Scorer(graph, ev, fixture()[2])
        for row in sc.context.rows.values():
            row['identity'] = None
        result = t.decode(sc, loss(graph, [(0, 3, C)]), wall_seconds=60)
        receipt = result['receipt']; trial.ledger.flatten(receipt, fixture()[2])
        self.assertFalse(receipt['confirmed_nct'])

    def test_duplicate_raw_edge_ids_do_not_create_new_musical_error(self):
        graph, ev, _ = toy(end=3, signatures=(C,), cap=3)
        graph = replace(graph, edges=graph.edges+(replace(graph.edges[0], group_id='duplicate'),))
        self.check_exact(graph, ev, fixture()[2], loss(graph, [(0, 3, C)]))


if __name__ == '__main__': unittest.main()
