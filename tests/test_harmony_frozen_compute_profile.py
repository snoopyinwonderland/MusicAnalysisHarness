from copy import deepcopy
import cProfile
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from musicanote_harness import harmony_frozen_compute_profile as p


class FrozenComputeProfileTests(unittest.TestCase):
    def inventory(self):
        rows = [dict(sample_id=str(i), selected_ids=['path'], status='selected', work_family_id=str(i % 5),
                     evaluation={'selected_hit': bool(i % 2)}) for i in range(12)]
        rows[0].update(selected_ids=None, status='context_wall_budget_abstention')
        rows[1].update(selected_ids=None, status='context_wall_budget_abstention')
        return rows, {str(i): i+1 for i in range(12)}

    def test_all_walls_and_size_only_distinct_controls(self):
        rows, sizes = self.inventory(); before = deepcopy(rows)
        selected = p.cohort(rows, sizes)
        self.assertEqual([r['sample_id'] for r, g in selected], ['0', '1', '11', '10', '9', '8'])
        self.assertEqual(rows, before)
        for r in rows: r['evaluation'] = {'selected_hit': not r['evaluation']['selected_hit']}
        self.assertEqual([r['sample_id'] for r, g in p.cohort(rows, sizes)], ['0', '1', '11', '10', '9', '8'])

    def test_changed_inventory_or_missing_controls_rejected(self):
        rows, sizes = self.inventory()
        for data, count in ((sizes | {'extra': 3}, 4), (sizes | {'0': 0}, 4), (sizes, 0), (sizes, 6)):
            with self.assertRaises(ValueError): p.cohort(rows, data, count)
        rows[0]['status'] = 'unexpected'
        with self.assertRaisesRegex(ValueError, 'unexpected_historical'): p.cohort(rows, sizes)

    def test_no_overwrite_before_reading_or_fit(self):
        with TemporaryDirectory() as d, patch.object(p.train, 'context', side_effect=AssertionError('read')):
            with self.assertRaisesRegex(ValueError, 'output_exists'): p.run(d)

    def test_raw_calls_including_callers_preserved(self):
        def helper(): return sum(range(10))
        profiler = cProfile.Profile(); profiler.runcall(helper)
        rows = p.profile_rows(profiler)
        self.assertTrue(any(r['function'] == 'helper' for r in rows))
        self.assertTrue(all(r['calls'] >= r['primitive_calls'] for r in rows))
        self.assertEqual(rows, sorted(rows, key=lambda r: (-r['cumulative_seconds'], r['file'], r['line'], r['function'])))


if __name__ == '__main__': unittest.main()
