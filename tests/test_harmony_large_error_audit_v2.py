from copy import deepcopy
from fractions import Fraction as F
import json
import unittest
from musicanote_harness import harmony_large_error_audit_v2 as a
import test_harmony_member_release as fixtures
from musicanote_harness import harmony_member_release as s


class LargeErrorAuditTests(unittest.TestCase):
    def test_tuple_list_equivalence_but_not_changed_content(self):
        case = dict(winner_path_ids=None)
        summary = a.t.summary([case]); summary['largest_completed_errors'] = []
        a.check_summary([case], json.loads(json.dumps(summary)))
        summary['counts']['records'] = 2
        with self.assertRaises(ValueError): a.check_summary([case], summary)

    def test_release_arithmetic_recomputed(self):
        builder = fixtures.MemberReleaseTests(); graph, ev = builder.make()
        value, receipt = builder.value(graph, ev)
        profile = dict(observations=[receipt], availability=True, known_partial_sum=s.q(value), feature=s.q(value))
        a.check_feature(profile)
        wrong = deepcopy(profile); wrong['observations'][0]['feature'] = s.q(F(3, 4))
        with self.assertRaisesRegex(ValueError, 'arithmetic'): a.check_feature(wrong)

    def test_path_unknown_cannot_become_zero(self):
        builder = fixtures.MemberReleaseTests(); graph, ev = builder.make()
        ev.rows[0]['clock_valid'] = False; value, receipt = builder.value(graph, ev)
        profile = dict(observations=[receipt], availability=False, known_partial_sum=s.q(0), feature=None)
        a.check_feature(profile); profile['feature'] = s.q(0)
        with self.assertRaisesRegex(ValueError, 'path_sum'): a.check_feature(profile)

    def test_list_tuple_in_nested_functional_context(self):
        original = {'signature': (('G', 0), (('C', 0), ('E', 0), ('G', 0)))}
        loaded = json.loads(json.dumps(original))
        self.assertNotEqual(original, loaded)
        self.assertTrue(a.t.parent.train.same_json(original, loaded))
        loaded['signature'][0][0] = 'F'
        self.assertFalse(a.t.parent.train.same_json(original, loaded))


if __name__ == '__main__': unittest.main()
