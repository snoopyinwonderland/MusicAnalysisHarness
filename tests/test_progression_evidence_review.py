"""Genuine small XML-derived saved packets; no historical corpus accuracy."""
from copy import deepcopy
from dataclasses import asdict
import unittest
from unittest.mock import patch

from musicanote_harness import progression_evidence_review as review
from musicanote_harness import proof_shared_source_progression_contrast as compact
from musicanote_harness import shared_source_progression_contrast as shared
from musicanote_harness import factor_interval_lattice as native
from musicanote_harness import factor_native_role_explanations as roles
from musicanote_harness import native_progression_contrast as parent
from musicanote_harness.musical_pattern_observation import digest, q
import test_native_progression_contrast as factory
from test_cross_batch_progression_contrast import request_ref


class EvidenceReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        factory.SavedProgressionContrastTests.setUpClass()
        cls.addClassCleanup(factory.SavedProgressionContrastTests.doClassCleanups)
        cls.fixture = factory.SavedProgressionContrastTests()
        cls.cache = {}

    def packet(self, name="passing", mode="candidate", control=False):
        identity = name, mode, control
        if identity not in self.cache:
            scope, lattice, entries, bundles = self.fixture.inputs(*identity)
            source = shared.prepare_saved_source(scope, lattice, bundles=bundles)
            group = compact.prepare_saved_group(source, entries, completion_request_ref=request_ref())
            self.cache[identity] = (source.export_source(), group.export_catalog(),
                [(asdict(task), compact.compare_block(group, task)) for task in group.iter_blocks()])
        return deepcopy(self.cache[identity])

    def result(self, *args):
        source, catalog, _ = self.packet(*args)
        return review.review_catalog(catalog, source)

    def test_all_candidates_preserved_unselected(self):
        source, catalog, blocks = self.packet()
        before = digest([source, catalog, blocks])
        result = review.review_catalog(catalog, source)
        self.assertEqual(result["summary"]["reviewed_candidates"], 2)
        self.assertEqual(len(result["candidate_reviews"]), len(catalog["group"]["entry_refs"]))
        self.assertTrue(all(v is False for v in result["flags"].values()))
        self.assertTrue(all(result[k] is None for k in ("selected", "rank", "confidence")))
        self.assertEqual(before, digest([source, catalog, blocks]))

    def test_no_native_role_or_pair_replay(self):
        source, catalog, blocks = self.packet()
        with patch.object(native, "compare_prepared", side_effect=AssertionError("replay")), \
             patch.object(roles, "explain_prepared", side_effect=AssertionError("replay")), \
             patch.object(compact, "compare_block", side_effect=AssertionError("replay")):
            review.review_catalog(catalog, source)
            self.assertEqual(review.audit_pair_block(blocks[0][1], catalog, task=blocks[0][0])["audited_pairs"], 1)

    def test_full_hold_does_not_require_vacuous_internal_relation(self):
        row = self.result("single", "single")["candidate_reviews"][0]
        self.assertTrue(row["no_internal_transition_is_not_hold_failure"])
        self.assertEqual(row["transitions"], [])
        self.assertNotIn("declared_progression_not_fully_supported", [i["reason"] for i in row["issues"]])

    def test_ordinary_positive_stays_conditional(self):
        row = self.result("ordinary", "single")["candidate_reviews"][0]
        self.assertEqual(row["transitions"][0]["state"], "conditional_joint_supported")
        self.assertIsNone(row["selected"])
        self.assertFalse(row["flags"]["key_confirmed"])

    def test_individual_resolution_not_whole_template(self):
        row = self.result("ordinary_first_adverse", "single")["candidate_reviews"][0]
        self.assertTrue(row["transitions"][0]["individual_role_support_without_whole_template"])
        self.assertNotEqual(row["transitions"][0]["state"], "conditional_joint_supported")

    def test_no_link_control_is_held_not_global_chord_rejection(self):
        row = self.result("ordinary", "single", True)["candidate_reviews"][0]
        self.assertEqual(row["transitions"][0]["state"], "held_under_same_completion")
        self.assertFalse(row["transitions"][0]["shape_conflict_rejects_all_chord_interpretations"])

    def test_unknown_key_axis_and_cadence_not_confirmed(self):
        scope, lattice, entries, bundles = self.fixture.inputs("passing", "key")
        source = shared.prepare_saved_source(scope, lattice, bundles=bundles)
        rows = []
        for entry in entries:
            group = compact.prepare_saved_group(source, [entry], completion_request_ref=request_ref())
            rows.extend(review.review_catalog(group.export_catalog(), source.export_source())["candidate_reviews"])
        self.assertEqual({r["key_coordinate_available"] for r in rows}, {False, True})
        self.assertNotEqual(rows[0]["fixed_premise_id"], rows[1]["fixed_premise_id"])
        for row in rows:
            self.assertTrue(all(c["confirmed"] is False for c in row["cadence_candidates"]))

    def test_same_signature_cut_not_auto_merged(self):
        result = self.result("passing", "partition")
        self.assertTrue(any(i["rule_id"] == "ER07" for r in result["candidate_reviews"] for i in r["issues"]))
        self.assertEqual(len(result["candidate_reviews"]), 2)
        self.assertNotEqual(*[r["fixed_premise_id"] for r in result["candidate_reviews"]])

    def test_fractional_note_time_and_pair_margins(self):
        source, catalog, blocks = self.packet("rational")
        result = review.review_catalog(catalog, source)
        self.assertTrue(any(o["observed_span"]["start"]["denominator"] == 3
            for r in result["candidate_reviews"] for s in r["slots"]
            for p in s["member_observations"] for o in p["observations"]))
        self.assertEqual(review.audit_pair_block(blocks[0][1], catalog, task=blocks[0][0])["audited_pairs"], 1)

    def test_attack_and_tie_refs_preserved(self):
        source, catalog, _ = self.packet("suspension_reattack", "single")
        result = review.review_catalog(catalog, source)
        sounds = {s["sound_ref"]: s for s in source["source_scope"]["sound_facts"]}
        for row in result["candidate_reviews"]:
            for slot in row["slots"]:
                for member in slot["member_observations"]:
                    for o in member["observations"]:
                        self.assertEqual(o["attack_note_ref"], sounds[o["sound_ref"]]["attack_note_ref"])
                        self.assertEqual(o["tie_chain_ref"], sounds[o["sound_ref"]]["tie_chain_ref"])

    def test_missing_member_cannot_become_present_by_rewriting_account(self):
        source, catalog, _ = self.packet()
        catalog["pair_index"][0]["account"]["raw_total_note_time_quarters"] = q(999)
        with self.assertRaises(ValueError):
            review.review_catalog(catalog, source)

    def test_foreign_source_and_lost_selector_rejected(self):
        source, catalog, _ = self.packet()
        catalog["source_catalog_ref"]["record_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            review.review_catalog(catalog, source)
        source, catalog, _ = self.packet()
        catalog["group"]["original_selector_indices"].pop()
        with self.assertRaises(ValueError):
            review.review_catalog(catalog, source)

    def test_pair_delta_corruption_rejected(self):
        _, catalog, blocks = self.packet()
        task, block = blocks[0]
        block["pairs"][0]["note_time_delta_right_minus_left"][parent.CATEGORIES[0]] = q(99)
        with self.assertRaises(ValueError):
            review.audit_pair_block(block, catalog, task=task)

    def test_pair_order_coverage_and_promoted_result_rejected(self):
        for modification in ("missing", "order", "selected"):
            _, catalog, blocks = self.packet()
            task, block = blocks[0]
            if modification == "missing":
                block["pairs"].clear()
            elif modification == "order":
                block["pairs"][0]["entry_indices"].reverse()
            else:
                block["pairs"][0]["selected"] = 0
            with self.assertRaises(ValueError):
                review.audit_pair_block(block, catalog, task=task)

    def test_pure_projection_zero_unresolved_missing_is_not_success(self):
        # Explicit projection-only counterexample, not an authenticated packet.
        source, catalog, _ = self.packet("single", "single")
        from musicanote_harness import lossless_json_dag_v2 as dag
        facet = dag.value_at(dag.import_record(catalog["payload"]), ("facets", 0))
        facet["slot_presentations"][0]["missing_guarded_spellings"] = [{"step": "F", "alter": q(1)}]
        key = source["lattice"]["keys"][0]
        projected = review.review_facet(facet, key)
        self.assertTrue(projected["zero_unresolved_time_with_missing_constituents"])
        self.assertIsNone(projected["selected"])


if __name__ == "__main__":
    unittest.main()
