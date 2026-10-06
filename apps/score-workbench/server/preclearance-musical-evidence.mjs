import {structureHash} from './structure-analysis-adapter.mjs';
export const MUSICAL_EVIDENCE_VERSION='preclearance-musical-evidence/1';
const clamp=x=>Math.max(0,Math.min(1,x));
const median=xs=>{const a=[...xs].sort((a,b)=>a-b);return a.length?a[Math.floor(a.length/2)]:1};
const note=e=>e.kind!=='rest'&&Number.isFinite(e.pitchMidi)&&e.isAttack!==false&&!e.tieStop;
const onset=e=>e.onsetQuarter??e.onset;
function timed(events){let cursor=0;return events.map(e=>{const start=Number.isFinite(onset(e))?onset(e):cursor;cursor=start+e.durationRatio;return {...e,onset:start}})}
function metric(e,meter){
 const [beats,unit]=String(e.meter??meter??'').split('/').map(Number);if(!beats||!unit||!Number.isFinite(e.beat))return null;
 const phase=e.beat-1,group=beats>3&&beats%3===0?12/unit:4/unit;
 if(Math.abs(phase)<1e-5)return 1;
 if(Math.abs(phase/group-Math.round(phase/group))>=1e-4)return .2;
 if(beats>3&&beats%3===0)return .65;
 return beats===4&&Math.abs(phase-8/unit)<1e-4?.65:.4;
}
/** Full source context ONLY: no query/pair is accepted by the anchor extractor. */
export function sourceAnchors(snapshot){
 const ns=timed(snapshot.events).filter(note),ends=new Set(snapshot.units.filter(u=>u.kind==='phrase').map(u=>u.endEventId??u.attackEventIds.at(-1)));
 return {version:MUSICAL_EVIDENCE_VERSION,snapshotId:snapshot.snapshotId,anchors:ns.flatMap((n,i)=>{
  const local=ns.slice(Math.max(0,i-4),i+5),long=n.durationRatio>=median(local.map(x=>x.durationRatio))*1.5;
  const m=metric(n,snapshot.meter),boundary=ends.has(n.id),prev=ns[i-1],next=ns[i+1];
  const stepIn=prev?Math.abs(n.pitchMidi-prev.pitchMidi):Infinity,stepOut=next?Math.abs(next.pitchMidi-n.pitchMidi):Infinity;
  const passing=prev&&next&&stepIn<=2&&stepOut<=2&&Math.sign(n.pitchMidi-prev.pitchMidi)===Math.sign(next.pitchMidi-n.pitchMidi);
  const neighbor=prev&&next&&prev.pitchMidi===next.pitchMidi&&stepIn<=2;
  const ornament=Boolean((passing||neighbor)&&!long&&m!==null&&m<.65);
  const reasons=[...(long?['locally-long']:[]),...(m!==null&&m>=.65?['metric-support']:[]),...(boundary?['phrase-end-hypothesis']:[])];
  // Require at least two independent supports. Strong beat alone is never enough.
  return !ornament&&reasons.length>=2?[{eventId:n.id,onset:n.onset,pitchMidi:n.pitchMidi,durationRatio:n.durationRatio,reasons,confidence:'heuristic',metric:m}]:[];
 }),limitations:['No harmonic reduction or Ursatz is inferred.','Tie continuations are not attacks.','Anchor absence means insufficient support, not structural dissimilarity.']};
}
function sequenceScore(a,b,cost){
 if(!a.length||!b.length)return null;
 let row=Array.from({length:b.length+1},(_,i)=>i);
 for(let i=1;i<=a.length;i++){const next=[i];for(let j=1;j<=b.length;j++)next[j]=Math.min(row[j]+1,next[j-1]+1,row[j-1]+cost(a[i-1],b[j-1]));row=next}
 return 100*clamp(1-row[b.length]/Math.max(a.length,b.length));
}
function shape(a,b){if(a===0&&b===0)return 'repeat';if(Math.sign(a)===Math.sign(b)&&Math.abs(a)<=2&&Math.abs(b)<=2)return 'step';if(Math.sign(a)!==Math.sign(b))return 'return';if(Math.abs(a)>=3&&Math.abs(b)>=3)return 'successive-leaps';return 'mixed';}
export function passageProfile(events){
 const all=timed(events),ns=all.filter(note);if(ns.length<2)return null;
 const start=ns[0].onset,end=Math.max(...all.map(n=>n.onset+n.durationRatio)),length=Math.max(.001,end-start);
 const pitches=ns.map(n=>n.pitchMidi),lo=Math.min(...pitches),hi=Math.max(...pitches),range=Math.max(1,hi-lo);
 const intervals=pitches.slice(1).map((p,i)=>p-pitches[i]),durationUnit=median(all.map(n=>n.durationRatio));
 const envelope=Array.from({length:16},(_,i)=>{const t=start+length*i/16;let n=ns[0];for(const next of ns){if(next.onset>t)break;n=next}return (n.pitchMidi-lo)/range});
 const occupancy=Array.from({length:16},(_,i)=>{const t=start+length*(i+.5)/16;return ns.some(n=>n.onset<=t&&n.onset+n.durationRatio>t)?1:0});
 return {envelope,occupancy,range:hi-lo,peakPosition:(ns[pitches.indexOf(hi)].onset-start)/length,
  rhythm:all.map(n=>[n.kind==='rest'?'rest':'note',n.durationRatio/durationUnit]),
  figures:intervals.slice(1).map((v,i)=>shape(intervals[i],v)),directions:intervals.map(Math.sign)};
}
export function comparePassages(query,candidate,{queryAnchors=[],candidateAnchors=[]}={}){
 const a=passageProfile(query),b=passageProfile(candidate);if(!a||!b)return {status:'insufficient-events'};
 const envelope=100*(1-a.envelope.reduce((s,v,i)=>s+Math.abs(v-b.envelope[i]),0)/16);
 const direction=sequenceScore(a.directions,b.directions,(x,y)=>x===y?0:1);
 const rhythm=sequenceScore(a.rhythm,b.rhythm,(x,y)=>x[0]!==y[0]?1:Math.min(1,Math.abs(Math.log2(x[1]/y[1]))/2));
 const figures=sequenceScore(a.figures,b.figures,(x,y)=>x===y?0:1);
 const restPlacement=100*(1-a.occupancy.reduce((s,v,i)=>s+Math.abs(v-b.occupancy[i]),0)/16);
 const interval=anchors=>anchors.slice(1).map((n,i)=>n.pitchMidi-anchors[i].pitchMidi);
 const structural=queryAnchors.length>=3&&candidateAnchors.length>=3?sequenceScore(interval(queryAnchors),interval(candidateAnchors),(x,y)=>Math.min(1,Math.abs(x-y)/4)):null;
 return {status:'estimated',contour:{score:(envelope+direction)/2,envelope,direction,peakDistance:Math.abs(a.peakPosition-b.peakPosition)},
  rhythm:{score:rhythm,restPlacement,tempoNormalized:true},figures:{score:figures,query:a.figures,candidate:b.figures},
  skeleton:{score:structural,queryAnchors,candidateAnchors,status:structural===null?'insufficient-independent-anchors':'schenker-informed-proxy',harmonyAssessed:false},
  profiles:{query:a,candidate:b},calibrated:false,legalProbability:false,scope:'selected-passages-not-whole-compositions',
  warning:'Common contours and figures are not distinctive by themselves. These layers do not rescue a weak direct match.'};
}
function family(unit,events){
 const ids=new Set(unit.attackEventIds),ns=events.filter(e=>ids.has(e.id)&&note(e));if(!ns.length)return null;
 const root=ns[0].pitchMidi,scale=median(ns.map(n=>n.durationRatio)),start=onset(ns[0]);
 return structureHash(ns.map(n=>[n.pitchMidi-root,Math.round(n.durationRatio/scale*1e5),Math.round((onset(n)-start)/scale*1e5)]));
}
/** Distinct phrase families, not task count, edition count or nested motif count. */
export function aggregatePhraseEvidence(snapshot,matches,{beta=.2}={}){
 if(!Number.isFinite(beta)||beta<0||beta>1)throw new Error('Invalid bonus cap');
 const phrases=snapshot.units.filter(u=>u.kind==='phrase'),notes=snapshot.events.filter(note),groups=new Map();
 for(const u of phrases){const key=family(u,notes);if(!key)continue;let g=groups.get(key);if(!g){g={familyId:key,units:[],score:0,covered:new Set(),queryIds:new Set()};groups.set(key,g)}g.units.push(u);for(const id of u.attackEventIds)g.queryIds.add(id)}
 const alignedUnion=new Set(matches.flatMap(m=>m.queryIds??[]));
 for(const g of groups.values())for(const m of matches){
  const ids=new Set((m.queryIds??[]).filter(id=>g.queryIds.has(id)));if(!ids.size)continue;
  const coverage=Math.max(...g.units.map(u=>u.attackEventIds.filter(id=>ids.has(id)).length/Math.max(1,u.attackEventIds.length)));
  // Fragment or nested motif cannot count as a fully supported phrase.
  if(coverage>=.7&&m.similarity>=70){g.score=Math.max(g.score,m.similarity*coverage);for(const id of ids)g.covered.add(id)}
 }
 const supported=[...groups.values()].filter(g=>g.score>0).sort((a,b)=>b.score-a.score),best=supported[0]?.score??null;
 const E=supported.slice(1).reduce((s,g)=>s+g.score/100,0),bonus=best===null?0:(100-best)*beta*(1-Math.exp(-E));
 const totalDuration=notes.reduce((s,n)=>s+n.durationRatio,0),selected=notes.filter(n=>alignedUnion.has(n.id));
 return {version:MUSICAL_EVIDENCE_VERSION,distinctPhraseFamilies:supported.length,matchedPhraseOccurrences:supported.reduce((s,g)=>s+g.units.filter(u=>u.attackEventIds.filter(id=>g.covered.has(id)).length/u.attackEventIds.length>=.7).length,0),
  attackCoverage:selected.length/Math.max(1,notes.length),durationCoverage:selected.reduce((s,n)=>s+n.durationRatio,0)/Math.max(.001,totalDuration),
  bestPhraseScore:best,additionalEvidence:E,bonus,reviewScore:best===null?null:best+bonus,beta,
  families:supported.map(g=>({familyId:g.familyId,phraseIds:g.units.map(u=>u.unitId),score:g.score,matchedEventIds:[...g.covered]})),
  scope:'input-snapshot-selected-stream',calibrated:false,legalProbability:false,rankingChanged:false,
  limitations:['Exact normalized repetitions share one family; approximate variation families need further review.','No rarity bonus without verified corpus distinctiveness.','Order/contiguity are not yet used as bonuses.']};
}
