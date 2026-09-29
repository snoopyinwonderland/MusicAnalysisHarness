"""Opt-in exact tuplet export-rounding repair, with cross-part corroboration.

Original XML remains authoritative and untouched. A derived XML plus a manifest
records all edits. No harmony labels, composer, title or measure numbers are rules.
"""
import argparse
from copy import deepcopy
from fractions import Fraction
import hashlib
import json
from math import lcm
from pathlib import Path
from xml.etree import ElementTree as ET

VERSION = 'corroborated-tuplet-rounding-0.1.0'
TYPES = {'maxima':32,'long':16,'breve':8,'whole':4,'half':2,'quarter':1,
         'eighth':Fraction(1,2),'16th':Fraction(1,4),'32nd':Fraction(1,8),
         '64th':Fraction(1,16),'128th':Fraction(1,32),'256th':Fraction(1,64)}


def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def expected_duration(note):
    tm=note.find('time-modification')
    if tm is None or note.find('grace') is not None or note.findtext('type') not in TYPES:
        return None
    actual=int(tm.findtext('actual-notes','0')); normal=int(tm.findtext('normal-notes','0'))
    if actual<=0 or normal<=0: return None
    dots=len(note.findall('dot'))
    return Fraction(TYPES[note.findtext('type')])*sum((Fraction(1,2**i) for i in range(dots+1)))*Fraction(normal,actual)


def measure_extent(measure, divisions, changes=None):
    cursor=previous=extent=Fraction(0)
    for el in measure:
        if el.tag=='attributes' and el.findtext('divisions'):
            divisions=int(el.findtext('divisions'))
        elif el.tag in ('backup','forward'):
            cursor+=Fraction(el.findtext('duration','0'))/divisions*(1 if el.tag=='forward' else -1)
            extent=max(extent,cursor)
        elif el.tag=='note':
            onset=previous if el.find('chord') is not None else cursor
            if el.find('chord') is None: previous=onset
            duration=(changes or {}).get(id(el),Fraction(el.findtext('duration','0'))/divisions)
            extent=max(extent,onset+duration)
            if el.find('chord') is None and el.find('grace') is None: cursor+=duration
    return extent,divisions


def rounded_groups(measure, divisions):
    """Only explicit, complete, uniform, single-lane groups with <1 tick error."""
    group=None; result=[]; ordinal=0
    for el in measure:
        if el.tag=='attributes' and el.findtext('divisions'):
            divisions=int(el.findtext('divisions')); group=None
        if el.tag in ('backup','forward') and Fraction(el.findtext('duration','0'))!=0:
            group=None
        if el.tag!='note': continue
        ordinal+=1
        marks=el.findall('notations/tuplet')
        starts=[m for m in marks if m.get('type')=='start']
        stops=[m for m in marks if m.get('type')=='stop']
        if starts:
            # Nested groups are deliberately unsupported, not flattened.
            group=[] if len(starts)==1 and group is None else None
        if group is None: continue
        expected=expected_duration(el)
        if expected is None or el.find('chord') is not None:
            group=None; continue
        tm=el.find('time-modification')
        signature=(el.findtext('voice'),el.findtext('staff','1'),el.findtext('type'),len(el.findall('dot')),
                   tm.findtext('actual-notes'),tm.findtext('normal-notes'))
        duration=Fraction(el.findtext('duration','0'))/divisions
        group.append({'element':el,'ordinal':ordinal,'expected':expected,'duration':duration,
                      'divisions':divisions,'signature':signature})
        if stops:
            if (len(stops)==1 and len({r['signature'] for r in group})==1
                    and len(group)==int(signature[4]) and len({r['divisions'] for r in group})==1
                    and signature[0] is not None
                    and any(r['expected']!=r['duration'] for r in group)
                    and all(0<r['duration'] and abs((r['expected']-r['duration'])*divisions)<1 for r in group)
                    and all((r['expected']*divisions).denominator!=1 for r in group)):
                result.append(group)
            group=None
    return result


