"""Same sealed 72 scopes, four component-support arms, labels opened last."""
import argparse
from collections import Counter
from copy import deepcopy
from pathlib import Path
from time import perf_counter
import json

from . import harmony_component_support_scoring as scoring
from . import harmony_root_context_trial as prior
from .harmony_source_clock import SourceClockGuard
from .harmony_common_benchmark import evaluate,native_prediction,native_reference,summarize
from .harmony_progression_search import _hash
from .harmony_candidate_recall import fraction as f,rational as q

VERSION="harmony-component-support-trial-0.1.0"
BASELINE_REPORT_SHA="94087347afb5f40b01e64574e77876ff1a047e1849fb15ff97472c88ff36109c"
load=prior.load
expanded=prior.expanded


def path_receipt(graph,ev,ids,args):
    by_id={e.group_id:e for e in graph.edges};runs=[]
    for ident in ids:
        e=by_id[ident]
        if runs and runs[-1][2]==e.signature:runs[-1]=runs[-1][0],e.end,e.signature
        else:runs.append((e.start,e.end,e.signature))
    context=scoring.ComponentContext(ev,**args)
    return {"existing_path_ids":ids,"raw_edges":len(ids),"harmonic_runs":len(runs),
        "costs":{a:q(scoring.score_path(graph,ev,ids,arm=a,**args)) for a in scoring.ARMS},
        "run_evidence":[{"span":{"start":q(a),"end":q(b)},"signature":sig,
            "features":{k:None if v is None else q(v) for k,v in scoring.features(graph,ev.source,context,a,b,sig)[0].items()},
            "observations":scoring.features(graph,ev.source,context,a,b,sig)[1]} for a,b,sig in runs],
        "source_labels_used_to_create_this_path":False}


