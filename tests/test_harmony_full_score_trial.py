from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from musicanote_harness import harmony_full_score_trial as t


class TrialTests(unittest.TestCase):
    def test_output_no_overwrite_precedes_any_source_read(self):
        with TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, 'no_overwrite'):
                t.run('nonexistent-source', Path(directory))

    def test_training_pins_cover_completed_pool_and_audit(self):
        self.assertEqual(len(t.training.PINS), 3)
        self.assertTrue(any(p.endswith('post-seal-audit.json') for p in t.training.PINS))
        self.assertTrue(all(len(h) == 64 for h in t.training.PINS.values()))

    def test_initial_and_trained_arms_are_not_target_paths(self):
        self.assertEqual(t.ARMS, ('initial_full_score', 'trained_full_score'))
        self.assertEqual(t.s.FIXED, ('blocker_exposure', 'unresolved_spelling_exposure'))
