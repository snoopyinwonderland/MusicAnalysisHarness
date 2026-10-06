"""Capture reproducible, local reviewer evidence; never mutate source/index."""
import json
import hashlib
from pathlib import Path
from urllib.request import urlopen

work_id = 'work-d522a3088dac61cb'
out = Path(__file__).parent / 'reports/reviewer-cases/pillar-beat-anchors-2026-09-23'
out.mkdir(parents=True, exist_ok=True)
work = json.load(urlopen(f'http://127.0.0.1:5173/api/work/{work_id}?structure=1', timeout=60))
xml = work.pop('xml')
(out / 'source.musicxml').write_text(xml, encoding='utf-8')
(out / 'api-snapshot.json').write_text(json.dumps(work, ensure_ascii=False, indent=2), encoding='utf-8')
review = {
 'work_id': work_id, 'source_sha256': hashlib.sha256(xml.encode()).hexdigest(),
 'context': 'Full source retained; review focuses on measures 4–12.',
 'status': 'reviewer alternatives, not adjudicated gold labels',
 'feedback': {
  '4': '첫 F#은 쉼 뒤 진입. 기둥 후보로 검토.',
  '5': '현재 표시가 적절함.',
  '6': '두 음 모두 기둥 후보.',
  '7': 'A G', '8': 'F# G', '9': 'B A', '10': 'B A',
  '11': ['B A', 'B A B A'],
  '12': ['B D', 'B B D B G'],
 },
 'rationale': '4/4의 박 단위 지속, 쉼 뒤 진입, 도약, 업빗 D의 강박 타이 점유. B A B의 보조 움직임은 축약 가설이며 화성 판정 아님.',
 'training_eligible': False,
}
(out / 'reviewer-feedback.json').write_text(json.dumps(review, ensure_ascii=False, indent=2), encoding='utf-8')
print(out)
