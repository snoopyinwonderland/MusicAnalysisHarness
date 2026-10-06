"""Synthetic/temp diagnostics: never depend on the user's local score corpora."""
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from musicanote_harness import source_locator_voice_audit as audit


def q(value):
    return {"numerator": value, "denominator": 1}


def source(nid, part="P1", voice="1", staff=1, status="explicit_source_voice_observed"):
    return {"note_id": nid, "source_part_id": part, "source_voice": voice,
            "source_staff": staff, "source_identity_status": status}


def note(nid, part="part1", voice="voice1"):
    return {"note_id": nid, "part_id": part, "voice_id": voice}


def mapped_xml(notes, part="P1"):
    return f'<score-partwise><part id="{part}"><measure number="1">{notes}</measure></part></score-partwise>'


def pitched(nid, extras=""):
    return f'<note id="{nid}"><pitch><step>C</step><octave>4</octave></pitch>{extras}</note>'


def write_json(path, value):
    Path(path).write_text(json.dumps(value), encoding="utf-8")


def read_json(path):
    return json.loads(Path(path).read_bytes())


def fixture(root, with_case=True):
    path = root / "source.musicxml"
    letters = "CDEF"
    raw_notes = []
    notes = []
    sounds = []
    for i, letter in enumerate(letters):
        source_voice = "2" if i == 1 else "1"
        staff = 2 if i == 3 else 1
        raw_notes.append(f'<note><pitch><step>{letter}</step><octave>4</octave></pitch>'
                         f'<duration>1</duration><voice>{source_voice}</voice><staff>{staff}</staff></note>')
        pitch = {"step": letter, "alter": q(0), "octave": 4,
                 "spelling": letter + "4", "midi_pitch": {"C": 60, "D": 62, "E": 64, "F": 65}[letter]}
        notes.append({"note_id": "n" + str(i + 1), "part_id": "part1", "voice_id": "voice1",
                      "display_staff_id": "staff" + str(staff), "measure_id": "m1",
                      "written_pitch": pitch, "onset_in_measure": q(i), "notated_duration_quarter": q(1),
                      "grace": {"is_grace": False}, "tie_role": "none"})
        sounds.append({"sounding_event_id": "s" + str(i + 1), "source_note_ids": ["n" + str(i + 1)],
                       "pitch": pitch, "span": {"start": q(i), "end": q(i + 1)}})
    path.write_text('<score-partwise><part-list><score-part id="P1"><part-name>Piano</part-name>'
                    '</score-part></part-list><part id="P1"><measure number="1">'
                    '<attributes><divisions>1</divisions></attributes>' + "".join(raw_notes) +
                    '</measure></part></score-partwise>', encoding="utf-8")
    ir = {"ir_document_id": "ir_fixture", "score": {"score_id": "score_fixture"},
          "parts": [{"part_id": "part1", "source_part_id": "P1", "staff_ids": ["staff1", "staff2"]}],
          "staves": [{"staff_id": "staff1", "staff_number": 1}, {"staff_id": "staff2", "staff_number": 2}],
          "voices": [{"voice_id": "voice1", "source_voice_number": "1"}],
          "measures": [{"measure_id": "m1", "printed_measure_number": "1"}],
          "note_events": notes, "sounding_events": sounds}
    original = root / "parent.json"
    frozen = root / "frozen.json"
    write_json(original, ir)
    frozen.write_bytes(original.read_bytes())
    labels = root / "opaque-labels.bin"
    labels.write_bytes(b"labels are hashed only and never input to source lane reasoning")
    entry = {"split": "train", "work_family_id": "work_fixture", "score_sha256": audit.digest(path),
             "score_source_path": str(path), "score_id": "score_fixture", "ir_document_id": "ir_fixture",
             "rights": {"internal_research_use": True, "model_training_approved": False,
                        "external_api_transmission_approved": False},
             "eligibility": {"automatic_training": False, "blind_evaluation": False}}
    pitch_policy = {"concert_pitch_normalization_verified": False}
    package = {"pair_id": "fixture:piece:1", "source": {"manifest_entry": entry,
        "source_files": {str(path): audit.digest(path), str(labels): audit.digest(labels)},
        "frozen_ir_path": str(frozen), "original_ir_path": str(original), "ir_sha256": audit.digest(frozen),
        "pitch_policy": pitch_policy}}
    plan_path = root / "plan.json"
    write_json(plan_path, {"packages": [package]})
    previous = root / "cases"
    previous.mkdir()
    write_json(previous / "run-contract.json", {"version": "historical"})
    report = {"complete": True, "inputs_unchanged": True, "snapshots_unchanged": True,
              "failed_rechecks": [], "source_labels_used": False, "accuracy_measured": False,
              "frozen_packages": 1, "supported_samples": int(with_case), "records": []}
    case_path = previous / "case.json.gz"
    if with_case:
        path_record = {"relation": "saved_role", "source_ref": "s1", "target_ref": "s2",
                       "carried_event_refs": ["s1"], "links": [["s1", "s2"]]}
        case = {"sample": {"sample_id": "sample_fixture"},
                "source_snapshot": {"manifest_entry": deepcopy(entry), "pitch_policy": deepcopy(pitch_policy),
                    "source_xml": str(path), "source_xml_sha256": audit.digest(path),
                    "canonical_ir": str(frozen), "canonical_ir_sha256": audit.digest(frozen)},
                "groups": [{"span": {"start": q(0), "cut": q(1), "end": q(2)}, "audits": [
                    {"query_index": 0, "pair": {"family": "V"},
                     "direct": {"status": "conditional_witness_rechecked", "selected_links": [["s1", "s2"]]},
                     "temporal": {"status": "conditional_witness_rechecked", "selected_paths": [path_record]}},
                    {"query_index": 1, "pair": {"family": "V"},
                     "direct": {"status": "conditional_witness_rechecked", "selected_links": [["s3", "s4"]]},
                     "temporal": {"status": "not_supported_in_saved_query"}}]}],
                "group_contexts": [{"span": {"start": q(0), "end": q(4)},
                                    "note_events": deepcopy(notes), "sounding_events": deepcopy(sounds)}]}
        case_path.write_bytes(gzip.compress(json.dumps(case).encode(), mtime=0))
        report["records"].append({"pair_id": package["pair_id"], "sample_id": "sample_fixture", "plan_index": 0,
                                  "artifact": str(case_path), "sha256": audit.digest(case_path)})
    write_json(previous / "report.json", report)
    return {"plan": plan_path, "cases": previous, "case": case_path, "source": path, "ir": ir,
            "original": original, "frozen": frozen, "labels": labels, "output": root / "audit"}


