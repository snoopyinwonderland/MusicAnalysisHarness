import json
import sys
from pathlib import Path

source = Path(sys.argv[1])
target = Path(sys.argv[2])
report = Path(sys.argv[3])
seen = {}
duplicates = []
kept = 0
with source.open(encoding="utf-8") as reader, target.open("w", encoding="utf-8") as writer:
    for line in reader:
        if not line.strip():
            continue
        item = json.loads(line)
        work_id = item["id"]
        if work_id in seen:
            duplicates.append({"workId": work_id, "source": item.get("source"), "duplicateOf": seen[work_id]})
            continue
        seen[work_id] = item.get("source")
        writer.write(json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n")
        kept += 1
report.write_text(json.dumps({"kept": kept, "duplicates": duplicates}, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"kept": kept, "duplicateCount": len(duplicates), "report": str(report)}, ensure_ascii=False, indent=2))
