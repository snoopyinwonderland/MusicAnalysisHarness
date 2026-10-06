import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from musicanote_harness.harmony_phase_checkpoint import AtomicTelemetry


class CheckpointTests(unittest.TestCase):
    def test_complete_atomic_checkpoint_and_active_phase(self):
        with TemporaryDirectory() as d:
            path=Path(d)/'phase.json';telemetry=AtomicTelemetry(path)
            telemetry.checkpoint(cells_consumed=32)
            with telemetry.phase('search',persist=True):
                row=json.loads(path.read_text())
                self.assertEqual(row['active'][0]['phase'],'search')
                self.assertEqual(row['progress']['cells_consumed'],32)
            self.assertEqual(json.loads(path.read_text())['active'],[])
            self.assertFalse(path.with_name(path.name+'.pending').exists())

    def test_failed_publish_preserves_previous_json(self):
        with TemporaryDirectory() as d:
            path=Path(d)/'phase.json';telemetry=AtomicTelemetry(path)
            telemetry.checkpoint(cells_consumed=32);before=path.read_bytes()
            with patch('musicanote_harness.harmony_phase_checkpoint.os.replace',side_effect=PermissionError('simulated interruption')):
                with self.assertRaises(PermissionError):telemetry.checkpoint(cells_consumed=64)
            self.assertEqual(path.read_bytes(),before)
            self.assertEqual(json.loads(path.read_text())['progress']['cells_consumed'],32)


if __name__=='__main__':unittest.main()
