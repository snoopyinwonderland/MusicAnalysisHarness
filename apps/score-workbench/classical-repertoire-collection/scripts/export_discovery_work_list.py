"""Export the immutable v4 work list to a separate JSONL discovery catalogue."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import openpyxl


SOURCE = Path(r"K:\MusicSearch\outputs\classical-repertoire-priority-2026-09-08\classical-repertoire-priority-v4.xlsx")
ROOT = Path(r"K:\MusicSearch\classical-repertoire-collection\workspace")
OUTPUT = ROOT / "catalog" / "discovery" / "works-v4.jsonl"


def stable_id(prefix: str, value: str) -> str:
    return f"{prefix}_{hashlib.sha256(value.strip().casefold().encode()).hexdigest()[:16]}"


def main() -> None:
    if OUTPUT.exists():
        raise FileExistsError(f"Refusing to overwrite existing artifact: {OUTPUT}")
    if not (ROOT / "changes" / "events.jsonl").is_file():
        raise FileNotFoundError("Run bootstrap_authority_backlog_streaming.py first")

    workbook = openpyxl.load_workbook(SOURCE, read_only=True, data_only=True)
    rows = workbook["작품 목록"].iter_rows(values_only=True)
    next(rows)
    headers = next(rows)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with OUTPUT.open("x", encoding="utf-8", newline="\n") as handle:
        for source_row, values in enumerate(rows, start=3):
            if not any(value is not None for value in values):
                continue
            item = dict(zip(headers, values))
            composer = item["작곡가"]
            title = item["작품명"]
            open_opus_id = str(item["Open Opus ID"] or "")
            stable_key = open_opus_id or f"{composer}|{title}|{item['카탈로그 번호'] or ''}"
            record = {
                "schemaVersion": "musicanote-classical-discovery-v1",
                "collectionWorkId": stable_id("wrk", f"{composer}|{stable_key}"),
                "composerId": stable_id("cmp", composer),
                "composerCanonical": composer,
                "titleCanonical": title,
                "catalogueNumber": item["카탈로그 번호"],
                "genre": item["장르"],
                "era": item["시대"],
                "compositionYear": item["작곡 연도"],
                "priorityGrade": item["등록 등급"],
                "priorityScore": item["우선순위 점수"],
                "collectionScope": item["수집 범위"],
                "legacyXmlAvailability": item["XML 확보 상태"],
                "legacyValidationStatus": item["검증 상태"],
                "openOpusId": open_opus_id or None,
                "authorityCollectionStatus": "waiting",
                "legacyWorkbookRow": source_row,
            }
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            count += 1

    event_path = ROOT / "changes" / "events.jsonl"
    event = {
        "eventId": "evt_20260922_export_discovery_work_list",
        "eventDate": "2026-09-22",
        "eventType": "discovery-list-export",
        "sourceWorkbook": str(SOURCE),
        "output": str(OUTPUT.relative_to(ROOT)),
        "workCount": count,
        "notes": "Exported the v4 discovery list without treating it as authority-verified.",
    }
    with event_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    with (ROOT / "changes" / "CHANGELOG.md").open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(f"- Exported {count} v4 discovery works to JSONL; authority status remains waiting.\n")
    print(json.dumps({"workCount": count, "output": str(OUTPUT)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
