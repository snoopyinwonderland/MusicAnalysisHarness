from copy import deepcopy
from fractions import Fraction
import gzip
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from musicanote_harness.harmony_candidate_recall import evaluate, paths_from_search, rational
from musicanote_harness.harmony_lattice_recall import cells_from_record, diagnose, run, union_time, validate_binding
from musicanote_harness.harmony_progression_search import _hash

C = (("C", 0), (("C", 0), ("E", 0), ("G", 0)))
D = (("D", 0), (("A", 0), ("D", 0), ("F", 0)))


def span(a, b):
    return {"start": rational(Fraction(a)), "end": rational(Fraction(b))}


def cell(a=0, b=2, sig=C):
    return {"start": Fraction(a), "end": Fraction(b), "signature": sig}


def fixture(points=(0, 1, 2), specs=((0, 2, C),), max_segments=6):
    points = list(map(Fraction, points)); groups, edges = [], []
    sample = {"sample_id": "sample", "span": span(points[0], points[-1])}
    for i, (a, b, sig) in enumerate(specs):
        root, members = sig
        reading = {"root_spelling": root, "members": members, "event_states": {},
                   "span": span(points[a], points[b]), "abstention_reasons": []}
        edge = {"from": a, "to": b, "span": reading["span"], "readings": [reading]}
        adapter = {"edge": i, "reading": 0}; edges.append(edge)
        groups.append({"group_id": "g"+str(i), "edge_index": i, "from": a, "to": b,
                       "span": reading["span"], "root_spelling": root, "members": members,
                       "event_states": {}, "candidate_blockers": [],
                       "origin_reading_keys": [deepcopy(adapter)], "adapter_reading_key": adapter})
    search = {"sample": sample, "selected": None, "source_labels_used": False,
              "status": "complete_path_proposals_not_verdict", "semantic_groups": groups,
              "budgets": {"max_segments": max_segments}, "unspelled_candidates": [], "proposals": [],
              "universe": {"stored_edges": len(edges), "stored_readings": len(edges), "semantic_groups": len(groups)}}
    bundle = {"sample": sample, "selected": None, "source_labels_used": False,
              "stages": {"lattice": {"status": "ready", "plan": {"points": [rational(x) for x in points]}, "edges": edges}}}
    return bundle, search, points


def prior(hit=False, selected=False):
    return {"candidate_hit": hit, "selected_hit": selected}


