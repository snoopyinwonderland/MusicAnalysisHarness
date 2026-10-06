"""Capture this reviewer case; measure choices are labels, never analyzer rules."""
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen
from single_score_melody_review import parse_source, fq, q

work_id='work-6ce4be62f719206b'
source=Path('MusicXML/3. Three Times a Lady, Piano Solo.musicxml.xml')
out=Path('reports/reviewer-cases/three-times-a-lady-phrase-alternatives-2026-09-22')
out.mkdir(parents=True,exist_ok=False)
data=source.read_bytes()
digest,events,warnings=parse_source(data)
snapshot=urlopen(f'http://127.0.0.1:5173/api/work/{work_id}?structure=1').read()
api=json.loads(snapshot)
if api['sourceId']!=source.name: raise ValueError('Unexpected source')
def anchor(measure,pitch):
    matches=[e for e in events if e['part']=='P1' and e['staff']=='1' and e['printedMeasure']==str(measure) and e['spelling']==pitch]
    if not matches: raise ValueError('Anchor not found')
    return min(matches,key=lambda e:fq(e['onset']))
start=anchor(5,'C6'); short=anchor(8,'Bb5'); long=anchor(11,'Ab4')
def span(last):
    return dict(start=start['onset'],end=q(fq(last['onset'])+fq(last['duration'])),endConvention='exclusive-note-release',startEventId=start['id'],lastEventId=last['id'])
record=dict(schema_name='musicanote-experimental-case-feedback',schema_version='0.1.0',
    workId=work_id,title=api['title'],sourceHash=digest,recorded_date='2026-09-22',
    human_verbatim='이 악보는 5번째 마디 앞은 전주, 첫 프레이즈는 1. 5번째 마디부터 8번째 마디 첫 번째 2분음표까지 또는 2. 5번째 마디부터 11번째 마디 첫 음 라까지로 볼 수 있습니다.',
    source_correction='User subsequently supplied this local work URL instead of the remote-desktop URL.',
    introduction=dict(start=q(fq(events[0]['onset'])*0),end=start['onset']),
    alternatives=[dict(id='A',span=span(short),status='human-proposed'),dict(id='B',span=span(long),status='human-proposed')],
    selected=None,training_eligible=False,production_applied=False,
    clarification='The XML pitch at measure 11 onset is Ab4, not A natural. User wording retained. Ending at note release is an assistant normalization, not a separately confirmed boundary coordinate.',
    contextEventIds=[e['id'] for e in events if 4<=e['measureOrdinal']<=12],
    provenance=dict(xml='source.musicxml',events='events.json',automaticSnapshot='automatic-snapshot.json'),
    parseWarnings=warnings)
(out/'source.musicxml').write_bytes(data)
(out/'automatic-snapshot.json').write_bytes(snapshot)
(out/'events.json').write_text(json.dumps(events,ensure_ascii=False,indent=2),encoding='utf-8')
(out/'human-annotation.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
assert hashlib.sha256((out/'source.musicxml').read_bytes()).hexdigest()==digest
print(json.dumps(record,ensure_ascii=False,indent=2))
