"""Small genuine XML/native fixtures; no actual corpus or production changes."""
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction
import unittest
from unittest.mock import patch

from musicanote_harness import cross_batch_progression_contrast as cross
from musicanote_harness import native_progression_contrast as legacy
from musicanote_harness import factor_interval_lattice as native
from musicanote_harness import factor_native_role_explanations as roles
from musicanote_harness import factor_expanded_hypotheses as kernels
from musicanote_harness.musical_pattern_observation import digest, f, q
import test_native_progression_contrast as fixture_module
from test_factor_musical_view import reseal
from test_factor_expanded_hypotheses import span


def request_ref(number=0):
    return kernels._ref(kernels._seal({"original_request_position": number}, "cbprequest_"))


class CrossBatchContrastTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture_module.SavedProgressionContrastTests.setUpClass()
        cls.addClassCleanup(fixture_module.SavedProgressionContrastTests.doClassCleanups)
        cls.fixture = fixture_module.SavedProgressionContrastTests()

    def inputs(self, name="passing", mode="candidate", control=False):
        return self.fixture.inputs(name, mode, control)

    def prepare(self, name="passing", mode="candidate", control=False, **options):
        scope, lattice, entries, bundles = self.inputs(name, mode, control)
        return cross.prepare_saved_group(scope, lattice, entries, bundles=bundles,
            completion_request_ref=request_ref(), **options)

    def assert_legacy(self, prepared):
        catalog = prepared.export_catalog()
        sounds = {s["sound_ref"]: s for s in catalog["source_sounds"]}
        count = 0
        for task in prepared.iter_blocks():
            block = cross.compare_block(prepared, task)
            self.assertEqual(block["computed_pairs"], task.expected_pairs)
            self.assertFalse(block["whole_group_complete"])
            self.assertTrue(all(v is False for v in block["flags"].values()))
            for compact in block["pairs"]:
                i, j = compact["entry_indices"]
                expected = legacy._pair(catalog["facets"][i], catalog["facets"][j], sounds)
                self.assertEqual(cross.materialize_pair(prepared, compact), expected)
                self.assertIsNone(compact["musical_outcome"])
                count += 1
        self.assertEqual(count, prepared.preflight_plan.planned_pairs)

    def test_candidate_exact_legacy_and_reversible_compact(self):
        prepared = self.prepare(selector_indices=[3, 18], block_size=1)
        self.assert_legacy(prepared)
        pair = cross.compare_block(prepared, next(prepared.iter_blocks()))["pairs"][0]
        self.assertEqual(pair["original_selector_indices"], [3, 18])
        self.assertEqual(sum(map(f, pair["note_time_delta_right_minus_left"].values()), Fraction()), 0)
        self.assertNotIn("changed_source_segments", pair)
        self.assertNotIn("aligned_bass_cells", pair)
        self.assertIsNotNone(pair["conditional_credit_delta_right_minus_left"])

    def test_fractional_partition_and_transition_exact_legacy(self):
        for name, mode in (("rational", "candidate"), ("passing", "partition"),
                ("ordinary_first_adverse", "transition")):
            with self.subTest(name=name, mode=mode):
                self.assert_legacy(self.prepare(name, mode, block_size=1))

    def test_global_third_cut_does_not_add_pair_cells(self):
        # All three are genuine registered selectors, not fabricated facets.
        source_fixture = self.fixture.fixture
        scope = source_fixture.case("three_slots")[0][1]
        lattice = source_fixture.record("three_slots")
        chord = fixture_module.fixture_module.members("C", "E", "G")
        selectors = [source_fixture.selector("three_slots"),
            source_fixture.selector("three_slots", partitions=[(span(0, 4), ("C", Fraction()), chord)], assumptions=[]),
            source_fixture.selector("three_slots", partitions=[(span(0, 1), ("C", Fraction()), chord),
                (span(1, 4), ("C", Fraction()), chord)], assumptions=[None])]
        session, comparison, bundle = source_fixture.comparison("three_slots", selectors=selectors)
        explained = roles.explain_prepared(roles.prepare_explanations(session, comparison), query_work_budget=100000000)
        entries = [{"native_path": p, "role_path": r, "comparison_ref": kernels._ref(comparison),
            "explanation_ref": kernels._ref(explained)} for p, r in zip(comparison["paths"], explained["paths"])]
        prepared = cross.prepare_saved_group(scope, lattice, entries, bundles={bundle["record_id"]: bundle},
            completion_request_ref=request_ref(), block_size=2)
        self.assert_legacy(prepared)
        self.assertEqual(prepared.preflight_plan.planned_pairs, 3)

    def test_source_note_multiplicity_not_clock_duration(self):
        prepared = self.prepare()
        compact = cross.compare_block(prepared, next(prepared.iter_blocks()))["pairs"][0]
        full = cross.materialize_pair(prepared, compact)
        raw = f(full["raw_total_note_time_quarters"])
        clock = sum((f(c["span"]["end"]) - f(c["span"]["start"]) for c in full["aligned_bass_cells"]), Fraction())
        self.assertEqual(clock, 4)
        self.assertGreater(raw, clock)
        self.assertEqual(sum((f(r["duration_quarters"]) for r in full["category_transfer_note_time"]), Fraction()), raw)

    def test_known_zero_empty_and_single_without_comparison(self):
        for size in (0, 1):
            scope, lattice, entries, bundles = self.inputs()
            prepared = cross.prepare_saved_group(scope, lattice, entries[:size], bundles=bundles,
                completion_request_ref=request_ref())
            self.assertEqual(prepared.preflight_plan.planned_pairs, 0)
            self.assertEqual(list(prepared.iter_blocks()), [])
            self.assertEqual(len(prepared.export_catalog()["facets"]), size)

    def test_original_completion_identity_even_same_bundle(self):
        scope, lattice, entries, bundles = self.inputs()
        a = cross.prepare_saved_group(scope, lattice, entries, bundles=bundles, completion_request_ref=request_ref(1))
        b = cross.prepare_saved_group(scope, lattice, entries, bundles=bundles, completion_request_ref=request_ref(2))
        self.assertNotEqual(a.group_ref, b.group_ref)
        pair = cross.compare_block(a, next(a.iter_blocks()))["pairs"][0]
        with self.assertRaisesRegex(ValueError, "foreign_saved_pair"):
            cross.materialize_pair(b, pair)
        with self.assertRaisesRegex(ValueError, "foreign_or_modified_block"):
            cross.compare_block(b, next(a.iter_blocks()))

    def test_genuine_origin_aliases_preserved_not_deduplicated(self):
        source_fixture = self.fixture.fixture
        scope = source_fixture.case("passing")[0][1]
        lattice = source_fixture.record("passing")
        by_signature = {}
        for catalog in lattice["catalog_inventory"]:
            if catalog["span"] == scope["analysis_span"]:
                for origin in catalog["origins"]:
                    by_signature.setdefault(digest(legacy._signature(origin)), []).append(origin)
        # The genuine unresolved supplier alternatives share a root/member
        # signature but retain their different provenance and logical tuples.
        aliases = next(rows[:2] for rows in by_signature.values() if len(rows) > 1)
        selectors = [source_fixture.selector("passing") for _ in aliases]
        for selector, origin in zip(selectors, aliases):
            selector["origin_ids"] = [origin["record_id"]]
        session, comparison, bundle = source_fixture.comparison("passing", selectors=selectors)
        explained = roles.explain_prepared(roles.prepare_explanations(session, comparison), query_work_budget=100000000)
        entries = [{"native_path": p, "role_path": r, "comparison_ref": kernels._ref(comparison),
            "explanation_ref": kernels._ref(explained)} for p, r in zip(comparison["paths"], explained["paths"])]
        prepared = cross.prepare_saved_group(scope, lattice, entries, bundles={bundle["record_id"]: bundle},
            completion_request_ref=request_ref())
        self.assert_legacy(prepared)
        pair = cross.compare_block(prepared, next(prepared.iter_blocks()))["pairs"][0]
        self.assertTrue(pair["alias_control"])
        self.assertTrue(all(f(v) == 0 for v in pair["note_time_delta_right_minus_left"].values()))
        self.assertEqual(len(prepared.export_catalog()["entries"]), 2)

    def test_tie_carry_and_reattack_closure_exact_legacy(self):
        for name in ("suspension_tie", "suspension_reattack"):
            with self.subTest(name=name):
                source_fixture = self.fixture.fixture
                scope = source_fixture.case(name)[0][1]
                lattice = source_fixture.record(name)
                primary = source_fixture.selector(name)
                variant = deepcopy(primary)
                target_id = primary["origin_ids"][-1]
                extent = source_fixture.case(name)[1][-1][0]
                alternative = next(o for catalog in lattice["catalog_inventory"] if catalog["span"] == extent
                    for o in catalog["origins"] if o["record_id"] != target_id and not o["blockers"]
                    and o["root"] is not None and o["members"] is not None)
                variant["origin_ids"][-1] = alternative["record_id"]
                session, comparison, bundle = source_fixture.comparison(name, selectors=[primary, variant])
                explained = roles.explain_prepared(roles.prepare_explanations(session, comparison), query_work_budget=100000000)
                entries = [{"native_path": p, "role_path": r, "comparison_ref": kernels._ref(comparison),
                    "explanation_ref": kernels._ref(explained)} for p, r in zip(comparison["paths"], explained["paths"])]
                prepared = cross.prepare_saved_group(scope, lattice, entries, bundles={bundle["record_id"]: bundle},
                    completion_request_ref=request_ref())
                self.assert_legacy(prepared)
                catalog = prepared.export_catalog()
                ties = [s for s in catalog["source_sounds"] if s["tie_chain_ref"] is not None]
                self.assertEqual(bool(ties), name == "suspension_tie")

    def test_unknown_credit_separate_from_six_rational_totals(self):
        source_fixture = self.fixture.fixture
        # A genuine sampled-lane grace point withholds the native bundle. Merely
        # setting a geometry budget to zero does NOT withhold a closed-form
        # complete-bipartite query, even when required links are nonempty.
        name = "grace"
        scope = source_fixture.case(name)[0][1]
        lattice = source_fixture.record(name)
        selectors = [source_fixture.selector(name)]
        selector = deepcopy(selectors[0])
        chosen = next(o for cat in lattice["catalog_inventory"] if cat["span"] == scope["analysis_span"]
            for o in cat["origins"] if o["record_id"] not in selector["origin_ids"])
        selector["origin_ids"] = [chosen["record_id"]]
        selectors.append(selector)
        session = source_fixture.session(name)
        bundle = native.compile_bundle_prepared(session, [])
        self.assertEqual(bundle["status"], "all_lane_witness_withheld")
        comparison = native.compare_prepared(session, selectors, bundle["record_id"])
        explained = roles.explain_prepared(roles.prepare_explanations(session, comparison), query_work_budget=100000000)
        entries = [{"native_path": p, "role_path": r, "comparison_ref": kernels._ref(comparison),
            "explanation_ref": kernels._ref(explained)} for p, r in zip(comparison["paths"], explained["paths"])]
        prepared = cross.prepare_saved_group(scope, lattice, entries, bundles={bundle["record_id"]: bundle},
            completion_request_ref=request_ref())
        compact = cross.compare_block(prepared, next(prepared.iter_blocks()))["pairs"][0]
        self.assertIsNone(compact["conditional_credit_delta_right_minus_left"])
        self.assertEqual(set(compact["note_time_delta_right_minus_left"]), set(cross.CATEGORIES))
        self.assertTrue(all(type(f(v)) is Fraction for v in compact["note_time_delta_right_minus_left"].values()))
        self.assert_legacy(prepared)
        known = self.prepare(control=True)
        known_pair = cross.compare_block(known, next(known.iter_blocks()))["pairs"][0]
        self.assertEqual(known_pair["conditional_credit_delta_right_minus_left"], q(0))

    def test_held_entry_rejected_not_deleted_to_known_empty(self):
        scope, lattice, entries, bundles = self.inputs()
        entries[0] = {**entries[0], "native_path": {"profiles": []}}
        with self.assertRaisesRegex(ValueError, "held_entry"):
            cross.prepare_saved_group(scope, lattice, entries, bundles=bundles, completion_request_ref=request_ref())

    def test_preflight_whole_hold_before_facet_or_body_validation(self):
        scope, lattice, entries, bundles = self.inputs()
        for limits in (replace(cross.Limits(), max_entries=1), replace(cross.Limits(), max_pairs=0),
                replace(cross.Limits(), max_work=0), replace(cross.Limits(), max_refinement_atoms=0),
                replace(cross.Limits(), max_vector_cells=0), replace(cross.Limits(), max_catalog_bytes=0),
                replace(cross.Limits(), max_block_pairs=0), replace(cross.Limits(), max_pair_record_bytes=0),
                replace(cross.Limits(), max_block_record_bytes=0)):
            with self.subTest(limits=limits):
                with patch.object(legacy, "_validate_entry", side_effect=AssertionError("no costly prefix")):
                    with self.assertRaises(cross.WholeGroupHold) as ctx:
                        cross.prepare_saved_group(scope, lattice, entries, bundles=bundles,
                            completion_request_ref=request_ref(), limits=limits)
                    self.assertEqual(ctx.exception.plan.planned_pairs, 1)
                    self.assertTrue(ctx.exception.plan.reasons)

    def test_count_hold_does_not_inspect_bad_large_bodies_or_materialize_tasks(self):
        scope, lattice, entries, bundles = self.inputs()
        with (patch.object(legacy, "_plan", side_effect=AssertionError("no body cost inspection")),
              patch.object(cross, "plan_blocks", side_effect=AssertionError("no quadratic task expansion"))):
            plan = cross.preflight_saved_group(scope, lattice, [{}] * 65, bundles=bundles,
                completion_request_ref=request_ref(), limits=replace(cross.Limits(), max_entries=64))
        self.assertEqual(plan.planned_pairs, 2080)
        self.assertEqual(plan.planned_blocks, 2)
        self.assertIsNone(plan.planned_work_upper_bound)
        self.assertEqual(plan.status, "whole_saved_group_hold")

    def test_exact_preflight_work_budget_boundary(self):
        scope, lattice, entries, bundles = self.inputs()
        plan = cross.preflight_saved_group(scope, lattice, entries, bundles=bundles, completion_request_ref=request_ref())
        exact = cross.prepare_saved_group(scope, lattice, entries, bundles=bundles,
            completion_request_ref=request_ref(), limits=replace(cross.Limits(), max_work=plan.planned_work_upper_bound))
        self.assert_legacy(exact)
        with self.assertRaises(cross.WholeGroupHold):
            cross.prepare_saved_group(scope, lattice, entries, bundles=bundles,
                completion_request_ref=request_ref(), limits=replace(cross.Limits(), max_work=plan.planned_work_upper_bound - 1))

    def test_pair_record_budget_holds_entire_block(self):
        # These positive caps admit the proven minimal record floor, but are
        # deliberately smaller than the real fixture's encoded pair/block.
        for limits in (replace(cross.Limits(), max_pair_record_bytes=512),
                replace(cross.Limits(), max_block_record_bytes=512)):
            prepared = self.prepare(limits=limits)
            block = cross.compare_block(prepared, next(prepared.iter_blocks()))
            self.assertEqual(block["status"], "whole_saved_block_hold")
            self.assertEqual(block["pairs"], [])
            self.assertEqual(block["computed_pairs"], 0)
            self.assertEqual(block["withheld_pairs"], 1)

    def test_no_native_or_role_producers_and_original_immutable(self):
        scope, lattice, entries, bundles = self.inputs()
        before = digest([scope, lattice, entries, bundles])
        with (patch.object(native, "prepare_lattice", side_effect=AssertionError("no native issuer")),
              patch.object(native, "compare_prepared", side_effect=AssertionError("no native replay")),
              patch.object(roles, "explain_prepared", side_effect=AssertionError("no role replay"))):
            prepared = cross.prepare_saved_group(scope, lattice, entries, bundles=bundles, completion_request_ref=request_ref())
            self.assert_legacy(prepared)
        self.assertEqual(before, digest([scope, lattice, entries, bundles]))
        exported = prepared.export_catalog()
        exported["facets"].clear()
        self.assertEqual(len(prepared.export_catalog()["facets"]), 2)
        with self.assertRaises(AttributeError):
            prepared._catalog = {}
        with self.assertRaises(TypeError):
            cross._issued(prepared).catalog["facets"][0]["selected"] = "winner"
        with self.assertRaisesRegex(ValueError, "factory"):
            cross.PreparedGroup(object(), {}, prepared.preflight_plan, cross.Limits())

    def test_forged_unregistered_handle_and_catalog_setattr_rejected(self):
        prepared = self.prepare()
        task = next(prepared.iter_blocks())
        fake = object.__new__(cross.PreparedGroup)
        for handle in (prepared, fake):
            with self.assertRaises(AttributeError):
                object.__setattr__(handle, "_catalog", {})
        with self.assertRaisesRegex(ValueError, "registered_validated"):
            cross.compare_block(fake, task)
        with self.assertRaisesRegex(ValueError, "registered_validated"):
            fake.export_catalog()
        with self.assertRaisesRegex(ValueError, "registered_validated"):
            cross.materialize_pair(fake, {})
        self.assertFalse(hasattr(cross, "_TOKEN"))
        original = cross._GROUPS[prepared]
        self.assertTrue(all(type(n) is int and type(d) is int
            for sound in original.sound_points for n, d in sound))
        self.assertTrue(all(type(n) is int and type(d) is int for n, d in original.bass_points))
        self.assertFalse(any(isinstance(value, Fraction)
            for sound in original.sound_points for point in sound for value in point))
        for field, value in (("sound_points", ()), ("bass_points", ()),
                ("catalog", cross._freeze(prepared.export_catalog())),
                ("plan", replace(original.plan, entry_count=0)),
                ("limits", replace(original.limits, max_work=0))):
            with self.subTest(field=field):
                cross._GROUPS[prepared] = replace(original, **{field: value})
                try:
                    with self.assertRaisesRegex(ValueError, "state_changed"):
                        cross.compare_block(prepared, task)
                finally:
                    cross._GROUPS[prepared] = original

    def test_block_admission_is_arithmetic_not_task_inventory_scan(self):
        prepared = self.prepare(block_size=1)
        task = next(prepared.iter_blocks())
        with patch.object(cross.PreparedGroup, "iter_blocks", side_effect=AssertionError("no all-task scan")):
            block = cross.compare_block(prepared, task)
        self.assertEqual(block["computed_pairs"], 1)

    def test_nested_dict_and_list_subclasses_rejected_before_owned_catalog(self):
        class MutableDict(dict):
            pass
        class MutableList(list):
            pass
        for kind in ("dict", "list"):
            scope, lattice, entries, bundles = self.inputs()
            if kind == "dict":
                entries[0]["native_path"]["profiles"][0]["rows"][0]["pitch"] = MutableDict(
                    entries[0]["native_path"]["profiles"][0]["rows"][0]["pitch"])
            else:
                entries[0]["native_path"]["profiles"][0]["rows"] = MutableList(
                    entries[0]["native_path"]["profiles"][0]["rows"])
            with self.subTest(kind=kind):
                with self.assertRaisesRegex(ValueError, "closed_plain_json"):
                    cross.prepare_saved_group(scope, lattice, entries, bundles=bundles, completion_request_ref=request_ref())

    def test_source_raw_profile_and_account_tamper_rejected(self):
        scope, lattice, entries, bundles = self.inputs()
        entries[0]["native_path"]["profiles"][0]["rows"][0]["state"] = "spelling_unresolved"
        with self.assertRaisesRegex(ValueError, "seal"):
            cross.prepare_saved_group(scope, lattice, entries, bundles=bundles, completion_request_ref=request_ref())
        scope, lattice, entries, bundles = self.inputs()
        entries[0]["role_path"]["account"]["raw_total_note_time_quarters"] = q(999)
        entries[0]["role_path"] = reseal(entries[0]["role_path"], "fmnrolepath_")
        with self.assertRaisesRegex(ValueError, "union_account"):
            cross.prepare_saved_group(scope, lattice, entries, bundles=bundles, completion_request_ref=request_ref())

    def test_resealed_pair_tamper_rejected(self):
        prepared = self.prepare()
        pair = cross.compare_block(prepared, next(prepared.iter_blocks()))["pairs"][0]
        pair["note_time_delta_right_minus_left"][cross.CATEGORIES[0]] = q(999)
        pair = reseal(pair, cross.PAIR_PREFIX)
        with self.assertRaisesRegex(ValueError, "disagrees"):
            cross.materialize_pair(prepared, pair)
        class AlwaysEqualDict(dict):
            def __ne__(self, other):
                return False
        with self.assertRaisesRegex(ValueError, "closed_plain_json"):
            cross.materialize_pair(prepared, AlwaysEqualDict(pair))

    def test_float_time_bad_indices_duplicate_and_cross_key_guards(self):
        scope, lattice, entries, bundles = self.inputs()
        entries[0]["native_path"]["partition"][0]["end"] = 4.0
        with self.assertRaisesRegex(ValueError, "float"):
            cross.prepare_saved_group(scope, lattice, entries, bundles=bundles, completion_request_ref=request_ref())
        for indices in ([1, 1], [2, 1], [True, 2], [1]):
            with self.subTest(indices=indices):
                with self.assertRaisesRegex(ValueError, "selector_indices"):
                    self.prepare(selector_indices=indices)
        scope, lattice, entries, bundles = self.inputs()
        with self.assertRaisesRegex(ValueError, "duplicate_saved"):
            cross.prepare_saved_group(scope, lattice, entries + [entries[0]], bundles=bundles, completion_request_ref=request_ref())
        with self.assertRaisesRegex(ValueError, "one_exact_key"):
            self.prepare(mode="key")
        scope, lattice, entries, bundles = self.inputs(mode="single")
        _, _, controls, other_bundles = self.inputs(mode="single", control=True)
        with self.assertRaisesRegex(ValueError, "one_exact_key_bundle_completion"):
            cross.prepare_saved_group(scope, lattice, entries + controls, bundles={**bundles, **other_bundles},
                completion_request_ref=request_ref())

    def test_foreign_or_modified_block_and_summary_stub_rejected(self):
        prepared = self.prepare()
        task = next(prepared.iter_blocks())
        with self.assertRaisesRegex(ValueError, "block_task"):
            cross.compare_block(prepared, replace(task, expected_pairs=9))
        for field, value in (("row_start", "0"), ("row_end", True), ("expected_pairs", 1.0)):
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, "block_task"):
                    cross.compare_block(prepared, replace(task, **{field: value}))
        with self.assertRaisesRegex(ValueError, "validated_saved_group"):
            cross.materialize_pair(prepared.export_catalog(), {})


