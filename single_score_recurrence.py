"""Experimental within-score repetition evidence. Never selects/deletes notes."""
from single_score_melody_review import fq
from collections import defaultdict, deque

VERSION='within-score-recurrence/0.2'

def align(a,b):
    # Timing is relative to each excerpt; insertions need not shift later matches.
    n,m=len(a),len(b); dp=[[0.]*(m+1) for _ in range(n+1)]; back={}
    for i in range(1,n+1): dp[i][0]=-i*.65
    for j in range(1,m+1): dp[0][j]=-j*.65
    shift=(b[0]['pitch']-a[0]['pitch'])%12
    ta,tb=fq(a[0]['onset']),fq(b[0]['onset'])
    at=[float(fq(x['onset'])-ta) for x in a];bt=[float(fq(y['onset'])-tb) for y in b]
    for i,x in enumerate(a,1):
        for j,y in enumerate(b,1):
            timing=abs(at[i-1]-bt[j-1])
            pitch=(y['pitch']-x['pitch'])%12==shift
            compatible=pitch and timing<=.25
            reward=2.-float(timing) if compatible else -2.
            choices=[(dp[i-1][j-1]+reward,1),(dp[i-1][j]-.65,2),(dp[i][j-1]-.65,3)]
            dp[i][j],back[i,j]=max(choices,key=lambda x:x[0])
    path=[];i,j=n,m
    while i or j:
        d=back.get((i,j),2 if i else 3)
        if d==1:
            i-=1;j-=1
            if (b[j]['pitch']-a[i]['pitch'])%12==shift and abs(at[i]-bt[j])<=.25:path.append((i,j))
        elif d==2:i-=1
        else:j-=1
    return list(reversed(path)),shift

def discover(notes,max_comparisons=12000):
    windows=[]
    for i,n in enumerate(notes):
        for duration in (4,8,16):
            stop=i
            while stop<len(notes) and fq(notes[stop]['onset'])<fq(n['onset'])+duration:stop+=1
            if 6<=stop-i<=40:windows.append((i,stop,duration))
    onsets=[fq(n['onset']) for n in notes]
    rhythms=[{onsets[k]-onsets[a] for k in range(a,z)} for a,z,d in windows]
    buckets=defaultdict(deque)
    span=(onsets[-1]-onsets[0]) if onsets else 0
    def zone(index):return min(3,int(4*(onsets[index]-onsets[0])/span)) if span else 0
    for ai,(a,z,duration) in enumerate(windows):
        for bi in range(ai+1,len(windows)):
            b,y,d=windows[bi]
            if d!=duration or onsets[b]<onsets[a]+duration:continue
            # A rhythm-first anchor gate, not exact melody matching.
            if len(rhythms[ai]&rhythms[bi])<5:continue
            buckets[zone(a),zone(b),d].append((a,z,b,y,d))
    eligible=sum(map(len,buckets.values()));counts=defaultdict(int);pairs=[];comparisons=0
    active=deque(sorted(buckets))
    while active and comparisons<max_comparisons:
            key=active.popleft();a,z,b,y,duration=buckets[key].popleft()
            if buckets[key]:active.append(key)
            comparisons+=1;counts[key]+=1;path,shift=align(notes[a:z],notes[b:y])
            if len(path)<6 or len(path)/min(z-a,y-b)<.75 or len(path)/max(z-a,y-b)<.5:continue
            # Repeated single notes alone are not distinctive evidence.
            if len({notes[a+i]['pitch']%12 for i,j in path})<3:continue
            pairs.append(dict(left=[a,z],right=[b,y],windowQuarters=duration,shift=shift,
                matches=[[a+i,b+j] for i,j in path],coverage=[len(path)/(z-a),len(path)/(y-b)],status='unreviewed'))
    return dict(version=VERSION,status='partial' if comparisons<eligible else 'complete-within-window-limits',comparisons=comparisons,pairs=pairs,
        eligibleComparisons=eligible,coverageBuckets=[dict(leftQuarter=k[0],rightQuarter=k[1],windowQuarters=k[2],examined=counts[k],remaining=len(buckets[k])) for k in sorted(buckets)],
        limitations=['4/8/16-quarter windows only; not Phrase or Motif boundaries','fixed relative timing; broad rhythmic variation remains deferred','overlapping windows are not independent repetitions','pitch-class correspondence is not proof of melody role'])

def long_fill_candidates(notes,discovery):
    """Unmatched runs between matched anchors. Difference is not accompaniment proof."""
    found={}
    for pi,p in enumerate(discovery['pairs']):
        for side in (0,1):
            matches=sorted((m[side],m[1-side]) for m in p['matches'])
            for (left,other_left),(right,other_right) in zip(matches,matches[1:]):
                start=left+1;length=right-start
                if not 3<=length<=16 or other_right-other_left>2:continue
                mid=notes[start:right];endpoint=min(notes[left]['pitch'],notes[right]['pitch'])
                if max(n['pitch'] for n in mid)>endpoint-5:continue
                # Require a short, limited-pitch texture rather than any unmatched melody.
                if len({n['pitch']%12 for n in mid})>4:continue
                from statistics import median
                typical=median(fq(n['duration']) for n in notes[max(0,left-8):right+9])
                if any(fq(n['duration'])>typical for n in mid):continue
                contradictions=[]
                run=notes[left:right+1]
                if len({n['voice'] for n in run})>1:contradictions.append('voice-change')
                if any(n['ties'] or n['unresolvedTie'] or len(n['sourceIds'])>1 for n in mid):contradictions.append('tie-protected')
                if any(fq(a['onset'])+fq(a['duration'])!=fq(b['onset']) for a,b in zip(run,run[1:])):contradictions.append('gap-or-overlap')
                if any(b['value'] in ('continue','end') for b in mid[0]['beams']) or any(b['value'] in ('begin','continue') for b in mid[-1]['beams']):contradictions.append('beam-crosses-edge')
                key=(start,right)
                if key not in found:found[key]=dict(id=f'long-{len(found)+1}',start=start,endExclusive=right,leftId=notes[left]['id'],rightId=notes[right]['id'],sourceIds=[s for n in mid for s in n['sourceIds']],status='blocked' if contradictions else 'unreviewed',contradictions=contradictions,evidence=['matched-surrounding-anchors','lower-short-texture','counterpart-has-fewer-attacks'],supportPairs=[],selected=False)
                found[key]['supportPairs'].append(pi)
    return list(found.values())

def assess(relations,discovery):
    result=[]
    for r in relations:
        protected=[];different=[]
        for k,p in enumerate(discovery['pairs']):
            for side in (0,1):
                mapping={m[side]:m[1-side] for m in p['matches']}
                if r['start']-1 not in mapping or r['endExclusive'] not in mapping:continue
                inside=list(range(r['start'],r['endExclusive']))
                count=sum(i in mapping for i in inside)
                evidence=dict(pairIndex=k,otherRange=p['right' if side==0 else 'left'])
                if count/len(inside)>=.7:protected.append(evidence)
                elif count==0:different.append(evidence)
        # A repeated low phrase may be melody OR accompaniment: protect from deletion.
        state='recurring-material-protect' if protected else 'variation-review' if different else 'insufficient-evidence'
        result.append(dict(relationId=r['id'],state=state,retainedEvidence=protected,variationEvidence=different,selected=False))
    return result
