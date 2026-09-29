"""Train-only appendix contract audit; literal doubling is not musical redundancy."""
import argparse
from collections import Counter
import hashlib
import html
import json
from pathlib import Path
from .cadential_six_four_audit import digest
from .harmony_case_retrieval import load_prepared_package
from .harmony_review_cohort import validate_split
from .harmony_review_supplement import verified_annotations, context_excerpt
from .score_reduction import VERSION, observe, proposal, notation_record, bounds
from .formal_ir import q


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def build(manifest_path, output):
    out = Path(output)
    if out.exists(): raise ValueError('output_exists')
    entries = json.loads(Path(manifest_path).read_bytes())['entries']
    validate_split(entries)
    entries = [e for e in entries if e['split'] == 'train' and e['collection_id'] in ('mozart-sonatas','beethoven-sonatas')]
    if len({e['package_path'] for e in entries}) != len(entries): raise ValueError('duplicate_package')
    if any(e['rights'].get('internal_research_use') is not True for e in entries): raise ValueError('research_not_permitted')
    out.mkdir(parents=True)
    code = ['score_reduction.py','score_reduction_audit.py','harmony_curriculum.py',
            'harmony_case_retrieval.py','harmony_review_cohort.py','harmony_review_supplement.py',
            'foundation_sonata_audit.py','dominant_area_evidence.py','formal_ir.py','cadential_six_four_audit.py']
    contract = {'version': VERSION, 'manifest_sha256': digest(manifest_path), 'entries': entries,
        'code_hashes': {n: digest(Path(__file__).with_name(n)) for n in code},
        'selection': 'all literal exact doubling groups; save first verified overlapping group of each kind per score',
        'production_enabled': False, 'training_eligible': False,
        'source_conditioned': 'annotation windows and boundary references only; no labels fed to literal detector'}
    write(out/'run-contract.json', contract)
    scores, cases, totals, excluded = [], [], Counter(), Counter()
    for e in entries:
        folder = Path(e['package_path'])
        if digest(e['score_source_path']) != e['score_sha256']: raise ValueError('source_hash_mismatch')
        hashes = {n: digest(folder/n) for n in ('canonical_music_ir.json','imported_annotations.jsonl','alignment_records.jsonl')}
        p = load_prepared_package(folder); ir = p['ir']
        if ir['ir_document_id'] != e['ir_document_id'] or ir['score']['score_id'] != e['score_id']: raise ValueError('identity_mismatch')
        original = json.dumps(ir, sort_keys=True)
        valid, skipped = verified_annotations(p,e); excluded.update(skipped)
        end = max(bounds(s['span'])[1] for s in ir['sounding_events'] if s['span']['start'] != s['span']['end'])
        observation = observe(ir, {'start':q(0),'end':q(end)})
        counts = Counter(g['kind'] for g in observation['exact_doublings']); totals.update(counts)
        write(out/(folder.name+'-inventory.json'), observation)
        chosen = set()
        for group in observation['exact_doublings']:
            if group['kind'] in chosen: continue
            ga,gb = bounds(group['span'])
            matches = [a for a in valid if bounds(a['target']['span'])[0] < gb and bounds(a['target']['span'])[1] > ga]
            if not matches: continue
            chosen.add(group['kind'])
            target = {'start':q(min(ga,min(bounds(a['target']['span'])[0] for a in matches))),
                      'end':q(max(gb,max(bounds(a['target']['span'])[1] for a in matches)))}
            boundary_refs = [{'id':a['annotation_id']+':'+side,'time':a['target']['span'][side],
                              'origin':'source_annotation'} for a in matches for side in ('start','end')]
            reduced = proposal(ir,target,[{'kind':'group_doubling','event_ids':group['event_ids'],
                                 'evidence_refs':['literal-exact-doubling']}],boundary_refs)
            assert reduced['boundary_refs'] == boundary_refs
            assert len(reduced['operations'][0]['source_events']) == len(group['event_ids'])
            excerpt = context_excerpt(ir,target)
            cid = 'app_'+hashlib.sha256((ir['ir_document_id']+'|'+group['kind']+'|'+group['event_ids'][0]).encode()).hexdigest()[:16]
            source_refs = {n['source_ref_id'] for n in excerpt['note_events']}
            case = {'case_id':cid,'identity':e,'package_hashes':hashes,'group':group,'proposal':reduced,
                'context_excerpt':excerpt,
                'source_references':[r for r in ir['source_references'] if r['source_ref_id'] in source_refs],
                'source_annotations':matches,
                'notation_records':[notation_record(a['raw_label'],'dcml_case_sensitive','local_chord',a['annotation_id']) for a in matches],
                'human_review':None,'musical_gold':False,'production_enabled':False,'training_eligible':False}
            write(out/(cid+'.json'),case)
            cases.append({'case_id':cid,'score':folder.name,'kind':group['kind'],
                'measure':matches[0]['raw_fields'].get('mn'), 'label':matches[0]['raw_label'],
                'event_ids':group['event_ids'],'sha256':digest(out/(cid+'.json'))})
        if json.dumps(ir,sort_keys=True) != original: raise ValueError('ir_mutated')
        if any(digest(folder/n) != sha for n,sha in hashes.items()): raise ValueError('package_mutated')
        scores.append({'score':folder.name,'identity':e,'package_hashes':hashes,
                       'events':len(observation['events']),'grace_pending':len(observation['grace_events_pending_role']),
                       'counts':dict(counts),'verified_annotations':len(valid),
                       'inventory_sha256':digest(out/(folder.name+'-inventory.json'))})
    summary = {'score_count':len(scores),'literal_groups':dict(totals),'saved_cases':len(cases),
               'events':sum(s['events'] for s in scores),'grace_pending':sum(s['grace_pending'] for s in scores),
               'verified_annotations':sum(s['verified_annotations'] for s in scores)}
    report = {'version':VERSION,'summary':summary,'scores':scores,'cases':cases,
        'excluded_annotations':dict(excluded),'contract_sha256':digest(out/'run-contract.json'),
        'source_ir_unchanged':True,'blind_reduction_accuracy_measured':False,'production_enabled':False}
    write(out/'report.json',report)
    return report


