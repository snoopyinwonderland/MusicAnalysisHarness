import json
import re
import sqlite3
import sys
import unicodedata
from collections import Counter
from pathlib import Path

coverage_path = Path(sys.argv[1])
db_path = Path(sys.argv[2])
output_path = Path(sys.argv[3])
coverage = json.loads(coverage_path.read_text(encoding="utf-8"))

def norm(value):
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).lower()
    return " ".join(re.findall(r"[a-z0-9]+", text))

db = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
meta = {}
for row in db.execute("select id,license,license_conflict,access_policy,pdmx_metadata,source_metadata from works"):
    if row[0] in meta:
        continue
    pdmx = {}
    source = {}
    try: pdmx = json.loads(row[4] or "{}")
    except Exception: pass
    try: source = json.loads(row[5] or "{}")
    except Exception: pass
    meta[row[0]] = {
        "license": row[1] or pdmx.get("license") or "",
        "license_conflict": bool(row[2] or pdmx.get("license_conflict")),
        "access_policy": row[3] or source.get("accessPolicy") or "",
        "n_notes": pdmx.get("n_notes"),
        "is_best_path": pdmx.get("is_best_path"),
        "is_best_arrangement": pdmx.get("is_best_arrangement"),
        "is_best_unique_arrangement": pdmx.get("is_best_unique_arrangement"),
    }
db.close()

arrangement_re = re.compile(r"\b(arr(?:anged|angement)?|transcri(?:bed|ption)|reduction|piano solo|piano duet|violin and piano|for piano|quartet version|orchestration)\b", re.I)
movement_re = re.compile(r"\b(mov(?:ement)?\.?\s*[ivx0-9]+|[ivx]+\.?\s+(?:allegro|adagio|andante|scherzo|finale)|act\s+[ivx0-9]+|scene\s+[ivx0-9]+)\b", re.I)

validated = []
for match in coverage["matches"]:
    if match["status"] not in {"보유", "부분 보유", "검토 필요"}:
        continue
    extra = meta.get(match.get("work_id"), {})
    combined = " ".join([match.get("matched_title", ""), match.get("matched_composer", ""), match.get("source", "")])
    target_norm = norm(match.get("title"))
    matched_norm = norm(match.get("matched_title"))
    arrangement = bool(arrangement_re.search(combined)) and not arrangement_re.search(match.get("title", ""))
    movement = bool(movement_re.search(combined)) and not movement_re.search(match.get("title", ""))
    if arrangement:
        relation = "편곡판 후보"
    elif movement:
        relation = "악장·부분 후보"
    elif match["method"] == "카탈로그 번호+작곡가/제목":
        relation = "동일 작품 후보"
    elif match["method"] == "제목+작곡가" and (target_norm == matched_norm or target_norm in matched_norm or matched_norm in target_norm):
        relation = "동일 작품 후보"
    else:
        relation = "동일성 검토"

    if extra.get("access_policy") == "research-preview":
        rights = "검색 조각만"
    elif extra.get("license_conflict"):
        rights = "라이선스 충돌 검토"
    elif str(extra.get("license", "")).lower() in {"cc-zero", "cc0", "publicdomain", "public-domain"}:
        rights = "공개 후보"
    elif extra.get("license"):
        rights = "라이선스 조건 확인"
    else:
        rights = "권리 미확인"

    if match["status"] == "보유" and relation == "동일 작품 후보" and match["confidence"] >= 0.92:
        validation_priority = "1. 고신뢰 표본 검증"
    elif relation in {"편곡판 후보", "악장·부분 후보"}:
        validation_priority = "2. 관계 검증"
    elif match["status"] == "부분 보유":
        validation_priority = "3. 부분 일치 검증"
    else:
        validation_priority = "4. 후보 재검토"

    validated.append({**match, **extra, "relation": relation, "rights": rights, "validation_priority": validation_priority, "manual_status": "미검증"})

validated.sort(key=lambda x: (x["validation_priority"], {"S":0,"A":1,"B":2,"C":3}.get(x["composer_grade"],9), -x["confidence"], x["composer"], x["title"]))
missing = [m for m in coverage["matches"] if m["status"] == "미보유"]
def score_value(item):
    value = item.get("score")
    if isinstance(value, (int, float)):
        return float(value)
    return {"A": 85, "B": 70, "C": 55, "D": 0}.get(item.get("tier"), 0)

missing.sort(key=lambda x: ({"A":0,"B":1,"C":2,"D":3}.get(x["tier"],9), {"S":0,"A":1,"B":2,"C":3}.get(x["composer_grade"],9), -score_value(x), x["composer"], x["title"]))
wave1 = []
per_composer = Counter()
for item in missing:
    if item["tier"] not in {"A", "B"} or item["composer_grade"] not in {"S", "A"}:
        continue
    limit = 12 if item["composer_grade"] == "S" else 7
    if per_composer[item["composer"]] >= limit:
        continue
    per_composer[item["composer"]] += 1
    wave1.append(item)
    if len(wave1) >= 500:
        break

payload = {
    "schema": "musicanote-classical-validation-v1",
    "coverage": str(coverage_path),
    "validation": validated,
    "validation_summary": dict(Counter(v["relation"] for v in validated)),
    "rights_summary": dict(Counter(v["rights"] for v in validated)),
    "priority_summary": dict(Counter(v["validation_priority"] for v in validated)),
    "wave1": wave1,
    "wave1_composers": len(per_composer),
}
output_path.parent.mkdir(parents=True, exist_ok=True)
output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({k: payload[k] for k in ["validation_summary","rights_summary","priority_summary","wave1_composers"]} | {"validation":len(validated),"wave1":len(wave1)}, ensure_ascii=False, indent=2))
