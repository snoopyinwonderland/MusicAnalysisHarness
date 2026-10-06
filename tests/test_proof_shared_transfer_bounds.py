"""Source-support/LCM proof controls; synthetic fixtures, not corpus accuracy."""
from dataclasses import replace
from fractions import Fraction
from itertools import combinations
import gc
import json
import random
import unittest
from unittest.mock import patch
import weakref

from musicanote_harness import proof_shared_transfer_bounds as bounds
from musicanote_harness import proof_shared_progression_streaming as stream
from musicanote_harness import proof_shared_source_progression_contrast as core
from musicanote_harness import shared_source_progression_contrast as shared
from musicanote_harness import lossless_json_dag_v2 as dag
from musicanote_harness import cross_batch_progression_contrast as codec
from musicanote_harness.musical_pattern_observation import q
from musicanote_harness import factor_native_role_explanations as roles
from musicanote_harness import factor_expanded_hypotheses as kernels
from test_cross_batch_progression_contrast import request_ref
from test_factor_expanded_hypotheses import span
import test_proof_shared_progression_streaming as fixtures


def raw(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False).encode("utf-8")


def refinement(points):
    return codec._freeze({"sounds": [{"points": [q(p) for p in sound]} for sound in points],
        "bass": {"points": []}})


class TransferArithmeticControls(unittest.TestCase):
    def budget(self, **options):
        return bounds._Budget(replace(bounds.DEFAULT_LIMITS, **options))

    def test_repeated_denominators_use_lcm_not_repeated_product_width(self):
        value = refinement([[Fraction(i, 4) for i in range(101)]] * 3)
        exact = bounds._endpoint_lattice(value, self.budget())
        legacy = stream._refinement_summary(value, stream._Measure(1000000000))
        self.assertEqual(exact["denominator_lcm"], 4)
        self.assertEqual(exact["total_span_numerator_bound"], 300)
        self.assertEqual(exact["endpoint_count"], 303)
        self.assertLess(exact["transfer_rational_bytes"], legacy["transfer_rational_bytes"])
        self.assertLessEqual(len(raw(q(Fraction(75)))), exact["transfer_rational_bytes"])

    def test_coprime_negative_offsets_all_interval_subset_sums_are_covered(self):
        sounds = [[Fraction(-2, 3), Fraction(1, 5), Fraction(7, 11)],
                  [Fraction(-1, 7), Fraction(0), Fraction(5, 13)]]
        exact = bounds._endpoint_lattice(refinement(sounds), self.budget())
        self.assertEqual(exact["denominator_lcm"], 3 * 5 * 7 * 11 * 13)
        intervals = [b - a for sound in sounds for a, b in zip(sound, sound[1:])]
        for count in range(len(intervals) + 1):
            for subset in combinations(intervals, count):
                value = sum(subset, Fraction())
                self.assertEqual(exact["denominator_lcm"] % value.denominator, 0)
                self.assertLessEqual(value.numerator, exact["total_span_numerator_bound"])
                self.assertLessEqual(len(raw(q(value))), exact["transfer_rational_bytes"])

    def test_empty_singleton_zero_duration_points_remain_valid_bounds(self):
        for points in ([], [[]], [[Fraction(9)]], [[Fraction(1, 3), Fraction(1, 3)]]):
            with self.subTest(points=points):
                exact = bounds._endpoint_lattice(refinement(points), self.budget())
                self.assertEqual(exact["total_span_numerator_bound"], 0)
                self.assertLessEqual(len(raw(q(Fraction()))), exact["transfer_rational_bytes"])

    def test_nonmonotone_and_invalid_rational_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "monotone"):
            bounds._endpoint_lattice(refinement([[Fraction(1), Fraction()]]), self.budget())
        for point in ({"numerator": True, "denominator": 1},
                      {"numerator": 0, "denominator": 0},
                      {"numerator": 0.0, "denominator": 1}):
            value = codec._freeze({"sounds": [{"points": [point]}]})
            with self.subTest(point=point):
                with self.assertRaises(ValueError):
                    bounds._endpoint_lattice(value, self.budget())

    def test_work_gate_precedes_gcd_and_hold_has_unknown_not_zero(self):
        with patch.object(bounds, "gcd", side_effect=AssertionError("no arithmetic before budget")):
            with self.assertRaises(bounds.TransferBoundHold) as caught:
                bounds._endpoint_lattice(refinement([[Fraction(1, 3)]]), self.budget(max_work=20))
        self.assertIsNone(caught.exception.diagnostics["raw_block_byte_upper_bound"])
        self.assertEqual(caught.exception.diagnostics["pair_outputs_computed"], 0)

    def test_bigint_bit_gate_precedes_gcd_or_large_product(self):
        with patch.object(bounds, "gcd", side_effect=AssertionError("no oversized gcd")):
            with self.assertRaises(bounds.TransferBoundHold):
                bounds._endpoint_lattice(refinement([[Fraction(1, 1 << 100)]]),
                    self.budget(max_integer_bits=64))
        budget = self.budget(max_integer_bits=64)
        with self.assertRaises(bounds.TransferBoundHold):
            budget.multiply(1 << 40, 1 << 40)

    def test_scratch_gate_precedes_arithmetic(self):
        with patch.object(bounds, "gcd", side_effect=AssertionError("no arithmetic before scratch reserve")):
            with self.assertRaisesRegex(bounds.TransferBoundHold, "scratch"):
                bounds._endpoint_lattice(refinement([[Fraction(1, 3)]]),
                    self.budget(max_scratch_bytes=1))

    def test_limits_reject_boolean_float_zero_and_negative(self):
        for name in ("max_work", "max_integer_bits", "max_scratch_bytes", "max_retained_proof_bytes"):
            for value in (True, 1.5, 0, -1):
                with self.subTest(name=name, value=value):
                    with self.assertRaises(ValueError):
                        replace(bounds.DEFAULT_LIMITS, **{name: value})

    def test_support_uses_source_rows_including_zero_credit_and_deduplicates(self):
        categories = core.CATEGORIES
        view = codec._freeze({"source_rows": {"a": [{"category": categories[0]}] * 5,
            "b": [{"category": categories[-1]}]}, "account": {"credit": None}})
        support, width, rows = bounds._entry_support(view, self.budget())
        self.assertEqual(set(support), {categories[0], categories[-1]})
        self.assertEqual(rows, 6)
        self.assertEqual(width, max(stream._string_width(c) for c in support))

    def test_closed_category_vocabulary_does_not_silently_drop_unknown(self):
        view = codec._freeze({"source_rows": {"a": [{"category": "new_unregistered_role"}]}})
        with self.assertRaisesRegex(ValueError, "closed_owned_transfer_category"):
            bounds._entry_support(view, self.budget())

    def test_cartesian_support_bound_covers_all_six_categories_and_empty_sets(self):
        categories = tuple(core.CATEGORIES)
        width = max(stream._string_width(c) for c in categories)
        full = (categories, width, 6)
        one = ((categories[0],), stream._string_width(categories[0]), 1)
        empty = ((), 0, 0)
        for left, right, atoms in ((full, full, 100), (full, one, 100), (empty, full, 100),
                                   (one, full, 3), (full, full, 0)):
            size, count = bounds._transfer_component(left, right, atoms, len(raw(q(Fraction(1, 3)))))
            self.assertEqual(count, min(len(left[0]) * len(right[0]), atoms))
            rows = [{"left": a, "right": b, "duration_quarters": q(Fraction(1, 3))}
                for a in left[0] for b in right[0]][:count]
            self.assertLessEqual(len(raw(rows)), size)

    def test_seeded_fraction_lattices_and_random_role_transfers(self):
        rng = random.Random(20261003)
        categories = tuple(core.CATEGORIES)
        for case in range(80):
            sounds = [sorted({Fraction(rng.randint(-12, 24), rng.randint(1, 8))
                for _ in range(rng.randint(2, 6))}) for _ in range(rng.randint(1, 4))]
            exact = bounds._endpoint_lattice(refinement(sounds), self.budget())
            transfers, left_set, right_set = {}, set(), set()
            for sound in sounds:
                for a, b in zip(sound, sound[1:]):
                    left, right = rng.choice(categories), rng.choice(categories)
                    left_set.add(left)
                    right_set.add(right)
                    transfers[(left, right)] = transfers.get((left, right), Fraction()) + b - a
            left = (tuple(sorted(left_set)), max((stream._string_width(c) for c in left_set), default=0), 0)
            right = (tuple(sorted(right_set)), max((stream._string_width(c) for c in right_set), default=0), 0)
            size, count = bounds._transfer_component(left, right, exact["sound_atoms"], exact["transfer_rational_bytes"])
            rows = [{"left": a, "right": b, "duration_quarters": q(v)} for (a, b), v in transfers.items()]
            with self.subTest(case=case):
                self.assertLessEqual(len(rows), count)
                self.assertLessEqual(len(raw(rows)), size)
                for value in transfers.values():
                    self.assertEqual(exact["denominator_lcm"] % value.denominator, 0)
                    self.assertLessEqual(value.numerator, exact["total_span_numerator_bound"])


class OwnedTransferBoundControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.ProofSharedProgressionStreamingControls.setUpClass()
        cls.addClassCleanup(fixtures.ProofSharedProgressionStreamingControls.doClassCleanups)
        cls.groups = dict(fixtures.ProofSharedProgressionStreamingControls.groups)
        fixture = fixtures.ProofSharedProgressionStreamingControls.fixture.fixture.fixture
        members = fixtures.fixture_module.fixture_module.fixture_module.members("C", "E", "G")
        selectors = [fixture.selector("three_slots"),
            fixture.selector("three_slots", partitions=[(span(0, 4), ("C", Fraction()), members)], assumptions=[]),
            fixture.selector("three_slots", partitions=[(span(0, 1), ("C", Fraction()), members),
                (span(1, 4), ("C", Fraction()), members)], assumptions=[None])]
        session, comparison, bundle = fixture.comparison("three_slots", selectors=selectors)
        explained = roles.explain_prepared(roles.prepare_explanations(session, comparison), query_work_budget=100000000)
        entries = [{"native_path": path, "role_path": role, "comparison_ref": kernels._ref(comparison),
            "explanation_ref": kernels._ref(explained)} for path, role in zip(comparison["paths"], explained["paths"])]
        source = shared.prepare_saved_source(fixture.case("three_slots")[0][1], fixture.record("three_slots"),
            bundles={bundle["record_id"]: bundle})
        cls.groups["three_entry_partition"] = (source, core.prepare_saved_group(source, entries,
            completion_request_ref=request_ref(), block_size=3))
        cls.proofs = {name: bounds.prepare_transfer_bounds(group) for name, (_, group) in cls.groups.items()}

    def test_preparation_no_export_decode_pair_atom_runs_or_outcome_sampling(self):
        _, group = self.groups["passing"]
        with patch.object(core.CompactPreparedGroup, "export_catalog", side_effect=AssertionError("no export")), \
                patch.object(shared.PreparedSource, "export_source", side_effect=AssertionError("no export")), \
                patch.object(dag, "value_at", side_effect=AssertionError("no decode")), \
                patch.object(core, "_compact_pair", side_effect=AssertionError("no outputs")), \
                patch.object(codec, "_runs", side_effect=AssertionError("no pair atom runs")):
            proof = bounds.prepare_transfer_bounds(group)
            info = bounds.proof_info(proof)
        self.assertEqual(info["entry_count"], group.preflight_plan.entry_count)
        self.assertEqual(info["pair_outputs_computed"], 0)
        self.assertTrue(info["descriptor_is_not_authority"])
        self.assertFalse(info["music_accuracy_or_selection_claimed"])
        self.assertGreater(info["inspected_source_rows"], 0)

    def test_genuine_blocks_and_every_transfer_fit_tighter_schema_bound(self):
        improvements = 0
        for name, (_, group) in self.groups.items():
            proof = self.proofs[name]
            info = bounds.proof_info(proof)
            for task in group.iter_blocks():
                with patch.object(core, "_compact_pair", side_effect=AssertionError("no output while bounding")), \
                        patch.object(codec, "_runs", side_effect=AssertionError("no pair atom runs")):
                    bound = bounds.task_stream_bound(proof, task)
                block = core.compare_block(group, task)
                self.assertEqual(bound["expected_pairs"], task.expected_pairs)
                self.assertLessEqual(len(raw(block)), bound["raw_block_byte_upper_bound"])
                self.assertLessEqual(bound["raw_block_byte_upper_bound"], bound["legacy_raw_block_byte_upper_bound"])
                improvements += bound["transfer_array_byte_savings_bound"] > 0
                owned = bounds._issued(proof)
                for pair in block["pairs"]:
                    self.assertLessEqual(len(raw(pair)), bound["maximum_pair_byte_upper_bound"])
                    left, right = pair["entry_indices"]
                    for transfer in pair["category_transfer_note_time"]:
                        self.assertIn(transfer["left"], owned.supports[left][0])
                        self.assertIn(transfer["right"], owned.supports[right][0])
                        value = Fraction(transfer["duration_quarters"]["numerator"],
                            transfer["duration_quarters"]["denominator"])
                        rational = info["rational_proof"]
                        self.assertEqual(rational["denominator_lcm"] % value.denominator, 0)
                        self.assertLessEqual(value.numerator, rational["total_span_numerator_bound"])
        self.assertGreater(improvements, 0)

    def test_proof_descriptor_forgery_and_other_group_task_are_rejected(self):
        proof = self.proofs["passing"]
        task = next(self.groups["passing"][1].iter_blocks())
        for fake in (bounds.proof_info(proof), object.__new__(bounds.TransferProof), None):
            with self.assertRaises(ValueError):
                bounds.task_stream_bound(fake, task)
        with self.assertRaises(ValueError):
            bounds.task_stream_bound(proof, next(self.groups["rational"][1].iter_blocks()))
        for changed in (replace(task, expected_pairs=True), replace(task, refinement_sha256="0" * 64),
                        replace(task, entry_inventory_sha256="0" * 64)):
            with self.assertRaises(ValueError):
                bounds.task_stream_bound(proof, changed)

    def test_three_pair_block_uses_sum_savings_and_safe_maximum_pair_bound(self):
        _, group = self.groups["three_entry_partition"]
        proof = self.proofs["three_entry_partition"]
        task = next(group.iter_blocks())
        old = stream.task_stream_bound(group, task)
        new = bounds.task_stream_bound(proof, task)
        self.assertEqual(task.expected_pairs, 3)
        self.assertEqual(new["legacy_raw_block_byte_upper_bound"], old["raw_block_byte_upper_bound"])
        self.assertEqual(new["raw_block_byte_upper_bound"], old["raw_block_byte_upper_bound"]
            - new["transfer_array_byte_savings_bound"])
        block = core.compare_block(group, task)
        self.assertEqual(block["computed_pairs"], 3)
        for pair in block["pairs"]:
            self.assertLessEqual(len(raw(pair)), new["maximum_pair_byte_upper_bound"])

    def test_preparation_limits_cannot_raise_defaults_or_authorize_json(self):
        _, group = self.groups["passing"]
        with self.assertRaises(ValueError):
            bounds.prepare_transfer_bounds(group, limits=replace(bounds.DEFAULT_LIMITS, max_work=1000000001))
        with self.assertRaises(ValueError):
            bounds.prepare_transfer_bounds(group.export_catalog())
        with self.assertRaisesRegex(bounds.TransferBoundHold, "retained"):
            bounds.prepare_transfer_bounds(group, limits=replace(bounds.DEFAULT_LIMITS, max_retained_proof_bytes=1))
        with self.assertRaises(bounds.TransferBoundHold):
            bounds.prepare_transfer_bounds(group, limits=replace(bounds.DEFAULT_LIMITS, max_work=1))

    def test_task_work_holds_are_unknown_with_no_pair_prefix(self):
        proof = self.proofs["passing"]
        task = next(self.groups["passing"][1].iter_blocks())
        for cap in (0, 1, 800):
            with patch.object(core, "_compact_pair", side_effect=AssertionError("no output")):
                held = bounds.task_stream_bound(proof, task, max_work=cap)
            self.assertEqual(held["status"], "whole_block_stream_bound_hold")
            self.assertIsNone(held["raw_block_byte_upper_bound"])
            self.assertIsNone(held["planning_work_upper_bound"])
            self.assertEqual(held["expected_pairs"], task.expected_pairs)
            self.assertEqual(held["pair_outputs_computed"], 0)

    def test_known_byte_hold_keeps_whole_task_and_exact_nonzero_bound(self):
        proof = self.proofs["passing"]
        task = next(self.groups["passing"][1].iter_blocks())
        held = bounds.task_stream_bound(proof, task, max_block_bytes=1)
        self.assertGreater(held["raw_block_byte_upper_bound"], 1)
        self.assertEqual(held["expected_pairs"], task.expected_pairs)
        self.assertEqual(held["reasons"], ["whole_block_schema_byte_bound_hold_no_prefix"])

    def test_tighter_term_can_clear_old_byte_hold_but_not_other_work_hold(self):
        proof = self.proofs["passing"]
        task = next(self.groups["passing"][1].iter_blocks())
        new = bounds.task_stream_bound(proof, task)
        old = stream.task_stream_bound(self.groups["passing"][1], task,
            max_block_bytes=new["raw_block_byte_upper_bound"])
        self.assertIn("whole_block_schema_byte_bound_hold_no_prefix", old["reasons"])
        ready = bounds.task_stream_bound(proof, task, max_block_bytes=new["raw_block_byte_upper_bound"])
        self.assertEqual(ready["reasons"], [])
        self.assertFalse(ready["historical_writer_or_coordinator_modified"])

    def test_proof_release_has_no_registry_cycle_with_gc_disabled(self):
        was = gc.isenabled()
        gc.disable()
        try:
            proof = bounds.prepare_transfer_bounds(self.groups["passing"][1])
            reference = weakref.ref(proof)
            count = len(bounds._PROOFS)
            proof = None
            self.assertIsNone(reference())
            self.assertEqual(len(bounds._PROOFS), count - 1)
        finally:
            if was:
                gc.enable()


if __name__ == "__main__":
    unittest.main()
