"""Multiscale pooled-note alternatives, without deleting ornaments or selecting truth.

The same note sequence may be a seventh unfolding or two triads. Keep both,
including timing support and the range of plausible boundary anchors.
"""
from collections import Counter,defaultdict
from fractions import Fraction as F
from itertools import product
import hashlib

from .formal_ir import q
from .harmony_joint import f,prepare
from .harmony_multiscale_shadow import continuous_sound
from .harmony_shared_tone_review import shapes,local_scorer
from .harmony_cost_diagnostic import transition

VERSION='distributed-competing-readings-0.1.0'
WIDTHS=(F(1,2),F(1),F(2))


def observe(ir,analysis_span=None):
    rows,neighbors=prepare(ir)
    if analysis_span is None:
        analysis_span={'start':q(0),'end':q(max((r['end'] for r in rows),default=F(0)))}
    start,end=f(analysis_span['start']),f(analysis_span['end'])
    if start<0 or end<start or (end==start and rows):raise ValueError('invalid_analysis_span')
    measures=ir.get('measures',[])
    grid=sorted({(f(m['global_start_quarter']),F(4,m['time_signature']['beat_type'])) for m in measures})
    def unit_at(t):return next((u for a,u in reversed(grid) if a<=t),F(1))
    score=local_scorer(ir,rows,neighbors,unit_at)
    points=sorted({r['start'] for r in rows if start<r['start']<end})
    pools={}
    def pool(a,b):
        if (a,b) not in pools:
            active=[r for r in rows if r['start']<b and r['end']>a]
            pcs={r['pitch']%12 for r in active}
            occupancy=defaultdict(F)
            for pc in pcs:
                intervals=sorted((max(a,r['start']),min(b,r['end'])) for r in active if r['pitch']%12==pc)
                finish=a
                for x,y in intervals:
                    occupancy[pc]+=max(F(0),y-max(x,finish));finish=max(finish,y)
            pools[(a,b)]={'active':active,'pcs':pcs,'occupancy':occupancy,
                           'continuous':continuous_sound(active,a,b)}
        return pools[(a,b)]
    alternatives=[];gates=Counter();tested=0
    for t in points:
        unit=unit_at(t)
        for wl,wr in product(WIDTHS,repeat=2):
            a,b=t-wl*unit,t+wr*unit
            if a<start or b>end:continue
            tested+=1
            touched={unit_at(a),unit_at(t)}|{u for x,u in grid if a<=x<b}
            if len(touched)!=1:
                gates['mixed_meter']+=1;continue
            left,right=pool(a,t),pool(t,b)
            if not left['continuous'] or not right['continuous']:
                gates['silence_inside_window']+=1;continue
            old,new=left['pcs'],right['pcs']
            ls,rs=shapes(old,3),shapes(new,3)
            if not ls or not rs:
                gates['not_two_complete_pooled_triads']+=1;continue
            unions=shapes(old|new,4)
            if len(old&new)!=2 or not unions:
                gates['not_two_common_pcs_with_seventh_union']+=1;continue
            # The right exclusive member can arrive after common tones. Its delay
            # stays explicit; never manufacture an attack at the proposed anchor.
            entering=[r for r in right['active'] if r['pitch']%12 in new-old and t<=r['start']<b]
            if not entering:
                gates['no_entering_member_attack']+=1;continue
            first=min(r['start'] for r in entering)
            leaving=[r for r in left['active'] if r['pitch']%12 in old-new]
            last=max(r['end'] for r in leaving)
            active={r['id']:r for r in left['active']+right['active']}
            merge=[];split=[]
            for shape in unions:
                s=score(a,b,shape);merge.append({'segments':[s],'local_cost':sum(s['cost_parts'].values())})
            for lshape,rshape in product(ls,rs):
                l,r=score(a,t,lshape),score(t,b,rshape);change,resolution=transition(l['candidate'],r['candidate'])
                split.append({'segments':[l,r],'transition_parts':{'label_change':change,'resolution_discount':resolution},
                    'local_cost':sum(l['cost_parts'].values())+sum(r['cost_parts'].values())+change+resolution})
            merge.sort(key=lambda v:v['local_cost']);split.sort(key=lambda v:v['local_cost'])
            evidence_id='dread_'+hashlib.sha256((str(a)+'|'+str(t)+'|'+str(b)+'|'+','.join(sorted(active))).encode()).hexdigest()[:20]
            before=[r for r in rows if r['start']<t<=r['end']]
            after=[r for r in rows if r['start']<=t<r['end']]
            bass_after=min((r['pitch'] for r in after),default=None)
            alternatives.append({'evidence_id':evidence_id,'span':{'start':q(a),'end':q(b)},'boundary':q(t),
                'window_width_beats':{'left':q(wl),'right':q(wr)},'beat_unit_quarter':q(unit),
                'left_pitch_classes':sorted(old),'right_pitch_classes':sorted(new),
                'common_pitch_classes':sorted(old&new),'event_refs':sorted(active),
                'entering_attack_refs':sorted(r['id'] for r in entering),'leaving_event_refs':sorted(r['id'] for r in leaving),
                'entry_delay_quarters':q(first-t),'last_exclusive_release':q(last),
                'first_exclusive_attack':q(first),
                'boundary_support_band':{'start':q(last),'end':q(first),'semantics':'closed uncertainty interval, not an event span'},
                'sustained_common_event_refs':sorted(r['id'] for r in active.values() if r['start']<t<r['end']),
                'occupancy_quarters':{side:{str(pc):q(d) for pc,d in sorted(p['occupancy'].items())} for side,p in [('left',left),('right',right)]},
                'bass':{'before_midi':min((r['pitch'] for r in before),default=None),'after_midi':bass_after,
                    'new_attack_refs':sorted(r['id'] for r in after if r['pitch']==bass_after and r['start']==t),
                    'continued_refs':sorted(r['id'] for r in after if r['pitch']==bass_after and r['start']<t)},
                'merged_seventh':merge,'split_triads':split,
                'split_minus_merge_cost':split[0]['local_cost']-merge[0]['local_cost'],
                'selected_hypothesis':None,'review_status':'ambiguous_needs_context'})
    groups=defaultdict(list)
    for alt in alternatives:groups[str(f(alt['boundary']))].append(alt)
    return {'version':VERSION,'analysis_span':analysis_span,'alternatives':alternatives,
        'boundary_groups':[{'boundary':q(F(t)),'evidence_refs':[a['evidence_id'] for a in alts],
            'window_pair_count':len(alts),'votes_or_confidence':False} for t,alts in sorted(groups.items(),key=lambda x:F(x[0]))],
        'gate_audit':{'window_pairs':tested,'first_failed_gate':dict(gates),'accepted':len(alternatives)},
        'source_labels_used':False,'selected_path_modified':False,'production_enabled':False,
        'cost_scope':'local fixed-window comparison; no external transitions or recurrent-figure cost',
        'limitations':['Exact pooled triads; no omitted roots or removal of NCTs',
            'Overlapping window support is not independent evidence or confidence',
            'A bass attack may be an arpeggio member, not a new harmonic root',
            'Candidate anchors and closed uncertainty bands are not confirmed boundaries',
            'No automatic score-specific or genre-specific rules']}
