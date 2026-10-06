import {alignStructureTemplate} from '../src/music/structureTemplateAlignment.ts';

const beat = n => [6,9,12].includes(n.meterCount) && n.meterUnit === 8 ? 1.5
  : [2,3,4].includes(n.meterCount) && [2,4,8].includes(n.meterUnit) ? 4/n.meterUnit : null;
function closure(notes, index) {
  const n=notes[index], next=notes[index+1], unit=n && beat(n);
  if (!unit || !next || n.meterCount!==next.meterCount || n.meterUnit!==next.meterUnit) return null;
  const gap=(next.onset-n.onset-n.durationRatio)/unit;
  return {duration:n.durationRatio/unit, gap,
    protected:!!n.breathSymbols?.length || gap>=4 || (gap>=2 && n.durationRatio/unit>=2)};
}
function interior(notes,start,end) {
  for(let k=start;k<end-1;k++) {
    const c=closure(notes,k);
    if(!c)return 'unknown-meter-or-context';
    if(c.protected)return 'protected-interior';
  }
  return null;
}
/** Bounded shadow proposals, not phrase segmentation or harmonic completeness. */
export function reviewElasticExtents(notes, groups, {maxAlignments=500,lookback=3,lookahead=4}={}) {
  if(!Number.isInteger(maxAlignments)||maxAlignments<0||!Number.isInteger(lookback)||lookback<0||lookback>4||!Number.isInteger(lookahead)||lookahead<0||lookahead>8)throw Error('Invalid review budget');
  let alignments=0, partial=false;
  const reviews=[];
  function* reviewGroup(group, review) {
    const {left,right}=group.anchor, i=left.startIndex,j=right.startIndex;
    const ends=(start,limit)=>{
      const found=[];
      for(let e=start+5;e<=Math.min(limit+lookahead,notes.length-1);e++) {
        const c=closure(notes,e-1);
        if(c && c.duration>=1 && c.gap>=1)found.push(e);
      }
      return found;
    };
    const {proposals,rejected}=review;
    const reject=reason=>{rejected[reason]=(rejected[reason]??0)+1};
    for(const le of ends(i,left.endIndexExclusive))for(const re of ends(j,right.endIndexExclusive)) {
      if(Math.abs((le-i)-(re-j))>lookahead)continue;
      for(let lb=0;lb<=Math.min(lookback,i);lb++)for(let rb=0;rb<=Math.min(lookback,j);rb++) {
        const ls=i-lb,rs=j-rb;
        if(le>rs){reject('overlapping-occurrences');continue;}
        const blocked=interior(notes,ls,le)||interior(notes,rs,re);
        if(blocked){reject(blocked);continue;}
        yield;
        alignments++;
        review.alignments++;
        const a=notes.slice(ls,le),b=notes.slice(rs,re),m=alignStructureTemplate(a,b);
        if(m.status!=='compared'){reject(m.status);continue;}
        const pairs=m.alignment.filter(p=>p.leftIndex!==null&&p.rightIndex!==null);
        if(!m.terminal.bothEndpointsPaired || pairs[0]?.leftIndex!==0 || pairs[0]?.rightIndex!==0 || !pairs.some(p=>p.leftIndex===lb&&p.rightIndex===rb)){
          reject('unpaired-endpoint-or-anchor');continue;
        }
        // Both sides must support a preparation; unrelated preceding notes cannot
        // be attached merely because the core makes the overall score high.
        const prefix=pairs.filter(p=>p.leftIndex<lb||p.rightIndex<rb),shift=notes[j].pitchMidi-notes[i].pitchMidi;
        if((lb||rb) && (!lb||!rb||prefix.length!==lb||prefix.length!==rb||prefix.some(p=>p.leftIndex>=lb||p.rightIndex>=rb||Math.abs(b[p.rightIndex].pitchMidi-a[p.leftIndex].pitchMidi-shift)>2))){
          reject('unsupported-preparation');continue;
        }
        const tempo=(notes[j].onset-b[0].onset)/(notes[i].onset-a[0].onset);
        if(prefix.length && prefix.some(p=>{
          const l=notes[i].onset-a[p.leftIndex].onset,r=notes[j].onset-b[p.rightIndex].onset;
          return Math.abs(Math.log2(r/(l*tempo)))>.25 || Math.abs(Math.log2(b[p.rightIndex].durationRatio/(a[p.leftIndex].durationRatio*tempo)))>.5;
        })){reject('preparation-rhythm-mismatch');continue;}
        if(m.coverage<75||m.melodic<75||m.rhythm<75){reject('insufficient-channel-support');continue;}
        const ref=(s,e)=>({startIndex:s,endIndexExclusive:e,startEventId:notes[s].id,lastEventId:notes[e-1].id});
        proposals.push({left:ref(ls,le),right:ref(rs,re),preparationCounts:[lb,rb],attackCountDifference:b.length-a.length,
          status:'review-candidate',alignment:m,decision:'cannot_judge'});
      }
    }
  }
  const jobs=groups.map(group=>{
    const review={anchor:group.anchor,proposals:[],rejected:{},alignments:0,status:'pending'};
    reviews.push(review);
    const iterator=reviewGroup(group,review),done=iterator.next().done;
    if(done)review.status='complete-within-bounds';
    return {iterator,review,done};
  });
  while(alignments<maxAlignments && jobs.some(job=>!job.done)) {
    for(const job of jobs) {
      if(job.done)continue;
      if(alignments>=maxAlignments)break;
      job.done=job.iterator.next().done;
      if(job.done)job.review.status='complete-within-bounds';
    }
  }
  for(const job of jobs)if(!job.done){job.review.status='partial';partial=true;}
  return {version:'repeat-elastic-extent-v0.2',status:partial?'partial':'complete-within-bounds',alignments,reviews,
    policy:{scheduler:'round-robin-per-group',maxAlignments,lookback,lookahead,minCoverage:75,minMelodic:75,minRhythm:75,calibrated:false},
    limitations:['No automatic boundary changes or harmonic claims','Preparation means supported preceding correspondence, not a proven musical function','Unequal preparation counts deferred; internal insertions/deletions supported','Endpoint rests inferred from snapshot, not XML validated','Fairness is among supplied groups only; upstream discovery and within-group ordering remain biased','Repeated-note alignment is evidence, not proven split/merge semantics']};
}
