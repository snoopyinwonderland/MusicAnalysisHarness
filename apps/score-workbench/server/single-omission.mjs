/** Experimental bounded omission hypothesis; unrelated to Schenker reduction.
 * Entire query must correspond under ONE transposition and tempo ratio, with
 * exactly ONE internal candidate attack omitted. No extra skips/substitutions.
 */
export function singleOmissionAlignment(query,candidate){
 const n=query.length;if(n<8||n>48||candidate.length<n+1)return null;
 if(new Set(query.map(e=>e.pitchMidi)).size<3)return null;
 const value=e=>Number(e.durationRatio),close=(a,b)=>Math.abs(a-b)<=1e-5*Math.max(1,Math.abs(a),Math.abs(b));
 if(query.some(e=>!Number.isFinite(e.pitchMidi)||!(value(e)>0)||!Number.isFinite(e.onset)))return null;
 let best=null;
 for(let start=0;start+n<candidate.length;start++){
  const span=candidate.slice(start,start+n+1);
  if(span.some(e=>!Number.isFinite(e.pitchMidi)||!(value(e)>0)||!Number.isFinite(e.onset)||e.isAttack===false||e.cue))continue;
  const transpose=span[0].pitchMidi-query[0].pitchMidi,tempo=value(span[0])/value(query[0]);
  if(tempo<.25||tempo>4)continue;
  for(let gap=1;gap<n;gap++){
   const mapped=span.filter((_,i)=>i!==gap);
   if(mapped.some((e,i)=>!close(e.pitchMidi-query[i].pitchMidi,transpose)||!close(value(e),value(query[i])*tempo)))continue;
   let valid=true;
   for(let i=1;i<n;i++){
    const candidateDelta=mapped[i].onset-mapped[i-1].onset-(i===gap?value(span[gap]):0);
    if(!close(candidateDelta,(query[i].onset-query[i-1].onset)*tempo)){valid=false;break}
   }
   if(!valid)continue;
   // An omitted event must be a real non-overlapping internal attack.
   if(span[gap].onset<span[gap-1].onset+value(span[gap-1])-1e-5||span[gap+1].onset<span[gap].onset+value(span[gap])-1e-5)continue;
   const cost=.8+.4*Math.max(0,Math.min(1,Number(span[gap].structuralWeight??1)));
   const path=[];for(let j=0;j<=n;j++)path.push(j===gap?{queryIndex:null,candidateIndex:start+j,type:'insertion',cost}:{queryIndex:j<gap?j:j-1,candidateIndex:start+j,type:'match',cost:0});
   const result={path,start,end:start+n,coverage:1,cost,similarity:100*Math.exp(-cost/n/.48),
    singleOmission:{candidateIndex:start+gap,transpose,tempo,verifiedAllRetainedPitches:true,verifiedRetainedTiming:true,version:'single-omission/1'}};
   if(!best||result.cost<best.cost)best=result;
  }
 }
 return best;
}
