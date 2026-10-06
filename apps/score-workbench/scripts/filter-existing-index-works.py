import json
import sqlite3
import sys
from pathlib import Path

source = Path(sys.argv[1])
database = Path(sys.argv[2])
target = Path(sys.argv[3])
report = Path(sys.argv[4])

items = [json.loads(line) for line in source.open(encoding="utf-8") if line.strip()]
ids = [item["id"] for item in items]
existing = set()

with sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True) as connection:
    for offset in range(0, len(ids), 500):
        chunk = ids[offset : offset + 500]
        placeholders = ",".join("?" for _ in chunk)
        rows = connection.execute(
            f"SELECT id FROM works WHERE id IN ({placeholders})", chunk
        )
        existing.update(row[0] for row in rows)

kept = []
duplicates = []
for item in items:
    if item["id"] in existing:
        duplicates.append(
            {"workId": item["id"], "source": item.get("source"), "reason": "already-indexed-content"}
        )
    else:
        kept.append(item)

with target.open("w", encoding="utf-8") as writer:
    for item in kept:
        writer.write(json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n")

report.write_text(
    json.dumps(
        {"input": len(items), "kept": len(kept), "existingDuplicateCount": len(duplicates), "duplicates": duplicates},
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)
print(json.dumps({"input": len(items), "kept": len(kept), "existingDuplicateCount": len(duplicates)}, indent=2))
