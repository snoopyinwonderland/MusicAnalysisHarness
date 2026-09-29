import unittest
from copy import deepcopy

from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_episodes import extract_episode, compare_episodes, categorize, judge_episode, reference_arrival


def score(transpose=0, target=(55, 59, 62), spread=False):
    sounds = []
    for bar, pitches in enumerate(((48, 51, 55), (54, 57, 60, 63), target, target)):
        for i, pitch in enumerate(pitches):
            onset = bar*4 + (i/2 if spread and bar == 1 else 0)
            sounds.append({"sounding_event_id": f"s{bar}_{i}", "pitch": {
                "midi_pitch": pitch+transpose, "spelling": str(pitch+transpose)},
                "span": {"start": q(onset), "end": q(bar*4+4)}})
    return {"sounding_events": sounds, "measures": [
        {"global_start_quarter": q(i*4), "actual_duration_quarter": q(4)} for i in range(4)]}


class EpisodeTests(unittest.TestCase):
    def test_source_arrival_and_key_change_remain_distinct(self):
        def ann(label, numeral, key="i"):
            return {"raw_label": label, "components": {"numeral": numeral, "globalkey": "c", "localkey": key}}
        source = ann("viio7/V", "vii")
        self.assertEqual(reference_arrival(source, [ann("V", "V")]), "next_annotated_target")
        self.assertEqual(reference_arrival(source, [ann("i64", "i"), ann("V", "V")]), "delayed_annotated_target")
        self.assertEqual(reference_arrival(source, [ann("I", "I", "V")]), "key_context_changed")

    def test_transposition_preserves_context_comparison(self):
        a = extract_episode(score(), {"start": q(4), "end": q(8)})
        b = extract_episode(score(5), {"start": q(4), "end": q(8)})
        self.assertEqual(compare_episodes(a, b)["score"], 1)
        self.assertEqual(a["context_span"], {"start": q(0), "end": q(16)})

    def test_same_chord_different_resolution_is_distinguished(self):
        a = extract_episode(score(), {"start": q(4), "end": q(8)})
        b = extract_episode(score(target=(48, 52, 55)), {"start": q(4), "end": q(8)})
        result = compare_episodes(a, b)
        self.assertEqual(result["channels"]["current.pitch_profile"], 1)
        self.assertLess(result["channels"]["after_0.pitch_profile"], .9)

    def test_arpeggiation_retains_harmonic_similarity(self):
        a = extract_episode(score(), {"start": q(4), "end": q(8)})
        b = extract_episode(score(spread=True), {"start": q(4), "end": q(8)})
        self.assertNotEqual(a["windows"]["current"]["texture"], b["windows"]["current"]["texture"])
        self.assertGreater(compare_episodes(a, b)["channels"]["current.pitch_profile"], .95)

    def test_dcml_quality_is_not_lost(self):
        c = categorize({"raw_label": "viio7/V", "components": {"numeral": "vii", "figbass": "7"},
                        "raw_fields": {"form": "o", "relativeroot": "V"}})
        self.assertEqual(c["quality"], "o")
        self.assertEqual(c["target"], "V")

    def test_deduplication_and_split_exclusion(self):
        ep = extract_episode(score(), {"start": q(4), "end": q(8)})
        refs = [{"case_id": str(i), "episode": ep, "category": {"family": "applied"},
                 "identity": {"work_family_id": "w1", "annotation_lineage_id": "l1", "split": "train"}} for i in range(5)]
        held = deepcopy(refs[0]); held["identity"] = {"work_family_id": "w2", "annotation_lineage_id": "l2", "split": "holdout"}
        result = judge_episode(ep, refs+[held], {"work_family_id": "query", "annotation_lineage_id": "query"})
        self.assertEqual(result["alternatives"][0]["independent_works"], 1)
        self.assertEqual(result["status"], "ambiguous")
        self.assertFalse(judge_episode(ep, refs, {"work_family_id": "w1", "annotation_lineage_id": "query"})["alternatives"])


if __name__ == "__main__":
    unittest.main()
