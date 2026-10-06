from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from musicanote_harness import harmony_component_support_trial as trial
from musicanote_harness.harmony_source_clock import SourceClockGuard
from musicanote_harness.harmony_common_benchmark import evaluate, native_prediction, native_reference, summarize
from musicanote_harness.harmony_progression_search import _hash
from test_harmony_bounded_recovery import fixture, sample
from test_harmony_exact_frontier import problem


class ComponentSupportTrialTests(unittest.TestCase):
    def disk(self,mode):
        with TemporaryDirectory() as folder:
            root=Path(folder);source=root/"prior";source.mkdir();output=root/"new"
            ir=fixture();target=sample();graph,ev=problem(ir)
            irpath=source/"ir.json.gz";trial.expanded.write_packet(irpath,ir)
            xml=source/"source.musicxml";xml.write_bytes(b"<score-partwise version='4.0'/>")
            source_info={"canonical_ir_path":str(irpath),"source_musicxml_path":str(xml),
                "original_ir_content_sha256":_hash(ir),"original_musicxml_sha256":trial.expanded.digest(xml),
                "full_score_saved_with_surrounding_context":True}
            gp=source/"graph.json.gz";trial.expanded.write_packet(gp,{"pair_id":"pair","sample_id":target["sample_id"],
                "span":target["span"],"source":source_info,"problem":trial.prior.prior.graph_packet(graph),"receipts":{}})
            arms={a:{"status":"source_preflight_abstention","selected_prediction":None} if mode=="abstention" else
                {"status":(v:=trial.scoring.prior.decode(graph,ev,arm=a))["status"],"selected_prediction":v["selected"]}
                for a in ("bass_return",)}
            packet={"pair_id":"pair","sample_id":target["sample_id"],"sample_span":target["span"],"plan_index":0,
                "collection_id":"c","work_family_id":"family","reference_binding_verified":True,
                "attempted":mode!="abstention","known_prior_diagnostic":True,"source_clock_gate":SourceClockGuard(ir).scope(target["span"]),
                "arms":arms,"graph_artifact":str(gp),"graph_sha256":trial.expanded.digest(gp)}
            if mode=="contamination":packet["arms"]["bass_return"]["evaluation"]={}
            if mode=="graph":packet["graph_sha256"]="changed"
            if mode=="source":source_info["original_musicxml_sha256"]="changed";trial.expanded.write_packet(gp,
                {"pair_id":"pair","sample_id":target["sample_id"],"span":target["span"],"source":source_info,
                 "problem":trial.prior.prior.graph_packet(graph),"receipts":{}});packet["graph_sha256"]=trial.expanded.digest(gp)
            pred=source/"p.json.gz";trial.expanded.write_packet(pred,packet)
            pins={str(Path(trial.__file__).resolve()):"changed"} if mode=="code" else {}
            trial.expanded.write(source/"run-contract.json",{"code_pins":pins,"source_labels_used_at_inference":False})
            trial.expanded.write(source/"prediction-freeze.json",{"contexts":1,"labels_read":False,
                "prediction_hashes":{str(pred):trial.expanded.digest(pred)}})
            record=deepcopy(packet);record["reference_cells"]=[{"span":target["span"],"signature":[["C",0],[["C",0],["E",0],["G",0]]]}]
            record["candidate_ceiling"]={"oracle_reference_witness":None}
            for a,v in record["arms"].items():v["evaluation"]=evaluate(native_reference(record),native_prediction(v["selected_prediction"],target["span"]),target["span"],selected=v["selected_prediction"] is not None)
            tables={a:summarize([record|record["arms"][a]]) for a in record["arms"]}
            trial.expanded.write(source/"report.json",{"records":[record],"tables":tables,"input_hashes":{},"code_hashes":{},"artifact_hashes":{},"cases":[]})
            original=trial.load
            def read(p):
                if Path(p)==source/"report.json":
                    seal=original(output/"prediction-freeze.json");self.assertFalse(seal["labels_read"])
                    for path,sha in seal["prediction_hashes"].items():self.assertEqual(trial.expanded.digest(path),sha)
                return original(p)
            with patch.object(trial,"BASELINE_REPORT_SHA",trial.expanded.digest(source/"report.json")),patch.object(trial,"load",side_effect=read),\
                 patch.object(trial.prior.prior,"prepare",side_effect=AssertionError("graph_rebuild_forbidden")):
                if mode in ("contamination","graph","source","code"):
                    with self.assertRaisesRegex(ValueError,"changed|reference_bearing"):trial.run(source,output)
                    return
                result=trial.run(source,output);report=original(output/"report.json")
                self.assertEqual(result["contexts"],1);self.assertFalse(result["graph_generation_performed"])
                self.assertEqual(result["fresh_selected_scopes"],int(mode!="abstention"))
                self.assertEqual(report["tables"]["control"],tables["bass_return"])
                self.assertEqual(set(report["tables"]),set(trial.scoring.ARMS))
                self.assertFalse(result["new_rules_adopted_for_production"])
                if mode!="abstention":self.assertEqual(_hash(original(gp)["problem"]),_hash(trial.prior.prior.graph_packet(graph)))

    def test_scope_contract_synthetic_seal_and_no_rebuild(self):self.disk("selected")
    def test_abstention_without_graph_read_keeps_denominator(self):self.disk("abstention")
    def test_nested_reference_contamination_rejected(self):self.disk("contamination")
    def test_original_graph_sha_required(self):self.disk("graph")
    def test_full_source_sha_required(self):self.disk("source")
    def test_sealed_old_code_unchanged(self):self.disk("code")
    def test_recursive_reference_guard(self):
        with self.assertRaisesRegex(ValueError,"reference_bearing"):trial.prior.check_prediction({"a":[{"oracle_reference_witness":[]}]})
    def test_output_not_overwritten(self):
        with TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError,"output_exists"):trial.run("missing",folder)


if __name__=="__main__":unittest.main()
