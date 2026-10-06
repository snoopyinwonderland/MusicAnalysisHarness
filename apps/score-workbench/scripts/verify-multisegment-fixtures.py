"""Validate generated fixtures with XML notation checks AND the production parser."""
import sys,json,hashlib,importlib.util
from pathlib import Path
from fractions import Fraction
from xml.etree import ElementTree as ET
root=Path(sys.argv[1])
target=root/"roundtrip-audit.json"
if target.exists(): raise RuntimeError("New audit output required")
spec=importlib.util.spec_from_file_location("production_parser",Path(__file__).with_name("build-musicxml-search-index.py"))
parser=importlib.util.module_from_spec(spec);spec.loader.exec_module(parser)
manifest=json.loads((root/"manifest.json").read_text("utf8"))
cases=json.loads((root/"evaluator/cases.json").read_text("utf8"))
audit=[];asset_events={}
for asset in manifest["assets"]:
    path=root/asset["path"];events=json.loads((root/asset["events"]).read_text("utf8"))
    assert hashlib.sha256(path.read_bytes()).hexdigest()==asset["hash"]
    xml=ET.parse(path).getroot();beats,unit=map(int,events["meter"].split("/"));bar=Fraction(beats*4,unit)
    ids=set();fragments={};tie_count=0
    for part in xml.findall("part"):
        pid=part.attrib["id"];onset=Fraction(0)
        for measure in part.findall("measure"):
            duration=Fraction(0)
            for note in measure.findall("note"):
                nid=note.attrib["id"];assert nid not in ids;ids.add(nid)
                d=Fraction(int(note.findtext("duration")),8);assert d>0
                ties={e.attrib["type"] for e in note.findall("tie")}
                notation={e.attrib["type"] for e in note.findall("notations/tied")};assert ties==notation
                pitch=None
                if note.find("pitch") is not None:
                    p=note.find("pitch");pitch=(int(p.findtext("octave"))+1)*12+parser.STEP[p.findtext("step")]+int(p.findtext("alter","0"))
                else: assert not ties
                eid=nid.split("-")[1]
                fragments.setdefault((pid,eid),[]).append((float(onset+duration),float(d),pitch,ties))
                duration+=d;tie_count+=len(ties)
            assert duration==bar,(path,pid,measure.attrib,duration,bar)
            onset+=duration
    for part in events["parts"]:
        for event in part["events"]:
            seq=fragments[(part["partId"],event["id"])]
            assert abs(seq[0][0]-event["onset"])<1e-8
            assert abs(sum(x[1] for x in seq)-event["durationRatio"])<1e-8
            assert all(x[2]==event["pitchMidi"] for x in seq)
            if event["kind"]=="note":
                for i,x in enumerate(seq):
                    assert ("stop" in x[3])==(i>0)
                    assert ("start" in x[3])==(i<len(seq)-1)
    parsed=parser.parse_musicxml(path)
    for part in events["parts"]:
        expected=[e for e in part["events"] if e["kind"]=="note"]
        stream=next((s for s in parsed["streams"] if s["id"]==part["partId"]+":1:1"),None)
        if not expected: assert stream is None;continue
        assert stream is not None
        assert len(stream["notes"])==len(expected),(path,len(stream["notes"]),len(expected))
        for actual,want in zip(stream["notes"],expected):
            assert actual["p"]==want["pitchMidi"] and abs(actual["o"]-want["onset"])<1e-8 and abs(actual["d"]-want["durationRatio"])<1e-8,(path,actual,want)
    rendered=next(x for x in manifest["render"] if x["path"]==asset["path"])
    svg="".join((root/p).read_text("utf8") for p in rendered["svgPaths"])
    asset_events[asset["path"]]=(events,ids,svg)
    audit.append({"path":asset["path"],"measureSums":True,"tieContinuity":True,"productionParserEquivalent":True,"tieTags":tie_count})
mapped=0
for case in cases:
    e=case["expected"];assert e["occurrenceCount"]==len(e["occurrences"])
    if "baseline" in case["tags"]: assert case["provenance"]["uploadHash"]==e["sourceHash"]
    assert e["distinctFamilies"]==len({o["familyId"] for o in e["occurrences"]})
    input_events,ids,svg=asset_events[case["query"]["musicXml"]]
    source_events=asset_events[e["sourceAsset"]][0]
    for occurrence in e["occurrences"]:
        for m in occurrence["mapping"]:
            for nid in m["inputXmlIds"]:
                assert nid in ids and ('id="'+nid+'"') in svg,(case["caseId"],nid)
            if m["sourceEventId"] is not None:
                source=next(p for p in source_events["parts"] if p["partId"]==occurrence["sourcePart"])
                note=next(n for n in source["events"] if n["id"]==m["sourceEventId"])
                assert note["pitchMidi"]==m["sourcePitch"] and note["durationRatio"]==m["sourceDuration"] and note["onset"]==m["sourceOnset"]
            mapped+=1
result={"assets":audit,"cases":len(cases),"mappedEvents":mapped,"allPassed":True,"searchExecuted":False,"humanListeningVerified":False}
assert sum(a["tieTags"] for a in audit)>0,"Fixtures must exercise actual ties"
target.write_text(json.dumps(result,indent=2),encoding="utf8")
print(json.dumps({"assets":len(audit),"cases":len(cases),"mappedEvents":mapped,"allPassed":True}))
