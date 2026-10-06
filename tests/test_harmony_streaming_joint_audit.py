import importlib.util
import json
from pathlib import Path
import unittest

from musicanote_harness import harmony_streaming_joint as stream
from test_harmony_streaming_joint import pages

spec = importlib.util.spec_from_file_location("stream_audit_v2", Path(__file__).parents[1]/"scripts/audit_harmony_streaming_joint_v2.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class AuditSerializationTests(unittest.TestCase):
    def test_json_array_checkpoint_and_in_memory_tuple_same_value(self):
        graph, ev, ranges, batches = pages(); session = stream.JointStream(graph, ev, ranges)
        session.consume(batches[0]); snapshot = session.snapshot()
        disk = json.loads(json.dumps(snapshot))
        restored = stream.JointStream(graph, ev, ranges, checkpoint=disk)
        self.assertNotEqual(restored.snapshot(), disk)  # Reproduce V1's direct-equality failure.
        self.assertTrue(audit.checkpoint_matches(restored.snapshot(), disk))
        self.assertEqual(restored.operations, session.operations)

    def test_real_counter_and_frontier_changes_not_hidden_by_normalization(self):
        graph, ev, ranges, batches = pages(); session = stream.JointStream(graph, ev, ranges)
        session.consume(batches[0]); snapshot = session.snapshot()
        for field in ("operations", "frontier"):
            disk = json.loads(json.dumps(snapshot))
            if field == "operations": disk[field] += 1
            else: disk[field][0]["cost_units"] += 1
            self.assertFalse(audit.checkpoint_matches(snapshot, disk))
            with self.assertRaisesRegex(ValueError, "binding_or_seal"):
                stream.JointStream(graph, ev, ranges, checkpoint=disk)


if __name__ == "__main__": unittest.main()
