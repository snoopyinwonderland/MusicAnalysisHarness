from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from jsonschema import Draft202012Validator

from musicanote_harness import musical_semantic_enrichment as semantic


def span(start=0, end=4, denominator=1):
    return {"start": {"numerator": start, "denominator": denominator},
            "end": {"numerator": end, "denominator": denominator}}


def context(raw="Note: a held line may change its function.", revision="source-r1"):
    return {"source_ref": "document:example", "source_revision": revision,
            "source_sha256": "a" * 64, "raw_text": raw,
            "location": {"kind": "source_statement", "locator": {"physical_line": 7,
                         "native_tag": "Note", "raw_value": raw[5:], "context_is_target": False}}}


def provenance(kind="rule"):
    return {"kind": kind, "actor_id": "author-1" if kind == "human" else None,
            "producer": {"name": "test-producer", "version": "1.0.0", "config_sha256": "d" * 64,
                         "model_ref": {"name": "test-model", "version": "m1"} if kind == "ai" else None,
                         "schema_ref": {"name": "test-output-contract", "version": "1.0.0"}}}


def review():
    return {"status": "validated", "reviewer_id": "reviewer-9", "review_ref": "review:9"}


def binding(target_span=None, harmony="h1", events=None):
    return {"score_id": "score-1", "score_sha256": "b" * 64, "ir_sha256": "c" * 64,
            "ir_schema_version": "0.1.0", "alignment_ref": "alignment:checked-1",
            "target": {"entity_refs": ["tied-event-1"] if events is None else events,
                       "span": target_span or span()},
            "harmony_assumption_ref": None if harmony is None else {
                "analysis_id": harmony, "analysis_sha256": "e" * 64, "engine_version": "harmony-1"}}


def case(case_id="case-1"):
    return {"case_id": case_id, "score_id": "score-1", "score_sha256": "b" * 64,
            "ir_sha256": "c" * 64, "ir_schema_version": "0.1.0", "span": span(),
            "entity_ids": ["tied-event-1"],
            "source_refs": [{"source_ref": "document:example", "source_revision": "source-r1", "source_sha256": "a" * 64}]}


def reseal(record):
    record = deepcopy(record)
    record.pop("record_id")
    record.pop("record_sha256")
    return semantic._seal(record)


