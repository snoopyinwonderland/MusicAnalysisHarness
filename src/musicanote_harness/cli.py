from __future__ import annotations

import argparse
import json
from pathlib import Path

from .batch import validate_corpus
from .corpus import inventory, write_inventory
from .core import MusicHarness, write_package
from .formal_ir import FormalIRAdapter, deterministic_evidence, legacy_analysis_records, q
from .engraving import musicxml_with_canonical_ids, render_musicxml_pages
from .source_enrichment import enrich_from_mapped_musicxml
from .formal_regression import validate_formal_corpus
from .review import write_review_html
from .dcml_import import prepare_dcml, write_dcml_package
from .harmony_surface import analyze_surface
from .harmony_surface_eval import evaluate_simple_dcml
from .harmony_unfolded import analyze_unfolded
from .classical_registry import inventory_classical
from .dcml_batch import validate_dcml_pairs
from .dcml_fast_audit import audit_all
from .annotation_source_audit import audit_jams, audit_romantext
from .harmony_case_retrieval import build_case_library, load_case_records, retrieve_cases
from .harmony_dataset_manifest import build_harmony_dataset_manifest, validate_harmony_data_release
from .harmony_case_retrieval_eval import evaluate_case_retrieval_ablation


def main() -> None:
    parser = argparse.ArgumentParser(prog="musicanote", description="Evidence-first MusicXML harness")
    sub = parser.add_subparsers(dest="command", required=True)
    inventory_parser = sub.add_parser("inventory", help="Inventory a MusicXML corpus, excluding melody files and exact duplicates")
    inventory_parser.add_argument("source", type=Path)
    inventory_parser.add_argument("--output", "-o", type=Path, default=Path("output/corpus_inventory.json"))
    batch_parser = sub.add_parser("validate-corpus", help="Run resumable file-by-file parser validation")
    batch_parser.add_argument("inventory", type=Path)
    batch_parser.add_argument("--output", "-o", type=Path, default=Path("output/corpus_validation"))
    batch_parser.add_argument("--limit", type=int)
    batch_parser.add_argument("--timeout", type=int, default=60)
    parse = sub.add_parser("parse", help="Create Canonical IR and validation report without musical inference")
    parse.add_argument("source", type=Path)
    parse.add_argument("--output", "-o", type=Path, default=Path("output"))
    analyze = sub.add_parser("analyze", help="Parse MusicXML and create an analysis package")
    analyze.add_argument("source", type=Path)
    analyze.add_argument("--output", "-o", type=Path, default=Path("output"))
    analyze.add_argument("--stdout", action="store_true")
    review = sub.add_parser("review", help="Create formal IR v0.1, deterministic evidence, and an interactive score review page")
    review.add_argument("source", type=Path)
    review.add_argument("--output", "-o", type=Path, default=Path("output/review"))
    review.add_argument("--measures", type=int, default=8)
    formal_corpus = sub.add_parser("validate-formal-corpus", help="Validate formal IR, source enrichment, and engraving ID mapping across non-melody MusicXML files")
    formal_corpus.add_argument("source", type=Path)
    formal_corpus.add_argument("--output", "-o", type=Path, default=Path("output/formal_regression"))
    formal_corpus.add_argument("--limit", type=int, default=10)
    dcml = sub.add_parser("prepare-dcml", help="Align one DCML harmony TSV track to a MusicXML score and formal IR")
    dcml.add_argument("--score", type=Path, required=True)
    dcml.add_argument("--measures", type=Path, required=True)
    dcml.add_argument("--harmonies", type=Path, required=True)
    dcml.add_argument("--notes", type=Path, required=True)
    dcml.add_argument("--output", "-o", type=Path, required=True)
    surface = sub.add_parser("analyze-surface", help="Run blind whole-score surface-sonority candidates from formal IR only")
    surface.add_argument("ir", type=Path)
    surface.add_argument("--output", "-o", type=Path, required=True)
    unfolded = sub.add_parser("analyze-unfolded", help="Run blind 1-4-beat unfolded surface-harmony segmentation from formal IR")
    unfolded.add_argument("ir", type=Path)
    unfolded.add_argument("--output", "-o", type=Path, required=True)
    surface_eval = sub.add_parser("evaluate-surface-dcml", help="Score only simple DCML labels against a separate blind surface result")
    surface_eval.add_argument("--surface", type=Path, required=True)
    surface_eval.add_argument("--annotations", type=Path, required=True)
    surface_eval.add_argument("--alignments", type=Path, required=True)
    surface_eval.add_argument("--output", "-o", type=Path, required=True)
    classical = sub.add_parser("inventory-classical", help="Read-only local classical-corpora asset inventory and DCML pair candidates")
    classical.add_argument("source", type=Path)
    classical.add_argument("--output", "-o", type=Path, required=True)
    dcml_batch = sub.add_parser("validate-dcml-batch", help="Bounded resumable alignment validation for DCML pair candidates")
    dcml_batch.add_argument("pairs", type=Path)
    dcml_batch.add_argument("--output", "-o", type=Path, required=True)
    dcml_batch.add_argument("--limit", type=int)
    dcml_batch.add_argument("--timeout", type=int, default=90)
    dcml_batch.add_argument("--workers", type=int, default=1)
    fast_audit = sub.add_parser("audit-dcml-annotations", help="Fast read-only TSV and score-structure audit for DCML MusicXML and MSCX candidates")
    fast_audit.add_argument("pairs", type=Path)
    fast_audit.add_argument("--output", "-o", type=Path, required=True)
    roman_audit = sub.add_parser("audit-romantext-sources", help="Read-only RomanText header and score-sibling audit")
    roman_audit.add_argument("assets", type=Path)
    roman_audit.add_argument("--output", "-o", type=Path, required=True)
    roman_align = sub.add_parser("align-romantext-scores", help="Audit RomanText events against sibling score coordinates")
    roman_align.add_argument("records", type=Path)
    roman_align.add_argument("--output", "-o", type=Path, required=True)
    roman_align.add_argument("--limit", type=int)
    roman_align.add_argument("--corpus", choices=("openscore-lieder", "when-in-rome"))
    roman_align.add_argument("--workers", type=int, default=1)
    roman_import = sub.add_parser("prepare-romantext", help="Import one aligned RomanText track and build a visual score review")
    roman_import.add_argument("--analysis", type=Path, required=True)
    roman_import.add_argument("--score", type=Path, required=True)
    roman_import.add_argument("--output", "-o", type=Path, required=True)
    roman_catalog = sub.add_parser("serve-romantext-catalog", help="Search audited RomanText pairs and lazily build score reviews")
    roman_catalog.add_argument("records", type=Path)
    roman_catalog.add_argument("--evidence-records", type=Path)
    roman_catalog.add_argument("--output", "-o", type=Path, required=True)
    roman_catalog.add_argument("--host", default="127.0.0.1")
    roman_catalog.add_argument("--port", type=int, default=8766)
    roman_catalog.add_argument("--case-library", type=Path)
    roman_catalog.add_argument("--dataset-manifest", type=Path)
    roman_catalog.add_argument("--case-review-output", type=Path)
    roman_evidence_batch = sub.add_parser("audit-romantext-evidence", help="Resumable corpus evidence audit for aligned RomanText labels")
    roman_evidence_batch.add_argument("records", type=Path)
    roman_evidence_batch.add_argument("--output", "-o", type=Path, required=True)
    roman_evidence_batch.add_argument("--limit", type=int)
    roman_evidence_batch.add_argument("--corpus", choices=("openscore-lieder", "when-in-rome"))
    roman_evidence_batch.add_argument("--workers", type=int, default=1)
    jams_audit = sub.add_parser("audit-jams-sources", help="Read-only ChoCo JAMS shape and provenance-candidate audit")
    jams_audit.add_argument("assets", type=Path)
    jams_audit.add_argument("--output", "-o", type=Path, required=True)
    case_library = sub.add_parser("build-harmony-case-library", help="Build source-linked retrieval cases from prepared Canonical IR packages")
    case_library.add_argument("source", type=Path)
    case_library.add_argument("--output", "-o", type=Path, required=True)
    case_library.add_argument("--limit", type=int)
    case_library.add_argument("--manifest", type=Path)
    dataset_manifest = sub.add_parser("build-harmony-dataset-manifest", help="Assign leakage-resistant work-family train/dev/holdout splits")
    dataset_manifest.add_argument("source", type=Path)
    dataset_manifest.add_argument("--output", "-o", type=Path, required=True)
    dataset_manifest.add_argument("--train-percent", type=int, default=70)
    dataset_manifest.add_argument("--dev-percent", type=int, default=15)
    dataset_validate = sub.add_parser("validate-harmony-data-release", help="Validate work-family split isolation and case identity links")
    dataset_validate.add_argument("--manifest", type=Path, required=True)
    dataset_validate.add_argument("--library", type=Path, required=True)
    dataset_validate.add_argument("--output", "-o", type=Path, required=True)
    case_eval = sub.add_parser("evaluate-harmony-case-retrieval", help="Compare surface, local-key, and voice-leading retrieval on a blind split")
    case_eval.add_argument("--library", type=Path, required=True)
    case_eval.add_argument("--output", "-o", type=Path, required=True)
    case_eval.add_argument("--query-split", choices=("dev", "holdout"), default="dev")
    case_eval.add_argument("--candidate-split", choices=("train",), default="train")
    case_eval.add_argument("--limit", type=int)
    case_query = sub.add_parser("query-harmony-cases", help="Retrieve different-score harmony analogies for one Canonical IR span")
    case_query.add_argument("--ir", type=Path, required=True)
    case_query.add_argument("--library", type=Path, required=True)
    case_query.add_argument("--start", required=True, help="Global quarter as integer or fraction, e.g. 12 or 25/2")
    case_query.add_argument("--end", required=True, help="Exclusive global quarter")
    case_query.add_argument("--limit", type=int, default=12)
    case_query.add_argument("--manifest", type=Path)
    case_query.add_argument("--output", "-o", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "validate-corpus":
        result = validate_corpus(args.inventory, args.output, args.limit, args.timeout)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "prepare-dcml":
        package = prepare_dcml(args.score, args.measures, args.harmonies, args.notes)
        write_dcml_package(package, args.output)
        print(json.dumps(package["report"], ensure_ascii=False, indent=2))
    elif args.command == "analyze-surface":
        from jsonschema import Draft202012Validator

        ir = json.loads(args.ir.read_text(encoding="utf-8"))
        result = analyze_surface(ir)
        schema_path = Path(__file__).resolve().parents[2] / "MUSICANOTE_Canonical_Music_IR" / "schemas" / "surface_harmony_pilot.schema.json"
        Draft202012Validator(json.loads(schema_path.read_text(encoding="utf-8"))).validate(result)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
    elif args.command == "analyze-unfolded":
        from jsonschema import Draft202012Validator

        ir = json.loads(args.ir.read_text(encoding="utf-8"))
        result = analyze_unfolded(ir)
        schema_path = Path(__file__).resolve().parents[2] / "MUSICANOTE_Canonical_Music_IR" / "schemas" / "unfolded_harmony_pilot.schema.json"
        Draft202012Validator(json.loads(schema_path.read_text(encoding="utf-8"))).validate(result)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
    elif args.command == "evaluate-surface-dcml":
        surface_result = json.loads(args.surface.read_text(encoding="utf-8"))
        annotations = [json.loads(row) for row in args.annotations.read_text(encoding="utf-8").splitlines() if row]
        alignments = [json.loads(row) for row in args.alignments.read_text(encoding="utf-8").splitlines() if row]
        result = evaluate_simple_dcml(surface_result, annotations, alignments)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({key: value for key, value in result.items() if key != "mismatch_examples"}, ensure_ascii=False, indent=2))
    elif args.command == "inventory-classical":
        result = inventory_classical(args.source, args.output)
        print(json.dumps({key: value for key, value in result.items() if key not in {"files_by_suffix", "files_by_candidate_role", "scan_error_examples"}}, ensure_ascii=True, indent=2))
    elif args.command == "validate-dcml-batch":
        result = validate_dcml_pairs(args.pairs, args.output, args.limit, args.timeout, args.workers)
        print(json.dumps({key: value for key, value in result.items() if key != "outcomes"}, ensure_ascii=False, indent=2))
    elif args.command == "audit-dcml-annotations":
        result = audit_all(args.pairs, args.output)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "audit-romantext-sources":
        result = audit_romantext(args.assets, args.output)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "align-romantext-scores":
        from .romantext_alignment import audit_romantext_alignments
        result = audit_romantext_alignments(args.records, args.output, args.limit, args.corpus, args.workers)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "prepare-romantext":
        from .romantext_import import prepare_romantext, write_romantext_package
        from .romantext_review import write_romantext_review_html

        package = prepare_romantext(args.analysis, args.score)
        write_romantext_package(package, args.output)
        pages, mapping = render_musicxml_pages(args.score, package["ir"])
        (args.output / "engraving_id_mapping_report.json").write_text(
            json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        write_romantext_review_html(package, pages, args.output / "romantext-review.html")
        print(json.dumps(package["report"], ensure_ascii=False, indent=2))
    elif args.command == "serve-romantext-catalog":
        from .romantext_catalog import serve_catalog

        serve_catalog(
            args.records, args.output, host=args.host, port=args.port,
            evidence_records_path=args.evidence_records,
            case_library_path=args.case_library,
            dataset_manifest_path=args.dataset_manifest,
            case_review_path=args.case_review_output,
        )
    elif args.command == "audit-romantext-evidence":
        from .romantext_evidence_batch import audit_romantext_evidence

        result = audit_romantext_evidence(args.records, args.output, args.limit, args.corpus, args.workers)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "audit-jams-sources":
        result = audit_jams(args.assets, args.output)
        print(json.dumps({key: value for key, value in result.items()
                          if key not in {"source_corpus_metadata", "annotation_tools_top20"}}, ensure_ascii=False, indent=2))
    elif args.command == "build-harmony-case-library":
        result = build_case_library(args.source, args.output, args.limit, args.manifest)
        print(json.dumps({key: value for key, value in result.items() if key not in {"score_counts", "errors"}}, ensure_ascii=False, indent=2))
    elif args.command == "build-harmony-dataset-manifest":
        result = build_harmony_dataset_manifest(
            args.source, args.output, train_percent=args.train_percent, dev_percent=args.dev_percent,
        )
        print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
    elif args.command == "validate-harmony-data-release":
        result = validate_harmony_data_release(args.manifest, args.library, args.output)
        print(json.dumps({"status": result["status"], **result["checks"]}, ensure_ascii=False, indent=2))
    elif args.command == "evaluate-harmony-case-retrieval":
        result = evaluate_case_retrieval_ablation(
            args.library, args.output, query_split=args.query_split,
            candidate_split=args.candidate_split, limit=args.limit,
        )
        print(json.dumps({"query_count": result["query_count"], "candidate_count": result["candidate_count"],
                          "results": [{key: value for key, value in row.items() if key != "per_family"}
                                      for row in result["results"]]}, ensure_ascii=False, indent=2))
    elif args.command == "query-harmony-cases":
        from fractions import Fraction

        ir = json.loads(args.ir.read_text(encoding="utf-8"))
        span = {"start": q(Fraction(args.start)), "end": q(Fraction(args.end))}
        query_identity = None
        if args.manifest:
            from .harmony_dataset_manifest import load_manifest_index
            query_identity = load_manifest_index(args.manifest).get(ir["ir_document_id"])
        result = retrieve_cases(
            ir, span, load_case_records(args.library), limit=args.limit,
            query_dataset_identity=query_identity,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"matches": len(result["matches"]), "label_alternatives": len(result["label_alternatives"])}, ensure_ascii=False, indent=2))
    elif args.command == "inventory":
        result = inventory(args.source)
        write_inventory(result, args.output)
        print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
        print(f"Inventory written to {args.output.resolve()}")
    elif args.command == "validate-formal-corpus":
        result = validate_formal_corpus(args.source, args.output, args.limit)
        print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
        print(f"Formal regression written to {args.output.resolve()}")
    elif args.command == "parse":
        result = MusicHarness().parse(args.source)
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / "canonical_ir.json").write_text(json.dumps(result["score"], ensure_ascii=False, indent=2), encoding="utf-8")
        (args.output / "validation_report.json").write_text(json.dumps(result["validation"], ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Canonical IR written to {args.output.resolve()}")
    elif args.command == "review":
        harness = MusicHarness()
        parsed = harness.parse(args.source)
        formal = FormalIRAdapter().convert(parsed["score"], args.source)
        mapped_xml, source_mapping = musicxml_with_canonical_ids(args.source, formal)
        enrichment_report = enrich_from_mapped_musicxml(formal, mapped_xml)
        evidence = deterministic_evidence(formal)
        analyzed = harness.analyze(args.source)
        analysis_records = legacy_analysis_records(formal, analyzed["analysis"])
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / "canonical_music_ir_v0.1.json").write_text(json.dumps(formal, ensure_ascii=False, indent=2), encoding="utf-8")
        mapping_summary = {key: value for key, value in source_mapping.items() if key != "matched_note_ids_in_source_order"}
        (args.output / "source_enrichment_report.json").write_text(json.dumps({"mapping": mapping_summary, "enrichment": enrichment_report}, ensure_ascii=False, indent=2), encoding="utf-8")
        (args.output / "deterministic_evidence.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
        (args.output / "legacy_analysis_hypotheses.json").write_text(json.dumps(analyzed["analysis"], ensure_ascii=False, indent=2), encoding="utf-8")
        (args.output / "analysis_records_v0.1.json").write_text(json.dumps(analysis_records, ensure_ascii=False, indent=2), encoding="utf-8")
        engraved_pages, engraving_mapping = render_musicxml_pages(args.source, formal)
        (args.output / "engraving_id_mapping_report.json").write_text(json.dumps(engraving_mapping, ensure_ascii=False, indent=2), encoding="utf-8")
        write_review_html(formal, evidence, analyzed["analysis"], args.output / "canonical-ir-review.html", args.measures, engraved_pages)
        print(f"Review package written to {args.output.resolve()}")
    elif args.command == "analyze":
        result = MusicHarness().analyze(args.source)
        write_package(result, args.output)
        if args.stdout:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"Analysis package written to {args.output.resolve()}")


if __name__ == "__main__":
    main()
