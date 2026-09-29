import unittest

from musicanote_harness.harmony_case_retrieval import build_case_records, compare_features, extract_case_feature, retrieve_cases


def rational(value):
    return {"numerator": value, "denominator": 1}


def package(score_id, pitches, label="I", transpose=0):
    sounds = []
    for index, pitch in enumerate(pitches):
        sounds.append({
            "sounding_event_id": f"{score_id}-sound-{index}",
            "source_note_ids": [f"{score_id}-note-{index}"],
            "pitch": {"midi_pitch": pitch + transpose, "spelling": f"p{pitch + transpose}"},
            "span": {"start": rational(0), "end": rational(4)},
        })
    ir = {"score": {"score_id": score_id}, "ir_document_id": f"ir-{score_id}", "sounding_events": sounds}
    annotation = {
        "annotation_id": f"ann-{score_id}", "raw_label": label, "components": {"chord": label, "key": "C"},
        "target": {"span": {"start": rational(0), "end": rational(4)}},
        "source_asset_sha256": "a" * 64, "source_locator": {"path": f"{score_id}.rntxt", "line": 1},
        "author_origin": "human", "source_review_status": "source_status_unknown",
    }
    return {
        "ir": ir, "annotations": [annotation],
        "alignments": [{"annotation_id": annotation["annotation_id"], "mapping_status": "exact"}],
        "source_evidence": {"records": [{"annotation_id": annotation["annotation_id"], "support_band": "strong_support", "status": "scored"}]},
        "report": {"source_sha256": {"score": "b" * 64}},
    }


class HarmonyCaseRetrievalTest(unittest.TestCase):
    def test_nct_geometry_records_shape_without_assigning_label(self):
        notes = []
        sounds = []
        for index, pitch in enumerate((60, 62, 60)):
            notes.append({"note_id": f"n{index}", "voice_id": "v1"})
            sounds.append({"sounding_event_id": f"s{index}", "attack_note_id": f"n{index}",
                           "pitch": {"midi_pitch": pitch, "spelling": str(pitch)},
                           "span": {"start": rational(index), "end": rational(index + 1)}})
        ir = {"score": {"score_id": "s"}, "ir_document_id": "ir", "measures": [],
              "note_events": notes, "sounding_events": sounds}
        feature = extract_case_feature(ir, {"start": rational(0), "end": rational(3)})
        self.assertEqual(feature["nct_geometry"]["counts"]["step_away_and_return"], 1)
        self.assertIn("no NCT type", feature["nct_geometry"]["interpretation"])

    def test_transposed_sonority_has_identical_relative_feature(self):
        left = build_case_records(package("left", [48, 52, 55]))[0]
        right = build_case_records(package("right", [48, 52, 55], transpose=5))[0]
        result = compare_features(left["feature"], right["feature"])
        self.assertEqual(result["channels"]["current_interval_profile"], 1.0)
        self.assertEqual(result["similarity"], 1.0)

    def test_query_excludes_same_score_and_keeps_competing_labels(self):
        query = package("query", [48, 52, 55])
        same = build_case_records(query)[0]
        tonic = build_case_records(package("tonic", [50, 54, 57], "I"))[0]
        dominant = build_case_records(package("dominant", [55, 59, 62], "V"))[0]
        result = retrieve_cases(query["ir"], {"start": rational(0), "end": rational(4)}, [same, tonic, dominant])
        self.assertEqual({row["score_id"] for row in result["matches"]}, {"tonic", "dominant"})
        self.assertEqual({row["label"] for row in result["label_alternatives"]}, {"I", "V"})
        self.assertTrue(result["policy"]["labels_hidden_from_query_features"])
        self.assertTrue(result["query"]["query_id"].startswith("hquery_"))
        self.assertIn("no label is copied", result["interpretation"])

    def test_different_quality_reports_a_profile_difference(self):
        major = build_case_records(package("major", [48, 52, 55]))[0]
        minor = build_case_records(package("minor", [48, 51, 55], "i"))[0]
        result = compare_features(major["feature"], minor["feature"])
        self.assertLess(result["similarity"], 1.0)
        self.assertIn("current_interval_profile", result["difference_reasons"])

    def test_one_score_cannot_flood_the_result(self):
        query = package("query", [48, 52, 55])
        repeated = build_case_records(package("candidate", [50, 54, 57]))[0]
        copies = [{**repeated, "case_id": f"copy-{index}", "annotation_id": f"ann-{index}"} for index in range(6)]
        result = retrieve_cases(query["ir"], {"start": rational(0), "end": rational(4)}, copies, limit=12)
        self.assertEqual(len(result["matches"]), 2)
        self.assertEqual(result["policy"]["per_score_result_limit"], 2)

    def test_query_excludes_same_work_family_and_annotation_lineage(self):
        query = package("query", [48, 52, 55])
        same_work = build_case_records(package("movement-two", [48, 52, 55], "I"))[0]
        same_lineage = build_case_records(package("other-score", [48, 52, 55], "V"))[0]
        allowed = build_case_records(package("independent", [48, 52, 55], "ii"))[0]
        same_work["dataset_identity"]["work_family_id"] = "family-a"
        same_lineage["dataset_identity"]["annotation_lineage_id"] = "lineage-a"
        result = retrieve_cases(
            query["ir"], {"start": rational(0), "end": rational(4)},
            [same_work, same_lineage, allowed],
            query_dataset_identity={"work_family_id": "family-a", "annotation_lineage_id": "lineage-a"},
        )
        self.assertEqual([row["score_id"] for row in result["matches"]], ["independent"])
        self.assertTrue(result["policy"]["same_work_family_excluded"])

    def test_holdout_query_retrieves_train_cases_only(self):
        query = package("query", [48, 52, 55])
        train = build_case_records(package("train-score", [48, 52, 55], "I"))[0]
        holdout = build_case_records(package("holdout-score", [48, 52, 55], "V"))[0]
        train["dataset_identity"]["split"] = "train"
        holdout["dataset_identity"]["split"] = "holdout"
        result = retrieve_cases(
            query["ir"], {"start": rational(0), "end": rational(4)}, [train, holdout],
            query_dataset_identity={"work_family_id": "query-family", "annotation_lineage_id": "query-lineage", "split": "holdout"},
        )
        self.assertEqual([row["score_id"] for row in result["matches"]], ["train-score"])
        self.assertEqual(result["policy"]["allowed_candidate_splits"], ["train"])


if __name__ == "__main__":
    unittest.main()