class LatticeRecallTests(unittest.TestCase):
    def test_retained_hit_has_witness(self):
        b, s, p = fixture()
        self.assertEqual(validate_binding(b, s, b["sample"]["span"]), p)
        d = diagnose(s, [cell()], p, prior(True, True))
        self.assertTrue(d["lattice_hit"]); self.assertEqual(d["outcome"], "selected_correct")
        self.assertEqual(d["minimum_segments"], 1)
        self.assertEqual(d["oracle_reference_witness"], ["g0"])
        self.assertFalse(d["witness_is_selected_prediction"])

    def test_selection_error_separate_from_retention(self):
        _, s, p = fixture()
        self.assertEqual(diagnose(s, [cell()], p, prior(True))["outcome"], "selection_error")

    def test_reference_present_before_retention(self):
        _, s, p = fixture()
        self.assertEqual(diagnose(s, [cell()], p, prior())["outcome"], "retention_or_search_budget_loss")

    def test_local_signature_missing(self):
        _, s, p = fixture(specs=((0, 2, D),))
        d = diagnose(s, [cell()], p, prior())
        self.assertEqual(d["outcome"], "local_spelled_signature_absent")
        self.assertEqual(d["local_signature_available_time"], rational(Fraction()))
        self.assertIsNone(d["oracle_reference_witness"])

    def test_gold_boundary_not_in_native_grid(self):
        _, s, p = fixture((0, 2), ((0, 1, C), (0, 1, D)))
        d = diagnose(s, [cell(0, 1), cell(1, 2, D)], p, prior())
        self.assertEqual(d["outcome"], "semantic_change_point_absent")
        self.assertEqual(d["missing_semantic_change_points"], [rational(Fraction(1))])
        self.assertEqual(d["local_signature_available_time"], rational(Fraction(2)))

    def test_same_signature_annotation_cut_not_required(self):
        _, s, p = fixture((0, 2), ((0, 1, C),))
        d = diagnose(s, [cell(0, 1), cell(1, 2)], p, prior())
        self.assertTrue(d["lattice_hit"])
        self.assertEqual(d["missing_semantic_change_points"], [])

    def test_local_coverage_does_not_prove_connected_partition(self):
        _, s, p = fixture((0, 1, 2, 3), ((0, 2, C), (1, 3, C)))
        d = diagnose(s, [cell(0, 3)], p, prior())
        self.assertEqual(d["local_signature_available_time"], rational(Fraction(3)))
        self.assertEqual(d["outcome"], "no_consistent_reference_partition")

    def test_segment_cap_separate_from_vocabulary_and_retention(self):
        _, s, p = fixture(specs=((0, 1, C), (1, 2, D)), max_segments=1)
        d = diagnose(s, [cell(0, 1), cell(1, 2, D)], p, prior())
        self.assertEqual(d["minimum_segments"], 2)
        self.assertTrue(d["unlimited_lattice_hit"]); self.assertFalse(d["lattice_hit"])
        self.assertEqual(d["outcome"], "segment_budget_loss")

    def test_enharmonic_not_equal(self):
        enharmonic = (("C", 0), (("C", 0), ("F", -1), ("G", 0)))
        _, s, p = fixture(specs=((0, 2, enharmonic),))
        self.assertFalse(diagnose(s, [cell()], p, prior())["lattice_hit"])

    def test_unknown_root_not_invented(self):
        _, s, p = fixture(specs=((0, 2, (None, C[1])),))
        self.assertFalse(diagnose(s, [cell()], p, prior())["lattice_hit"])

    def test_blocked_witness_is_not_a_validated_music_claim(self):
        _, s, p = fixture(); s["semantic_groups"][0]["candidate_blockers"] = ["unconfirmed_role"]
        d = diagnose(s, [cell()], p, prior())
        self.assertTrue(d["lattice_hit"])
        self.assertTrue(d["group_blockers_not_overridden_or_musically_validated"])

    def test_partial_reference_not_false_or_oracle_completion(self):
        _, s, p = fixture()
        self.assertEqual(diagnose(s, [cell(sig=None)], p, prior())["lattice_hit"], None)

    def test_unavailable_lattice_remains_unknown(self):
        _, s, _ = fixture(); s["lattice_status"] = "baseline_not_ready"
        self.assertEqual(diagnose(s, [cell()], None, prior()),
                         {"outcome": "lattice_unavailable", "lattice_hit": None, "lattice_status": "baseline_not_ready"})

    def test_lost_native_reading_detected(self):
        b, s, _ = fixture(); s["semantic_groups"] = []
        with self.assertRaisesRegex(ValueError, "inventory"):
            validate_binding(b, s, b["sample"]["span"])

    def test_changed_native_meaning_detected(self):
        b, s, _ = fixture(); s["semantic_groups"][0]["root_spelling"] = ("D", 0)
        with self.assertRaisesRegex(ValueError, "meaning"):
            validate_binding(b, s, b["sample"]["span"])

    def test_minimum_witness_deterministic_and_nonmutating(self):
        _, s, p = fixture(specs=((0, 1, C), (1, 2, C), (0, 2, C)))
        before = deepcopy(s); d = diagnose(s, [cell()], p, prior())
        self.assertEqual(d["oracle_reference_witness"], ["g2"])
        self.assertEqual(s, before)
        s["semantic_groups"].reverse()
        self.assertEqual(diagnose(s, [cell()], p, prior()), d)

    def test_union_time_is_exact(self):
        self.assertEqual(union_time([(Fraction(0),Fraction(1,3)),(Fraction(1,6),Fraction(2,3))]), Fraction(2,3))

    def test_retained_hit_inconsistent_with_lattice_rejected(self):
        _, s, p = fixture(specs=((0, 2, D),))
        with self.assertRaisesRegex(ValueError, "witness"):
            diagnose(s, [cell()], p, prior(True))

    def test_reference_partition_validated(self):
        record = {"sample_span": span(0,2), "reference_cells": [{"span": span(1,2), "signature": C}]}
        with self.assertRaisesRegex(ValueError, "partition"):
            cells_from_record(record)

    def test_physical_frozen_runner_no_inference_or_overwrite(self):
        with TemporaryDirectory() as tmp:
            folder=Path(tmp); previous=folder/'previous'; previous.mkdir()
            digest=lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
            entry={"score_sha256":"synthetic-score", "work_family_id":"family", "split":"dev",
                   "rights":{"internal_research_use":True}}
            bundle, search, _=fixture()
            search["input_bundle_content_sha256"]=_hash(bundle)
            search["proposals"]=[{"proposal_id":"p0","complete_context_path":True,
                "semantic_group_refs":["g0"],"path":[{"edge":0,"reading":0}],"objective":{
                    "total_note_time":rational(Fraction(2)),"raw_nonmember_note_time":rational(Fraction()),
                    "blocked_note_time":rational(Fraction()),"spelling_unresolved_note_time":rational(Fraction()),"segment_count":1}}]
            context=folder/'context.json.gz'
            provenance={"manifest_entry":entry}
            context.write_bytes(gzip.compress(json.dumps({"pair_id":"pair","plan_index":0,
                "bundle":bundle,"provenance":provenance}).encode()))
            packet=folder/'search.json.gz'
            packet.write_bytes(gzip.compress(json.dumps({"pair_id":"pair","plan_index":0,"sample":bundle["sample"],
                "provenance":provenance,"source_labels_used":False,"search":search,
                "previous_context_artifact":str(context),"previous_context_sha256":digest(context),
                "input_bundle_content_sha256":_hash(bundle)}).encode()))
            evaluation=evaluate(paths_from_search(search,span(0,2)),[cell()])
            code=Path(__file__).resolve().parents[1]/'src/musicanote_harness/harmony_candidate_recall.py'
            row={"pair_id":"pair","plan_index":0,"sample_id":"sample","sample_span":span(0,2),
                 "work_family_id":"family","split":"dev","artifact":str(packet),"artifact_sha256":digest(packet),
                 "evaluation":evaluation,"reference_cells":[{"span":span(0,2),"signature":C}]}
            report=previous/'report.json'
            report.write_text(json.dumps({"complete":True,"source_labels_used_for_selection":False,
                "training_performed":False,"blind_test_accuracy_measured":False,"code_sha256":digest(code),
                "input_hashes":{str(packet):digest(packet)},"package_manifest":[entry],"records":[row],
                "summary":{"contexts":1,"packages":1,"work_families":1,"fully_evaluable_contexts":1,"recall_at_24":1}}))
            result=run(previous,folder/'out',digest(report))
            self.assertEqual(result["summary"]["lattice_hit_contexts"],1)
            self.assertFalse(result["reference_witnesses_are_inference"])
            self.assertFalse(result["candidate_inventory_or_search_modified"])
            with self.assertRaisesRegex(ValueError,"overwrite"):
                run(previous,folder/'out',digest(report))
            packet.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,"frozen_input_changed"):
                run(previous,folder/'new',digest(report))


if __name__ == "__main__":
    unittest.main()
