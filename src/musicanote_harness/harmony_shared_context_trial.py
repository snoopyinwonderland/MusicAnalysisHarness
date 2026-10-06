"""Frozen replay with same-harmony invariance checks on shared spelling sets."""
import argparse
from pathlib import Path
import sys
from .harmony_shared_context import augment as build, compare, VERSION
from .harmony_boundary_assessment_trial import run

BOUNDARY_KEY='shared_context'
TOP_KEYS={'shared_context_version','shared_context_preview'}
COUNTS_KEY='shared_context_counts'
TITLE='동일 문맥의 화음 유지·분할 대조'

def augment(baseline):
    result=build(baseline)
    for bi,b in enumerate(result['boundaries']):
        c=b['shared_context'];checks=[]
        if c['status']!='ready':continue
        maps=[]
        for rows in (result['hold_readings'],b['left']['readings'],b['right']['readings']):
            m={}
            for i,r in enumerate(rows):
                if not r['condition']['abstention_reasons']:m.setdefault(tuple(sorted(tuple(p) for p in r['members'])),i)
            maps.append(m)
        assignments=result['assignments']
        aids=sorted({min(assignments,key=lambda a:len(a['links']))['assignment_id'],max(assignments,key=lambda a:len(a['links']))['assignment_id']})
        for members in sorted(set(maps[0])&set(maps[1])&set(maps[2])):
            indices=[m[members] for m in maps]
            for aid in aids:
                comparison=compare(result,bi,*indices,aid)
                assert comparison['same_harmony_invariant_passed']
                checks.append({'indices':indices,'assignment_ref':aid,'passed':True})
        c['invariance_checks']=checks
        c['invariance_selection']='First unblocked reading per common spelling set; minimum/maximum link assignments, deduplicated. Not all combinations.'
    return result

def counts(e):
    return {'boundaries':1,e['status']:1,'geometry_patterns':len(e['patterns']),
            'same_harmony_checks':len(e.get('invariance_checks',[])),
            'withheld_shapes':len(e['withheld_pattern_reasons'])}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();run(a.source,a.output,stage=sys.modules[__name__])
