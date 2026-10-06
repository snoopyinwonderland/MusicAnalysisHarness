"""Offline single-score hypotheses. No paired score, labels, or production imports."""
import argparse, hashlib, html, json, statistics
from collections import defaultdict
from fractions import Fraction as F
from pathlib import Path
import xml.etree.ElementTree as ET

VERSION = 'single-score-melody-review/0.1'
def q(x): return {'n': x.numerator, 'd': x.denominator}
def fq(x): return F(x['n'], x['d'])

def parse_source(data):
    root = ET.fromstring(data)
    for el in root.iter(): el.tag = el.tag.split('}')[-1]
    if root.tag != 'score-partwise': raise ValueError('Only score-partwise is supported')
    digest = hashlib.sha256(data).hexdigest()
    events, warnings = [], []
    for part in root.findall('part'):
        offset, divisions, nominal = F(0), F(1), None
        for mi, measure in enumerate(part.findall('measure'), 1):
            cursor = last = maximum = F(0)
            last_voice = last_staff = '1'
            for ei, el in enumerate(measure):
                if el.tag == 'attributes':
                    if el.findtext('divisions'): divisions = F(el.findtext('divisions'))
                    time = el.find('time')
                    if time is not None:
                        try: nominal = sum(F(v) for v in time.findtext('beats').split('+')) * 4 / F(time.findtext('beat-type'))
                        except (AttributeError, ValueError): nominal = None
                    continue
                duration = F(el.findtext('duration', '0')) / divisions
                if el.tag == 'backup': cursor -= duration; continue
                if el.tag == 'forward': cursor += duration; maximum = max(maximum, cursor); continue
                if el.tag != 'note': continue
                chord, grace = el.find('chord') is not None, el.find('grace') is not None
                onset = last if chord else cursor
                voice = el.findtext('voice') or (last_voice if chord else '1')
                staff = el.findtext('staff') or (last_staff if chord else '1')
                last_voice, last_staff = voice, staff
                pitch = el.find('pitch'); midi = spelling = None
                if pitch is not None:
                    step, octave = pitch.findtext('step'), int(pitch.findtext('octave'))
                    alter = F(pitch.findtext('alter', '0'))
                    midi = float((octave+1)*12 + {'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}[step] + alter)
                    spelling = step + ({F(0):'',F(1):'#',F(-1):'b',F(2):'##',F(-2):'bb'}.get(alter, f'({alter})')) + str(octave)
                event = dict(id=f'{digest[:16]}:{part.attrib["id"]}:m{mi}:e{ei}',part=part.attrib['id'],staff=staff,voice=voice,
                    measureOrdinal=mi,printedMeasure=measure.get('number'),onset=q(offset+onset),duration=q(duration),pitch=midi,spelling=spelling,
                    rest=el.find('rest') is not None,grace=grace,chord=chord,beams=[dict(number=b.get('number'),value=b.text) for b in el.findall('beam')],
                    ties=[t.get('type') for t in el.findall('tie')],sourceElementIndex=ei)
                events.append(event)
                if not chord: last = onset
                if not chord and not grace: cursor += duration
                maximum = max(maximum, cursor, onset + (F(0) if grace else duration))
            pickup = measure.get('implicit') == 'yes' or (mi == 1 and nominal is not None and maximum < nominal)
            if cursor < 0: warnings.append(f'negative-cursor:{part.attrib["id"]}:{mi}')
            offset += maximum if pickup or nominal is None else max(maximum, nominal)
    return digest, events, warnings

def sounding(events):
    chains, output, warnings = {}, [], []
    for e in sorted(events, key=lambda e:(fq(e['onset']),e['sourceElementIndex'])):
        if e['pitch'] is None or e['grace']: continue
        key = (e['part'],e['staff'],e['voice'],e['pitch'])
        prior = chains.get(key)
        if 'stop' in e['ties'] and prior and fq(prior['onset']) + fq(prior['duration']) == fq(e['onset']):
            prior['duration'] = q(fq(prior['duration']) + fq(e['duration']))
            prior['sourceIds'].append(e['id'])
            if 'start' not in e['ties']: chains.pop(key,None)
            continue
        if 'stop' in e['ties']: warnings.append('unresolved-tie:'+e['id'])
        item = dict(e, sourceIds=[e['id']], unresolvedTie='stop' in e['ties'])
        output.append(item)
        if 'start' in e['ties']: chains[key] = item
        else: chains.pop(key,None)
    return output, warnings

def hypotheses(events):
    """Conservative low-register filling hypotheses, not a melody classifier."""
    notes, warnings = sounding(events)
    if not notes: return dict(baseline=[],candidates=[],relations=[],warnings=warnings)
    # Source appearance order, not numeric part ID; keep staff scope fixed.
    part = next(e['part'] for e in events if e['pitch'] is not None)
    staff = min((n['staff'] for n in notes if n['part']==part), key=lambda x:int(x))
    groups = defaultdict(list)
    for n in notes:
        if n['part']==part and n['staff']==staff: groups[fq(n['onset'])].append(n)
    baseline = [max(g,key=lambda n:(n['pitch'],fq(n['duration']))) for _,g in sorted(groups.items())]
    relations = []
    for start in range(1,len(baseline)-1):
        for length in range(1,9):
            stop = start+length
            if stop >= len(baseline): break
            left,right = baseline[start-1],baseline[stop]; mid=baseline[start:stop]
            # Require multiple independent clues. Never delete a source event.
            if abs(left['pitch']-right['pitch'])>5: continue
            if min(left['pitch'],right['pitch'])-max(n['pitch'] for n in mid)<5: continue
            durations=[fq(n['duration']) for n in baseline[max(0,start-8):min(len(baseline),stop+8)]]
            typical=statistics.median(durations)
            if not typical or any(fq(n['duration'])>typical for n in mid): continue
            if length>1 and len(set(n['pitch']%12 for n in mid))>3: continue
            if any(len(n['sourceIds'])>1 or n['ties'] or n['unresolvedTie'] for n in mid): continue
            run=[left]+mid+[right]
            if len(set(n['voice'] for n in run))>1: continue
            if any(fq(a['onset'])+fq(a['duration'])!=fq(b['onset']) for a,b in zip(run,run[1:])): continue
            # A beamed continuation into either endpoint contradicts a clean split.
            if any(b['value'] in ('continue','end') for b in mid[0]['beams']): continue
            if any(b['value'] in ('begin','continue') for b in mid[-1]['beams']): continue
            relations.append(dict(id=f'rel-{len(relations)+1}',start=start,endExclusive=stop,
                sourceIds=[sid for n in mid for sid in n['sourceIds']],leftId=left['id'],rightId=right['id'],
                type='low-register-fill-candidate',status='unreviewed',confidence=None,
                evidence=['lower-register-between-nearby-endpoints','relative-duration','continuous-written-timeline']+(['limited-pitch-class-texture'] if length>1 else []),
                limitations=['may-be-intentional-melodic-leap','no-harmony-or-recurrence-validation']))
    candidates=[]
    for name,limit in [('single-fill',1),('texture-fill',8)]:
        removed=set(); chosen=[]
        for r in sorted(relations,key=lambda r:(r['start'],-r['endExclusive'])):
            if r['endExclusive']-r['start']>limit: continue
            if any(i in removed for i in range(r['start']-1,r['endExclusive']+1)): continue
            removed.update(range(r['start'],r['endExclusive']));chosen.append(r['id'])
        candidates.append(dict(name=name,eventIds=[n['id'] for i,n in enumerate(baseline) if i not in removed],relations=chosen,
            excludedIds=[n['id'] for i,n in enumerate(baseline) if i in removed],selected=False))
    return dict(scope=dict(part=part,staff=staff),baseline=[n['id'] for n in baseline],sounding=notes,candidates=candidates,relations=relations,warnings=warnings)

def run(paths,out):
    out=Path(out)
    if out.exists(): raise ValueError('Refusing overwrite')
    out.mkdir(parents=True)
    cards=[]
    for i,path in enumerate(paths,1):
        data=Path(path).read_bytes();digest,events,warnings=parse_source(data);result=hypotheses(events)
        report=dict(version=VERSION,source=Path(path).name,sourceHash=digest,events=events,parseWarnings=warnings,**result)
        folder=out/str(i);folder.mkdir();(folder/'source.musicxml').write_bytes(data)
        (folder/'review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        byid={n['id']:n for n in result.get('sounding',[])}
        rows=[]
        for r in result['relations']:
            ns=[byid[id] for id in result['baseline'][r['start']:r['endExclusive']]]
            left,right=byid[r['leftId']],byid[r['rightId']]
            fmt=lambda n:f"m{n['printedMeasure']} {n['spelling']} ({fq(n['duration'])}q)"
            rows.append('<tr><td>'+html.escape(fmt(left))+'</td><td class="candidate">'+html.escape(' → '.join(map(fmt,ns)))+'</td><td>'+html.escape(fmt(right))+'</td><td>'+html.escape(', '.join(r['evidence']))+'</td></tr>')
        cards.append(f'<section><h2>{html.escape(Path(path).name)}</h2><p>원본 음표/쉼 {len(events)}개 · 상성부 최고음 baseline {len(result["baseline"])}개 · 미확정 관계 {len(rows)}개</p><p>후보별 제외 제안: '+html.escape(str([(c['name'],len(c['excludedIds'])) for c in result['candidates']]))+f'</p><a href="{i}/review.json">전체 사실·후보 JSON</a> · <a href="{i}/source.musicxml">원본 악보</a><table><tr><th>앞 중심음 후보</th><th>낮은 채움음 후보 — 삭제 확정 아님</th><th>뒤 중심음 후보</th><th>근거</th></tr>'+''.join(rows)+'</table></section>')
        print(json.dumps(dict(source=Path(path).name,events=len(events),baseline=len(result['baseline']),relations=len(rows),candidates=[(c['name'],len(c['excludedIds'])) for c in result['candidates']],warnings=len(warnings)+len(result['warnings'])),ensure_ascii=False))
    (out/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>단일 악보 선율 후보 검토</title><style>body{font:16px/1.6 sans-serif;margin:32px;max-width:1400px}table{border-collapse:collapse;width:100%}td,th{border:1px solid #ccc;padding:8px}.candidate{background:#fff2ce}section{margin:36px 0}</style><h1>단일 악보 선율 후보 · 오프라인 검토</h1><p>다른 판본·정답·기존 Phrase 경계를 입력하지 않았습니다. 노란 음표는 반주 확정이 아니라 검토 후보입니다. 원본/tie/음가는 그대로 보존합니다. 운영 분석과 악보 viewer는 변경하지 않았습니다.</p>'+''.join(cards),encoding='utf-8')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('sources',nargs='+');a=p.parse_args();run(a.sources,a.out)
