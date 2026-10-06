import sys,json,importlib.util,hashlib
from pathlib import Path
import xml.etree.ElementTree as ET
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=False)
spec=importlib.util.spec_from_file_location("parser",Path(__file__).with_name("build-musicxml-search-index.py"));p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
pairs=json.loads(Path("evaluation/real-cases/five-pairs/manifest.json").read_text("utf8"))["pairs"]
for c in pairs:
 if c["caseId"] not in ("RC-003","RC-004","RC-005"):continue
 path=Path(c["uploadPath"]);parsed=p.parse_musicxml(path);root=p.read_root(path)
 streams=parsed["streams"]
 # Choose highest parser melody-role score, independent of expected match/region.
 s=streams[0];events=[];meter_by_ordinal={};timeline=[];current=None
 part=next(x for x in root if p.tag(x)=='part' and x.get('id')==s['part'])
 for ordinal,measure in enumerate([x for x in part if p.tag(x)=='measure'],1):
  attributes=p.child(measure,'attributes');time=p.child(attributes,'time') if attributes is not None else None
  if time is not None:
   value=p.text(time,'beats','')+'/'+p.text(time,'beat-type','')
   if value!=current:timeline.append({'measureOrdinal':ordinal,'meter':value})
   current=value
  meter_by_ordinal[ordinal]=current
 for i,n in enumerate(s["notes"]):
  label=n.get('mn',str(n['m']))
  try:label=int(label)
  except ValueError:pass
  events.append({"id":f"upload-{i}","kind":"note","pitchMidi":n["p"],"spelling":n.get("s"),"onset":n["o"],"durationRatio":n["d"],"measure":label,"measureOrdinal":n["m"],"meter":meter_by_ordinal[n['m']],"beat":n.get("b"),"partId":s["part"],"voice":s["voice"],"staff":s['staff']})
 meters=set(meter_by_ordinal.values())
 meter=next(iter(meters)) if len(meters)==1 else "unknown"
 record={"case":c,"input":{"identity":{"sourceId":"private-upload:"+parsed["hash"],"streamId":s["id"]},"sourceHash":parsed["hash"],"parserVersion":"build-musicxml-search-index.py:"+hashlib.sha256(Path("scripts/build-musicxml-search-index.py").read_bytes()).hexdigest()+";upload-context:"+hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),"meter":meter,"meterTimeline":timeline,"events":events},"streamAudit":[{"id":x["id"],"role":x["role"],"notes":len(x["notes"])} for x in streams],"selectedStream":s["id"]}
 (out/(c["caseId"]+".json")).write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding="utf8")
 print(c["caseId"],s["id"],len(events),meter)