def render_examples(output):
    """First saved case for each composer, original engraved score, no auto reduction."""
    from .engraving import render_musicxml_pages
    from .harmony_visual_review import system_fragments
    from xml.etree import ElementTree as ET
    out=Path(output); report=json.loads((out/'report.json').read_text(encoding='utf-8'))
    verification=json.loads((out/'verification.json').read_text(encoding='utf-8'))
    quarantined=set(verification['quarantined_case_ids'])
    selected=[]; seen=set(); blocks=[]; mappings=[]; skipped=[]
    for row in report['cases']:
        case=json.loads((out/(row['case_id']+'.json')).read_text(encoding='utf-8'))
        coll=case['identity']['collection_id']
        if coll in seen: continue
        if row['case_id'] in quarantined:
            skipped.append({'case_id':row['case_id'],'reason':'context_xml_ir_mismatch'})
            continue
        ir=load_prepared_package(case['identity']['package_path'])['ir']
        pages,mapping=render_musicxml_pages(case['identity']['score_source_path'],ir)
        if not mapping['complete'] or mapping['semantic_mismatches']:
            skipped.append({'case_id':row['case_id'],'reason':'render_mapping_not_exact','mapping':mapping})
            continue
        seen.add(coll); selected.append(row['case_id'])
        mappings.append({'case_id':row['case_id'],'mapping':mapping})
        refs={n for ev in case['proposal']['operations'][0]['source_events'] for n in ev['source_note_ids']}
        fragments=system_fragments(pages,{n['note_id'] for n in case['context_excerpt']['note_events']})
        svgs=[]; colored=set()
        for f in fragments:
            root=ET.fromstring(f['svg'])
            for node in root.iter():
                nid=node.get('data-id') or node.get('id')
                if nid in refs:
                    node.set('style','fill:#aa36b8;color:#aa36b8;stroke:#aa36b8'); colored.add(nid)
            svgs.append(ET.tostring(root,encoding='unicode'))
        if colored != refs: raise ValueError('missing_highlight_reference')
        pitches=', '.join(str(ev['pitch']) for ev in case['proposal']['operations'][0]['source_events'])
        blocks.append('<section><h2>'+html.escape(row['score'])+' · measure '+html.escape(str(row['measure']))+
            '</h2><p>보라색: 동일한 시작·끝과 철자를 가진 중복음. 제거해도 된다는 뜻이 아닙니다.</p><p>'+html.escape(pitches)+
            '</p><p>원주석(자동 추론 아님): '+html.escape(' → '.join(a['raw_label'] for a in case['source_annotations']))+
            '</p><a href="'+row['case_id']+'.json">원음·시간·출처·검토 기록 JSON</a>'+''.join(svgs)+'</section>')
    page='''<!doctype html><html lang="ko"><meta charset="utf-8"><title>부록 검증 — 원음 보존</title>
    <style>body{font:17px system-ui;margin:24px;background:#f5f6f8}section{background:white;padding:24px;margin:24px 0}svg{width:100%;height:auto}h1{font-size:26px}</style>
    <h1>부록 검증: 중복음 관찰과 분석적 축약을 분리</h1><p>원 MusicXML 악보입니다. 새 화성/멜로디 정답이나 완성된 축약 악보가 아닙니다. 각 작곡가의 첫 렌더링 검증 통과 사례를 표시합니다.</p>'''+''.join(blocks)+'''<script>
    document.querySelectorAll('svg').forEach(s=>{const g=s.querySelector('.system');if(g){const b=g.getBBox();s.setAttribute('viewBox',[b.x-100,b.y-180,b.width+200,b.height+360].join(' '));}});
    </script></html>'''
    (out/'index.html').write_text(page,encoding='utf-8')
    write(out/'render-report.json',{'selected':selected,'mappings':mappings,'skipped':skipped,'html_sha256':digest(out/'index.html')})