class MusicalSemanticEnrichmentTest(unittest.TestCase):
    def source(self, **kwargs):
        return semantic.build_source_claim(case_id="case-1", source_context=context(), **kwargs)

    def bound(self, source=None, **kwargs):
        defaults = {"source_claim": source or self.source(), "binding": binding(),
                    "axis": "harmonic_role", "term": "suspension", "provenance": provenance()}
        defaults.update(kwargs)
        return semantic.build_bound_claim(**defaults)

    def test_legacy_optional_absence_is_not_assessed_not_negative(self):
        legacy = [{"case_id": "z", "old_field": "unchanged"}, {"case_id": "a"}]
        before = deepcopy(legacy)
        result = semantic.plan_coverage(legacy, [])
        self.assertEqual([row["case_id"] for row in result], ["a", "z"])
        self.assertEqual(legacy, before)
        self.assertEqual(result[0]["missing_axes"], list(semantic.AXES))
        self.assertEqual(set(result[0]["axis_states"].values()), {"not_assessed"})
        self.assertNotIn("absent", json.dumps(result))

    def test_raw_source_is_exact_and_unaligned(self):
        raw = "Note:  held note?\tperhaps melody, not proven.  "
        source = semantic.build_source_claim(case_id="case-1", source_context=context(raw))
        self.assertEqual(source["source_context"]["raw_text"], raw)
        self.assertEqual(source["record_kind"], "SOURCE")
        self.assertIsNone(source["binding"])
        self.assertIsNone(source["claim"]["axis"])
        self.assertIsNone(source["confidence"])
        self.assertEqual(source["human_review"]["status"], "unreviewed")
        self.assertFalse(source["use_policy"]["training_eligible"])

    def test_source_tag_routing_does_not_claim_typed_truth(self):
        source = self.source(axis="form_role")
        result = semantic.plan_coverage([case()], [source])[0]
        self.assertEqual(result["axis_states"]["form_role"], "needs_alignment")
        self.assertIn("form_role", result["missing_axes"])
        self.assertIsNone(source["claim"]["term"])

    def test_source_cannot_acquire_binding_or_covered_status(self):
        for field, value in (("binding", binding()), ("coverage_state", "covered")):
            source = self.source()
            source[field] = value
            with self.assertRaises(ValueError):
                reseal(source)

    def test_append_is_idempotent_and_preserves_old_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "new-sidecar.jsonl"
            source = self.source()
            self.assertTrue(semantic.append_record(path, source))
            original = path.read_bytes()
            self.assertFalse(semantic.append_record(path, source))
            self.assertEqual(path.read_bytes(), original)
            revised = self.source(lineage_id=source["lineage_id"], revision=2,
                                  supersedes=semantic.record_ref(source), rationale="clarified uncertainty")
            self.assertTrue(semantic.append_record(path, revised))
            self.assertTrue(path.read_bytes().startswith(original))
            self.assertEqual(len(semantic.load_records(path)), 2)

    def test_missing_optional_store_is_empty(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(semantic.load_records(Path(folder) / "missing.jsonl"), [])

    def test_duplicate_history_and_tampering_are_rejected(self):
        source = self.source()
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            semantic.validate_records([source, source])
        tampered = deepcopy(source)
        tampered["source_context"]["raw_text"] = "invented correction"
        with self.assertRaisesRegex(ValueError, "Tampered"):
            semantic.validate_record(tampered)

    def test_source_and_bound_are_distinct_linked_records(self):
        source = self.source()
        bound = self.bound(source)
        semantic.validate_records([source, bound], legacy_cases=[case()])
        self.assertNotEqual(source["record_id"], bound["record_id"])
        self.assertEqual(bound["source_claim_ref"], semantic.record_ref(source))
        self.assertEqual(source["coverage_state"], "needs_alignment")

    def test_unknown_source_and_forward_refs_fail(self):
        source, bound = self.source(), self.bound()
        with self.assertRaisesRegex(ValueError, "Missing, forward"):
            semantic.validate_records([bound, source])
        changed = deepcopy(bound)
        changed["source_claim_ref"]["record_sha256"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "tampered"):
            semantic.validate_records([source, reseal(changed)])

    def test_bound_context_cannot_drift_from_source(self):
        source, bound = self.source(), self.bound()
        changed = deepcopy(bound)
        changed["source_context"]["source_revision"] = "source-r2"
        with self.assertRaisesRegex(ValueError, "exactly match"):
            semantic.validate_records([source, reseal(changed)])

    def test_rational_bounds_reject_empty_reverse_negative_float_zero_denominator(self):
        for bad in (span(1, 1), span(3, 2), span(-1, 3), span(0, 4, 0), span(0.5, 4)):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.bound(binding=binding(bad))

    def test_rational_equivalent_bounds_are_valid(self):
        source = self.source()
        bound = self.bound(source, binding=binding(span(0, 8, 2)))
        semantic.validate_records([source, bound], legacy_cases=[case()])

    def test_confidence_is_nullable_and_explicitly_sourced(self):
        with self.assertRaises(ValueError):
            self.source(confidence=0.7)
        with self.assertRaises(ValueError):
            self.source(confidence=None, confidence_semantics="source_reported")
        with self.assertRaises(ValueError):
            self.source(confidence=1.1, confidence_semantics="source_reported")
        with self.assertRaises(ValueError):
            self.source(confidence=0.7, confidence_semantics="calibrated_probability")
        source = self.source(confidence=0.7, confidence_semantics="source_reported")
        self.assertEqual(source["confidence"], 0.7)
        self.assertEqual(source["human_review"]["status"], "unreviewed")

    def test_ai_guess_has_model_ref_and_no_automatic_human_validation(self):
        candidate = self.bound(provenance=provenance("ai"), confidence=0.8,
                               confidence_semantics="uncalibrated_score")
        self.assertEqual(candidate["human_review"]["status"], "unreviewed")
        bad = provenance("ai")
        bad["producer"]["model_ref"] = None
        with self.assertRaises(ValueError):
            self.bound(provenance=bad)
        with self.assertRaises(ValueError):
            self.bound(human_review={"status": "validated", "reviewer_id": None, "review_ref": None})

    def test_all_provenance_kinds_and_separate_reviewer(self):
        for kind in ("imported_source", "rule", "ai", "human"):
            bound = self.bound(provenance=provenance(kind), human_review=review())
            semantic.validate_record(bound)
            self.assertEqual(bound["human_review"]["reviewer_id"], "reviewer-9")
            self.assertNotEqual(bound["provenance"]["actor_id"], "reviewer-9")

    def test_policies_are_inherited_or_unknown_never_permission_grants(self):
        source = self.source()
        self.assertEqual(source["source_context"]["rights"]["training_status"], "unknown")
        inherited = context()
        inherited["rights"] = {"rights_status": "inherited", "rights_ref": "policy:license-1",
                               "training_status": "inherited", "training_ref": "policy:training-restrictions"}
        source = semantic.build_source_claim(case_id="case-1", source_context=inherited)
        self.assertFalse(source["use_policy"]["training_eligible"])
        inherited["rights"]["rights_ref"] = None
        with self.assertRaises(ValueError):
            semantic.build_source_claim(case_id="case-1", source_context=inherited)

    def test_numeric_source_revision_must_match_hash(self):
        source = context(revision="sha256:" + "b" * 64)
        with self.assertRaisesRegex(ValueError, "Source revision"):
            semantic.build_source_claim(case_id="case-1", source_context=source)

    def test_revision_cannot_skip_fork_or_cross_source_revision(self):
        source = self.source()
        for revision in (2, 3):
            successor = self.source(lineage_id=source["lineage_id"], revision=revision,
                                    supersedes=semantic.record_ref(source), rationale="revision")
            if revision == 3:
                with self.assertRaisesRegex(ValueError, "current lineage tip"):
                    semantic.validate_records([source, successor])
            else:
                fork = self.source(lineage_id=source["lineage_id"], revision=2,
                                   supersedes=semantic.record_ref(source), rationale="fork")
                with self.assertRaisesRegex(ValueError, "current lineage tip"):
                    semantic.validate_records([source, successor, fork])
        changed = semantic.build_source_claim(case_id="case-1", source_context=context(revision="source-r2"),
            lineage_id=source["lineage_id"], revision=2, supersedes=semantic.record_ref(source))
        with self.assertRaisesRegex(ValueError, "cannot retarget"):
            semantic.validate_records([source, changed])

    def test_unknown_fields_terms_and_versions_are_rejected(self):
        for axis, term in (("voice_role", "suspension"), ("unregistered_axis", "x"), (None, "melody")):
            with self.assertRaises(ValueError):
                self.source(axis=axis, term=term)
        source = self.source()
        for field, value in (("schema_version", "9.0"), ("free_json", {"truth": True})):
            changed = deepcopy(source)
            changed[field] = value
            with self.assertRaises(ValueError):
                reseal(changed)

    def test_schema_and_runtime_register_same_term_dictionary(self):
        schema = json.loads(semantic.SCHEMA_PATH.read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema)
        for axis, terms in semantic.TERMS.items():
            for term in terms:
                validator.validate(self.source(axis=axis, term=term))

    def test_orthogonal_melody_and_chord_tone_are_not_mutually_exclusive(self):
        source = self.source()
        melody = self.bound(source, axis="voice_role", term="melody")
        chord = self.bound(source, term="chord_tone")
        semantic.validate_records([source, melody, chord], legacy_cases=[case()])
        group = semantic.plan_coverage([case()], [source, melody, chord])[0]["assumption_groups"][0]
        self.assertEqual(group["axis_states"]["voice_role"], "pending_review")
        self.assertEqual(group["axis_states"]["harmonic_role"], "pending_review")

    def test_tied_event_can_change_role_at_rational_boundary(self):
        source = self.source()
        suspension = self.bound(source, binding=binding(span(0, 3, 2)), term="suspension")
        chord = self.bound(source, binding=binding(span(3, 8, 2)), term="chord_tone")
        semantic.validate_records([source, suspension, chord], legacy_cases=[case()])
        self.assertEqual(suspension["binding"]["target"]["entity_refs"], chord["binding"]["target"]["entity_refs"])
        self.assertNotEqual(suspension["lineage_id"], chord["lineage_id"])

    def test_harmony_assumptions_not_pooled_even_for_same_role(self):
        source = self.source()
        claims = [self.bound(source, binding=binding(harmony=h), term="chord_tone", human_review=review(), coverage_state="covered") for h in ("h1", "h2")]
        result = semantic.plan_coverage([case()], [source, *claims])[0]
        self.assertEqual(len(result["assumption_groups"]), 2)
        self.assertEqual(result["axis_states"]["harmonic_role"], "covered_partial")
        self.assertIn("harmonic_role", result["missing_axes"])

    def test_role_references_and_harmony_assumption_are_required(self):
        with self.assertRaises(ValueError):
            self.bound(binding=binding(harmony=None))
        with self.assertRaises(ValueError):
            self.bound(binding=binding(events=[]))

    def test_changed_hash_or_source_revision_invalidates_coverage(self):
        source = self.source()
        bound = self.bound(source, human_review=review(), coverage_state="covered_partial")
        for field in ("ir_sha256", "score_sha256"):
            changed = case()
            changed[field] = "f" * 64
            result = semantic.plan_coverage([changed], [source, bound])[0]
            self.assertIn("harmonic_role", result["missing_axes"])
            self.assertEqual(result["stale_record_ids"][0]["reason"], field + "_mismatch")
            with self.assertRaisesRegex(ValueError, "Stale"):
                semantic.validate_records([source, bound], legacy_cases=[changed])
        changed = case()
        changed["source_refs"][0]["source_revision"] = "source-r2"
        result = semantic.plan_coverage([changed], [source, bound])[0]
        self.assertEqual(len(result["stale_record_ids"]), 2)
        self.assertEqual(result["axis_states"]["harmonic_role"], "not_assessed")

    def test_partial_coverage_remains_missing_and_cannot_be_unreviewed(self):
        source = self.source()
        with self.assertRaises(ValueError):
            self.bound(source, coverage_state="covered_partial")
        bound = self.bound(source, coverage_state="covered_partial", human_review=review())
        result = semantic.plan_coverage([case()], [source, bound])[0]
        self.assertEqual(result["axis_states"]["harmonic_role"], "covered_partial")
        self.assertIn("harmonic_role", result["missing_axes"])

    def test_complete_coverage_requires_known_scope_and_inventory(self):
        source = self.source()
        complete = self.bound(source, coverage_state="covered", human_review=review())
        semantic.validate_records([source, complete], legacy_cases=[case()])
        self.assertNotIn("harmonic_role", semantic.plan_coverage([case()], [source, complete])[0]["missing_axes"])
        for field in ("span", "entity_ids"):
            incomplete = case()
            incomplete.pop(field)
            with self.assertRaises(ValueError):
                semantic.validate_records([source, complete], legacy_cases=[incomplete])
            self.assertIn("harmonic_role", semantic.plan_coverage([incomplete], [source, complete])[0]["missing_axes"])

    def test_single_note_whole_piece_span_cannot_self_certify_coverage(self):
        source = self.source()
        complete = self.bound(source, coverage_state="covered", human_review=review())
        multiple = case()
        multiple["entity_ids"].append("note-2")
        with self.assertRaisesRegex(ValueError, "inventory"):
            semantic.validate_records([source, complete], legacy_cases=[multiple])
        planned = semantic.plan_coverage([multiple], [source, complete])[0]
        self.assertIn("harmonic_role", planned["missing_axes"])
        self.assertEqual(planned["stale_record_ids"][0]["reason"], "complete_inventory_mismatch")

    def test_mixed_complete_and_unrelated_bound_history_is_readable(self):
        source = self.source()
        complete = self.bound(source, coverage_state="covered", human_review=review())
        other_source = semantic.build_source_claim(case_id="other", source_context=context())
        other_bound = self.bound(other_source)
        semantic.validate_records([source, complete, other_source, other_bound], legacy_cases=[case(), case("other")])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "new.jsonl"
            for record in (source, complete, other_source, other_bound):
                semantic.append_record(path, record, legacy_cases=[case(), case("other")])
            self.assertEqual(len(semantic.load_records(path)), 4)
        mismatch = case()
        mismatch["span"] = span(0, 8)
        planned = semantic.plan_coverage([mismatch, case("other")], [source, complete, other_source, other_bound])
        self.assertIn("harmonic_role", planned[0]["missing_axes"])

    def test_unregistered_ir_events_and_targets_are_not_reused(self):
        source = self.source()
        bound = self.bound(source)
        for descriptor in ({"case_id": "case-1", "artifact_hash": "c" * 64}, {**case(), "entity_ids": ["other-event"]}):
            with self.assertRaisesRegex(ValueError, "Stale"):
                semantic.validate_records([source, bound], legacy_cases=[descriptor])
            self.assertIn("harmonic_role", semantic.plan_coverage([descriptor], [source, bound])[0]["missing_axes"])
        outside = self.bound(source, binding=binding(span(0, 8)))
        with self.assertRaisesRegex(ValueError, "outside"):
            semantic.validate_records([source, outside], legacy_cases=[case()])

    def test_bound_append_requires_independent_registration(self):
        source = self.source()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "new.jsonl"
            semantic.append_record(path, source)
            with self.assertRaisesRegex(ValueError, "independent"):
                semantic.append_record(path, self.bound(source))
            self.assertEqual(semantic.load_records(path), [source])

    def test_placement_relations_resolve_and_check_half_open_chronology(self):
        source = self.source()
        first = self.bound(source, binding=binding(span(0, 2)), axis="placement", term="foreground")
        after = self.bound(source, binding=binding(span(2, 4)), axis="placement", term="after",
                           relations=[{"relation_type": "after", "target_ref": semantic.record_ref(first)}])
        semantic.validate_records([source, first, after], legacy_cases=[case()])
        for kind in ("before", "overlaps"):
            bad = self.bound(source, binding=binding(span(2, 4)), axis="placement", term="after",
                             relations=[{"relation_type": kind, "target_ref": semantic.record_ref(first)}])
            with self.assertRaisesRegex(ValueError, "chronology|intersection"):
                semantic.validate_records([source, first, bad], legacy_cases=[case()])

    def test_relation_cannot_pool_changed_harmony_and_forward_reference(self):
        source = self.source()
        first = self.bound(source)
        other = self.bound(source, binding=binding(harmony="h2"), relations=[{
            "relation_type": "supports", "target_ref": semantic.record_ref(first)}])
        with self.assertRaisesRegex(ValueError, "changed"):
            semantic.validate_records([source, first, other])
        with self.assertRaisesRegex(ValueError, "forward"):
            semantic.validate_records([source, other, first])

    def test_planner_is_deterministic_and_superseded_claim_not_current(self):
        source = self.source()
        bound = self.bound(source)
        revised = self.bound(source, lineage_id=bound["lineage_id"], revision=2,
            supersedes=semantic.record_ref(bound), human_review=review(), coverage_state="covered_partial")
        history = [source, bound, revised]
        result = semantic.plan_coverage([case()], history)
        self.assertEqual(result, semantic.plan_coverage([case()], history))
        ids = result[0]["assumption_groups"][0]["record_ids"]
        self.assertEqual(ids, [revised["record_id"]])
        self.assertEqual(result[0]["axis_states"]["harmonic_role"], "covered_partial")

    def test_legacy_inventory_mappings_strings_and_duplicates_fail_closed(self):
        source = self.source()
        complete = self.bound(source, coverage_state="covered", human_review=review())
        invalid = ({"tied-event-1": False}, "tied-event-1", ("tied-event-1",),
                   ["tied-event-1", "tied-event-1"], [None], [1], [""], [" "])
        for inventory in invalid:
            with self.subTest(inventory=inventory):
                descriptor = case()
                descriptor["entity_ids"] = inventory
                with self.assertRaisesRegex(ValueError, "Legacy entity_ids"):
                    semantic.plan_coverage([descriptor], [source, complete])
                with self.assertRaisesRegex(ValueError, "Legacy entity_ids"):
                    semantic.validate_records([source, complete], legacy_cases=[descriptor])

    def test_legacy_per_axis_inventory_requires_known_axes_and_typed_lists(self):
        invalid = ([], "harmonic_role", {"fake_axis": []},
                   {"harmonic_role": {"tied-event-1": True}}, {"harmonic_role": "tied-event-1"},
                   {"harmonic_role": None}, {"harmonic_role": ["tied-event-1", "tied-event-1"]},
                   {"harmonic_role": ["unregistered-event"]})
        for inventory in invalid:
            with self.subTest(inventory=inventory):
                descriptor = case()
                descriptor["required_entity_ids"] = inventory
                with self.assertRaisesRegex(ValueError, "Legacy required_entity_ids"):
                    semantic.plan_coverage([descriptor], [])
        descriptor = case()
        descriptor["entity_ids"].append("other-event")
        descriptor["required_entity_ids"] = {"harmonic_role": ["tied-event-1"], "texture": []}
        source = self.source()
        complete = self.bound(source, coverage_state="covered", human_review=review())
        semantic.validate_records([source, complete], legacy_cases=[descriptor])
        self.assertNotIn("harmonic_role", semantic.plan_coverage([descriptor], [source, complete])[0]["missing_axes"])

    def test_legacy_source_reference_containers_and_values_fail_closed(self):
        invalid = ({"document:example": "source-r1"}, "document:example", ("document:example",),
                   [None], [9], [""], [" "], [{"source_ref": "document:example"}],
                   [{"source_ref": 9, "source_revision": "r1"}],
                   [{"source_ref": "document:example", "source_revision": None}],
                   [{"source_ref": "document:example", "source_revision": "r1", "source_sha256": "invalid"}],
                   [{"source_ref": "document:example", "source_revision": "r1", "misspelled_hash": "a" * 64}],
                   [{"source_ref": "document:example", "source_revision": "sha256:" + "a" * 64, "source_sha256": "b" * 64}],
                   ["document:example", "document:example"])
        for refs in invalid:
            with self.subTest(refs=refs):
                descriptor = case()
                descriptor["source_refs"] = refs
                with self.assertRaisesRegex(ValueError, "[Ll]egacy source_refs|legacy hash"):
                    semantic.plan_coverage([descriptor], [])

    def test_unknown_legacy_consumed_fields_still_mean_unregistered_not_complete(self):
        descriptor = {"case_id": "case-1", "source_refs": None, "entity_ids": None,
                      "required_entity_ids": None, "unrelated_legacy_metadata": {"preserved": True}}
        before = deepcopy(descriptor)
        self.assertEqual(set(semantic.plan_coverage([descriptor], [])[0]["axis_states"].values()), {"not_assessed"})
        self.assertEqual(descriptor, before)

    def test_source_tag_spelling_is_retained_without_becoming_semantics(self):
        raw_context = context("note:  free analyst prose.  ")
        raw_context["location"]["locator"]["source_tag_spelling"] = "note"
        source = semantic.build_source_claim(case_id="case-1", source_context=raw_context)
        self.assertEqual(source["source_context"]["location"]["locator"]["source_tag_spelling"], "note")
        self.assertEqual(source["source_context"]["raw_text"], "note:  free analyst prose.  ")
        self.assertIsNone(source["claim"]["axis"])
        self.assertIsNone(source["binding"])

    def test_conflicting_duplicate_legacy_source_revision_hash_fails_closed(self):
        descriptor = case()
        duplicate = deepcopy(descriptor["source_refs"][0])
        duplicate["source_sha256"] = "b" * 64
        descriptor["source_refs"].append(duplicate)
        with self.assertRaisesRegex(ValueError, "Duplicate legacy source_refs"):
            semantic.plan_coverage([descriptor], [])

    def test_malformed_inventory_cannot_append_or_change_existing_bytes(self):
        source = self.source()
        complete = self.bound(source, coverage_state="covered", human_review=review())
        descriptor = case()
        descriptor["entity_ids"] = {"tied-event-1": False}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "new.jsonl"
            semantic.append_record(path, source)
            before = path.read_bytes()
            with self.assertRaisesRegex(ValueError, "Legacy entity_ids"):
                semantic.append_record(path, complete, legacy_cases=[descriptor])
            self.assertEqual(path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
