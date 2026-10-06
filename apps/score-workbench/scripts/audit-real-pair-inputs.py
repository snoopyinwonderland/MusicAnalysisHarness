import sys,json,importlib.util
from pathlib import Path
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=False)
spec=importlib.util.spec_from_file_location('parser',Path(__file__).with_name('build-musicxml-search-index.py'));p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
manifest=json.loads(Path('evaluation/real-cases/five-pairs/manifest.json').read_text('utf8'))
summary=[]
for case in manifest['pairs']:
 for role in ('upload','reference'):
  path=Path(case[role+'Path']);parsed=p.parse_musicxml(path);root=p.read_root(path);parts=[]
  for part in [x for x in root if p.tag(x)=='part']:
   meter=None;measures=[]
   for ordinal,m in enumerate([x for x in part if p.tag(x)=='measure'],1):
    a=p.child(m,'attributes');t=p.child(a,'time') if a is not None else None
    if t is not None:meter=p.text(t,'beats','')+'/'+p.text(t,'beat-type','')
    measures.append({'ordinal':ordinal,'xmlLabel':m.get('number'),'implicit':m.get('implicit'),'meter':meter})
   parts.append({'partId':part.get('id'),'measures':measures})
  record={'caseId':case['caseId'],'role':role,'path':str(path),'parsed':parsed,'parts':parts,'warnings':['Stream is upper note of simultaneous chords, not all chord tones.','Pitches are written MusicXML pitches; transposing-instrument audit required.','Original tie pieces remain in XML; parser notes merge ties.']}
  (out/(case['caseId']+'-'+role+'.json')).write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8')
  summary.append({'caseId':case['caseId'],'role':role,'hash':parsed['hash'],'streams':[{'id':s['id'],'partName':s['partName'],'notes':len(s['notes']),'role':s['role']} for s in parsed['streams']]})
(out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(summary,ensure_ascii=False))
