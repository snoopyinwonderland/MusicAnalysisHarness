import importlib.util
from copy import deepcopy
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("temporal_audit", Path(__file__).resolve().parents[1]/"scripts/audit_harmony_temporal_scoring.py")
audit = importlib.util.module_from_spec(spec); spec.loader.exec_module(audit)


class TemporalAuditTests(unittest.TestCase):
    def packet(self): return {"sample_span": {"start": 0, "end": 1}, "arms": {"baseline": {"selected_prediction": {"x": (1, 2)}}}}
    def test_canonical_json_array_and_tuple_equal(self):
        packet = self.packet(); row = deepcopy(packet)
        row["arms"]["baseline"]["selected_prediction"]["x"] = [1, 2]
        row["arms"]["baseline"]["evaluation"] = {"selected_hit": False}
        audit.compare_packet(packet, row)
    def test_prediction_tamper_rejected(self):
        packet = self.packet(); row = deepcopy(packet)
        row["arms"]["baseline"]["selected_prediction"]["x"] = (1, 3)
        with self.assertRaisesRegex(ValueError, "changed"): audit.compare_packet(packet, row)
    def test_reference_inference_contamination_rejected(self):
        packet = self.packet(); packet["arms"]["baseline"]["evaluation"] = {}
        with self.assertRaisesRegex(ValueError, "reference_in_prediction"): audit.compare_packet(packet, packet)


if __name__ == "__main__": unittest.main()
