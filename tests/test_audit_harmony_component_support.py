from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from audit_harmony_component_support import compare_packet
from musicanote_harness.harmony_root_context_trial import check_prediction


class ComponentSupportAuditTests(unittest.TestCase):
    def test_json_array_tuple_is_canonical(self):
        packet={"arms":{"combined":{"selected_prediction":{"members":[["C",0]]}}}}
        row=deepcopy(packet);row["arms"]["combined"]["selected_prediction"]["members"]=[("C",0)]
        row["arms"]["combined"]["evaluation"]={};compare_packet(packet,row)
    def test_score_tamper_is_not_ignored(self):
        packet={"arms":{"combined":{"selected_prediction":{"cost":1}}}}
        row=deepcopy(packet);row["arms"]["combined"]["selected_prediction"]["cost"]=2
        with self.assertRaisesRegex(ValueError,"sealed_prediction_changed"):compare_packet(packet,row)
    def test_gold_nested_in_receipt_rejected(self):
        with self.assertRaisesRegex(ValueError,"reference_bearing"):check_prediction({"receipts":[{"evaluation":{}}]})


if __name__=="__main__":unittest.main()
