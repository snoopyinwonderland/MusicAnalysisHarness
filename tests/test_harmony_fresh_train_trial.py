from copy import deepcopy
from tempfile import TemporaryDirectory
import unittest
from musicanote_harness import harmony_fresh_train_trial as t


class TrialTests(unittest.TestCase):
    def test_train_cohort_not_only_historical_updates_and_no_dev(self):
        rows = [{'sample_id': x, 'split': split, 'work_family_id': 'f'} for x, split in [('a', 'train'), ('b', 'dev'), ('c', 'train')]]
        previous, learned = {'records': deepcopy(rows)}, {'records': deepcopy(rows)}
        _, selected = t.train_records(previous, learned, {'e': {'manifest_entry_id': 'e'}})
        self.assertEqual([r['sample_id'] for r in selected], ['a', 'c'])

    def test_duplicate_or_changed_cohort_rejected(self):
        rows = [{'sample_id': 'a', 'split': 'train', 'work_family_id': 'f'}]
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            t.train_records({'records': rows+rows}, {'records': rows}, {})
        with self.assertRaisesRegex(ValueError, 'scope_set'):
            t.train_records({'records': rows}, {'records': []}, {})

    def test_quarantine_abstention_partial_and_error_categories(self):
        gate, result = {'accepted': True}, {'selected': {}}
        ev = {'fully_evaluable': True, 'selected_hit': False}
        for ceiling, expected in [({'reachable': True}, 'selection_error_with_reference_path'),
                                  ({'reachable': False}, 'reference_path_absent_or_cap_blocked'),
                                  ({'reachable': None}, 'reference_path_unresolved')]:
            self.assertEqual(t.classify(gate, ceiling, result, ev), expected)
        self.assertEqual(t.classify({'accepted': False}, {}, result, ev), 'source_clock_quarantined')
        self.assertEqual(t.classify(gate, {}, {'selected': None}, ev), 'prediction_abstention')
        self.assertEqual(t.classify(gate, {}, result, ev | {'fully_evaluable': False}), 'partial_or_unsupported_reference')
        self.assertEqual(t.classify(gate, {}, result, ev | {'selected_hit': True}), 'reference_agreement')

    def test_no_overwrite(self):
        with TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError, 'output_exists'): t.run(d)
