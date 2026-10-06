from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from audit_harmony_root_context import compare_packet
from musicanote_harness.harmony_root_context_trial import check_prediction


class RootContextAuditTests(unittest.TestCase):
    def test_json_array_and_python_tuple_compare_canonically(self):
        packet={"arms":{"bass_return":{"selected_prediction":{"members":[["C",0]]}}}}
        row=deepcopy(packet);row["arms"]["bass_return"]["selected_prediction"]["members"]=[("C",0)]
        row["arms"]["bass_return"]["evaluation"]={};compare_packet(packet,row)
    def test_score_tamper_rejected(self):
        packet={"arms":{"bass_return":{"selected_prediction":{"cost":1}}}}
        row=deepcopy(packet);row["arms"]["bass_return"]["selected_prediction"]["cost"]=2
        with self.assertRaisesRegex(ValueError,"sealed_prediction_changed"):compare_packet(packet,row)
    def test_gold_anywhere_in_prediction_rejected(self):
        with self.assertRaisesRegex(ValueError,"reference_bearing"):check_prediction({"a":[{"evaluation":{}}]})


if __name__=="__main__":unittest.main()
