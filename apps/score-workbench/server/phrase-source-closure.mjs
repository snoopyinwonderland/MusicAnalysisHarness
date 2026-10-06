// Offline observations only. This is not a canonical tie-chain parser or cadence classifier.
const value=f=>f.n/f.d;
const samePitch=(a,b)=>JSON.stringify(a.pitch)===JSON.stringify(b.pitch);
export function sourceClosure(evidence,notes,index){
 const mapping=evidence.mappings.find(m=>m.index===index);
 const observed=evidence.observed;
 let cursor=observed.findIndex(n=>n.id===mapping?.sourceEventId);
 const unknown=reason=>({status:'unknown',reason,eventId:notes[index]?.id});
 if(cursor<0||!notes[index])return unknown('missing-source-mapping');
 const attack=observed[cursor],chain=[attack];
 if(attack.grace||attack.chord||attack.tie.includes('stop'))return unknown('unsupported-attack');
 while(chain.at(-1).tie.includes('start')){
  const next=observed[++cursor];
  if(!next||next.kind!=='note'||next.chord||next.grace||next.source.staff!==attack.source.staff||!samePitch(attack,next)||!next.tie.includes('stop'))return unknown('unresolved-tie-continuation');
  chain.push(next);
 }
 const rests=[];
 while(observed[cursor+1]?.kind==='rest')rests.push(observed[++cursor]);
 const next=observed[cursor+1];
 const nextMapping=evidence.mappings.find(m=>m.index===index+1);
 if(!next||next.id!==nextMapping?.sourceEventId)return unknown('next-attack-not-adjacent-in-source');
 const sequence=[...chain,...rests,next];
 if(sequence.some(n=>n.grace||n.chord||n.source.staff!==attack.source.staff||!Number.isFinite(value(n.durationQuarter))))return unknown('unsupported-source-sequence');
 for(let i=1;i<sequence.length;i++){
  const a=sequence[i-1],b=sequence[i];
  if(a.source.measureOrdinal===b.source.measureOrdinal){
   if(Math.abs(a.quarterPositionInMeasure+value(a.durationQuarter)-b.quarterPositionInMeasure)>1e-6)return unknown('noncontiguous-source-timeline');
  }else if(b.source.measureOrdinal!==a.source.measureOrdinal+1||Math.abs(b.quarterPositionInMeasure)>1e-6)return unknown('unsupported-measure-transition');
 }
 const sourceDuration=chain.reduce((s,n)=>s+value(n.durationQuarter),0);
 const explicitRestDuration=rests.reduce((s,n)=>s+value(n.durationQuarter),0);
 const flattenedDuration=notes[index].durationRatio;
 const inferredGap=Number(notes[index+1].onset)-Number(notes[index].onset)-flattenedDuration;
 return {status:'observed',eventId:notes[index].id,nextEventId:notes[index+1].id,
  sourceNoteIds:chain.map(n=>n.id),sourceRestIds:rests.map(n=>n.id),sourceDuration,explicitRestDuration,
  durationMatches:Math.abs(sourceDuration-flattenedDuration)<1e-6,gapMatches:Math.abs(explicitRestDuration-inferredGap)<1e-6,
  flattenedDuration,inferredGap,releaseNotation:{measureOrdinal:chain.at(-1).source.measureOrdinal,quarterPosition:chain.at(-1).quarterPositionInMeasure+value(chain.at(-1).durationQuarter)},
  breathSymbols:sequence.slice(0,-1).flatMap(n=>n.breathSymbols??[]),
  limitations:['legacy numeric positions','cross-bar continuity assumes prior measure ends at last observed event; no meter validation','duration/rest agreement is not a phrase or cadence decision']};
}
