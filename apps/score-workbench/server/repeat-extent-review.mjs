import {alignStructureTemplate} from '../src/music/structureTemplateAlignment.ts';
import {durationRestVariants} from './repeat-first.mjs';
const beat=n=>[6,9,12].includes(n.meterCount)&&n.meterUnit===8?1.5:([2,3,4].includes(n.meterCount)&&[2,4,8].includes(n.meterUnit)?4/n.meterUnit:null);
const closure=(notes,index)=>{
 const n=notes[index],next=notes[index+1],unit=n&&beat(n);
 if(!unit||!next)return {status:'unknown'};
 const gap=next.onset-n.onset-n.durationRatio;
 return {status:'observed',durationBeats:n.durationRatio/unit,gapBeats:gap/unit,protected:!!n.breathSymbols?.length||gap/unit>=4||(gap/unit>=2&&n.durationRatio/unit>=2),eventId:n.id,nextEventId:next.id,provenance:'snapshot-tie-accumulated-duration-and-inferred-gap'};
};
/** Collapse contained windows only against their original representative; no transitive family growth. */
export function reviewRepeatExtents(notes,result){
 const ordered=[...result.candidates].sort((a,b)=>(b.left.endIndexExclusive-b.left.startIndex)-(a.left.endIndexExclusive-a.left.startIndex)||a.left.startIndex-b.left.startIndex);
 const groups=[];
 for(const c of ordered){
  const g=groups.find(g=>{const r=g.representative;return c.right.startIndex-c.left.startIndex===r.right.startIndex-r.left.startIndex&&c.left.startIndex>=r.left.startIndex&&c.left.endIndexExclusive<=r.left.endIndexExclusive&&c.right.startIndex>=r.right.startIndex&&c.right.endIndexExclusive<=r.right.endIndexExclusive});
  if(g)g.windows.push(c);else groups.push({representative:c,windows:[c]});
 }
 return {version:'repeat-extent-review-v0.1',searchStatus:result.status,groups:groups.map(g=>{
  const c=g.representative,i=c.left.startIndex,j=c.right.startIndex,max=Math.min(c.left.endIndexExclusive-i,c.right.endIndexExclusive-j),endpoints=[];
  for(let length=5;length<=max;length++){
   const left=closure(notes,i+length-1),right=closure(notes,j+length-1);
   if(left.status!=='observed'||right.status!=='observed'||left.durationBeats<1||right.durationBeats<1||left.gapBeats<1||right.gapBeats<1)continue;
   const crossing=[];
   for(let k=1;k<length;k++)if(closure(notes,i+k-1).protected||closure(notes,j+k-1).protected)crossing.push(k);
   const a=notes.slice(i,i+length),b=notes.slice(j,j+length),alignment=alignStructureTemplate(a,b);
   endpoints.push({left:{startEventId:a[0].id,lastEventId:a.at(-1).id,endExclusiveIndex:i+length},right:{startEventId:b[0].id,lastEventId:b.at(-1).id,endExclusiveIndex:j+length},leftClosure:left,rightClosure:right,protectedInteriorOffsets:crossing,status:crossing.length?'blocked-by-protected-interior':'review-candidate',alignment,variants:alignment.status==='compared'?durationRestVariants(a,b,alignment.alignment):[]});
  }
  const variants=[...new Map(g.windows.flatMap(w=>w.variants).map(v=>[`${v.leftEventId}|${v.rightEventId}`,v])).values()];
  return {anchor:{left:c.left,right:c.right},windowCount:g.windows.length,lowInformation:c.lowInformation,variants,endpoints,decision:'cannot_judge',limitations:['contained-window group is not a motif family','start is a retrieval anchor; preparatory-note completeness not established','equal attack-count endpoint candidates only; insertion/deletion extent mapping deferred','one-beat arrival/rest is a review filter, not cadence or merge proof','no source XML rest validation in this stage']};
 }),decision:'shadow-review-only'};
}
