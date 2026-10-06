"""Small genuine saved XML controls; no actual historical archive execution."""
from copy import deepcopy
from contextlib import nullcontext
from dataclasses import asdict, replace
from fractions import Fraction
import gc
import weakref
import sys
import unittest
from unittest.mock import patch

from musicanote_harness import proof_shared_source_progression_contrast as compact
from musicanote_harness import compact_source_progression_contrast as frozen_compact
from musicanote_harness import cross_batch_progression_contrast as codec
from musicanote_harness import shared_source_progression_contrast as shared
from musicanote_harness import native_progression_contrast as legacy
from musicanote_harness import factor_expanded_hypotheses as kernels
from musicanote_harness import factor_interval_lattice as native
from musicanote_harness import factor_native_role_explanations as roles
from musicanote_harness.musical_pattern_observation import digest, f, q
import test_shared_source_progression_contrast as shared_fixture
from test_cross_batch_progression_contrast import request_ref
from test_factor_musical_view import reseal
from test_factor_expanded_hypotheses import span


class ProofSharedSourceContrastTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        shared_fixture.SharedSourceContrastTests.setUpClass()
        cls.addClassCleanup(shared_fixture.SharedSourceContrastTests.doClassCleanups)
        cls.fixture = shared_fixture.SharedSourceContrastTests()

    def inputs(self, name="passing", mode="candidate", control=False):
        scope, lattice, entries, bundles = self.fixture.inputs(name, mode, control)
        return shared.prepare_saved_source(scope, lattice, bundles=bundles), entries

    def prepare(self, name="passing", mode="candidate", control=False, **options):
        source, entries = self.inputs(name, mode, control)
        group = compact.prepare_saved_group(source, entries, completion_request_ref=request_ref(), **options)
        return source, entries, group

    def assert_legacy(self, source, entries, group):
        catalog = group.export_catalog()
        sounds = {s["sound_ref"]: s for s in source.export_source()["source_scope"]["sound_facts"]}
        count = 0
        for i, entry in enumerate(entries):
            self.assertEqual(group.export_entry(i), entry)
            self.assertEqual(digest(group.export_entry(i)), digest(entry))
        for task in group.iter_blocks():
            block = compact.compare_block(group, task)
            self.assertEqual(block["computed_pairs"], task.expected_pairs)
            self.assertEqual(block["withheld_pairs"], 0)
            self.assertFalse(block["whole_group_complete"])
            self.assertTrue(all(v is False for v in block["flags"].values()))
            for pair in block["pairs"]:
                i, j = pair["entry_indices"]
                self.assertEqual(compact.materialize_pair(group, pair),
                    legacy._pair(group.export_facet(i), group.export_facet(j), sounds))
                count += 1
        self.assertEqual(count, group.preflight_plan.planned_pairs)
        for forbidden in ("entries", "facets", "source_scope", "lattice", "bundles", "source_sounds"):
            self.assertNotIn(forbidden, catalog)
        self.assertEqual(len(catalog["all_original_entry_roots"]), len(entries))
        self.assertEqual(len(catalog["all_original_facet_roots"]), len(entries))

    def test_candidate_exact_entry_and_legacy_pair_reconstruction(self):
        source, entries, group = self.prepare(selector_indices=[3, 18], block_size=1)
        self.assert_legacy(source, entries, group)
        pair = compact.compare_block(group, next(group.iter_blocks()))["pairs"][0]
        self.assertEqual(pair["original_selector_indices"], [3, 18])
        self.assertEqual(group.preflight_plan.actual_catalog_bytes, codec._bytes(group.export_catalog()))

    def test_partition_transition_rational_exact(self):
        for name, mode in (("passing", "partition"), ("ordinary_first_adverse", "transition"), ("rational", "candidate")):
            with self.subTest(name=name, mode=mode):
                self.assert_legacy(*self.prepare(name, mode))

    def test_raw_note_time_multiplicity_is_not_clock_time(self):
        source, entries, group = self.prepare()
        pair = compact.materialize_pair(group, compact.compare_block(group, next(group.iter_blocks()))["pairs"][0])
        raw = f(pair["raw_total_note_time_quarters"])
        clock = sum((f(c["span"]["end"]) - f(c["span"]["start"]) for c in pair["aligned_bass_cells"]), Fraction())
        self.assertEqual(clock, 4)
        self.assertGreater(raw, clock)
        self.assertEqual(sum((f(r["duration_quarters"]) for r in pair["category_transfer_note_time"]), Fraction()), raw)

    def from_selectors(self, name, selectors, withheld=False):
        fixture = self.fixture.fixture.fixture
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
        return source, entries, compact.prepare_saved_group(source, entries, completion_request_ref=request_ref())

    def test_tie_carry_vs_reattack_source_closure(self):
        fixture = self.fixture.fixture.fixture
        for name in ("suspension_tie", "suspension_reattack"):
            primary = fixture.selector(name)
            variant = deepcopy(primary)
            target = primary["origin_ids"][-1]
            extent = fixture.case(name)[1][-1][0]
            alternative = next(o for c in fixture.record(name)["catalog_inventory"] if c["span"] == extent
                for o in c["origins"] if o["record_id"] != target and not o["blockers"]
                and o["root"] is not None and o["members"] is not None)
            variant["origin_ids"][-1] = alternative["record_id"]
            source, entries, group = self.from_selectors(name, [primary, variant])
            self.assert_legacy(source, entries, group)
            self.assertEqual(any(s["tie_chain_ref"] is not None for s in source.export_source()["source_scope"]["sound_facts"]),
                name == "suspension_tie")

    def test_genuine_spelling_aliases_keep_distinct_original_entries(self):
        fixture = self.fixture.fixture.fixture
        scope = fixture.case("passing")[0][1]
        signatures = {}
        for catalog in fixture.record("passing")["catalog_inventory"]:
            if catalog["span"] == scope["analysis_span"]:
                for origin in catalog["origins"]:
                    signatures.setdefault(digest(legacy._signature(origin)), []).append(origin)
        aliases = next(rows[:2] for rows in signatures.values() if len(rows) > 1)
        selectors = [fixture.selector("passing") for _ in aliases]
        for selector, origin in zip(selectors, aliases):
            selector["origin_ids"] = [origin["record_id"]]
        source, entries, group = self.from_selectors("passing", selectors)
        self.assert_legacy(source, entries, group)
        pair = compact.compare_block(group, next(group.iter_blocks()))["pairs"][0]
        self.assertTrue(pair["alias_control"])
        self.assertNotEqual(group.export_entry(0), group.export_entry(1))
        self.assertNotEqual(group.export_catalog()["all_original_entry_roots"][0], group.export_catalog()["all_original_entry_roots"][1])

    def test_unknown_credit_is_not_zero(self):
        fixture = self.fixture.fixture.fixture
        primary = fixture.selector("grace")
        variant = deepcopy(primary)
        scope = fixture.case("grace")[0][1]
        alternative = next(o for c in fixture.record("grace")["catalog_inventory"] if c["span"] == scope["analysis_span"]
            for o in c["origins"] if o["record_id"] not in primary["origin_ids"])
        variant["origin_ids"] = [alternative["record_id"]]
        source, entries, group = self.from_selectors("grace", [primary, variant], withheld=True)
        self.assert_legacy(source, entries, group)
        pair = compact.compare_block(group, next(group.iter_blocks()))["pairs"][0]
        self.assertIsNone(pair["conditional_credit_delta_right_minus_left"])
        _, _, known = self.prepare(control=True)
        pair = compact.compare_block(known, next(known.iter_blocks()))["pairs"][0]
        self.assertEqual(pair["conditional_credit_delta_right_minus_left"], q(0))

    def test_exact_union_is_less_than_sum_and_vectors_use_true_union(self):
        source, entries, group = self.prepare("passing", "partition")
        facets = [group.export_facet(i) for i in range(len(entries))]
        coarse = sum(2 * (sum(len(rows) for rows in fa["source_segments"].values()) + len(fa["bass_cells"])) for fa in facets)
        self.assertLess(group.preflight_plan.refinement_atom_upper_bound, coarse)
        self.assertEqual(group.preflight_plan.vector_cell_upper_bound,
            len(entries) * group.preflight_plan.refinement_atom_upper_bound)
        self.assert_legacy(source, entries, group)

    def test_third_candidate_extra_point_preserves_original_pair_rows(self):
        fixture = self.fixture.fixture.fixture
        members = shared_fixture.fixture_module.fixture_module.members("C", "E", "G")
        selectors = [fixture.selector("three_slots"),
            fixture.selector("three_slots", partitions=[(span(0, 4), ("C", Fraction()), members)], assumptions=[]),
            fixture.selector("three_slots", partitions=[(span(0, 1), ("C", Fraction()), members),
                (span(1, 4), ("C", Fraction()), members)], assumptions=[None])]
        source, entries, group = self.from_selectors("three_slots", selectors)
        self.assert_legacy(source, entries, group)
        self.assertEqual(group.preflight_plan.planned_pairs, 3)
        # Same category does not merge two ORIGINAL rows; only a third entry's
        # otherwise unused global point disappears in a pair-specific run.
        self.assertEqual(list(codec._runs([q(0), q(1), q(2), q(3)], [0, 0, 1], [0, 0, 0])),
            [(0, 2, 0, 0), (2, 3, 1, 0)])

    def test_abandoned_preflight_draft_is_not_retained_by_weak_registry(self):
        source, entries = self.inputs()
        plan = compact.preflight_saved_group(source, entries, completion_request_ref=request_ref())
        self.assertFalse(plan.reasons)
        observed = weakref.ref(plan)
        del plan
        gc.collect()
        self.assertIsNone(observed())

    def test_known_empty_single_original_group_geometry(self):
        source, entries = self.inputs()
        for n in (0, 1):
            group = compact.prepare_saved_group(source, entries[:n], completion_request_ref=request_ref(),
                key_ref=entries[0]["native_path"]["key_ref"], bundle_ref=entries[0]["native_path"]["bundle_ref"])
            self.assertEqual(group.preflight_plan.entry_count, n)
            self.assertEqual(group.preflight_plan.planned_pairs, 0)
            self.assertEqual(list(group.iter_blocks()), [])
            self.assertEqual(len(group.export_catalog()["all_original_entry_roots"]), n)

    def test_materialization_reserves_source_closures_before_row_decode(self):
        source, entries, original = self.prepare()
        original_pair = compact.compare_block(original, next(original.iter_blocks()))["pairs"][0]
        group = compact.prepare_saved_group(source, entries, completion_request_ref=request_ref(),
            limits=replace(shared.GroupLimits(), max_pair_record_bytes=codec._bytes(original_pair)))
        pair = compact.compare_block(group, next(group.iter_blocks()))["pairs"][0]
        original_decode = compact.dag.value_at
        def no_rows(handle, path=()):
            if "source_segments" in path or "bass_cells" in path:
                raise AssertionError("row decoded before full expanded closure reservation")
            return original_decode(handle, path)
        with patch.object(compact.dag, "value_at", side_effect=no_rows):
            with self.assertRaisesRegex(ValueError, "whole_materialized_pair_expanded_bytes"):
                compact.materialize_pair(group, pair)

    def test_two_original_requests_share_one_owned_source(self):
        source, entries = self.inputs()
        groups = [compact.prepare_saved_group(source, entries, completion_request_ref=request_ref(i)) for i in (1, 2)]
        self.assertIs(compact._issued(groups[0]).source, compact._issued(groups[1]).source)
        self.assertNotEqual(groups[0].group_ref, groups[1].group_ref)
        pair = compact.compare_block(groups[0], next(groups[0].iter_blocks()))["pairs"][0]
        with self.assertRaisesRegex(ValueError, "foreign_compact_pair"):
            compact.materialize_pair(groups[1], pair)
        with self.assertRaisesRegex(ValueError, "foreign_or_modified"):
            compact.compare_block(groups[1], next(groups[0].iter_blocks()))

    def test_preflight_is_owned_no_revalidation_on_issue(self):
        source, entries = self.inputs()
        plan = compact.preflight_saved_group(source, entries, completion_request_ref=request_ref())
        self.assertFalse(plan.reasons)
        with patch.object(compact, "_validate_entry", side_effect=AssertionError("validation repeated")):
            group = compact.prepare_preflight(plan)
        self.assertEqual(group.export_entry(0), entries[0])
        with self.assertRaisesRegex(ValueError, "owned_compact"):
            compact.prepare_preflight(replace(plan))
        with self.assertRaisesRegex(ValueError, "owned_compact"):
            compact.prepare_preflight(plan.record())

    def test_count_gate_before_traversal_or_quadratic_allocations(self):
        source, entries = self.inputs()
        with (patch.object(compact, "_measure", side_effect=AssertionError("body measured")),
                patch.object(compact, "_facet", side_effect=AssertionError("facet issued"))):
            plan = compact.preflight_saved_group(source, entries, completion_request_ref=request_ref(),
                limits=replace(shared.GroupLimits(), max_entries=1))
        self.assertEqual((plan.entry_count, plan.planned_pairs, plan.stage), (2, 1, "counts"))
        self.assertTrue(plan.reasons)
        with self.assertRaises(compact.WholeGroupHold):
            compact.prepare_preflight(plan)

    def test_vector_gate_before_vector_allocation(self):
        source, entries = self.inputs()
        with patch.object(compact, "_refinement", side_effect=AssertionError("vectors allocated")):
            plan = compact.preflight_saved_group(source, entries, completion_request_ref=request_ref(),
                limits=replace(shared.GroupLimits(), max_vector_cells=1))
        self.assertEqual(plan.stage, "exact_refinement")
        self.assertIsNotNone(plan.refinement_atom_upper_bound)
        self.assertEqual(plan.planned_pairs, 1)

    def test_work_and_byte_holds_no_group_prefix(self):
        source, entries = self.inputs()
        for limits in (replace(shared.GroupLimits(), max_work=1), replace(shared.GroupLimits(), max_catalog_bytes=1)):
            plan = compact.preflight_saved_group(source, entries, completion_request_ref=request_ref(), limits=limits)
            self.assertTrue(plan.reasons)
            self.assertEqual(plan.entry_count, 2)
            self.assertEqual(plan.planned_pairs, 1)
            self.assertNotIn(plan, compact._PLANS)

    def test_small_block_hold_does_not_return_favourable_prefix(self):
        _, _, group = self.prepare(limits=replace(shared.GroupLimits(), max_pair_record_bytes=64))
        task = next(group.iter_blocks())
        block = compact.compare_block(group, task)
        self.assertEqual(block["pairs"], [])
        self.assertEqual(block["computed_pairs"], 0)
        self.assertEqual(block["withheld_pairs"], task.expected_pairs)

    def test_foreign_source_and_modified_intrinsic_body_rejected(self):
        source, entries = self.inputs()
        _, wrong = self.inputs("rational")
        with self.assertRaises(ValueError):
            compact.prepare_saved_group(source, wrong, completion_request_ref=request_ref())
        mutated = deepcopy(entries)
        mutated[0]["native_path"]["profiles"][0]["rows"][0]["duration_quarters"] = q(99)
        mutated[0]["native_path"] = reseal(mutated[0]["native_path"], "fmilpath_")
        with self.assertRaises(ValueError):
            compact.prepare_saved_group(source, mutated, completion_request_ref=request_ref())

    def test_factory_no_old_group_registration_or_whole_source_export(self):
        source, entries = self.inputs()
        with (patch.object(shared, "prepare_saved_group", side_effect=AssertionError("old group factory")),
                patch.object(codec, "prepare_saved_group", side_effect=AssertionError("old group factory")),
                patch.object(shared.PreparedSource, "export_source", side_effect=AssertionError("source exported"))):
            group = compact.prepare_saved_group(source, entries, completion_request_ref=request_ref())
            compact.compare_block(group, next(group.iter_blocks()))
        self.assertIs(type(group), compact.CompactPreparedGroup)

    def test_closed_types_selectors_and_pair_tamper(self):
        source, entries, group = self.prepare()
        for selectors in ([1, True], [3, 2], [1, 1], [1]):
            with self.assertRaises(ValueError):
                compact.prepare_saved_group(source, entries, completion_request_ref=request_ref(), selector_indices=selectors)
        pair = compact.compare_block(group, next(group.iter_blocks()))["pairs"][0]
        pair["alias_control"] = not pair["alias_control"]
        pair = reseal(pair, compact.PAIR_PREFIX)
        with self.assertRaisesRegex(ValueError, "disagrees"):
            compact.materialize_pair(group, pair)
        with self.assertRaises(ValueError):
            compact.CompactPreparedGroup()

    def test_caller_mutation_cannot_change_admitted_payload(self):
        source, entries, group = self.prepare()
        snapshot = group.export_entry(0)
        entries[0]["native_path"]["profiles"].clear()
        self.assertEqual(group.export_entry(0), snapshot)
        exported = group.export_catalog()
        exported["pair_index"].clear()
        self.assertTrue(group.export_catalog()["pair_index"])

    def test_caller_mutation_after_owned_snapshot_does_not_change_group(self):
        source, entries = self.inputs()
        original_freeze = codec._freeze
        def mutate(value):
            if type(value) is dict and value.get("version") == compact.VERSION and value.get("codec") == compact.ENCODING:
                entries[0]["comparison_ref"]["record_id"] += "mutated"
            return original_freeze(value)
        with patch.object(codec, "_freeze", side_effect=mutate):
            group = compact.prepare_saved_group(source, entries, completion_request_ref=request_ref())
        self.assertNotEqual(group.export_entry(0)["comparison_ref"], entries[0]["comparison_ref"])

    def test_budget_boundaries_use_original_work_and_exact_encoded_catalog(self):
        source, entries, group = self.prepare()
        observed = group.preflight_plan
        self.assertGreater(observed.planned_work_upper_bound, observed.dag_encoded_bytes)
        self.assertLess(observed.dag_encoded_bytes, observed.dag_expanded_bytes)
        self.assertGreaterEqual(observed.owned_input_snapshot_work, 2 * (observed.local_input_json_bytes + observed.input_visits))
        self.assertEqual(observed.input_guard_passes, 1)
        self.assertEqual(observed.snapshot_validation_passes, 1)
        self.assertGreater(observed.seal_validation_work, 0)
        for field, value in (("max_work", observed.planned_work_upper_bound - 1),
                ("max_refinement_atoms", observed.refinement_atom_upper_bound - 1)):
            plan = compact.preflight_saved_group(source, entries, completion_request_ref=request_ref(),
                limits=replace(shared.GroupLimits(), **{field: value}))
            self.assertTrue(plan.reasons)

    def test_exact_owned_count_must_match_early_count_gate(self):
        source, entries = self.inputs()
        original_freeze = compact.dag.freeze_json
        def changed_before_scan(value, **options):
            if type(value) is list and len(value) == 5 and value[0] is entries:
                entries.append(deepcopy(entries[0]))
            return original_freeze(value, **options)
        with patch.object(compact.dag, "freeze_json", side_effect=changed_before_scan):
            with self.assertRaisesRegex(ValueError, "entry_count_changed"):
                compact.preflight_saved_group(source, entries, completion_request_ref=request_ref())

    def test_raw_snapshot_pass_once_then_only_new_facets_are_frozen(self):
        source, entries = self.inputs()
        original_scan, original_freeze = compact.dag._preflight, compact.dag.freeze_json
        scans, freezes = [], []
        def scan(value, limits):
            if type(value) is list and len(value) == 5 and value[0] is entries:
                scans.append("raw")
            return original_scan(value, limits)
        def freeze(value, **options):
            freezes.append("raw" if type(value) is list and len(value) == 5 and value[0] is entries else "facets")
            return original_freeze(value, **options)
        with (patch.object(compact.dag, "_preflight", side_effect=scan),
                patch.object(compact.dag, "freeze_json", side_effect=freeze),
                patch.object(frozen_compact, "preflight_saved_group", side_effect=AssertionError("old factory"))):
            plan = compact.preflight_saved_group(source, entries, completion_request_ref=request_ref())
        self.assertFalse(plan.reasons)
        self.assertEqual(scans, ["raw"])
        self.assertEqual(freezes, ["raw", "facets"])
        with (patch.object(compact.dag, "freeze_json", side_effect=AssertionError("snapshot repeated")),
                patch.object(compact, "_validate_entry", side_effect=AssertionError("intrinsic repeated"))):
            compact.prepare_preflight(plan)

    def test_exact_node_seal_cache_never_uses_claimed_record_id(self):
        good = kernels._seal({"note_refs": ["n1", "n1"], "credit": None, "zero": q(0)}, "proof_")
        evil = deepcopy(good)
        evil["credit"] = q(0)
        snapshot = compact.dag.freeze_json([good, deepcopy(good), evil])
        proof = compact._SealProof(snapshot, 100000)
        try:
            proof.check(good, (0,), "proof_")
            passes = proof.passes
            proof.check(good, (1,), "proof_")
            self.assertEqual(proof.passes, passes)
            self.assertGreater(proof.hits, 0)
            with self.assertRaisesRegex(ValueError, "invalid_expanded_record_seal"):
                proof.check(evil, (2,), "proof_")
            self.assertGreater(proof.passes, passes)
        finally:
            proof.close()

    def test_forged_registry_entry_and_codec_reload_never_issue_domain_proof(self):
        source, entries = self.inputs()
        plan = compact.preflight_saved_group(source, entries, completion_request_ref=request_ref())
        copy = replace(plan)
        compact._PLANS[copy] = compact._PLANS[plan]
        try:
            with self.assertRaisesRegex(ValueError, "state_changed"):
                compact.prepare_preflight(copy)
        finally:
            del compact._PLANS[copy]
        group = compact.prepare_preflight(plan)
        reloaded = compact.dag.import_record(group.export_catalog()["payload"])
        with self.assertRaises(ValueError):
            compact.prepare_preflight(reloaded)
        with self.assertRaises(ValueError):
            compact.preflight_saved_group(source.export_source(), entries, completion_request_ref=request_ref())

    def test_snapshot_binds_optional_refs_and_selectors_before_later_caller_mutation(self):
        source, entries = self.inputs()
        completion, selectors = request_ref(17), [4, 9]
        key, bundle = deepcopy(entries[0]["native_path"]["key_ref"]), deepcopy(entries[0]["native_path"]["bundle_ref"])
        expected = deepcopy([completion, selectors, key, bundle])
        original_validate = compact._validate_entry
        changed = []
        def mutate(*args):
            if not changed:
                completion["record_id"] += "changed"
                selectors[:] = [7, 12]
                key["record_id"] += "changed"
                bundle["record_id"] += "changed"
                entries[0]["comparison_ref"]["record_id"] += "changed"
                changed.append(True)
            return original_validate(*args)
        with patch.object(compact, "_validate_entry", side_effect=mutate):
            group = compact.prepare_saved_group(source, entries, completion_request_ref=completion,
                selector_indices=selectors, key_ref=key, bundle_ref=bundle)
        binding = group.export_catalog()["group"]
        self.assertEqual([binding["completion_request_ref"], binding["original_selector_indices"],
            binding["key_ref"], binding["bundle_ref"]], expected)
        self.assertNotEqual(group.export_entry(0)["comparison_ref"], entries[0]["comparison_ref"])

    def test_canonical_catalog_stream_matches_full_exported_sha(self):
        _, _, group = self.prepare()
        catalog = group.export_catalog()
        self.assertEqual(digest({k: v for k, v in catalog.items() if k not in ("record_id", "record_sha256")}),
            catalog["record_sha256"])
        state = compact._issued(group)
        self.assertNotIn("payload", state.catalog)
        self.assertEqual(group.preflight_plan.actual_catalog_bytes, codec._bytes(catalog))
        self.assertEqual(group.preflight_plan.stage, "complete")
        self.assertTrue(catalog["preflight_plan"]["all_original_entries_retained"])

    def test_new_small_group_actual_work_below_frozen_work_without_dropping_costs(self):
        source, entries = self.inputs()
        old = frozen_compact.preflight_saved_group(source, entries, completion_request_ref=request_ref())
        new = compact.preflight_saved_group(source, entries, completion_request_ref=request_ref())
        self.assertFalse(old.reasons)
        self.assertFalse(new.reasons)
        self.assertLess(new.planned_work_upper_bound, old.planned_work_upper_bound)
        for field in ("owned_input_snapshot_work", "decoded_entry_work", "seal_validation_work",
                "canonicalization_work", "proof_composition_work", "catalog_finalization_work"):
            self.assertGreater(getattr(new, field), 0)
        self.assertEqual(new.entry_count, old.entry_count)
        self.assertEqual(new.planned_pairs, old.planned_pairs)
        self.assertEqual(asdict(compact.GroupLimits()), asdict(shared.GroupLimits()))

    def test_traceback_retention_does_not_keep_local_seal_caches_or_proofs(self):
        source, entries = self.inputs()
        original_entries = deepcopy(entries)
        snapshots, proof_refs = [], []
        original_freeze, original_seals = compact.dag.freeze_json, compact._SealProof
        def freeze(*args, **kwargs):
            value = original_freeze(*args, **kwargs)
            proof_refs.append(weakref.ref(value))
            return value
        def seals(*args, **kwargs):
            value = original_seals(*args, **kwargs)
            snapshots.append(value)
            return value
        def interrupted(*args, **kwargs):
            try:
                raise KeyboardInterrupt("retain traceback")
            finally:
                args = kwargs = None
        old_gc = gc.isenabled()
        gc.disable()
        try:
            for owner, name in ((compact, "_facet"), (compact.dag, "_hash_visit"),
                    (compact.dag, "_decode_visit"), (None, "malformed_header")):
                with self.subTest(interruption=name):
                    snapshots.clear(); proof_refs.clear()
                    captured = None
                    case_entries = entries
                    interruption = nullcontext()
                    if owner is None:
                        case_entries = deepcopy(entries)
                        del case_entries[0]["native_path"]["key_ref"]
                    else:
                        interruption = patch.object(owner, name, new=interrupted)
                    with (patch.object(compact.dag, "freeze_json", new=freeze),
                            patch.object(compact, "_SealProof", new=seals),
                            interruption):
                        try:
                            compact.preflight_saved_group(source, case_entries, completion_request_ref=request_ref())
                        except (KeyboardInterrupt, ValueError):
                            captured = sys.exc_info()[2]
                    self.assertIsNotNone(captured)
                    self.assertTrue(all(not p.hashes and not p.checks and p.snapshot is None for p in snapshots))
                    self.assertTrue(all(ref() is None for ref in proof_refs))
                    self.assertEqual(entries, original_entries)
        finally:
            captured = None
            if old_gc:
                gc.enable()

    def test_gc_disabled_success_and_hold_expire_temporary_json_proofs(self):
        source, entries = self.inputs()
        observed = []
        original_freeze, original_compose = compact.dag.freeze_json, compact.dag.compose_proofs
        def freeze(*args, **kwargs):
            value = original_freeze(*args, **kwargs)
            observed.append(weakref.ref(value))
            return value
        def compose(*args, **kwargs):
            value = original_compose(*args, **kwargs)
            observed.append(weakref.ref(value))
            return value
        old_gc = gc.isenabled()
        gc.disable()
        try:
            with (patch.object(compact.dag, "freeze_json", new=freeze),
                    patch.object(compact.dag, "compose_proofs", new=compose)):
                plan = compact.preflight_saved_group(source, entries, completion_request_ref=request_ref())
                held = compact.preflight_saved_group(source, entries, completion_request_ref=request_ref(),
                    limits=replace(shared.GroupLimits(), max_vector_cells=1))
            self.assertFalse(plan.reasons)
            self.assertTrue(held.reasons)
            self.assertTrue(all(ref() is None for ref in observed))
            group = compact.prepare_preflight(plan)
            self.assertEqual(group.export_entry(0), entries[0])
        finally:
            if old_gc:
                gc.enable()

    def test_replaced_source_or_payload_state_is_not_owned_group_authority(self):
        source, entries, group = self.prepare()
        other_source, _, other_group = self.prepare()
        state = compact._GROUPS[group]
        for forged in (replace(state, source=other_source),
                replace(state, payload=compact._issued(other_group).payload)):
            compact._GROUPS[group] = forged
            try:
                with self.assertRaisesRegex(ValueError, "state_changed"):
                    compact.compare_block(group, next(other_group.iter_blocks()))
            finally:
                compact._GROUPS[group] = state

    def test_late_codec_hold_diagnostics_are_retained_without_capability(self):
        source, entries = self.inputs()
        error = compact.dag.DagHold("synthetic_composition_gate", {"charged_work_units_lower_bound": 999,
            "scope": "cumulative_codec_not_whole_group"})
        with patch.object(compact.dag, "compose_proofs", side_effect=error):
            plan = compact.preflight_saved_group(source, entries, completion_request_ref=request_ref())
        self.assertEqual(plan.stage, "proof_composition")
        self.assertEqual(plan.entry_count, 2)
        self.assertEqual(plan.planned_pairs, 1)
        self.assertEqual(plan.codec_hold_reason, "synthetic_composition_gate")
        self.assertIn('"charged_work_units_lower_bound":999', plan.codec_hold_diagnostics_json)
        self.assertNotIn(plan, compact._PLANS)
        with self.assertRaises(compact.WholeGroupHold):
            compact.prepare_preflight(plan)


if __name__ == "__main__":
    unittest.main()
