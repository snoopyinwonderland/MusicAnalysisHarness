from __future__ import annotations

import argparse
import json
from pathlib import Path

from .batch import validate_corpus
from .corpus import inventory, write_inventory
from .core import MusicHarness, write_package
from .formal_ir import FormalIRAdapter, deterministic_evidence, legacy_analysis_records
from .engraving import render_musicxml_pages
from .review import write_review_html


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
    args = parser.parse_args()
    if args.command == "validate-corpus":
        result = validate_corpus(args.inventory, args.output, args.limit, args.timeout)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "inventory":
        result = inventory(args.source)
        write_inventory(result, args.output)
        print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
        print(f"Inventory written to {args.output.resolve()}")
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
        evidence = deterministic_evidence(formal)
        analyzed = harness.analyze(args.source)
        analysis_records = legacy_analysis_records(formal, analyzed["analysis"])
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / "canonical_music_ir_v0.1.json").write_text(json.dumps(formal, ensure_ascii=False, indent=2), encoding="utf-8")
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
