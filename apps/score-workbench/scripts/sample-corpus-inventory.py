import json
import sys
from pathlib import Path

source = Path(sys.argv[1])
target = Path(sys.argv[2])
sample_size = int(sys.argv[3])
payload = json.loads(source.read_text(encoding="utf-8"))
files = sorted(payload["files"], key=lambda row: (row["bytes"], row["relative_path"]))

if sample_size >= len(files):
    sample = files
else:
    indices = [round(index * (len(files) - 1) / (sample_size - 1)) for index in range(sample_size)]
    sample = [files[index] for index in indices]

hash_groups = {}
for row in payload["files"]:
    hash_groups.setdefault(row["sha256"], []).append(row["relative_path"])
duplicates = [group for group in hash_groups.values() if len(group) > 1]

result = {
    **{key: value for key, value in payload.items() if key != "files"},
    "summary": {
        "total_files": len(sample),
        "total_bytes": sum(row["bytes"] for row in sample),
        "population_files": len(files),
        "population_bytes": sum(row["bytes"] for row in files),
        "population_unique_hashes": len(hash_groups),
        "population_duplicate_files": sum(len(group) - 1 for group in duplicates),
        "population_duplicate_groups": len(duplicates),
    },
    "files": sample,
}
target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
