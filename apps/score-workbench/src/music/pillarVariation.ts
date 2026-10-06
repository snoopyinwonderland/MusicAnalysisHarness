import type {CorpusNote} from '../types';

export type PillarCorrespondence={otherNoteId:string;ruleVersion:'pillar-variation-0.1';transposition:number;timeScale:number};
// Conservative local comparison: four anchors, up to two inserted attacks.
// Bounded lookahead prevents an all-pairs scan on long scores.
export function pillarVariationEvidence(notes:CorpusNote[]):Map<number,PillarCorrespondence[]>{
 const result=new Map<number,PillarCorrespondence[]>();
 const valid=(ns:CorpusNote[])=>ns.every(n=>n.pitchMidi!==null&&Number.isFinite(n.onset)&&n.durationRatio>0)
  &&ns.slice(1).every((n,k)=>n.onset!>ns[k].onset!&&n.onset!-ns[k].onset!-ns[k].durationRatio<.001);
 const add=(i:number,j:number,t:number,s:number)=>{
  const prior=result.get(i)??[];
  if(prior.length<8&&!prior.some(e=>e.otherNoteId===notes[j].id))result.set(i,[...prior,{otherNoteId:notes[j].id,ruleVersion:'pillar-variation-0.1',transposition:t,timeScale:s}]);
 };
 for(let i=0;i+3<notes.length;i++){
  const a=notes.slice(i,i+4);if(!valid(a))continue;
  const intervals=a.slice(1).map((n,k)=>n.pitchMidi!-a[k].pitchMidi!);
  if(new Set(intervals).size<2||new Set(a.map(n=>n.pitchMidi)).size<3)continue;
  const span=a[3].onset!-a[0].onset!;
  for(let j=i+4;j<Math.min(notes.length-3,i+129);j++)for(let length=4;length<=6&&j+length<=notes.length;length++){
   const b=notes.slice(j,j+length);if(!valid(b))continue;
   const scale=(b[length-1].onset!-b[0].onset!)/span;if(scale<.5||scale>2)continue;
   const trans=b[0].pitchMidi!-a[0].pitchMidi!;
   for(let x=1;x<length-2;x++)for(let y=x+1;y<length-1;y++){
    const positions=[0,x,y,length-1];
    const errors=positions.map((p,k)=>Math.abs(b[p].pitchMidi!-a[k].pitchMidi!-trans));
    if(errors[3]!==0||errors.filter(e=>e>0).length>1||errors.some(e=>e>1))continue;
    if(positions.some((p,k)=>Math.abs((b[p].onset!-b[0].onset!)/scale-(a[k].onset!-a[0].onset!))>span*.08))continue;
    // Inserted notes must be short relative to their surrounding anchor interval.
    if(b.some((n,k)=>!positions.includes(k)&&n.durationRatio>(b[length-1].onset!-b[0].onset!)/4))continue;
    positions.forEach((p,k)=>{if(errors[k]===0){add(i+k,j+p,trans,scale);add(j+p,i+k,-trans,1/scale);}});
   }
  }
 }
 return result;
}
