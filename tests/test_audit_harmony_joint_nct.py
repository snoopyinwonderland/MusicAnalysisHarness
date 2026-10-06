from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from audit_harmony_joint_nct import check_confirmation


class JointNCTAuditTests(unittest.TestCase):
    def packet(self):return {'confidence':None,'human_validated':False,'joint_nct_observations':[
        {'confirmed_nct':False,'raw_nonmember_cost_removed':False,'status':'conditional_support','withheld_reasons':[]}]}

    def test_unverified_nct_not_promoted(self):
        p=self.packet();check_confirmation(p)
        p['joint_nct_observations'][0]['confirmed_nct']=True
        with self.assertRaisesRegex(ValueError,'unsupported_nct_confirmation'):check_confirmation(p)

    def test_withheld_credit_and_confidence_rejected(self):
        p=self.packet();p['joint_nct_observations'][0]['withheld_reasons']=['wrong_role']
        with self.assertRaisesRegex(ValueError,'withheld_credit_consumed'):check_confirmation(p)
        p=self.packet();p['confidence']=.9
        with self.assertRaisesRegex(ValueError,'unsupported_confirmation'):check_confirmation(p)


if __name__=='__main__':unittest.main()
