"""Create initial authority-list queues without modifying the v4 workbook."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import date
from pathlib import Path

import openpyxl


SOURCE = Path(r"K:\MusicSearch\outputs\classical-repertoire-priority-2026-09-08\classical-repertoire-priority-v4.xlsx")
ROOT = Path(r"K:\MusicSearch\classical-repertoire-collection\workspace")
RUN_DATE = date(2026, 9, 22).isoformat()
SCHEMA = "musicanote-classical-authority-backlog-v1"


def entity_id(prefix: str, value: str) -> str:
    return f"{prefix}_{hashlib.sha256(value.strip().casefold().encode()).hexdigest()[:16]}"


def records(sheet):
    iterator = sheet.iter_rows(values_only=True)
    next(iterator)
    headers = next(iterator)
    for row_number, values in enumerate(iterator, start=3):
        if not any(value is not None for value in values):
            continue
        yield row_number, dict(zip(headers, values))


def save_jsonl(relative: str, items: list[dict]) -> None:
    path = ROOT / relative
    if path.exists():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        for item in items:
            handle.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")


def save_text(relative: str, text: str) -> None:
    path = ROOT / relative
    if path.exists():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def main() -> None:
    if ROOT.exists():
        raise FileExistsError(f"Refusing to reuse existing workspace: {ROOT}")
    book = openpyxl.load_workbook(SOURCE, read_only=True, data_only=True)

    composers = []
    ids = {}
    complete = Counter()
    years = Counter()
    policies = Counter()
    for source_row, row in records(book["작곡가 목록"]):
        name = row["작곡가"]
        cid = entity_id("cmp", name)
        ids[name] = cid
        complete[row["Complete Catalogue 상태"]] += 1
        years[row["작품 연도 보완"]] += 1
        policies[row["수집 정책"]] += 1
        composers.append({
            "schemaVersion": SCHEMA,
            "composerId": cid,
            "composerCanonical": name,
            "era": row["시대"],
            "birthYear": row["출생 연도"],
            "deathYear": row["사망 연도"],
            "priorityGrade": row["작곡가 등급"],
            "collectionPolicy": row["수집 정책"],
            "completeCatalogueStatus": row["Complete Catalogue 상태"],
            "workDateEnrichmentStatus": row["작품 연도 보완"],
            "openOpusId": row["Open Opus ID"],
            "legacySourceUrl": row["출처 URL"],
            "authorityCollectionStatus": "waiting",
            "legacyWorkbookRow": source_row,
        })

    catalogues = []
    for source_row, row in records(book["전작 카탈로그"]):
        name = row["작곡가"]
        catalogues.append({
            "schemaVersion": SCHEMA,
            "composerId": ids.get(name, entity_id("cmp", name)),
            "composerCanonical": name,
            "priorityGrade": row["등급"],
            "catalogueAbbreviation": row["약호"],
            "catalogueCanonicalName": row["카탈로그"],
            "authorityProvider": row["우선 출처"],
            "authorityUrl": row["URL"],
            "collectionNotes": row["사용 메모"],
            "handoffVerificationStatus": row["확인 상태"],
            "internalMappingStatus": row["내부 매핑 상태"],
            "authorityCollectionStatus": "waiting",
            "legacyWorkbookRow": source_row,
        })

    supplemental = []
    for source_row, row in records(book["보완 작곡가"]):
        name = row["작곡가"]
        supplemental.append({
            "schemaVersion": SCHEMA,
            "composerId": entity_id("cmp", name),
            "composerCanonical": name,
            "era": row["시대"],
            "birthYear": row["출생"],
            "deathYear": row["사망"],
            "priorityGrade": row["제안 등급"],
            "region": row["지역"],
            "inclusionRationale": row["보완 목적"],
            "representativeWorks": row["대표 작품"],
            "initialRightsClassification": row["권리 1차 분류"],
            "verificationNotes": row["검증 메모"],
            "authorityCollectionStatus": "waiting",
            "legacyWorkbookRow": source_row,
        })

    work_count = missing_year = missing_catalogue = 0
    for _, row in records(book["작품 목록"]):
        work_count += 1
        missing_year += row["작곡 연도"] is None
        missing_catalogue += row["카탈로그 번호"] is None

    save_jsonl("catalog/authority/composer-backlog.jsonl", composers)
    save_jsonl("catalog/authority/s-composer-catalogue-registry.jsonl", catalogues)
    save_jsonl("catalog/authority/supplementary-composer-backlog.jsonl", supplemental)
    source_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    save_jsonl("changes/events.jsonl", [{
        "eventId": "evt_20260922_bootstrap_authority_backlog",
        "eventDate": RUN_DATE,
        "eventType": "workspace-bootstrap",
        "sourceWorkbook": str(SOURCE),
        "sourceWorkbookSha256": source_hash,
        "notes": "Generated pending queues. The source workbook was not modified.",
    }])
    save_text("README.md", "# Classical repertoire collection\n\nThis is a non-destructive continuation of the handoff. The v4 workbook is the immutable baseline. Files in `catalog/authority/` are pending collection queues, not verified authority records.\n")
    save_text("changes/CHANGELOG.md", f"# Change log\n\n## {RUN_DATE}\n\n- Created pending authority-list queues from v4 without modifying the source workbook.\n")
    save_text("reports/list-collection-audit-2026-09-22.md", f"""# List collection audit — {RUN_DATE}

- Baseline composers: {len(composers)}
- Baseline works: {work_count}
- S-grade catalogue registry rows: {len(catalogues)}
- Supplementary-composer candidates: {len(supplemental)}
- Complete Catalogue statuses: {dict(sorted(complete.items()))}
- Work-year enrichment statuses: {dict(sorted(years.items()))}
- Collection policies: {dict(sorted(policies.items()))}
- Works without composition year: {missing_year}
- Works without catalogue number: {missing_catalogue}

The baseline is a discovery list. Pending entries require authority-source verification before they become catalogued records.
""")
    print(json.dumps({"composers": len(composers), "works": work_count, "s_catalogues": len(catalogues), "supplementary": len(supplemental)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
