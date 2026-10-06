"""Metamorphic XML test using the experimental, not production, adapter."""
import copy
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from single_score_melody_review import parse_source, hypotheses, fq


def split_notes(data, limit=10):
    root=ET.fromstring(data)
    for e in root.iter(): e.tag=e.tag.split('}')[-1]
    changes=[]
    types={'whole':'half','half':'quarter','quarter':'eighth','eighth':'16th'}
    for part in root.findall('part'):
        for mi,m in enumerate(part.findall('measure'),1):
            children=list(m)
            for ei,n in enumerate(children):
                if len(changes)>=limit: break
                if n.tag!='note' or n.find('pitch') is None: continue
                if any(n.find(tag) is not None for tag in ['chord','grace','tie','notations','beam','lyric','dot','time-modification']): continue
                if ei+1<len(children) and children[ei+1].tag=='note' and children[ei+1].find('chord') is not None: continue
                typ=n.findtext('type'); duration=n.findtext('duration')
                if typ not in types or not duration or int(duration)<=0 or int(duration)%2: continue
                a,b=copy.deepcopy(n),copy.deepcopy(n)
                for note,tie in [(a,'start'),(b,'stop')]:
                    note.attrib.pop('id',None)
                    note.find('duration').text=str(int(duration)//2)
                    note.find('type').text=types[typ]
                    note.insert(list(note).index(note.find('duration'))+1,ET.Element('tie',type=tie))
                    notation=ET.SubElement(note,'notations'); ET.SubElement(notation,'tied',type=tie)
                index=list(m).index(n);m.remove(n);m.insert(index,a);m.insert(index+1,b)
                changes.append(dict(part=part.attrib['id'],measureOrdinal=mi,sourceElementIndex=ei,type=typ,durationDivisions=int(duration)))
    return ET.tostring(root,encoding='utf-8',xml_declaration=True),changes


def normalize(data):
    _,events,warnings=parse_source(data)
    result=hypotheses(events)
    def facts(n): return {k:n[k] for k in ['part','staff','voice','onset','duration','pitch','spelling','printedMeasure','measureOrdinal']}
    byid={n['id']:n for n in result['sounding']}
    baseline=[facts(byid[id]) for id in result['baseline']]
    # Stable test indices only, not source IDs across edited XML.
    notes=[dict(id=f'test-{i}',kind='note',onset=float(fq(n['onset'])),durationRatio=float(fq(n['duration'])),pitchMidi=n['pitch'],
                measure=int(n['printedMeasure']) if str(n['printedMeasure']).isdigit() else n['measureOrdinal'],measureOrdinal=n['measureOrdinal']) for i,n in enumerate(baseline)]
    return dict(sounding=[facts(n) for n in result['sounding']],baseline=baseline,notes=notes,warnings=warnings+result['warnings'])


def run():
    root=Path('reports/phrase-tie-notation-2026-09-22');root.mkdir(parents=True,exist_ok=False)
    summaries=[]
    for id in ['S-STRUCT-004','S-STRUCT-005','S-STRUCT-006','three-times-a-lady']:
        data=(Path('reports/phrase-consistency-2026-09-22')/id/'source.musicxml').read_bytes()
        changed,changes=split_notes(data)
        before,after=normalize(data),normalize(changed)
        folder=root/id;folder.mkdir()
        (folder/'source.musicxml').write_bytes(data);(folder/'split.musicxml').write_bytes(changed)
        result=dict(case=id,sourceHash=hashlib.sha256(data).hexdigest(),variantHash=hashlib.sha256(changed).hexdigest(),changes=changes,
                    soundingEqual=before['sounding']==after['sounding'],baselineEqual=before['baseline']==after['baseline'],before=before,after=after)
        (folder/'normalization.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        summaries.append(dict(case=id,splitCount=len(changes),soundingEqual=result['soundingEqual'],baselineEqual=result['baselineEqual'],warnings=[before['warnings'],after['warnings']]))
    (root/'summary.json').write_text(json.dumps(summaries,indent=2),encoding='utf-8')
    print(json.dumps(summaries,indent=2))


if __name__=='__main__':run()