def verify(output):
    """Replay saved cases and independently compare context notes to raw MusicXML.

    Explicit indexed source XPath is required; never guess around a missing path.
    Verifies spelling, notated onset/duration and source voice/staff, not harmony.
    """
    import re
    from fractions import Fraction
    from xml.etree import ElementTree as ET
    from .dominant_area_evidence import _exact
    out=Path(output); report=json.loads((out/'report.json').read_text(encoding='utf-8'))
    contract=json.loads((out/'run-contract.json').read_text(encoding='utf-8'))
    if digest(out/'run-contract.json') != report['contract_sha256']: raise ValueError('contract_hash_mismatch')
    for name,sha in contract['code_hashes'].items():
        if digest(Path(__file__).with_name(name)) != sha: raise ValueError('code_hash_mismatch:'+name)
    cache={}; checked=set(); comparisons=0; mismatches=[]; quarantined=set(); passes=0
    for row in report['cases']:
        path=out/(row['case_id']+'.json')
        if digest(path) != row['sha256']: raise ValueError('case_hash_mismatch')
        case=json.loads(path.read_text(encoding='utf-8')); e=case['identity']; key=e['package_path']
        if key not in cache:
            if digest(e['score_source_path']) != e['score_sha256']: raise ValueError('score_hash_mismatch')
            for name,sha in case['package_hashes'].items():
                if digest(Path(key)/name) != sha: raise ValueError('package_hash_mismatch')
            ir=load_prepared_package(key)['ir']; xml={}
            root=ET.parse(e['score_source_path']).getroot()
            # Normalize only element namespace, never notes/pitches/timing.
            for el in root.iter(): el.tag=el.tag.rsplit('}',1)[-1]
            for pi,part in enumerate(root.findall('part'),1):
                divisions=1
                for mi,measure in enumerate(part.findall('measure'),1):
                    cursor=Fraction(0); previous=Fraction(0); ni=0
                    for el in measure:
                        if el.tag=='attributes' and el.findtext('divisions'):
                            divisions=int(el.findtext('divisions'))
                        elif el.tag in ('backup','forward'):
                            cursor+=Fraction(int(el.findtext('duration')),divisions)*(1 if el.tag=='forward' else -1)
                        elif el.tag=='note':
                            ni+=1; onset=previous if el.find('chord') is not None else cursor
                            if el.find('chord') is None: previous=onset
                            duration=Fraction(int(el.findtext('duration','0')),divisions)
                            p=el.find('pitch')
                            if p is not None:
                                xml[pi,mi,ni]=(part.get('id'),measure.get('number'),el.findtext('voice','1'),el.findtext('staff','1'),
                                    onset,duration,p.findtext('step'),Fraction(p.findtext('alter','0')),int(p.findtext('octave')))
                            if el.find('chord') is None and el.find('grace') is None: cursor+=duration
            cache[key]=(ir,xml)
        ir,xml=cache[key]
        old=case['proposal']; operations=[{k:v for k,v in op.items() if k in ('kind','event_ids','evidence_refs')} for op in old['operations']]
        if proposal(ir,old['target_span'],operations,old['boundary_refs']) != old: raise ValueError('proposal_replay_mismatch')
        refs={r['source_ref_id']:r for r in case['source_references']}
        for note in case['context_excerpt']['note_events']:
            ref=refs[note['source_ref_id']]; xpath=ref.get('source_xpath') or ''
            m=re.fullmatch(r'/score-partwise/part\[(\d+)\]/measure\[(\d+)\]/note\[(\d+)\]',xpath)
            if not m: raise ValueError('indexed_source_xpath_required')
            value=xml[tuple(map(int,m.groups()))]; p=note['written_pitch']
            expected=(ref['source_part_id'],str(ref['source_measure_number']),str(ref['source_voice']),str(ref['source_staff']),
                      _exact(note['onset_in_measure']),_exact(note['notated_duration_quarter']),p['step'],_exact(p['alter']),p['octave'])
            if value != expected:
                fields=['part','measure','voice','staff','onset','duration','step','alter','octave']
                group_notes={n for ev in old['operations'][0]['source_events'] for n in ev['source_note_ids']}
                mismatches.append({'case_id':row['case_id'],'note_id':note['note_id'],
                    'source_xpath':xpath,'source_musicxml':e['score_source_path'],
                    'source_measure':ref['source_measure_number'],'in_doubling_group':note['note_id'] in group_notes,
                    'differences':{f:{'xml':str(x),'ir':str(y)} for f,x,y in zip(fields,value,expected) if x!=y}})
                quarantined.add(row['case_id'])
            else: passes+=1
            checked.add((key,note['note_id'])); comparisons+=1
    result={'case_replays':len(report['cases']),'context_note_comparisons':comparisons,
            'unique_xml_notes_compared':len(checked),'exact_note_comparisons':passes,'score_packages':len(cache),
            'mismatches':mismatches,'quarantined_case_ids':sorted(quarantined),
            'fully_xml_matching_cases':len(report['cases'])-len(quarantined),
            'checks':['source_hash','package_hash','case_hash','code_hash','proposal_replay',
                      'xml_part_measure_voice_staff_pitch_onset_duration'],
            'musical_accuracy_measured':False}
    write(out/'verification.json',result)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--manifest'); parser.add_argument('--output',required=True)
    parser.add_argument('--render-only',action='store_true'); parser.add_argument('--verify-only',action='store_true'); args=parser.parse_args()
    if args.verify_only: print(json.dumps(verify(args.output),indent=2))
    elif args.render_only: render_examples(args.output)
    else: print(json.dumps(build(args.manifest,args.output)['summary'],indent=2))
