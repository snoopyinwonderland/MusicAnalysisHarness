from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('scalar_metric_audit_v2', Path('scripts/audit_harmony_context_scalar_metrics_v2.py'))
audit = importlib.util.module_from_spec(spec); spec.loader.exec_module(audit)


class ScalarCounterTests(unittest.TestCase):
    def test_tuple_list_same_path_does_not_count_as_changed(self):
        row = {'selected_ids': ('a', 'b'), 'prior_selected_ids': ['a', 'b'],
               'original_baseline_ids': ['a', 'c'], 'evaluation': {'unchanged': True}}
        before = deepcopy(row); normalized = audit.canonical_records([row])[0]
        self.assertEqual(normalized['selected_ids'], normalized['prior_selected_ids'])
        self.assertNotEqual(normalized['selected_ids'], normalized['original_baseline_ids'])
        self.assertEqual(row, before); self.assertEqual(normalized['evaluation'], row['evaluation'])

    def test_abstention_stays_null_and_invalid_id_path_rejected(self):
        row = dict.fromkeys(audit.FIELDS)
        self.assertEqual(audit.canonical_records([row]), [row])
        for bad in ('a', [], [1], ['']):
            with self.assertRaises(ValueError): audit.canonical_records([row | {'selected_ids': bad}])

    def test_only_allowed_counter_differences_are_identified(self):
        raw = {'against_same_model_stage80': {'changes': {'path_changed_with_complete_selection': 104}, 'time': .48}}
        fixed = {'against_same_model_stage80': {'changes': {'path_changed_with_complete_selection': 14}, 'time': .48}}
        changes = audit.differences(raw, fixed)
        self.assertEqual(changes, [(('against_same_model_stage80', 'changes', 'path_changed_with_complete_selection'), 104, 14)])
        self.assertTrue({p for p, _, _ in changes} <= audit.ALLOWED)


if __name__ == '__main__': unittest.main()
