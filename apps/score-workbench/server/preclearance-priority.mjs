import {structureHash} from './structure-analysis-adapter.mjs';
export const PRIORITY_VERSION='preclearance-priority/1';
const clamp=n=>Math.max(0,Math.min(1,n));
/** Query-internal information only. This does NOT estimate corpus rarity or copyright. */
export function queryInformation(events){
 const notes=events.filter(e=>e.kind==='note'),intervals=notes.slice(1).map((n,i)=>n.pitchMidi-notes[i].pitchMidi);
 if(!intervals.length)return {score:0,repeatRatio:1,intervalKinds:0,corpusDistinctiveness:null};
 const counts=new Map();for(const interval of intervals)counts.set(interval,(counts.get(interval)||0)+1);
 const entropy=[...counts.values()].reduce((s,n)=>s-n/intervals.length*Math.log2(n/intervals.length),0);
 const repeatRatio=(counts.get(0)||0)/intervals.length;
 return {score:clamp(.5*(1-repeatRatio)+.5*entropy/Math.log2(Math.max(2,Math.min(8,intervals.length)))),
  repeatRatio,intervalKinds:counts.size,entropyBits:entropy,corpusDistinctiveness:null};
}
export function prioritizePreclearance(report){
 const result=structuredClone(report),tasks=new Map(report.runs.map(r=>[r.taskId,r.selection.task]));
 const ranking=[];
 for(const group of result.works){
  const assessments=group.matches.map((m,index)=>{
   const task=tasks.get(m.taskId),notes=task?.query.events.filter(e=>e.kind==='note');
   if(!notes?.length||!Number.isFinite(m.similarity)||m.structureStatus!=='completed'||!Number.isFinite(m.importanceComparison?.jointSupport))
    return {index,status:'needs-review',score:null,reason:'Missing query, similarity or structural evidence'};
   const information=queryInformation(task.query.events),ids=new Set(notes.map(n=>n.id));
   const coverage=new Set((m.queryIds??[]).filter(id=>ids.has(id))).size/ids.size;
   const continuity=clamp(m.candidateImportance.matchedAttackCount/Math.max(1,m.candidateImportance.spanAttackCount));
   // A bounded penalty, not an additive bonus: no structure score rescues low similarity.
   const factors={queryInformation:.5+.5*information.score,alignedCoverage:Math.sqrt(coverage),
    candidateContinuity:Math.sqrt(continuity),structure:.8+.2*clamp(m.importanceComparison.jointSupport)};
   const score=clamp(m.similarity/100)*100*Object.values(factors).reduce((a,b)=>a*b,1);
   return {index,status:'estimated',score,information,coverage,continuity,factors,similarity:m.similarity,
    queryImportance:m.importanceComparison.query,candidateImportance:m.importanceComparison.candidate};
  });
  const scored=assessments.filter(a=>a.score!==null).sort((a,b)=>b.score-a.score||a.index-b.index),best=scored[0];
  group.priorityAssessment={version:PRIORITY_VERSION,score:best?.score??null,status:best?'estimated':'needs-review',
   representativeMatchIndex:best?.index??null,assessments,aggregation:'maximum-not-sum',calibrated:false,legalProbability:false,
   corpusDistinctiveness:null,rightsAdjustment:'not-applied'};
  ranking.push({key:group.key,title:group.title,searchRank:ranking.length+1,score:best?.score??null});
 }
 ranking.sort((a,b)=>(b.score??-1)-(a.score??-1)||a.searchRank-b.searchRank);
 result.priorityReview={version:PRIORITY_VERSION,inputHash:structureHash(report),ranking:ranking.map((r,i)=>({...r,reviewRank:i+1})),
  status:'experimental-not-calibrated',searchRankingChanged:false,
  warnings:['Query information is not corpus rarity. Common scale/arpeggio patterns may still rank highly.',
   'Scores order human review only; they are not infringement probabilities or legal clearance.',
   'No rights adjustment is inferred from age or accessPolicy. Missing evidence requires review.']};
 return result;
}
