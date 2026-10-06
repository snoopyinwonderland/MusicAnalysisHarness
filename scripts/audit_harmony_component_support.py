"""Post-seal replay: references, source clocks, old control, new costs/receipts."""
import argparse
from pathlib import Path
import json

from musicanote_harness import harmony_component_support_trial as trial
from musicanote_harness.harmony_common_benchmark import evaluate,native_prediction,native_reference,summarize
from musicanote_harness.harmony_source_clock import SourceClockGuard
from musicanote_harness.harmony_progression_search import _hash
from audit_harmony_temporal_scoring import compare_packet


def run(root):
    root=Path(root);dest=root/"post-seal-audit.json"
    if dest.exists():raise ValueError("output_exists_no_overwrite")
    report=trial.load(root/"report.json");freeze=trial.load(root/"prediction-freeze.json")
    pins=report["input_hashes"]|report["code_hashes"]|report["artifact_hashes"]
    def check():
        for p,h in pins.items():
            if trial.expanded.digest(p)!=h:raise ValueError("guard_changed:"+p)
    check()
    if freeze["labels_read"] is not False or freeze["contexts"]!=report["contexts"]:raise ValueError("seal_changed")
    source=Path(trial.load(root/"run-contract.json")["baseline_source"])
    prior={(r["pair_id"],r["sample_id"]):r for r in map(trial.load,trial.load(source/"prediction-freeze.json")["prediction_hashes"])}
    sealed={(r["pair_id"],r["sample_id"]):r for r in map(trial.load,freeze["prediction_hashes"])}
    tables={a:[] for a in trial.scoring.ARMS};cache={};edges=scores=bridges=missing=0
    for row in report["records"]:
        key=row["pair_id"],row["sample_id"];old=prior.pop(key);packet=sealed.pop(key)
        trial.prior.check_prediction(packet);compare_packet(packet,row)
        if row["sample_span"]!=old["sample_span"] or row["plan_index"]!=old["plan_index"]:raise ValueError("scope_changed")
        for a,result in row["arms"].items():
            value=evaluate(native_reference(row),native_prediction(result["selected_prediction"],row["sample_span"]),row["sample_span"],selected=result["selected_prediction"] is not None)
            if value!=result["evaluation"]:raise ValueError("evaluation_changed")
            tables[a].append(row|result)
        if not row["attempted"]:
            if any(r["selected_prediction"] is not None or r["status"]!=old["arms"]["bass_return"]["status"] for r in row["arms"].values()):raise ValueError("old_abstention_changed")
            continue
        if _hash(trial.prior.prior.musical_value(row["arms"]["control"]["selected_prediction"]))!=_hash(trial.prior.prior.musical_value(old["arms"]["bass_return"]["selected_prediction"])):raise ValueError("control_prediction_changed")
        if trial.expanded.digest(row["graph_artifact"])!=row["graph_sha256"]:raise ValueError("graph_changed")
        saved=trial.load(row["graph_artifact"]);graph=trial.prior.prior.graph_from_packet(saved["problem"])
        if _hash(trial.prior.prior.graph_packet(graph))!=_hash(saved["problem"]):raise ValueError("graph_codec_changed")
        edges+=len(graph.edges);pair=row["pair_id"]
        if pair not in cache:
            src=saved["source"];ir=trial.load(src["canonical_ir_path"])
            if _hash(ir)!=src["original_ir_content_sha256"]:raise ValueError("source_ir_changed")
            if trial.expanded.digest(src["source_musicxml_path"])!=src["original_musicxml_sha256"]:raise ValueError("source_xml_changed")
            view,grace=trial.prior.prior.bounded.grace_projection(ir);cache[pair]=ir,view,grace,SourceClockGuard(ir)
        ir,view,grace,clock=cache[pair];gate=clock.scope(row["sample_span"])
        if not gate["accepted"] or _hash(gate)!=_hash(row["source_clock_gate"]):raise ValueError("clock_gate_changed")
        ev,args=trial.prior.evidence_args(ir,view,grace,row["sample_span"],clock)
        for a,result in row["arms"].items():
            selected=result["selected_prediction"]
            if selected is None:continue
            if selected["confidence"] is not None or selected["human_validated"] is not False:raise ValueError("unsupported_confirmation")
            ids=trial.prior.prior.path_ids(selected)
            if trial.q(trial.scoring.score_path(graph,ev,ids,arm=a,**args))!=selected["score_cost"]:raise ValueError("winner_independent_cost_changed")
            receipt=trial.path_receipt(graph,ev,ids,args)
            actual=[d for r in receipt["run_evidence"] for d in r["observations"]]
            if _hash(actual)!=_hash(selected["component_support_observations"]):raise ValueError("component_receipt_changed")
            if a=="combined":
                bridges+=sum(d["kind"].startswith("held_member_cross_run") for d in actual)
                missing+=sum(bool(d.get("unobserved_members")) for d in actual if d["kind"]=="unobserved_defining_members")
            scores+=1
    if prior or sealed:raise ValueError("scope_denominator_changed")
    for a,rs in tables.items():
        if summarize(rs)!=report["tables"][a]:raise ValueError("metric_table_changed")
    for saved in report["cases"]:
        case=trial.load(saved["case_path"]);row=case["record"];graph=trial.prior.prior.graph_from_packet(trial.load(row["graph_artifact"])["problem"])
        ir,view,grace,clock=cache[row["pair_id"]];ev,args=trial.prior.evidence_args(ir,view,grace,row["sample_span"],clock)
        if case["human_validated"] or not case["reference_witness_never_used_for_inference"]:raise ValueError("case_confirmation_changed")
        for receipt in case["scored_selected_paths"].values():
            if _hash(trial.path_receipt(graph,ev,receipt["existing_path_ids"],args))!=_hash(receipt):raise ValueError("case_receipt_changed")
        if "reference_witness_scores" in case:
            witness=case["reference_witness_scores"];actual=trial.path_receipt(graph,ev,witness["existing_path_ids"],args)
            actual["source_labels_used_to_create_this_path"]=True
            if _hash(actual)!=_hash(witness):raise ValueError("posthoc_reference_changed")
    check()
    result={"passed":True,"unique_hashes_checked":len(pins),"scopes":len(report["records"]),"attempted_scopes":report["fresh_selected_scopes"],
        "full_source_packages":len(cache),"graph_edges_roundtripped":edges,"independent_winner_costs_checked":scores,
        "combined_held_step_receipts":bridges,"combined_runs_with_unobserved_defining_members":missing,
        "cases":len(report["cases"]),"metrics_replayed":list(tables),"report_sha256":trial.expanded.digest(root/"report.json"),
        "audit_code_sha256":trial.expanded.digest(__file__),"new_inference_or_training_performed":False}
    trial.expanded.write(dest,result);return result


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--root",required=True)
    args=parser.parse_args();print(json.dumps(run(args.root),ensure_ascii=False,indent=2),flush=True)
