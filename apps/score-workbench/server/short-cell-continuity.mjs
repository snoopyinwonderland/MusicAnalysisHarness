// Frozen Phrase spans; suppress at most the boundary after a short repeated cell.
export function shortCellContinuity(notes,boundaries){
 const beat=n=>[6,9,12].includes(n?.meterCount)&&n.meterUnit===8?1.5:[2,3,4].includes(n?.meterCount)&&[2,4,8].includes(n?.meterUnit)?4/n.meterUnit:null;
 const gap=i=>notes[i].onset-notes[i-1].onset-notes[i-1].durationRatio;
 const near=(a,b)=>Math.abs(a-b)<1e-6;
 const starts=[0,...boundaries.filter(b=>b.index>0&&b.strength>=.65).map(b=>b.index),notes.length],decisions=[];
 for(let p=0;p+2<starts.length;p++){
  const s=starts[p],c=starts[p+1],e=starts[p+2],len=c-s,u=beat(notes[s]);
  if(!u||len<4||len>8||e-c<2*len||e>=notes.length)continue;
  const region=notes.slice(s,e+1);
  if(region.some((n,k)=>beat(n)!==u||n.meterCount!==notes[s].meterCount||n.meterUnit!==notes[s].meterUnit||![n.onset,n.durationRatio,n.pitchMidi].every(Number.isFinite)||n.durationRatio<=0||n.tieStop||n.isAttack===false||(k&&n.onset<=region[k-1].onset)))continue;
  // Short in metric time, not merely low note count. The later closure must be stronger.
  if(notes[c].onset-notes[s].onset>4*u||gap(c)<=0||gap(c)>.5*u||notes[c-1].durationRatio>u||notes[e-1].durationRatio<u||gap(e)<u||gap(e)<2*gap(c))continue;
  if(notes.slice(s,e-1).some(n=>n.breathSymbols?.length)||boundaries.slice(s+1,e).some(b=>b.longRestBoundary))continue;
  if(notes.slice(s,e-1).some((n,k)=>gap(s+k+1)<-1e-6||gap(s+k+1)>=4*u||(gap(s+k+1)>=2*u&&n.durationRatio>=2*u)))continue;
  let valid=true,changedIntervals=0;
  for(let k=0;k<len;k++){
   if(!near(notes[s+k].durationRatio,notes[c+k].durationRatio))valid=false;
   if(k){
    if(!near(notes[s+k].onset-notes[s+k-1].onset,notes[c+k].onset-notes[c+k-1].onset))valid=false;
    const a=notes[s+k].pitchMidi-notes[s+k-1].pitchMidi,b=notes[c+k].pitchMidi-notes[c+k-1].pitchMidi;
    if(Math.sign(a)!==Math.sign(b)||Math.abs(a-b)>2)valid=false;
    if(!near(a,b))changedIntervals++;
   }
  }
  if(!valid||new Set(notes.slice(s,c).map(n=>n.pitchMidi)).size<3)continue;
  decisions.push({boundaryIndex:c,sourceStart:s,sourceEnd:c,repeatedStart:c,repeatedEnd:c+len,targetEnd:e,sourceEventId:notes[s].id,repeatedEventId:notes[c].id,cellAttacks:len,changedIntervals,beatQuarters:u,gapQuarters:gap(c),endingGapQuarters:gap(e),interpretation:'motif-scale-boundary-within-phrase-not-cadence'});
 }
 return {version:'short-cell-continuity-v0.1',decisions};
}
