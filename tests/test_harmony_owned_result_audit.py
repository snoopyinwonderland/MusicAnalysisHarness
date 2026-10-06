from fractions import Fraction as F
import unittest

from audit_harmony_owned_results import source_duration


class SourceDurationTests(unittest.TestCase):
    def fixture(self, score, start, duration):
        return dict(score=dict(duration_quarters=score), measures=[
            dict(global_start_quarter=start, actual_duration_quarter=duration)])

    def test_trailing_measure_end_not_last_note_release(self):
        self.assertEqual(source_duration(self.fixture('193', '192', '2')), F(194))

    def test_score_release_can_extend_beyond_measure_end(self):
        self.assertEqual(source_duration(self.fixture('195', '192', '2')), F(195))

    def test_fractional_pickup_and_tuplet_times_are_exact(self):
        self.assertEqual(source_duration(self.fixture('5/3', '4/3', '2/3')), F(2))

    def test_empty_measure_list_retains_score_clock(self):
        self.assertEqual(source_duration(dict(score=dict(duration_quarters='1/3'), measures=[])), F(1,3))
