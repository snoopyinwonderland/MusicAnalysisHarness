"""Create a non-destructive S-grade authority-collection work queue."""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(r"K:\MusicSearch\classical-repertoire-collection\workspace")
REGISTRY = ROOT / "catalog" / "authority" / "s-composer-catalogue-registry.jsonl"
WORKS = ROOT / "catalog" / "discovery" / "works-v4.jsonl"
OUT = ROOT / "catalog" / "authority" / "s-composer-authority-work-queue.jsonl"
REPORT = ROOT / "reports" / "s-composer-coverage-audit-2026-09-22.md"


def load_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main():
    if OUT.exists() or REPORT.exists():
        raise FileExistsError("Refusing to overwrite an existing S-grade audit")
    registry = load_jsonl(REGISTRY)
    stats = defaultdict(lambda: {"works": 0, "missingCatalogue": 0, "missingYear": 0})
    for work in load_jsonl(WORKS):
        key = work["composerId"]
        stats[key]["works"] += 1
        stats[key]["missingCatalogue"] += work["catalogueNumber"] is None
        stats[key]["missingYear"] += work["compositionYear"] is None

    queue = []
    for item in registry:
        counts = stats[item["composerId"]]
        queue.append({
            **item,
            "baselineWorkCount": counts["works"],
            "baselineWorksMissingCatalogue": counts["missingCatalogue"],
            "baselineWorksMissingCompositionYear": counts["missingYear"],
            "nextAction": "Harvest authority catalogue metadata; map by stable work ID, not workbook row.",
            "queueStatus": "ready",
        })
    queue.sort(key=lambda item: (-item["baselineWorksMissingCatalogue"], -item["baselineWorkCount"], item["composerCanonical"]))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("x", encoding="utf-8", newline="\n") as handle:
        for item in queue:
            handle.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")

    lines = ["# S-grade authority collection audit — 2026-09-22", "", "| Composer | Baseline works | Missing catalogue | Missing year | Source |", "|---|---:|---:|---:|---|"]
    for item in queue:
        lines.append(f"| {item['composerCanonical']} | {item['baselineWorkCount']} | {item['baselineWorksMissingCatalogue']} | {item['baselineWorksMissingCompositionYear']} | {item['authorityProvider']} |")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    event = {"eventId": "evt_20260922_s_composer_audit", "eventDate": "2026-09-22", "eventType": "authority-queue-build", "queueCount": len(queue), "notes": "Built S-grade source-mapping queue from the immutable discovery list."}
    with (ROOT / "changes" / "events.jsonl").open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    with (ROOT / "changes" / "CHANGELOG.md").open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(f"- Built an authority-metadata work queue for {len(queue)} S-grade composers.\n")
    print(json.dumps({"queueCount": len(queue), "output": str(OUT)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
