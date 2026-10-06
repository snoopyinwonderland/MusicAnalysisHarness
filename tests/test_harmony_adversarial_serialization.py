"""Regression for the audit's tuple-versus-JSON-array comparison failure."""
import json
import unittest
from musicanote_harness.harmony_structured_learning import content_hash


class AdversarialSerializationTests(unittest.TestCase):
    def test_runtime_path_tuples_and_persisted_json_arrays_are_equivalent(self):
        value = {'negative_ids': ('edge_a', 'edge_b'), 'target_ids': ('edge_c',),
                 'ordinary_ids': ('edge_c',), 'cost': {'numerator': 1, 'denominator': 3}}
        persisted = json.loads(json.dumps(value))
        self.assertNotEqual(value, persisted)
        self.assertEqual(content_hash(value), content_hash(persisted))

    def test_array_order_is_never_normalized_away(self):
        self.assertNotEqual(content_hash({'ids': ('a', 'b')}), content_hash({'ids': ['b', 'a']}))

    def test_null_and_known_zero_remain_distinct(self):
        self.assertNotEqual(content_hash({'feature': None}), content_hash({'feature': {'numerator': 0, 'denominator': 1}}))

    def test_exact_rational_or_feature_tampering_still_fails(self):
        value = {'delta': {'numerator': 1, 'denominator': 3}, 'available': False}
        for changed in ({'delta': {'numerator': 2, 'denominator': 3}, 'available': False},
                        value | {'available': True}):
            self.assertNotEqual(content_hash(value), content_hash(changed))


if __name__ == '__main__': unittest.main()