def run(source,output):
    source,output=Path(source),Path(output)
    if output.exists():raise ValueError("output_exists_no_overwrite")
    started=perf_counter();guards={};artifacts={}
    def read(p,expected=None):
        p=Path(p);sha=expanded.digest(p)
        if expected is not None and sha!=expected:raise ValueError("pinned_input_changed:"+str(p))
        name=str(p.resolve())
        if name in guards and guards[name]!=sha:raise ValueError("input_changed_during_read")
        guards[name]=sha;return load(p)
    contract=read(source/"run-contract.json");freeze=read(source/"prediction-freeze.json")
    if freeze["labels_read"] is not False or contract["source_labels_used_at_inference"] is not False:raise ValueError("unsealed_baseline")
    for p,h in contract["code_pins"].items():
        if expanded.digest(p)!=h:raise ValueError("baseline_engine_changed:"+p)
        guards[p]=h
    packets=[read(p,h) for p,h in sorted(freeze["prediction_hashes"].items())]
    keys={(r["pair_id"],r["sample_id"]) for r in packets}
    if len(keys)!=freeze["contexts"] or len(packets)!=len(keys):raise ValueError("scope_denominator_changed")
    for packet in packets:prior.check_prediction(packet)
    code={str(p.resolve()):expanded.digest(p) for p in Path(__file__).parent.glob("*.py")}
    for p in (Path("tests/test_harmony_component_support_scoring.py"),Path("tests/test_harmony_component_support_trial.py"),
              Path("scripts/audit_harmony_component_support.py"),Path("tests/test_audit_harmony_component_support.py")):
        if p.exists():code[str(p.resolve())]=expanded.digest(p)
    output.mkdir(parents=True);(output/"predictions").mkdir();(output/"cases").mkdir()
    def save(p,value,compressed=False):
        (expanded.write_packet if compressed else expanded.write)(p,value)
        artifacts[str(p.resolve())]=expanded.digest(p);return str(p.resolve())
    save(output/"run-contract.json",{"version":VERSION,"baseline_source":str(source.resolve()),
        "baseline_report_expected_sha256":BASELINE_REPORT_SHA,"code_pins":code,"arms":scoring.ARMS,
        "defining_weight":q(scoring.DEFINING_WEIGHT),"held_step_weight":q(scoring.HELD_STEP_WEIGHT),
        "same_original_graphs":True,"old_abstentions_not_retried":True,"transition_budget":2_000_000,
        "source_labels_used_at_inference":False,"training_performed":False,"parameter_sweep":False,
        "independent_test_accuracy_measured":False,"production_modified":False})
    rows=[];cache={}
    for old in packets:
        key=old["pair_id"],old["sample_id"]
        row={k:deepcopy(old[k]) for k in ("pair_id","sample_id","sample_span","plan_index","collection_id",
            "work_family_id","reference_binding_verified","source_clock_gate","attempted","known_prior_diagnostic")}
        row["arms"]={}
        if row["attempted"]:
            packet=read(old["graph_artifact"],old["graph_sha256"]);prior.check_prediction(packet)
            if (packet["pair_id"],packet["sample_id"],packet["span"])!=(key[0],key[1],row["sample_span"]):raise ValueError("graph_scope_changed")
            graph=prior.prior.graph_from_packet(packet["problem"])
            if _hash(prior.prior.graph_packet(graph))!=_hash(packet["problem"]):raise ValueError("graph_codec_changed")
            row.update(graph_artifact=old["graph_artifact"],graph_sha256=old["graph_sha256"],source=packet["source"])
            if key[0] not in cache:
                src=packet["source"];ir=read(src["canonical_ir_path"])
                if _hash(ir)!=src["original_ir_content_sha256"]:raise ValueError("case_ir_changed")
                xml=Path(src["source_musicxml_path"]);sha=expanded.digest(xml)
                if sha!=src["original_musicxml_sha256"]:raise ValueError("case_xml_changed")
                guards[str(xml.resolve())]=sha
                view,grace=prior.prior.bounded.grace_projection(ir);cache[key[0]]=ir,view,grace,SourceClockGuard(ir)
            ir,view,grace,clock=cache[key[0]];gate=clock.scope(row["sample_span"])
            if not gate["accepted"] or _hash(gate)!=_hash(row["source_clock_gate"]):raise ValueError("source_clock_gate_changed")
            ev,args=prior.evidence_args(ir,view,grace,row["sample_span"],clock)
            for arm in scoring.ARMS:
                tick=perf_counter();result=scoring.decode(graph,ev,arm=arm,**args)
                if arm=="control" and _hash(prior.prior.musical_value(result["selected"]))!=_hash(prior.prior.musical_value(old["arms"]["bass_return"]["selected_prediction"])):
                    raise ValueError("fresh_control_winner_changed")
                if result["selected"] is not None and q(scoring.score_path(graph,ev,prior.prior.path_ids(result["selected"]),arm=arm,**args))!=result["selected"]["score_cost"]:
                    raise ValueError("winner_independent_cost_mismatch")
                row["arms"][arm]={"status":result["status"],"selected_prediction":result["selected"],
                    "elapsed_seconds":perf_counter()-tick,"transitions":result["transitions"],
                    "exact_optimum_under_declared_score":result["exact_optimum_under_declared_score"],
                    "search_diagnostics":result["search_diagnostics"],"component_support_contract":result["component_support_contract"]}
            clock.check_source()
        else:
            row["arms"]={a:{"status":old["arms"]["bass_return"]["status"],"selected_prediction":None,
                "elapsed_seconds":0,"reused_old_abstention":True} for a in scoring.ARMS}
        row["prediction_artifact"]=save(output/"predictions"/(_hash(key)[:20]+".json.gz"),row,True);rows.append(row)
        save(output/"progress.json",{"complete":False,"phase":"predictions_before_reference_read","scopes":len(rows),"elapsed_seconds":perf_counter()-started})
        print(f"[component support {len(rows)}/{freeze['contexts']}] {key[0]}: "+", ".join(a+":"+r["status"] for a,r in row["arms"].items()),flush=True)
    save(output/"prediction-freeze.json",{"version":VERSION,"labels_read":False,"contexts":len(rows),
        "prediction_hashes":{r["prediction_artifact"]:artifacts[r["prediction_artifact"]] for r in rows}})
    # First reference-bearing report read. Previous development exposure remains.
    baseline=read(source/"report.json",BASELINE_REPORT_SHA)
    for p,h in (baseline["input_hashes"]|baseline["code_hashes"]|baseline["artifact_hashes"]).items():
        if expanded.digest(p)!=h:raise ValueError("baseline_artifact_changed:"+p)
        guards[p]=h
    refs={(r["pair_id"],r["sample_id"]):r for r in baseline["records"]}
    if set(refs)!=keys:raise ValueError("reference_scope_changed")
    prior_cases={(r["pair_id"],r["sample_id"]) for r in baseline["cases"]}
    changes=[];cases=[]
    for row in rows:
        key=row["pair_id"],row["sample_id"];ref=refs[key]
        row["reference_cells"]=deepcopy(ref["reference_cells"]);row["candidate_ceiling"]=deepcopy(ref["candidate_ceiling"])
        for a,result in row["arms"].items():
            result["evaluation"]=evaluate(native_reference(row),native_prediction(result["selected_prediction"],row["sample_span"]),row["sample_span"],selected=result["selected_prediction"] is not None)
        changed=[a for a in scoring.ARMS if a!="control" and _hash(native_prediction(row["arms"][a]["selected_prediction"],row["sample_span"]))!=_hash(native_prediction(row["arms"]["control"]["selected_prediction"],row["sample_span"]))]
        if changed:
            changes.append({"pair_id":key[0],"sample_id":key[1],"changed_arms":changed,
                "matched_time_deltas":{a:q(f(row["arms"][a]["evaluation"]["components"]["root_members"]["matched"])-f(row["arms"]["control"]["evaluation"]["components"]["root_members"]["matched"])) for a in changed}})
        if row["attempted"] and (changed or key in prior_cases or row["known_prior_diagnostic"]):
            graph=prior.prior.graph_from_packet(read(row["graph_artifact"])["problem"])
            ir,view,grace,clock=cache[key[0]];ev,args=prior.evidence_args(ir,view,grace,row["sample_span"],clock)
            case={"record":row,"source":row["source"],"scored_selected_paths":{a:path_receipt(graph,ev,prior.prior.path_ids(v["selected_prediction"]),args) for a,v in row["arms"].items() if v["selected_prediction"] is not None},
                "human_validated":False,"independent_test_case":False,"reference_witness_never_used_for_inference":True}
            witness=ref["candidate_ceiling"].get("oracle_reference_witness") if ref["candidate_ceiling"] else None
            if witness:
                case["reference_witness_scores"]=path_receipt(graph,ev,witness,args)
                case["reference_witness_scores"]["source_labels_used_to_create_this_path"]=True
            cases.append({"pair_id":key[0],"sample_id":key[1],"case_path":save(output/"cases"/(_hash(key)[:20]+".json.gz"),case,True)})
    tables={a:summarize([r|r["arms"][a] for r in rows]) for a in scoring.ARMS}
    if tables["control"]!=baseline["tables"]["bass_return"]:raise ValueError("control_metric_changed")
    for p,h in (guards|code|artifacts).items():
        if expanded.digest(p)!=h:raise ValueError("guard_changed:"+p)
    report={"version":VERSION,"complete":True,"contexts":len(rows),"fresh_selected_scopes":sum(r["attempted"] for r in rows),"full_source_packages":len(cache),
        "tables":tables,"changed":changes,"cases":cases,"records":rows,"input_hashes":guards,"code_hashes":code,"artifact_hashes":artifacts,
        "status_counts":{a:dict(Counter(r["arms"][a]["status"] for r in rows)) for a in scoring.ARMS},
        "all_predictions_sealed_before_reference_report_read":True,"source_labels_used_at_inference":False,
        "training_performed":False,"parameter_sweep":False,"independent_test_accuracy_measured":False,
        "full_roman_accuracy_measured":False,"new_rules_adopted_for_production":False,"production_modified":False,
        "graph_generation_performed":False,"elapsed_seconds":perf_counter()-started}
    expanded.write(output/"report.json",report)
    return {k:v for k,v in report.items() if k not in ("records","input_hashes","code_hashes","artifact_hashes","tables","changed")}


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--source",required=True);parser.add_argument("--output",required=True)
    args=parser.parse_args();print(json.dumps(run(args.source,args.output),ensure_ascii=False,indent=2),flush=True)
