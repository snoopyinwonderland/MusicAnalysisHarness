"""Preserve the review and full score; do not modify the source or production index."""
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

work_id = 'work-16741cf68d493e35'
out = Path(__file__).parent / 'reports/reviewer-cases/especially-first-phrase-2026-09-23'
out.mkdir(parents=True, exist_ok=True)
work = json.load(urlopen(f'http://127.0.0.1:5173/api/work/{work_id}?structure=1', timeout=60))
xml = work['xml']
selected = work.get('structureWork', work)
review = {
 'work_id': work_id, 'source_sha256': hashlib.sha256(xml.encode()).hexdigest(),
 'reviewer_text': '이 악보의 1번 프레이즈는 1번 마디부터 4번 마디까지 같은데 경계가 잘못 분석되었습니다.',
 'status': 'reviewer-proposed-range', 'training_eligible': False,
 'proposed_span': {'start_quarter': 0, 'end_quarter_exclusive': 16, 'start_measure': 1, 'end_measure_inclusive': 4},
 'context': 'Full XML and API snapshot retained, including preceding/following material.',
 'diagnosis': {'current_boundary_index': 9, 'current_next_onset': 11,
  'cues': selected['phraseAnalysis']['boundaries'][9]['cues'],
  'source_conflict': 'm3 F5: type half + dot versus duration 512 at divisions 256; root D5 duration 768.',
  'missing_boundary': 'm5 start index11 onset16: no temporal gap; strength below threshold.',
  'production_modified': False},
}
for name, content in [('source.musicxml', xml), ('api-snapshot.json', json.dumps(work, ensure_ascii=False, indent=2)), ('reviewer-feedback.json', json.dumps(review, ensure_ascii=False, indent=2))]:
 target=out/name
 if target.exists():
  raise RuntimeError(f'Refusing to overwrite existing snapshot: {target}')
 target.write_text(content, encoding='utf-8')
print(out)
