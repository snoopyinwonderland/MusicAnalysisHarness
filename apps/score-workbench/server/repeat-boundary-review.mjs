/** Compare only AFTER discovery; never feed baseline cuts into candidate finding. */
export function compareRepeatBoundaries(notes,boundaries,elasticReview){
  const cuts=new Set(boundaries.filter(b=>b.supported).map(b=>b.index));
  const rows=[],seen=new Set();
  for(const group of elasticReview.reviews)for(const p of group.proposals){
    const key=[p.left.startIndex,p.left.endIndexExclusive,p.right.startIndex,p.right.endIndexExclusive].join(':');
    if(seen.has(key))continue;
    seen.add(key);
    const range=r=>({...r,startMeasure:notes[r.startIndex].measure,endMeasure:notes[r.endIndexExclusive-1].measure,
      internalCuts:[...cuts].filter(i=>i>r.startIndex&&i<r.endIndexExclusive).map(i=>({index:i,nextEventId:notes[i].id,measure:notes[i].measure})),
      startAtBaselineBoundary:r.startIndex===0||cuts.has(r.startIndex),endAtBaselineBoundary:r.endIndexExclusive===notes.length||cuts.has(r.endIndexExclusive)});
    const left=range(p.left),right=range(p.right);
    const differences=p.alignment.alignment.filter(s=>s.leftIndex!==null&&s.rightIndex!==null&&s.leftIndex>0&&s.rightIndex>0).flatMap(s=>{
      const li=left.startIndex+s.leftIndex,ri=right.startIndex+s.rightIndex;
      return cuts.has(li)===cuts.has(ri)?[]:[{leftEventId:notes[li].id,rightEventId:notes[ri].id,leftBoundary:cuts.has(li),rightBoundary:cuts.has(ri)}];
    });
    rows.push({left,right,correspondingBoundaryDifferences:differences,channels:{melodic:p.alignment.melodic,rhythm:p.alignment.rhythm,coverage:p.alignment.coverage},
      decision:'cannot_judge',reason:differences.length?'different-cuts-at-aligned-attacks':'no-mapped-cut-difference',alternatives:['keep-baseline','review-extent'],autoApply:false});
  }
  return {version:'repeat-boundary-review-v0.1',status:elasticReview.status,rows,limitations:['Missing proposals are not evidence to keep or remove a boundary','Aligned attacks do not establish identical musical functions','Gap-only alignment positions are not mapped boundary evidence','No cadence judgment or automatic merge']};
}
