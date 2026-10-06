"""Genuine small XML/native inputs; sensitivity is not musical accuracy."""
from copy import deepcopy
from fractions import Fraction
import unittest
from unittest.mock import patch

from musicanote_harness import completion_evidence_contrast as core
from musicanote_harness import progression_evidence_review as review
from musicanote_harness import native_progression_contrast as parent
from musicanote_harness import factor_interval_lattice as native
from musicanote_harness import factor_native_role_explanations as roles
from musicanote_harness.musical_pattern_observation import digest, f, q
import test_native_progression_contrast as factory


class CompletionContrastTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        factory.SavedProgressionContrastTests.setUpClass()
        cls.addClassCleanup(factory.SavedProgressionContrastTests.doClassCleanups)
        cls.fixture = factory.SavedProgressionContrastTests()
        cls.cache = {}

    def pair(self, name="passing"):
        if name not in self.cache:
            rows, all_bundles = [], {}
            for control in (True, False):
                scope, lattice, entries, bundles = self.fixture.inputs(name, "single", control)
                origins = {o["record_id"]: o for c in lattice["catalog_inventory"] for o in c["origins"]}
                sounds = {s["sound_ref"]: s for s in scope["sound_facts"]}
                entry = entries[0]
                facet = parent._facet(entry, scope,
                    [origins[r["record_id"]] for r in entry["native_path"]["origin_refs"]], sounds)
                key = next(k for k in lattice["keys"] if k["record_id"] == facet["key_ref"]["record_id"])
                rows.append(review.review_facet(facet, key))
                all_bundles.update(bundles)
            self.cache[name] = rows[0], rows[1], scope, all_bundles
        return deepcopy(self.cache[name])

    def test_real_passing_credit_sensitive_to_links_not_winner(self):
        result = core.compare_reviews(*self.pair())
        self.assertGreater(f(result["conditional_credit_delta_quarters"]), 0)
        self.assertTrue(result["changed_sound_credit_spans"])
        self.assertTrue(result["raw_source_music_unchanged"])
        self.assertFalse(result["independent_completions_unioned"])
        self.assertTrue(all(v is False for v in result["flags"].values()))
        self.assertTrue(all(result[k] is None for k in ("selected", "rank", "confidence")))

    def test_reverse_contrast_negates_credit_not_combines(self):
        a, b, scope, bundles = self.pair()
        forward = core.compare_reviews(a, b, scope, bundles)
        reverse = core.compare_reviews(b, a, scope, bundles)
        self.assertEqual(f(forward["conditional_credit_delta_quarters"]), -f(reverse["conditional_credit_delta_quarters"]))
        self.assertEqual(forward["category_delta_right_minus_left"],
                         {k: q(-f(v)) for k, v in reverse["category_delta_right_minus_left"].items()})

    def test_rational_duration_stays_exact(self):
        result = core.compare_reviews(*self.pair("rational"))
        self.assertTrue(any(f(r["duration_quarters"]) == Fraction(1, 3)
                            for r in result["changed_sound_credit_spans"]))

    def test_no_replay_or_input_mutation(self):
        args = self.pair()
        before = digest(args)
        with patch.object(native, "compare_prepared", side_effect=AssertionError("replay")), \
             patch.object(roles, "explain_prepared", side_effect=AssertionError("replay")):
            core.compare_reviews(*args)
        self.assertEqual(digest(args), before)

    def test_first_adverse_endpoint_not_skipped_for_later_resolution(self):
        a, b, scope, bundles = self.pair("ordinary_first_adverse")
        result = core.compare_reviews(a, b, scope, bundles)
        self.assertTrue(result["transition_contrasts"])
        self.assertTrue(any(t["whole_template_truth_change"][1] == "false"
                            for t in result["transition_contrasts"]))

    def test_tie_and_reattack_source_observations_not_changed(self):
        for name in ("suspension_tie", "suspension_reattack"):
            a, b, scope, bundles = self.pair(name)
            result = core.compare_reviews(a, b, scope, bundles)
            self.assertEqual(a["slots"], b["slots"])
            self.assertTrue(result["raw_source_music_unchanged"])

    def test_same_completion_rejected(self):
        a, b, scope, bundles = self.pair()
        with self.assertRaisesRegex(ValueError, "distinct_completion"):
            core.compare_reviews(a, a, scope, bundles)

    def test_wrong_key_partition_or_origin_cannot_be_ordinal_pair(self):
        for field in ("key_ref", "partition", "slots"):
            a, b, scope, bundles = self.pair()
            b[field] = None
            with self.assertRaisesRegex(ValueError, "identical_source_harmony"):
                core.compare_reviews(a, b, scope, bundles)

    def test_wrong_raw_account_cannot_be_source_sensitivity(self):
        a, b, scope, bundles = self.pair()
        b["note_time_account"]["raw_state_note_time_quarters"] = {}
        with self.assertRaisesRegex(ValueError, "identical_raw_music"):
            core.compare_reviews(a, b, scope, bundles)

    def test_duplicate_or_outside_source_credit_rejected(self):
        for outside in (False, True):
            a, b, scope, bundles = self.pair()
            credit = b["note_time_account"]["explained_intervals_by_sound"]
            self.assertTrue(credit)
            if outside:
                credit[0]["spans"][0]["end"] = q(1000)
            else:
                credit.append(deepcopy(credit[0]))
            with self.assertRaises(ValueError):
                core.compare_reviews(a, b, scope, bundles)

    def test_promoted_or_foreign_bundle_rejected(self):
        for field in ("selected", "bundle_ref"):
            a, b, scope, bundles = self.pair()
            if field == "selected":
                b[field] = 0
            else:
                b[field]["record_sha256"] = "0" * 64
            with self.assertRaises(ValueError):
                core.compare_reviews(a, b, scope, bundles)

    def test_nominal_cadence_stays_unconfirmed(self):
        a, b, scope, bundles = self.pair("ordinary")
        result = core.compare_reviews(a, b, scope, bundles)
        self.assertTrue(all(c["confirmed"] is False for c in result["right_cadence_candidates"]))

    def test_unknown_key_not_certified_by_more_voice_links(self):
        rows, all_bundles = [], {}
        for control in (True, False):
            scope, lattice, entries, bundles = self.fixture.inputs("ordinary", "key", control)
            entry = entries[-1]  # Genuine explicit unknown-key selector, not a relabelled known key.
            origins = {o["record_id"]: o for c in lattice["catalog_inventory"] for o in c["origins"]}
            sounds = {s["sound_ref"]: s for s in scope["sound_facts"]}
            facet = parent._facet(entry, scope,
                [origins[r["record_id"]] for r in entry["native_path"]["origin_refs"]], sounds)
            key = next(k for k in lattice["keys"] if k["record_id"] == facet["key_ref"]["record_id"])
            rows.append(review.review_facet(facet, key))
            all_bundles.update(bundles)
        result = core.compare_reviews(rows[0], rows[1], scope, all_bundles)
        self.assertFalse(rows[0]["key_coordinate_available"])
        self.assertFalse(rows[1]["key_coordinate_available"])
        self.assertFalse(rows[1]["key_inferred"])
        self.assertTrue(all(v is False for v in result["flags"].values()))

    def test_changed_function_declaration_not_a_completion_contrast(self):
        a, b, scope, bundles = self.pair("ordinary")
        b["transitions"][0]["assumption"] = None
        with self.assertRaisesRegex(ValueError, "identical_transition_assumptions"):
            core.compare_reviews(a, b, scope, bundles)


if __name__ == "__main__":
    unittest.main()
