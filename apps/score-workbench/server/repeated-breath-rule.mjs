// Conservative whole-span correspondence. No work identity or measure exceptions.
export function repeatedBreathDecisions(notes,boundaries,{maxComparisons=4096}={}){
 const unit=n=>[6,9,12].includes(n?.meterCount)&&n.meterUnit===8?1.5:[2,3,4].includes(n?.meterCount)&&[2,4,8].includes(n?.meterUnit)?4/n.meterUnit:null;
 const close=(a,b)=>Math.abs(a-b)<1e-6;
 const gap=i=>notes[i].onset-notes[i-1].onset-notes[i-1].durationRatio;
 const starts=[0,...boundaries.filter(b=>b.index>0&&b.strength>=.65).map(b=>b.index),notes.length];
 const spans=starts.slice(0,-1).map((s,i)=>[s,starts[i+1]]),decisions=[];let comparisons=0;
 const valid=(s,e)=>e-s>=8&&e-s<=64&&e<notes.length&&notes.slice(s,e+1).every((n,k)=>unit(n)&&unit(n)===unit(notes[s])&&[n.onset,n.durationRatio,n.pitchMidi].every(Number.isFinite)&&n.durationRatio>0&&n.isAttack!==false&&!n.tieStop&&(!k||n.onset>notes[s+k-1].onset));
 const ending=e=>notes[e-1].durationRatio>=unit(notes[e-1])&&gap(e)>=unit(notes[e-1]);
 const protectedInside=(s,e)=>boundaries.slice(s+1,e).some(b=>b.longRestBoundary)||notes.slice(s,e-1).some((n,k)=>n.breathSymbols?.length||gap(s+k+1)<-1e-6||gap(s+k+1)>=4*unit(n)||(gap(s+k+1)>=2*unit(n)&&n.durationRatio>=2*unit(n)));
 for(let t=0;t+1<spans.length;t++){
  const s=spans[t][0],cut=spans[t][1],e=spans[t+1][1];
  if(!valid(s,e)||!ending(e)||protectedInside(s,e))continue;
  const u=unit(notes[cut-1]),tg=gap(cut);
  if(tg<=0||tg>.5*u||notes[cut-1].durationRatio>u)continue;
  for(const [a,z] of spans){
   if(!(z<=s||a>=e)||z-a!==e-s||!valid(a,z)||!ending(z)||protectedInside(a,z))continue;
   if(comparisons>=maxComparisons)return {decisions,comparisons,status:'partial'};
   comparisons++;
   const k=cut-s,sourceCut=a+k,shift=notes[s].pitchMidi-notes[a].pitchMidi;
   // Local duration-to-rest substitution must preserve the next attack exactly.
   if(!close(gap(sourceCut),0)||!close(notes[cut].onset-notes[cut-1].onset,notes[sourceCut].onset-notes[sourceCut-1].onset)||!close(notes[sourceCut-1].durationRatio,notes[cut-1].durationRatio+tg))continue;
   if(!close(notes[cut].pitchMidi-notes[sourceCut].pitchMidi,shift)||!close(notes[cut-1].pitchMidi-notes[sourceCut-1].pitchMidi,shift))continue;
   let pitches=0,rhythm=0,edges=true;
   for(let j=0;j<e-s;j++){
    const residual=Math.abs(notes[s+j].pitchMidi-notes[a+j].pitchMidi-shift);
    if(residual<=2)pitches++;
    if((j<4||j>=e-s-4)&&residual>2)edges=false;
    if(j&&close(notes[s+j].onset-notes[s+j-1].onset,notes[a+j].onset-notes[a+j-1].onset))rhythm++;
   }
   if(!edges||pitches/(e-s)<.8||rhythm/(e-s-1)<.8)continue;
   decisions.push({boundaryIndex:cut,sourceStart:a,sourceEnd:z,targetStart:s,targetEnd:e,sourceBoundaryIndex:sourceCut,sourceEventId:notes[sourceCut]?.id,targetEventId:notes[cut]?.id,pitchSupport:pitches/(e-s),rhythmSupport:rhythm/(e-s-1),gapQuarters:tg,beatQuarters:u});break;
  }
 }
 return {decisions,comparisons,status:'complete'};
}
