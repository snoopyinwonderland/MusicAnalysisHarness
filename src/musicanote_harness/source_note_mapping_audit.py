"""Non-destructive source-link repair candidates and independent XML comparison.

Does not republish dataset manifests, change IDs/timing/voices, or overwrite old
packages. Candidate IR must not replace an immutable IR revision silently.
"""
import argparse
from collections import Counter
from copy import deepcopy
from fractions import Fraction
import hashlib
import json
from pathlib import Path
from xml.etree import ElementTree as ET
from .engraving import musicxml_with_canonical_ids, SOURCE_MAPPING_VERSION
from .source_enrichment import enrich_from_mapped_musicxml
from .cadential_six_four_audit import digest


def write(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')


def xml_inventory(source):
    root=ET.parse(source).getroot()
    for el in root.iter(): el.tag=el.tag.rsplit('}',1)[-1]
    rows={}
    for pi,part in enumerate(root.findall('part'),1):
        divisions=1
        for mi,measure in enumerate(part.findall('measure'),1):
            cursor=previous=Fraction(0); ni=0
            for el in measure:
                if el.tag=='attributes' and el.findtext('divisions'): divisions=int(el.findtext('divisions'))
                elif el.tag in ('backup','forward'):
                    cursor+=Fraction(int(el.findtext('duration')),divisions)*(1 if el.tag=='forward' else -1)
                elif el.tag=='note':
                    ni+=1; onset=previous if el.find('chord') is not None else cursor
                    if el.find('chord') is None: previous=onset
                    duration=Fraction(int(el.findtext('duration','0')),divisions)
                    p=el.find('pitch')
                    if p is not None:
                        rows[f'/score-partwise/part[{pi}]/measure[{mi}]/note[{ni}]']={
                            'part':part.get('id'),'measure':measure.get('number'),'voice':el.findtext('voice'),
                            'staff':int(el.findtext('staff','1')),'onset':str(onset),'duration':str(duration),
                            'step':p.findtext('step'),'alter':str(Fraction(p.findtext('alter','0'))),
                            'octave':int(p.findtext('octave'))}
                    if el.find('chord') is None and el.find('grace') is None: cursor+=duration
    return rows


def compare(ir,raw,eligible=None):
    refs={r['source_ref_id']:r for r in ir['source_references']}
    results={}
    def f(x): return str(Fraction(x['numerator'],x['denominator']))
    for n in ir['note_events']:
        nid=n['note_id']; ref=refs[n['source_ref_id']]; loc=ref.get('source_xpath')
        if eligible is not None and nid not in eligible:
            results[nid]={'status':'unresolved_mapping'}; continue
        if loc not in raw:
            results[nid]={'status':'missing_locator'}; continue
        p=n['written_pitch']
        expected={'part':ref['source_part_id'],'measure':str(ref['source_measure_number']),
            'voice':ref['source_voice'],'staff':ref['source_staff'],'onset':f(n['onset_in_measure']),
            'duration':f(n['notated_duration_quarter']),'step':p['step'],'alter':f(p['alter']),'octave':p['octave']}
        diffs={k:{'xml':v,'ir':expected[k]} for k,v in raw[loc].items() if v!=expected[k]}
        results[nid]={'status':'mismatch' if diffs else 'exact','source_xpath':loc,'differences':diffs}
    return results


def build(previous_audit,output):
    previous=Path(previous_audit); out=Path(output)
    if out.exists(): raise ValueError('output_exists')
    oldreport=json.loads((previous/'report.json').read_text(encoding='utf-8'))
    entries=[s['identity'] for s in oldreport['scores']]
    if any(e['split']!='train' or e['rights'].get('internal_research_use') is not True for e in entries):
        raise ValueError('train_internal_research_only')
    out.mkdir(parents=True)
    contract={'version':SOURCE_MAPPING_VERSION,'previous_report_sha256':digest(previous/'report.json'),
        'code_hashes':{n:digest(Path(__file__).with_name(n)) for n in ('engraving.py','source_enrichment.py','source_note_mapping_audit.py')},
        'publication':'candidate_only_not_dataset_manifest_migration','production_data_modified':False}
    write(out/'run-contract.json',contract)
    scores=[]; case_checks=[]; corrected_notes=0; changed_refs=0; beforetot=Counter(); aftertot=Counter()
    for e in entries:
        folder=Path(e['package_path']); name=e['collection_id']+'--'+folder.name
        target=out/name; target.mkdir()
        paths={n:folder/n for n in ('canonical_music_ir.json','imported_annotations.jsonl','alignment_records.jsonl')}
        oldhashes={n:digest(p) for n,p in paths.items()}
        if digest(e['score_source_path']) != e['score_sha256']: raise ValueError('source_hash_mismatch')
        ir=json.loads(paths['canonical_music_ir.json'].read_text(encoding='utf-8')); before=deepcopy(ir)
        raw=xml_inventory(e['score_source_path']); oldcheck=compare(ir,raw)
        xml,mapping=musicxml_with_canonical_ids(e['score_source_path'],ir)
        enrich_from_mapped_musicxml(ir,xml)
        newcheck=compare(ir,raw,set(mapping['matched_note_ids_in_source_order']))
        # No event identities, times, logical voices, pitches, tie membership or
        # annotations may be silently migrated by this source-link repair.
        for a,b in zip(before['note_events'],ir['note_events']):
            if {k:v for k,v in a.items() if k not in ('notation','grace')} != {k:v for k,v in b.items() if k not in ('notation','grace')}:
                raise ValueError('core_note_changed')
            if {k:v for k,v in a['grace'].items() if k!='slash'} != {k:v for k,v in b['grace'].items() if k!='slash'}:
                raise ValueError('grace_identity_changed')
        for k in ('score','ir_document_id','sounding_events','tie_chains','attack_events','voices'):
            if before[k]!=ir[k]: raise ValueError('core_changed:'+k)
        changes=[]
        oldrefs={r['source_ref_id']:r for r in before['source_references']}
        for r in ir['source_references']:
            if r!=oldrefs[r['source_ref_id']]:
                changes.append({'source_ref_id':r['source_ref_id'],'before':oldrefs[r['source_ref_id']],'after':r})
        oldnotes={n['note_id']:n for n in before['note_events']}
        notation_changes=[{'note_id':n['note_id'],'before':oldnotes[n['note_id']]['notation'],'after':n['notation']}
                          for n in ir['note_events'] if n['notation']!=oldnotes[n['note_id']]['notation']]
        fixed=[nid for nid,r in oldcheck.items() if r['status']=='mismatch' and newcheck[nid]['status']=='exact']
        corrected_notes+=len(fixed); changed_refs+=len(changes)
        bc=Counter(r['status'] for r in oldcheck.values()); ac=Counter(r['status'] for r in newcheck.values())
        beforetot.update(bc); aftertot.update(ac)
        # Unmatched stale locators remain in the archival candidate for diff,
        # but newcheck marks them unusable. Never publish this file alone.
        write(target/'candidate_ir.json',ir)
        write(target/'repair.json',{'identity':e,'input_hashes':oldhashes,'mapping':mapping,
            'before_comparison':oldcheck,'after_comparison':newcheck,'source_ref_changes':changes,
            'notation_changes':notation_changes,'fixed_note_ids':fixed,
            'candidate_sha256':digest(target/'candidate_ir.json'), 'usable_only_with_mapping_gate':True})
        for row in oldreport['cases']:
            case=json.loads((previous/(row['case_id']+'.json')).read_text(encoding='utf-8'))
            if case['identity']['package_path']!=e['package_path']: continue
            ids={n['note_id'] for n in case['context_excerpt']['note_events']}
            counts=dict(Counter(newcheck[n]['status'] for n in ids))
            case_checks.append({'case_id':row['case_id'],'score':name,'after_counts':counts,
                'xml_context_verified':all(newcheck[n]['status']=='exact' for n in ids),
                'candidate_ir':str((target/'candidate_ir.json').resolve())})
        if any(digest(p)!=oldhashes[n] for n,p in paths.items()): raise ValueError('original_package_modified')
        if digest(e['score_source_path'])!=e['score_sha256']: raise ValueError('original_xml_modified')
        scores.append({'score':name,'before':dict(bc),'after':dict(ac),'fixed_notes':len(fixed),
            'changed_source_refs':len(changes),'changed_notation_records':len(notation_changes),
            'voice_hint_disagreements':len(mapping['voice_hint_disagreements']),
            'unresolved_note_ids':mapping['unmatched_ir_note_ids'],
            'repair_sha256':digest(target/'repair.json')})
    report={'version':SOURCE_MAPPING_VERSION,'scores':scores,'case_checks':case_checks,
        'summary':{'scores':len(scores),'before':dict(beforetot),'after':dict(aftertot),
                   'fixed_note_links':corrected_notes,'changed_source_refs':changed_refs,
                   'previous_cases_verified':sum(c['xml_context_verified'] for c in case_checks),
                   'previous_cases_total':len(case_checks)},
        'original_xml_packages_and_annotations_unchanged':True,'core_ids_timing_pitches_unchanged':True,
        'production_data_modified':False,'contract_sha256':digest(out/'run-contract.json')}
    write(out/'report.json',report)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--previous-audit',required=True); parser.add_argument('--output',required=True)
    args=parser.parse_args(); print(json.dumps(build(args.previous_audit,args.output)['summary'],indent=2))
