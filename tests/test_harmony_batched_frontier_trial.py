from unittest.mock import patch
import unittest

from musicanote_harness import harmony_batched_frontier_trial as batched_trial
import test_harmony_exact_frontier_trial as proofs


class BatchedFrontierTrialTests(proofs.ExactFrontierTrialTests):
    """Apply the same physical seal/control/tamper tests to the factored runner."""
    def setUp(self):
        p = patch.object(proofs, "trial", batched_trial)
        p.start(); self.addCleanup(p.stop)


if __name__ == "__main__": unittest.main()
