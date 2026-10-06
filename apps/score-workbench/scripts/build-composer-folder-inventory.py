import hashlib
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
output = Path(sys.argv[2])
folders = sys.argv[3:] or ["Beethoven", "Mozart", "Chopin"]
records = []
for folder in folders:
    directory = root / folder
    if not directory.is_dir():
        raise SystemExit(f"Missing folder: {directory}")
    for file in sorted(directory.rglob("*")):
        if not file.is_file() or file.suffix.lower() not in {".xml", ".musicxml", ".mxl"}:
            continue
        relative = file.relative_to(root).as_posix()
        records.append({
            "relative_path": relative,
            "source_id": relative,
            "bytes": file.stat().st_size,
            "sha256": hashlib.sha256(file.read_bytes()).hexdigest(),
            "category": "classical-composer-folder",
            "eligible_for_harmony_corpus": True,
            "excluded_reason": None,
            "duplicate_of": None,
        })

payload = {
    "schema_version": "musicanote-corpus-inventory-0.1",
    "root": str(root),
    "folders": folders,
    "summary": {
        "total_files": len(records),
        "total_bytes": sum(row["bytes"] for row in records),
    },
    "files": records,
}
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(payload["summary"] | {"output": str(output)}, ensure_ascii=False, indent=2))