class PureBlockAndRefinementControls(unittest.TestCase):
    def test_upper_triangle_0_1_64_65_and_tail_coverage(self):
        for n in (0, 1, 2, 63, 64, 65, 129, 342, 463):
            with self.subTest(n=n):
                tasks = list(cross.plan_blocks(n))
                pairs = [pair for task in tasks for pair in task.pair_indices()]
                self.assertEqual(len(pairs), n * (n - 1) // 2)
                self.assertEqual(len(pairs), len(set(pairs)))
                self.assertTrue(all(0 <= i < j < n for i, j in pairs))
                self.assertEqual(sum(t.expected_pairs for t in tasks), len(pairs))
                self.assertTrue(all(t.expected_pairs <= 4096 for t in tasks))
                if n == 463:
                    self.assertEqual(len(tasks), 36)
                if n == 342:
                    self.assertEqual(len(tasks), 21)

    def test_same_category_original_cut_not_coalesced(self):
        # Same category is deliberately irrelevant: distinct original row IDs
        # preserve pair-specific cuts while a THIRD entry's global cut vanishes.
        points = [q(0), q(1), q(2), q(3)]
        self.assertEqual(list(cross._runs(points, [0, 0, 1], [0, 0, 0])), [(0, 2, 0, 0), (2, 3, 1, 0)])

    def test_closed_boolean_and_invalid_budgets(self):
        with self.assertRaises(ValueError):
            cross.Limits(max_work=True)
        for count, size in ((True, 64), (1, 0), (-1, 64), (65, False), (65, 65)):
            with self.assertRaises(ValueError):
                list(cross.plan_blocks(count, size))


if __name__ == "__main__":
    unittest.main()
