import {compareDetailedContour} from './contour-seeds.mjs';

const intervals = ns => ns.slice(1).map((n,i)=>n.p-ns[i].p);
const median = xs => [...xs].sort((a,b)=>a-b)[Math.floor(xs.length/2)] ?? 0;
const editSimilarity = (a,b,cost) => {
 let row=Array.from({length:b.length+1},(_,i)=>i);
 for(let i=1;i<=a.length;i++) {const next=[i];for(let j=1;j<=b.length;j++)next[j]=Math.min(row[j]+1,next[j-1]+1,row[j-1]+cost(a[i-1],b[j-1]));row=next;}
 return 100*Math.max(0,1-row[b.length]/Math.max(1,a.length,b.length));
};
const ratioCost=(a,b)=>Math.min(1,Math.abs(Math.log2(a/b)));
const timeline = ns => {
 const start=ns[0].o,end=Math.max(...ns.map(n=>n.o+n.d));
 return Array.from({length:64},(_,i)=>{
  const t=start+(end-start)*(i+.5)/64;
  return ns.find(n=>n.o<=t&&t<n.o+n.d)?.p ?? null;
 });
};
/** Diagnostic only: no calibrated overall score or retrieval/risk decision.
 * Every attack is retained; inversion applies once to the entire input.
 */
export function compareSegments(a,b){
 if(a.length<4||b.length<4||[...a,...b].some(n=>!Number.isFinite(n.p)||!Number.isFinite(n.o)||!(n.d>0)))throw Error('At least four valid sounding attacks per segment required');
 const rhythm=(field)=>{
  const values=ns=>field==='duration'?ns.map(n=>n.d):ns.slice(1).map((n,i)=>n.o-ns[i].o);
  const x=values(a),y=values(b);if([...x,...y].some(v=>v<=0))return null;
  // One common clock for durations and onset gaps. Median note values jump
  // discontinuously when a single added note crosses the 8th/16th majority.
  const unit=ns=>(ns.at(-1).o-ns[0].o)/(ns.length-1);
  const mx=unit(a),my=unit(b);if(!(mx>0&&my>0))return null;
  return editSimilarity(x.map(v=>v/mx),y.map(v=>v/my),ratioCost);
 };
 const x=timeline(a),y=timeline(b),shared=x.map((p,i)=>p!==null&&y[i]!==null?i:null).filter(i=>i!==null);
 const variants=[1,-1].map(sign=>{
  const offsets=shared.map(i=>y[i]-sign*x[i]),offset=median(offsets);
  return {transformation:sign===1?'transposition':'global-chromatic-inversion',
   intervalEdit:editSimilarity(intervals(a).map(v=>v*sign),intervals(b),(u,v)=>Math.min(1,Math.abs(u-v)/4)),
   contour:compareDetailedContour(a.map(n=>sign*n.p),b.map(n=>n.p)),
   normalizedTimePitchAgreement:shared.length?100*shared.reduce((sum,i)=>sum+Math.max(0,1-Math.abs(sign*x[i]+offset-y[i])/6),0)/shared.length:null,
   fittedSemitoneOffset:offset};
 });
 return {schema:'segment-comparison/1',calibrated:false,countsAsRetrievalSuccess:false,
  noteCounts:[a.length,b.length],durationRatioEdit:rhythm('duration'),onsetIntervalRatioEdit:rhythm('onset'),
  normalizedTimeSoundRestAgreement:100*x.filter((v,i)=>(v===null)===(y[i]===null)).length/64,
  sharedSoundingSamples:shared.length,variants,
  warnings:['Diagnostic constants (4/6 semitones, 64 samples) are uncalibrated; no composite score.','Timing normalized globally, not arbitrary local stretching.','Inversion evidence is separate from audible resemblance; no risk or ranking boost.']};
}