def normalize_tree(root):
    """Return a new tree and exact edit proposals, or no-op. No rounding tolerance."""
    root=deepcopy(root)
    if root.tag!='score-partwise': raise ValueError('unnamespaced_partwise_required')
    parts=root.findall('part')
    if len(parts)<2: raise ValueError('independent_part_corroboration_required')
    measures=[p.findall('measure') for p in parts]
    if len({len(ms) for ms in measures})!=1: raise ValueError('part_measure_count_mismatch')
    grids=[]
    for ms in measures:
        d=1; grid=[]
        for m in ms:
            incoming=d; extent,d=measure_extent(m,d)
            grid.append((extent,incoming))
        grids.append(grid)
    edits=[]; changes={}; multiplier=1
    for mi in range(len(measures[0])):
        extents=[g[mi][0] for g in grids]
        if len(set(extents))==1: continue
        if len({ms[mi].get('number') for ms in measures})!=1: continue
        proposals=[]
        for pi,ms in enumerate(measures):
            groups=rounded_groups(ms[mi],grids[pi][mi][1])
            if not groups: continue
            local={id(r['element']):r['expected'] for group in groups for r in group}
            target,_=measure_extent(ms[mi],grids[pi][mi][1],local)
            others=[extent for i,extent in enumerate(extents) if i!=pi]
            if not others or any(x!=target for x in others): continue
            proposals.append((pi,groups,target))
        # No voting between conflicting repairs; exactly one independently supported part.
        if len(proposals)!=1: continue
        pi,groups,target=proposals[0]
        for group in groups:
            for r in group:
                changes[id(r['element'])]=r['expected']
                multiplier=lcm(multiplier,(r['expected']*r['divisions']).denominator)
                edits.append({'xpath':f'/score-partwise/part[{pi+1}]/measure[{mi+1}]/note[{r["ordinal"]}]/duration',
                    'part':parts[pi].get('id'),'physical_measure':mi+1,'printed_measure':measures[pi][mi].get('number'),
                    'before_quarters':str(r['duration']),'after_quarters':str(r['expected']),
                    'source_divisions':r['divisions'],'group_ratio':f'{r["signature"][4]}:{r["signature"][5]}',
                    'corroborated_measure_duration':str(target),'reason':'explicit_complete_tuplet_and_other_parts_agree'})
    # Uniformly increase the existing divisions; preserve every other time value exactly.
    if changes:
        for part in parts:
            d=1
            for m in part.findall('measure'):
                for el in m:
                    if el.tag=='attributes' and el.find('divisions') is not None:
                        d=int(el.findtext('divisions'));el.find('divisions').text=str(d*multiplier)
                    for timing in el.iter():
                        if timing.tag not in ('duration','offset') or timing.text is None: continue
                        if el.tag=='note' and timing.tag=='duration' and id(el) in changes:
                            value=changes[id(el)]*d*multiplier
                        else: value=Fraction(timing.text)*multiplier
                        if value.denominator!=1: raise ValueError('non_integer_scaled_xml_time')
                        timing.text=str(value.numerator)
        corrected=[]
        for part in root.findall('part'):
            d=1; grid=[]
            for m in part.findall('measure'):
                extent,d=measure_extent(m,d);grid.append(extent)
            corrected.append(grid)
        if any(grid!=corrected[0] for grid in corrected[1:]):
            raise ValueError('uncorroborated_grid_difference_remains')
    return root,{'version':VERSION,'divisions_multiplier':multiplier,'edits':edits,
        'policy':'exact_type_dot_tuplet_ratio_complete_group_sub_tick_error_other_parts_agree',
        'source_overwrite':False,'harmonic_labels_used':False}


def repair(source, output):
    if output.exists() or output.with_suffix('.repair.json').exists(): raise ValueError('output_exists')
    source_hash=digest(source)
    root,report=normalize_tree(ET.parse(source).getroot())
    if not report['edits']: raise ValueError('no_corroborated_rounding_repair')
    output.parent.mkdir(parents=True,exist_ok=True)
    ET.ElementTree(root).write(output,encoding='utf-8',xml_declaration=True)
    report.update(original_source=str(source.resolve()),source_sha256=source_hash,
                  normalized_source=str(output.resolve()),normalized_sha256=digest(output))
    if digest(source)!=source_hash: raise ValueError('source_changed')
    output.with_suffix('.repair.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('source',type=Path);ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();r=repair(args.source,args.output)
    print(json.dumps({'edited_notes':len(r['edits']),'multiplier':r['divisions_multiplier'],'output':str(args.output)}))