class SourceLocatorVoiceAuditTests(unittest.TestCase):
    def test_fresh_mapped_locator_includes_rests_in_note_ordinal(self):
        xml = mapped_xml('<note><rest/><duration>1</duration></note>' + pitched("n1", "<voice>1</voice>"))
        rows = audit.mapped_note_sources(xml, {"note_events": [note("n1")]}, ["n1"])
        self.assertEqual(rows["n1"]["source_xpath"], "/score-partwise/part[1]/measure[1]/note[2]")
        self.assertEqual(rows["n1"]["source_element_index"], 1)
        self.assertTrue(rows["n1"]["staff_defaulted_from_absence"])
        self.assertEqual(rows["n1"]["source_staff"], 1)

    def test_missing_voice_is_not_inherited_or_defaulted(self):
        xml = mapped_xml(pitched("n1", "<voice>1</voice>") + pitched("n2"))
        rows = audit.mapped_note_sources(xml, {"note_events": [note("n1"), note("n2")]}, ["n1", "n2"])
        self.assertIsNone(rows["n2"]["source_voice"])
        self.assertEqual(rows["n2"]["source_identity_status"], "missing_explicit_source_voice")

    def test_duplicate_empty_voice_and_invalid_staff_fail_closed(self):
        for extras in ("<voice/>", "<voice>1</voice><voice>2</voice>",
                       "<voice>   </voice>", "<voice>\n\t </voice>",
                       "<voice>1</voice><staff/>", "<voice>1</voice><staff>0</staff>",
                       "<voice>1</voice><staff>   </staff>",
                       "<voice>1</voice><staff>1</staff><staff>2</staff>"):
            with self.subTest(extras=extras):
                rows = audit.mapped_note_sources(mapped_xml(pitched("n1", extras)),
                                                {"note_events": [note("n1")]}, ["n1"])
                self.assertEqual(rows["n1"]["source_identity_status"], "unsupported_source_fields")

    def test_explicit_whitespace_voice_retains_presence_and_blocks_lane_identity(self):
        rows = audit.mapped_note_sources(mapped_xml(pitched("n1", "<voice>   </voice>")),
                                        {"note_events": [note("n1")]}, ["n1"])
        self.assertIsNone(rows["n1"]["source_voice"])
        self.assertEqual(rows["n1"]["source_voice_element_count"], 1)
        self.assertEqual(rows["n1"]["source_field_blockers"], ["empty_explicit_source_voice"])
        lanes = audit.lane_inventory([note("n1")], rows)
        self.assertEqual(lanes["counts"]["no_explicit_source_lane"], 1)
        self.assertEqual(lanes["counts"]["unsupported_source_field_lanes"], 1)

    def test_explicit_whitespace_staff_is_not_absent_default_one(self):
        rows = audit.mapped_note_sources(mapped_xml(pitched("n1", "<voice>1</voice><staff> \n\t </staff>")),
                                        {"note_events": [note("n1")]}, ["n1"])
        self.assertIsNone(rows["n1"]["source_staff"])
        self.assertEqual(rows["n1"]["source_staff_element_count"], 1)
        self.assertFalse(rows["n1"]["staff_defaulted_from_absence"])
        self.assertEqual(rows["n1"]["source_field_blockers"], ["empty_or_invalid_explicit_source_staff"])

    def test_whitespace_source_or_target_endpoint_and_temporal_path_fail_closed(self):
        for malformed in ("<voice>   </voice>", "<voice>1</voice><staff>   </staff>"):
            for endpoint in ("na", "nb"):
                with self.subTest(malformed=malformed, endpoint=endpoint):
                    xml = mapped_xml("".join(pitched(nid, malformed if nid == endpoint else "<voice>1</voice>")
                                             for nid in ("na", "nb")))
                    rows = audit.mapped_note_sources(xml, {"note_events": [note("na"), note("nb")]},
                                                    ["na", "nb"])
                    sounds = {"a": {"source_note_ids": ["na"]}, "b": {"source_note_ids": ["nb"]}}
                    direct = audit.classify_link(["a", "b"], sounds, rows)
                    self.assertEqual(direct["status"], "unsupported_source_fields")
                    self.assertFalse(direct["contrapuntal_identity_certified"])
                    path = {"relation": "role", "source_ref": "a", "target_ref": "b",
                            "carried_event_refs": ["a"], "links": [["a", "b"]]}
                    temporal = audit.classify_temporal_path(path, sounds, rows)
                    self.assertEqual(temporal["source_lane_statuses"], ["unsupported_source_fields"])

    def test_raw_staff_lexeme_is_preserved_and_number_normalized(self):
        rows = audit.mapped_note_sources(mapped_xml(pitched("n1", "<voice>1</voice><staff>+01</staff>")),
                                        {"note_events": [note("n1")]}, ["n1"])
        self.assertEqual(rows["n1"]["source_staff_raw"], "+01")
        self.assertEqual(rows["n1"]["source_staff"], 1)

    def test_original_unmatched_ids_do_not_masquerade_as_mapping(self):
        rows = audit.mapped_note_sources(mapped_xml(pitched("n1", "<voice>1</voice>")),
                                        {"note_events": [note("n1")]}, [])
        self.assertEqual(rows, {})

    def test_duplicate_eligible_source_id_and_unknown_mapper_id_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate_mapped_source_note_id"):
            audit.mapped_note_sources(mapped_xml(pitched("n1") + pitched("n1")),
                                     {"note_events": [note("n1")]}, ["n1"])
        with self.assertRaisesRegex(ValueError, "unknown_matched_note_id"):
            audit.mapped_note_sources(mapped_xml(pitched("n1")), {"note_events": [note("n1")]}, ["wrong"])

    def test_matched_coverage_and_nonpitched_ids_rejected(self):
        with self.assertRaisesRegex(ValueError, "matched_source_note_coverage_mismatch"):
            audit.mapped_note_sources(mapped_xml(""), {"note_events": [note("n1")]}, ["n1"])
        with self.assertRaisesRegex(ValueError, "mapped_id_not_single_pitched_note"):
            audit.mapped_note_sources(mapped_xml('<note id="n1"><rest/></note>'),
                                     {"note_events": [note("n1")]}, ["n1"])

    def test_duplicate_source_part_ids_are_not_identity_certified(self):
        xml = '<score-partwise><part id="P1"><measure>' + pitched("n1", "<voice>1</voice>") + '</measure></part>'
        xml += '<part id="P1"><measure>' + pitched("n2", "<voice>1</voice>") + '</measure></part></score-partwise>'
        rows = audit.mapped_note_sources(xml, {"note_events": [note("n1"), note("n2")]}, ["n1", "n2"])
        self.assertTrue(all(r["source_identity_status"] == "unsupported_source_fields" for r in rows.values()))

    def test_lane_mixture_and_unmapped_exclusions_are_distinct(self):
        notes = [note("a"), note("b"), note("unmapped"), note("unknown", voice="other")]
        sources = {"a": source("a"), "b": source("b", voice="2"),
                   "unknown": source("unknown", voice=None, status="missing_explicit_source_voice")}
        result = audit.lane_inventory(notes, sources)
        self.assertEqual(result["counts"]["multiple_explicit_source_lanes"], 1)
        self.assertEqual(result["counts"]["missing_source_voice_lanes"], 1)
        self.assertEqual(result["counts"]["unmapped_notes"], 1)
        mixed = next(r for r in result["lanes"] if r["mixed_explicit_source_lane"])
        self.assertEqual(mixed["unmapped_note_ids"], ["unmapped"])
        self.assertFalse(mixed["contrapuntal_identity_certified"])

    def test_single_lane_can_cross_staff_without_changing_source_voice(self):
        result = audit.lane_inventory([note("a"), note("b")],
                                     {"a": source("a"), "b": source("b", staff=2)})
        self.assertEqual(result["explicit_source_lane_cardinality_counts"], {"1": 1})
        self.assertEqual(result["staff_cardinality_counts"], {"2": 1})

    def test_link_identity_uses_part_and_voice_not_staff(self):
        sounds = {"a": {"source_note_ids": ["na"]}, "b": {"source_note_ids": ["nb"]}}
        raw = {"na": source("na"), "nb": source("nb", staff=2)}
        self.assertEqual(audit.classify_link(["a", "b"], sounds, raw)["status"], audit.SAME)
        raw["nb"] = source("nb", part="P2")
        self.assertEqual(audit.classify_link(["a", "b"], sounds, raw)["status"], "different_explicit_source_lane")
        self.assertFalse(audit.classify_link(["a", "b"], sounds, raw)["contrapuntal_identity_certified"])

    def test_link_missing_unmapped_and_ambiguous_tie_provenance_are_preserved(self):
        sounds = {"a": {"source_note_ids": ["na"]}, "b": {"source_note_ids": ["nb", "nc"]}}
        raw = {"na": source("na"), "nb": source("nb"), "nc": source("nc", voice="2")}
        self.assertEqual(audit.classify_link(["a", "b"], sounds, raw)["status"], "ambiguous_sound_source_voice")
        del raw["nc"]
        self.assertEqual(audit.classify_link(["a", "b"], sounds, raw)["status"], "unmapped_source_note")
        raw["nc"] = source("nc", voice=None, status="missing_explicit_source_voice")
        self.assertEqual(audit.classify_link(["a", "b"], sounds, raw)["status"], "missing_explicit_source_voice")
        self.assertEqual(audit.classify_link(["a", "missing"], sounds, raw)["status"], "unknown_sounding_event")

    def test_temporal_carry_links_are_included_and_original_not_mutated(self):
        path = {"relation": "role", "source_ref": "a", "target_ref": "c",
                "carried_event_refs": ["a", "b"], "links": [["a", "b"], ["b", "c"]]}
        sounds = {s: {"source_note_ids": [s]} for s in "abc"}
        raw = {s: source(s) for s in "abc"}
        before = deepcopy(path)
        result = audit.classify_temporal_path(path, sounds, raw)
        self.assertEqual(len(result["link_audits"]), 2)
        self.assertEqual(result["source_lane_statuses"], [audit.SAME])
        self.assertEqual(path, before)
        raw["b"]["source_voice"] = "2"
        self.assertEqual(audit.classify_temporal_path(path, sounds, raw)["source_lane_statuses"],
                         ["different_explicit_source_lane"])

    def test_temporal_saved_chain_mismatch_not_silently_repaired(self):
        path = {"relation": "role", "source_ref": "a", "target_ref": "c",
                "carried_event_refs": ["a", "b"], "links": [["a", "c"]]}
        with self.assertRaisesRegex(ValueError, "saved_temporal_link_chain_mismatch"):
            audit.classify_temporal_path(path, {}, {})

    def test_policy_is_preserved_and_protected_split_or_implicit_rights_rejected(self):
        for split in ("train", "dev"):
            value = {"split": split, "rights": {"internal_research_use": True},
                     "work_family_id": "family", "score_sha256": "hash"}
            before = deepcopy(value)
            audit.validate_policy(value)
            self.assertEqual(value, before)
        for split in ("blind", "holdout", "test", None):
            with self.assertRaisesRegex(ValueError, "protected_or_unassigned_split"):
                audit.validate_policy({"split": split})
        for approval in (False, None, 1, "true"):
            with self.assertRaisesRegex(ValueError, "internal_research_not_approved"):
                audit.validate_policy({"split": "train", "rights": {"internal_research_use": approval}})

    def test_disk_run_preserves_inputs_and_reports_mixture_and_both_witness_types(self):
        with TemporaryDirectory() as tmp:
            data = fixture(Path(tmp))
            before = {key: data[key].read_bytes() for key in ("plan", "case", "source", "original", "frozen", "labels")}
            result = audit.run(data["plan"], data["cases"], data["output"])
            self.assertTrue(result["complete"])
            summary = result["summary"]
            self.assertEqual(summary["mapping"]["matched"], 4)
            self.assertEqual(summary["global_logical_lanes"]["multiple_explicit_source_lanes"], 1)
            self.assertEqual(summary["context_counts"]["mixed_contexts"], 1)
            self.assertEqual(summary["positive_witnesses"]["direct"]["records"],
                             {"different_explicit_source_lane": 1, audit.SAME: 1})
            self.assertEqual(summary["positive_witnesses"]["temporal"]["links"],
                             {"different_explicit_source_lane": 1})
            for flag in ("source_labels_used", "accuracy_measured", "core_modified", "production_modified",
                         "engine_recomputed", "gate_changed", "split_rights_changed", "gold_promoted",
                         "training_promoted", "external_transmission", "source_contrapuntal_identity_certified"):
                self.assertIs(result[flag], False)
            for path, sha in result["artifact_hashes"].items():
                self.assertEqual(audit.digest(path), sha)
            for key, payload in before.items():
                self.assertEqual(data[key].read_bytes(), payload)
            artifact = result["records"][0]["artifact"]
            package = json.loads(gzip.decompress(Path(artifact).read_bytes()))
            self.assertEqual(package["manifest_entry"]["rights"]["model_training_approved"], False)
            self.assertEqual(package["manifest_entry"]["split"], "train")

    def test_empty_supported_cases_do_not_fabricate_witnesses(self):
        with TemporaryDirectory() as tmp:
            data = fixture(Path(tmp), with_case=False)
            result = audit.run(data["plan"], data["cases"], data["output"])
            self.assertEqual(result["summary"]["case_samples"], 0)
            self.assertEqual(result["summary"]["positive_witnesses"]["direct"]["records"], {})

    def test_existing_output_refused_before_missing_input_reads(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            marker = root / "keep.txt"
            marker.write_bytes(b"keep")
            with self.assertRaisesRegex(ValueError, "output_exists_no_overwrite"):
                audit.run(root / "missing", root / "missing", root)
            self.assertEqual(marker.read_bytes(), b"keep")

    def test_source_and_case_hash_mismatches_block_before_output(self):
        for field in ("source", "case"):
            with TemporaryDirectory() as tmp:
                data = fixture(Path(tmp))
                data[field].write_bytes(data[field].read_bytes() + b"changed")
                with self.subTest(field=field), self.assertRaisesRegex(ValueError, "input_hash_mismatch"):
                    audit.run(data["plan"], data["cases"], data["output"])
                self.assertFalse(data["output"].exists())

    def test_case_context_event_mismatch_detected(self):
        with TemporaryDirectory() as tmp:
            data = fixture(Path(tmp))
            case = json.loads(gzip.decompress(data["case"].read_bytes()))
            case["group_contexts"][0]["note_events"][0]["voice_id"] = "changed"
            data["case"].write_bytes(gzip.compress(json.dumps(case).encode(), mtime=0))
            report = read_json(data["cases"] / "report.json")
            report["records"][0]["sha256"] = audit.digest(data["case"])
            write_json(data["cases"] / "report.json", report)
            with self.assertRaisesRegex(ValueError, "parent_context_note_identity_mismatch"):
                audit.run(data["plan"], data["cases"], data["output"])

    def test_changed_input_during_mapping_cannot_certify_complete(self):
        with TemporaryDirectory() as tmp:
            data = fixture(Path(tmp))
            original_mapper = audit.musicxml_with_canonical_ids

            def mutating_source(path, ir):
                result = original_mapper(path, ir)
                data["source"].write_bytes(data["source"].read_bytes() + b"<!-- changed -->")
                return result

            with patch.object(audit, "musicxml_with_canonical_ids", side_effect=mutating_source):
                result = audit.run(data["plan"], data["cases"], data["output"])
            self.assertFalse(result["complete"])
            self.assertFalse(result["input_hashes_unchanged"])
            self.assertEqual(result["changed_inputs"], [str(data["source"].resolve())])

    def test_code_file_list_changes_are_guarded_without_editing_workspace(self):
        with TemporaryDirectory() as tmp:
            data = fixture(Path(tmp), with_case=False)
            with patch.object(audit, "_code_hashes", side_effect=[{"existing": "sha"}, {"existing": "sha", "new": "sha"}]):
                result = audit.run(data["plan"], data["cases"], data["output"])
            self.assertFalse(result["complete"])
            self.assertEqual(result["changed_code"], ["new"])

    def test_mapper_mutation_of_parent_memory_is_rejected(self):
        with TemporaryDirectory() as tmp:
            data = fixture(Path(tmp), with_case=False)
            original_mapper = audit.musicxml_with_canonical_ids

            def mutating_mapper(path, ir):
                result = original_mapper(path, ir)
                ir["voices"][0]["source_voice_number"] = "changed"
                return result

            with patch.object(audit, "musicxml_with_canonical_ids", side_effect=mutating_mapper):
                with self.assertRaisesRegex(ValueError, "mapper_mutated_parent_ir"):
                    audit.run(data["plan"], data["cases"], data["output"])


if __name__ == "__main__":
    unittest.main()
