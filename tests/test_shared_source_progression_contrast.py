"""New shared-source codec: small genuine XML fixtures, not full-corpus runs."""
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction
import unittest
from unittest.mock import patch

from musicanote_harness import shared_source_progression_contrast as shared
from musicanote_harness import cross_batch_progression_contrast as old
from musicanote_harness import native_progression_contrast as legacy
from musicanote_harness import factor_interval_lattice as native
from musicanote_harness import factor_native_role_explanations as roles
from musicanote_harness import factor_expanded_hypotheses as kernels
from musicanote_harness.musical_pattern_observation import digest, f, q
import test_native_progression_contrast as fixture_module
from test_cross_batch_progression_contrast import request_ref
from test_factor_musical_view import reseal
from test_factor_expanded_hypotheses import span


class SharedSourceContrastTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture_module.SavedProgressionContrastTests.setUpClass()
        cls.addClassCleanup(fixture_module.SavedProgressionContrastTests.doClassCleanups)
        cls.fixture = fixture_module.SavedProgressionContrastTests()

    def inputs(self, name="passing", mode="candidate", control=False):
        return self.fixture.inputs(name, mode, control)

    def prepare(self, name="passing", mode="candidate", control=False, **options):
        scope, lattice, entries, bundles = self.inputs(name, mode, control)
        source = shared.prepare_saved_source(scope, lattice, bundles=bundles)
        prepared = shared.prepare_saved_group(source, entries, completion_request_ref=request_ref(), **options)
        return source, prepared

    def assert_legacy(self, source, prepared):
        catalog = prepared.export_catalog()
        source_catalog = source.export_source()
        sounds = {s["sound_ref"]: s for s in source_catalog["source_scope"]["sound_facts"]}
        count = 0
        for task in prepared.iter_blocks():
            block = shared.compare_block(prepared, task)
            self.assertEqual(block["computed_pairs"], task.expected_pairs)
            self.assertFalse(block["whole_group_complete"])
            self.assertTrue(all(value is False for value in block["flags"].values()))
            for pair in block["pairs"]:
                i, j = pair["entry_indices"]
                self.assertEqual(shared.materialize_pair(prepared, pair),
                    legacy._pair(catalog["facets"][i], catalog["facets"][j], sounds))
                self.assertIsNone(pair["musical_outcome"])
                count += 1
        self.assertEqual(count, prepared.preflight_plan.planned_pairs)

    def test_candidate_exact_legacy_and_originalselectors(self):
        source, prepared = self.prepare(selector_indices=[3, 18], block_size=1)
        self.assert_legacy(source, prepared)
        pair = shared.compare_block(prepared, next(prepared.iter_blocks()))["pairs"][0]
        self.assertEqual(pair["original_selector_indices"], [3, 18])
        self.assertEqual(sum(map(f, pair["note_time_delta_right_minus_left"].values()), Fraction()), 0)

    def test_note_multiplicity_not_clockduration(self):
        source, group = self.prepare()
        compact = shared.compare_block(group, next(group.iter_blocks()))["pairs"][0]
        pair = shared.materialize_pair(group, compact)
        raw = f(pair["raw_total_note_time_quarters"])
        clock = sum((f(c["span"]["end"]) - f(c["span"]["start"]) for c in pair["aligned_bass_cells"]), Fraction())
        self.assertEqual(clock, 4)
        self.assertGreater(raw, clock)
        self.assertEqual(sum((f(c["duration_quarters"]) for c in pair["category_transfer_note_time"]), Fraction()), raw)

    def entries_from(self, fixture, name, selectors, *, withheld=False):
        if withheld:
            session = fixture.session(name)
            bundle = native.compile_bundle_prepared(session, [])
            comparison = native.compare_prepared(session, selectors, bundle["record_id"])
        else:
            session, comparison, bundle = fixture.comparison(name, selectors=selectors)
        explained = roles.explain_prepared(roles.prepare_explanations(session, comparison), query_work_budget=100000000)
        entries = [{"native_path": p, "role_path": r, "comparison_ref": kernels._ref(comparison),
            "explanation_ref": kernels._ref(explained)} for p, r in zip(comparison["paths"], explained["paths"])]
        source = shared.prepare_saved_source(fixture.case(name)[0][1], fixture.record(name),
            bundles={bundle["record_id"]: bundle})
        group = shared.prepare_saved_group(source, entries, completion_request_ref=request_ref())
        return source, group

    def test_tiecarry_and_reattack_exactclosures(self):
        fixture = self.fixture.fixture
        for name in ("suspension_tie", "suspension_reattack"):
            with self.subTest(name=name):
                primary = fixture.selector(name)
                variant = deepcopy(primary)
                target = primary["origin_ids"][-1]
                extent = fixture.case(name)[1][-1][0]
                alternative = next(o for c in fixture.record(name)["catalog_inventory"] if c["span"] == extent
                    for o in c["origins"] if o["record_id"] != target and not o["blockers"]
                    and o["root"] is not None and o["members"] is not None)
                variant["origin_ids"][-1] = alternative["record_id"]
                source, group = self.entries_from(fixture, name, [primary, variant])
                self.assert_legacy(source, group)
                ties = [s for s in source.export_source()["source_scope"]["sound_facts"] if s["tie_chain_ref"] is not None]
                self.assertEqual(bool(ties), name == "suspension_tie")

    def test_genuine_alias_provenance_not_deduplicated(self):
        fixture = self.fixture.fixture
        scope = fixture.case("passing")[0][1]
        signatures = {}
        for containing in fixture.record("passing")["catalog_inventory"]:
            if containing["span"] == scope["analysis_span"]:
                for origin in containing["origins"]:
                    signatures.setdefault(digest(legacy._signature(origin)), []).append(origin)
        aliases = next(rows[:2] for rows in signatures.values() if len(rows) > 1)
        selectors = [fixture.selector("passing") for _ in aliases]
        for selector, origin in zip(selectors, aliases): selector["origin_ids"] = [origin["record_id"]]
        source, group = self.entries_from(fixture, "passing", selectors)
        self.assert_legacy(source, group)
        pair = shared.compare_block(group, next(group.iter_blocks()))["pairs"][0]
        self.assertTrue(pair["alias_control"])
        self.assertEqual(len(group.export_catalog()["entries"]), 2)
        self.assertTrue(all(f(value) == 0 for value in pair["note_time_delta_right_minus_left"].values()))

    def test_nullable_credit_not_knownzero(self):
        fixture = self.fixture.fixture
        primary = fixture.selector("grace")
        variant = deepcopy(primary)
        scope = fixture.case("grace")[0][1]
        alternative = next(o for c in fixture.record("grace")["catalog_inventory"] if c["span"] == scope["analysis_span"]
            for o in c["origins"] if o["record_id"] not in primary["origin_ids"])
        variant["origin_ids"] = [alternative["record_id"]]
        source, group = self.entries_from(fixture, "grace", [primary, variant], withheld=True)
        self.assert_legacy(source, group)
        pair = shared.compare_block(group, next(group.iter_blocks()))["pairs"][0]
        self.assertIsNone(pair["conditional_credit_delta_right_minus_left"])
        self.assertEqual(set(pair["note_time_delta_right_minus_left"]), set(shared.CATEGORIES))
        self.assertTrue(all(type(f(value)) is Fraction for value in pair["note_time_delta_right_minus_left"].values()))
        _, known = self.prepare(control=True)
        pair = shared.compare_block(known, next(known.iter_blocks()))["pairs"][0]
        self.assertEqual(pair["conditional_credit_delta_right_minus_left"], q(0))

    def test_rational_partition_and_transition_exact_legacy(self):
        for name, mode in (("rational", "candidate"), ("passing", "partition"),
                ("ordinary_first_adverse", "transition")):
            with self.subTest(name=name, mode=mode):
                source, group = self.prepare(name, mode, block_size=1)
                self.assert_legacy(source, group)

    def test_source_once_local_catalog_does_not_contain_lattice(self):
        scope, lattice, entries, bundles = self.inputs()
        source = shared.prepare_saved_source(scope, lattice, bundles=bundles)
        groups = [shared.prepare_saved_group(source, entries, completion_request_ref=request_ref(i)) for i in (1, 2)]
        state = shared._source_issued(source)
        for group in groups:
            self.assertIs(shared._issued(group).source, source)
            catalog = group.export_catalog()
            self.assertEqual(catalog["source_catalog_ref"], source.source_ref)
            for name in ("source_scope", "lattice", "bundles", "source_sounds"):
                self.assertNotIn(name, catalog)
        for containing in state.catalog["lattice"]["catalog_inventory"]:
            for origin in containing["origins"]:
                self.assertIs(state.origins[origin["record_id"]], origin)
        self.assertNotEqual(groups[0].group_ref, groups[1].group_ref)
        pair = shared.compare_block(groups[0], next(groups[0].iter_blocks()))["pairs"][0]
        with self.assertRaisesRegex(ValueError, "foreign_saved_pair"):
            shared.materialize_pair(groups[1], pair)
        with self.assertRaisesRegex(ValueError, "foreign_or_modified"):
            shared.compare_block(groups[1], next(groups[0].iter_blocks()))

    def test_local_preflight_does_not_serialize_or_copy_whole_source(self):
        source, group = self.prepare()
        scope, _, entries, _ = self.inputs()
        original = old._copy
        seen = []
        def bounded_copy(value):
            if value is shared._source_issued(source).catalog or value is shared._source_issued(source).catalog["lattice"]:
                raise AssertionError("whole source copied per group")
            seen.append(value)
            return original(value)
        with (patch.object(old, "_copy", side_effect=bounded_copy),
                patch.object(shared.PreparedSource, "export_source", side_effect=AssertionError("no source export")),
                patch.object(old, "prepare_saved_group", side_effect=AssertionError("no old handle factory"))):
            fresh = shared.prepare_saved_group(source, entries, completion_request_ref=request_ref(7))
            shared.compare_block(fresh, next(fresh.iter_blocks()))
        self.assertGreater(len(seen), 0)
        self.assertEqual(group.preflight_plan.local_input_json_bytes, fresh.preflight_plan.local_input_json_bytes)

    def test_empty_and_single_preserve_originalpremises(self):
        scope, lattice, entries, bundles = self.inputs()
        source = shared.prepare_saved_source(scope, lattice, bundles=bundles)
        for n in (0, 1):
            group = shared.prepare_saved_group(source, entries[:n], completion_request_ref=request_ref(n),
                key_ref=entries[0]["native_path"]["key_ref"], bundle_ref=entries[0]["native_path"]["bundle_ref"])
            self.assertEqual(group.preflight_plan.planned_pairs, 0)
            self.assertEqual(list(group.iter_blocks()), [])
            self.assertEqual(group.export_catalog()["group"]["key_ref"], entries[0]["native_path"]["key_ref"])
        with self.assertRaisesRegex(ValueError, "empty_group_requires"):
            shared.prepare_saved_group(source, [], completion_request_ref=request_ref())

    def test_count_gate_before_badbody_or_taskallocation(self):
        source, _ = self.prepare()
        with (patch.object(legacy, "_plan", side_effect=AssertionError("no body work")),
                patch.object(shared, "plan_blocks", side_effect=AssertionError("no task list")),
                patch.object(legacy, "_validate_entry", side_effect=AssertionError("no validation"))):
            plan = shared.preflight_saved_group(source, [{}] * 65, completion_request_ref=request_ref(),
                limits=replace(shared.GroupLimits(), max_entries=64))
        self.assertEqual((plan.entry_count, plan.planned_pairs, plan.planned_blocks), (65, 2080, 2))
        self.assertIsNone(plan.planned_work_upper_bound)
        self.assertIsNone(plan.local_input_json_bytes)

    def test_source_count_hold_before_seals_and_bytes(self):
        scope, lattice, _, bundles = self.inputs()
        with (patch.object(kernels, "_check", side_effect=AssertionError("no seal")),
                patch.object(old, "_bytes", side_effect=AssertionError("no encoding"))):
            with self.assertRaises(shared.WholeSourceHold) as result:
                shared.prepare_saved_source(scope, lattice, bundles=bundles,
                    limits=replace(shared.SourceLimits(), max_origins=0))
        self.assertGreater(result.exception.plan.origin_count, 0)
        self.assertIsNone(result.exception.plan.input_json_bytes)

    def test_source_and_group_exactbudget_boundaries(self):
        scope, lattice, entries, bundles = self.inputs()
        plan = shared.preflight_saved_source(scope, lattice, bundles=bundles)
        for field, cost in (("max_source_record_bytes", plan.source_record_byte_upper_bound),
                ("max_source_work", plan.planned_work_upper_bound)):
            with self.subTest(field=field):
                source = shared.prepare_saved_source(scope, lattice, bundles=bundles,
                    limits=replace(shared.SourceLimits(), **{field: cost}))
                with self.assertRaises(shared.WholeSourceHold):
                    shared.prepare_saved_source(scope, lattice, bundles=bundles,
                        limits=replace(shared.SourceLimits(), **{field: cost - 1}))
        plan = shared.preflight_saved_group(source, entries, completion_request_ref=request_ref())
        for field, cost in (("max_work", plan.planned_work_upper_bound),
                ("max_catalog_bytes", plan.catalog_byte_upper_bound)):
            with self.subTest(field=field):
                group = shared.prepare_saved_group(source, entries, completion_request_ref=request_ref(),
                    limits=replace(shared.GroupLimits(), **{field: cost}))
                self.assert_legacy(source, group)
                with patch.object(legacy, "_validate_entry", side_effect=AssertionError("no prefix")):
                    with self.assertRaises(shared.WholeGroupHold):
                        shared.prepare_saved_group(source, entries, completion_request_ref=request_ref(),
                            limits=replace(shared.GroupLimits(), **{field: cost - 1}))

    def test_all_group_limits_whole_hold_no_validation(self):
        source, _ = self.prepare()
        _, _, entries, _ = self.inputs()
        for field in ("max_entries", "max_pairs", "max_work", "max_refinement_atoms", "max_vector_cells",
                "max_catalog_bytes", "max_block_pairs", "max_pair_record_bytes", "max_block_record_bytes"):
            with self.subTest(field=field), patch.object(legacy, "_validate_entry", side_effect=AssertionError("no prefix")):
                with self.assertRaises(shared.WholeGroupHold) as result:
                    shared.prepare_saved_group(source, entries, completion_request_ref=request_ref(),
                        limits=replace(shared.GroupLimits(), **{field: 0}))
                self.assertEqual(result.exception.plan.planned_pairs, 1)

    def test_actual_pair_or_block_overflow_discards_wholeblock(self):
        for limits in (replace(shared.GroupLimits(), max_pair_record_bytes=512),
                replace(shared.GroupLimits(), max_block_record_bytes=512)):
            source, group = self.prepare(limits=limits)
            block = shared.compare_block(group, next(group.iter_blocks()))
            self.assertEqual(block["status"], "whole_saved_block_hold")
            self.assertEqual(block["pairs"], [])
            self.assertEqual((block["computed_pairs"], block["withheld_pairs"]), (0, 1))

    def test_foreign_source_key_bundle_origin_and_seals(self):
        for target in ("lattice", "lattice_span", "bundle_lattice", "key", "key_segment", "origin_scope", "origin_catalog"):
            scope, lattice, _, bundles = self.inputs()
            with self.subTest(target=target):
                if target == "lattice":
                    lattice["binding"]["score_id"] = "foreign"
                    lattice = reseal(lattice, native.PREFIX)
                elif target == "lattice_span":
                    lattice["analysis_span"] = span(0, 1)
                    lattice = reseal(lattice, native.PREFIX)
                elif target == "bundle_lattice":
                    bundle = next(iter(bundles.values()))
                    bundle["lattice_ref"] = request_ref(100)
                    bundle = reseal(bundle, native.BUNDLE_PREFIX)
                    bundles = {bundle["record_id"]: bundle}
                elif target == "key":
                    lattice["keys"][0]["scope_ref"] = request_ref(100)
                    lattice["keys"][0] = reseal(lattice["keys"][0], kernels.KEY_PREFIX)
                    lattice = reseal(lattice, native.PREFIX)
                elif target == "key_segment":
                    lattice["keys"][0]["segments"][0]["span"] = span(0, 1)
                    lattice["keys"][0] = reseal(lattice["keys"][0], kernels.KEY_PREFIX)
                    lattice = reseal(lattice, native.PREFIX)
                else:
                    containing = lattice["catalog_inventory"][0]
                    origin = containing["origins"][0]
                    origin["scope_ref" if target == "origin_scope" else "catalog_id"] = request_ref(100) if target == "origin_scope" else "foreign"
                    containing["origins"][0] = reseal(origin, native.ORIGIN_PREFIX)
                    lattice = reseal(lattice, native.PREFIX)
                with self.assertRaises(ValueError):
                    shared.prepare_saved_source(scope, lattice, bundles=bundles)

    def test_input_and_export_mutations_do_not_change_ownedsource_or_groups(self):
        scope, lattice, entries, bundles = self.inputs()
        before = digest([scope, lattice, entries, bundles])
        source = shared.prepare_saved_source(scope, lattice, bundles=bundles)
        group = shared.prepare_saved_group(source, entries, completion_request_ref=request_ref())
        self.assertEqual(before, digest([scope, lattice, entries, bundles]))
        export = source.export_source()
        export["lattice"]["catalog_inventory"].clear()
        local = group.export_catalog()
        local["facets"].clear()
        scope.clear(); lattice.clear(); entries.clear(); bundles.clear()
        self.assertGreater(len(source.export_source()["lattice"]["catalog_inventory"]), 0)
        self.assertEqual(len(group.export_catalog()["facets"]), 2)
        self.assert_legacy(source, group)

    def test_input_mutation_during_validation_is_rejected(self):
        scope, lattice, entries, bundles = self.inputs()
        source = shared.prepare_saved_source(scope, lattice, bundles=bundles)
        real_facet = legacy._facet
        def mutating(*args):
            result = real_facet(*args)
            entries[0]["comparison_ref"]["record_id"] = "modified_after_validation"
            return result
        with patch.object(legacy, "_facet", side_effect=mutating):
            with self.assertRaisesRegex(ValueError, "inputs_modified"):
                shared.prepare_saved_group(source, entries, completion_request_ref=request_ref())

    def test_source_and_group_freeze_mutationwindows_rejected(self):
        original = old._freeze
        scope, lattice, entries, bundles = self.inputs()
        def mutate_source(value):
            result = original(value)
            scope["binding"]["score_id"] = "modified_during_freeze"
            return result
        with patch.object(old, "_freeze", side_effect=mutate_source):
            with self.assertRaisesRegex(ValueError, "inputs_modified"):
                shared.prepare_saved_source(scope, lattice, bundles=bundles)
        scope, lattice, entries, bundles = self.inputs()
        source = shared.prepare_saved_source(scope, lattice, bundles=bundles)
        def mutate_group(value):
            result = original(value)
            entries[0]["comparison_ref"]["record_id"] = "modified_during_freeze"
            return result
        with patch.object(old, "_freeze", side_effect=mutate_group):
            with self.assertRaisesRegex(ValueError, "inputs_modified"):
                shared.prepare_saved_group(source, entries, completion_request_ref=request_ref())

    def test_forged_handles_and_privateauth_tamper_rejected(self):
        source, group = self.prepare()
        with self.assertRaises(ValueError): shared.PreparedSource()
        with self.assertRaises(ValueError): shared.SharedPreparedGroup()
        with self.assertRaises(AttributeError): object.__setattr__(source, "_catalog", {})
        with self.assertRaises(AttributeError): object.__setattr__(group, "_catalog", {})
        with self.assertRaisesRegex(ValueError, "registered_validated"):
            shared.prepare_saved_group(source.export_source(), [], completion_request_ref=request_ref())
        fake_source = object.__new__(shared.PreparedSource)
        with self.assertRaisesRegex(ValueError, "registered_validated"):
            fake_source.export_source()
        fake_group = object.__new__(shared.SharedPreparedGroup)
        with self.assertRaisesRegex(ValueError, "registered_validated"):
            shared.compare_block(fake_group, next(group.iter_blocks()))
        source_state, group_state = shared._SOURCES[source], shared._GROUPS[group]
        for field, value in (("plan", replace(source_state.plan, origin_count=0)),
                ("scope_bytes", 0), ("catalog", old._freeze(source.export_source()))):
            with self.subTest(field=field):
                shared._SOURCES[source] = replace(source_state, **{field: value})
                try:
                    with self.assertRaisesRegex(ValueError, "state_changed"):
                        shared.compare_block(group, next(group.iter_blocks()))
                finally: shared._SOURCES[source] = source_state
        for field, value in (("sound_points", ()), ("plan", replace(group_state.plan, entry_count=0)),
                ("catalog", old._freeze(group.export_catalog()))):
            shared._GROUPS[group] = replace(group_state, **{field: value})
            try:
                with self.assertRaisesRegex(ValueError, "state_changed"):
                    group.export_catalog()
            finally: shared._GROUPS[group] = group_state
        self.assertTrue(all(type(n) is int and type(d) is int for sound in group_state.sound_points for n, d in sound))
        with self.assertRaises(TypeError): source_state.catalog["lattice"]["keys"][0]["selected"] = True

    def test_source_and_group_plainjson_and_float_contract(self):
        class BadDict(dict): pass
        class BadList(list): pass
        for kind in ("source_dict", "source_list", "group_dict", "group_float"):
            scope, lattice, entries, bundles = self.inputs()
            with self.subTest(kind=kind):
                if kind == "source_dict": scope["binding"] = BadDict(scope["binding"])
                elif kind == "source_list": lattice["keys"] = BadList(lattice["keys"])
                if kind.startswith("source"):
                    with self.assertRaises(ValueError): shared.prepare_saved_source(scope, lattice, bundles=bundles)
                else:
                    source = shared.prepare_saved_source(scope, lattice, bundles=bundles)
                    if kind == "group_dict": entries[0]["comparison_ref"] = BadDict(entries[0]["comparison_ref"])
                    else: entries[0]["native_path"]["partition"][0]["end"] = 4.0
                    with self.assertRaises(ValueError): shared.prepare_saved_group(source, entries, completion_request_ref=request_ref())

    def test_duplicate_crosskey_crossbundle_and_selector_order_rejected(self):
        source, _ = self.prepare()
        _, _, entries, _ = self.inputs()
        with self.assertRaisesRegex(ValueError, "duplicate_saved"):
            shared.prepare_saved_group(source, entries + [entries[0]], completion_request_ref=request_ref())
        for indices in ([1, 1], [2, 1], [True, 2], [1]):
            with self.assertRaisesRegex(ValueError, "selector_indices"):
                shared.prepare_saved_group(source, entries, completion_request_ref=request_ref(), selector_indices=indices)
        with self.assertRaisesRegex(ValueError, "one_exact_key"):
            self.prepare(mode="key")
        scope, lattice, entries, bundles = self.inputs(mode="single")
        _, _, control, other = self.inputs(mode="single", control=True)
        source = shared.prepare_saved_source(scope, lattice, bundles={**bundles, **other})
        with self.assertRaisesRegex(ValueError, "one_exact_key"):
            shared.prepare_saved_group(source, entries + control, completion_request_ref=request_ref())

    def test_resealed_account_and_profile_corruption_rejected(self):
        scope, lattice, entries, bundles = self.inputs()
        source = shared.prepare_saved_source(scope, lattice, bundles=bundles)
        entries[0]["role_path"]["account"]["raw_total_note_time_quarters"] = q(999)
        entries[0]["role_path"] = reseal(entries[0]["role_path"], "fmnrolepath_")
        with self.assertRaisesRegex(ValueError, "union_account"):
            shared.prepare_saved_group(source, entries, completion_request_ref=request_ref())
        _, _, entries, _ = self.inputs()
        entries[0]["native_path"]["profiles"][0]["rows"][0]["state"] = "spelling_unresolved"
        with self.assertRaisesRegex(ValueError, "seal"):
            shared.prepare_saved_group(source, entries, completion_request_ref=request_ref())

    def test_pairtamper_and_foreignblock_and_oldtypes_rejected(self):
        source, group = self.prepare()
        task = next(group.iter_blocks())
        pair = shared.compare_block(group, task)["pairs"][0]
        pair["note_time_delta_right_minus_left"][shared.CATEGORIES[0]] = q(999)
        with self.assertRaisesRegex(ValueError, "disagrees"):
            shared.materialize_pair(group, reseal(pair, shared.PAIR_PREFIX))
        for field, value in (("expected_pairs", 9), ("row_start", "0"), ("row_end", True),
                ("source_sha256", "0" * 64)):
            with self.assertRaises(ValueError): shared.compare_block(group, replace(task, **{field: value}))
        class AlwaysEqual(str):
            def __ne__(self, other): return False
        for field in ("source_sha256", "group_sha256", "refinement_sha256", "entry_inventory_sha256"):
            with self.assertRaises(ValueError): shared.compare_block(group, replace(task, **{field: AlwaysEqual("foreign")}))
        with self.assertRaises(ValueError): shared.materialize_pair(group.export_catalog(), {})
        with self.assertRaises(ValueError): shared.materialize_pair(group, [])
        with self.assertRaises(ValueError): shared.compare_block(group, next(old.plan_blocks(2)))

    def test_no_producers_no_oldhandle_registration(self):
        scope, lattice, entries, bundles = self.inputs()
        old_handles = len(old._GROUPS)
        with (patch.object(native, "prepare_lattice", side_effect=AssertionError("no issuer")),
                patch.object(native, "compare_prepared", side_effect=AssertionError("no replay")),
                patch.object(roles, "explain_prepared", side_effect=AssertionError("no roles")),
                patch.object(old, "prepare_saved_group", side_effect=AssertionError("no old factory"))):
            source = shared.prepare_saved_source(scope, lattice, bundles=bundles)
            group = shared.prepare_saved_group(source, entries, completion_request_ref=request_ref())
            self.assert_legacy(source, group)
        self.assertEqual(len(old._GROUPS), old_handles)

    def test_global_third_cut_exactlegacy(self):
        fixture = self.fixture.fixture
        scope = fixture.case("three_slots")[0][1]
        lattice = fixture.record("three_slots")
        members = fixture_module.fixture_module.members("C", "E", "G")
        selectors = [fixture.selector("three_slots"),
            fixture.selector("three_slots", partitions=[(span(0, 4), ("C", Fraction()), members)], assumptions=[]),
            fixture.selector("three_slots", partitions=[(span(0, 1), ("C", Fraction()), members),
                (span(1, 4), ("C", Fraction()), members)], assumptions=[None])]
        session, comparison, bundle = fixture.comparison("three_slots", selectors=selectors)
        explained = roles.explain_prepared(roles.prepare_explanations(session, comparison), query_work_budget=100000000)
        entries = [{"native_path": p, "role_path": r, "comparison_ref": kernels._ref(comparison),
            "explanation_ref": kernels._ref(explained)} for p, r in zip(comparison["paths"], explained["paths"])]
        source = shared.prepare_saved_source(scope, lattice, bundles={bundle["record_id"]: bundle})
        group = shared.prepare_saved_group(source, entries, completion_request_ref=request_ref(), block_size=2)
        self.assert_legacy(source, group)
        self.assertEqual(group.preflight_plan.planned_pairs, 3)


class SharedGeometryControls(unittest.TestCase):
    def test_exact_nonempty_task_geometry(self):
        for count in (0, 1, 2, 64, 65, 129, 342, 463):
            tasks = list(shared.plan_blocks(count))
            pairs = [pair for task in tasks for pair in task.pair_indices()]
            self.assertEqual(len(pairs), count * (count - 1) // 2)
            self.assertEqual(len(pairs), len(set(pairs)))
            self.assertTrue(all(t.expected_pairs > 0 for t in tasks))

    def test_integer_limits_closed(self):
        for cls in (shared.SourceLimits, shared.GroupLimits):
            name = next(iter(cls.__dataclass_fields__))
            with self.assertRaises(ValueError): cls(**{name: True})
        for count, size in ((True, 64), (1, 0), (-1, 64), (1, False), (65, 65)):
            with self.assertRaises(ValueError): list(shared.plan_blocks(count, size))


if __name__ == "__main__":
    unittest.main()
