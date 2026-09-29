"""Independent XML change whitelist and exact coordinate aliases for a repair."""
import argparse
from fractions import Fraction
import json
from pathlib import Path
from xml.etree import ElementTree as ET
from .source_sequence_audit import xml_rows
from .source_timing_diagnostics import inspect
from .tuplet_time_repair import digest


def elements(root):
    found={}
    def visit(node,path):
        found[path]=node; counts={}
        for child in node:
            counts[child.tag]=counts.get(child.tag,0)+1
            visit(child,path+'/'+child.tag+f'[{counts[child.tag]}]')
    visit(root,'/'+root.tag)
    return found


def verify_xml(source,derived,manifest):
    if digest(source)!=manifest['source_sha256'] or digest(derived)!=manifest['normalized_sha256']:
        raise ValueError('source_or_derived_hash_changed')
    old=elements(ET.parse(source).getroot()); new=elements(ET.parse(derived).getroot())
    if old.keys()!=new.keys(): raise ValueError('xml_structure_changed')
    edits={r['xpath']+'[1]':r for r in manifest['edits']}
    observed_edits=set();multiplier=Fraction(manifest['divisions_multiplier'])
    for path,a in old.items():
        b=new[path]
        if a.attrib!=b.attrib: raise ValueError('xml_attributes_changed:'+path)
        at=(a.text or '').strip();bt=(b.text or '').strip()
        if path in edits:
            edit=edits[path];d=Fraction(edit['source_divisions'])
            if Fraction(at)/d!=Fraction(edit['before_quarters']) or Fraction(bt)/(d*multiplier)!=Fraction(edit['after_quarters']):
                raise ValueError('repair_duration_differs_from_manifest')
            observed_edits.add(path)
        elif a.tag in ('divisions','duration','offset') and at:
            if Fraction(bt)!=Fraction(at)*multiplier: raise ValueError('unlisted_time_change:'+path)
        elif at!=bt: raise ValueError('non_time_content_changed:'+path)
    if observed_edits!=set(edits): raise ValueError('missing_edit_target')
    original,_=xml_rows(source);normalized,_=xml_rows(derived)
    if len(original)!=len(normalized): raise ValueError('event_count_changed')
    aliases=[]
    for a,b in zip(original,normalized):
        if a['xpath']!=b['xpath'] or a['token'][2:]!=b['token'][2:]: raise ValueError('pitch_tie_grace_or_event_order_changed')
        aliases.append({'source_xpath':a['xpath'],'original_global_quarter':a['global_onset'],
            'normalized_global_quarter':b['global_onset'],'original_local_quarter':a['token'][0],
            'normalized_local_quarter':b['token'][0],'original_duration_quarter':a['token'][1],
            'normalized_duration_quarter':b['token'][1],
            'automatic_external_annotation_retarget':False})
    return {'xml_structure_and_nontime_content_preserved':True,'edited_duration_count':len(edits),
        'event_count':len(aliases),'changed_global_onsets':sum(a['original_global_quarter']!=a['normalized_global_quarter'] for a in aliases),
        'coordinate_aliases':aliases,'original_sha256':manifest['source_sha256'],
        'normalized_sha256':manifest['normalized_sha256']}


def build(derived,output):
    if output.exists():raise ValueError('output_exists')
    proof=json.loads(derived.with_suffix('.repair.json').read_text(encoding='utf-8'))
    checked=verify_xml(Path(proof['original_source']),derived,proof)
    timing=inspect(derived)
    if timing['part_grid_disagreements'] or timing['source_parser_global_time_mismatches'] or timing['ambiguous_lane_events']:
        raise ValueError('normalized_timing_not_consistent')
    checked['timing_validation']=timing
    output.write_text(json.dumps(checked,ensure_ascii=False,indent=2),encoding='utf-8')
    return {k:v for k,v in checked.items() if k not in ('coordinate_aliases','timing_validation')}


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('derived',type=Path);ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();print(json.dumps(build(args.derived,args.output)))
