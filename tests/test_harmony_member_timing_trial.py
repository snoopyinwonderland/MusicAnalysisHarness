import unittest
from tempfile import TemporaryDirectory
from musicanote_harness import harmony_member_timing_trial as t
from musicanote_harness.harmony_temporal_scoring import bind
import test_harmony_recipe_balance_trial as template
from test_harmony_member_timing_learning import row as train_row


class TrialTests(unittest.TestCase):
    def disk(self, mode):
        return bind(template.TrialTests.disk, {'t': t, 'train_row': train_row})(self, mode)
    def test_seal_and_same_control(self): self.disk('selected')
    def test_abstentions(self): self.disk('abstention')
    def test_reference_contamination(self): self.disk('contamination')
    def test_graph_tamper(self): self.disk('graph')
    def test_source_tamper(self): self.disk('source')
    def test_no_overwrite(self):
        with TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError, 'output_exists'): t.run('missing', d)
