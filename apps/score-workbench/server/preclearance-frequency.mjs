import {structureHash} from './structure-analysis-adapter.mjs';
export const FREQUENCY_VERSION='preclearance-source-frequency/1';
export function intervalTokens(events){
 const notes=events.filter(e=>e.kind==='note'),intervals=notes.slice(1).map((n,i)=>n.pitchMidi-notes[i].pitchMidi);
 return [...new Set(intervals.slice(0,Math.max(0,intervals.length-4)).map((_,i)=>`i5:${intervals.slice(i,i+5).join(',')}`))];
}
export function frequencyEvidence(tokens,counts,totalSources){
 const grams=tokens.map(token=>({token,sourceCount:counts[token]??null}));
 if(!tokens.length||totalSources<2||grams.some(g=>!Number.isInteger(g.sourceCount)||g.sourceCount<1||g.sourceCount>totalSources))
  return {status:'unknown',rarityProxy:null,factor:null,grams,totalSources,reason:'Insufficient evidence, absent token or invalid source count'};
 const values=grams.map(g=>Math.log((totalSources+1)/(g.sourceCount+1))/Math.log(totalSources+1)).sort((a,b)=>a-b),mid=Math.floor(values.length/2);
 const rarityProxy=values.length%2?values[mid]:(values[mid-1]+values[mid])/2;
 return {status:'measured',rarityProxy,factor:.85+.15*rarityProxy,grams,totalSources,
  scope:'median normalized IDF of unique 5-interval grams across distinct source files',completeMelodyFrequency:false};
}
/** A/B layer only: retains both original search order and baseline review scores. */
export function compareCorpusPriority(report,{counts,totalSources}){
 const output=structuredClone(report),tasks=new Map(report.runs.map(r=>[r.taskId,frequencyEvidence(intervalTokens(r.selection.task.query.events),counts,totalSources)]));
 const ranking=report.works.map((w,searchIndex)=>{
  const matches=w.priorityAssessment.assessments.map(a=>{
   const evidence=tasks.get(w.matches[a.index].taskId);
   return {matchIndex:a.index,baselineScore:a.score,score:a.score!==null&&evidence?.factor!=null?a.score*evidence.factor:null,evidence};
  });
  const best=matches.filter(m=>m.score!==null).sort((a,b)=>b.score-a.score||a.matchIndex-b.matchIndex)[0];
  return {key:w.key,title:w.title,searchRank:searchIndex+1,baselineRank:report.priorityReview.ranking.find(r=>r.key===w.key)?.reviewRank,
   baselineScore:w.priorityAssessment.score,score:best?.score??null,representativeMatchIndex:best?.matchIndex??null,matches};
 });
 ranking.sort((a,b)=>(b.score??-1)-(a.score??-1)||a.searchRank-b.searchRank);
 output.corpusPriorityReview={version:FREQUENCY_VERSION,inputHash:structureHash(report),totalSources,counts,
  ranking:ranking.map((r,i)=>({...r,reviewRank:i+1})),calibrated:false,searchRankingChanged:false,baselinePriorityChanged:false,
  warnings:['Source-file frequency, not canonical composition frequency; editions remain separate.',
   'Short interval grams ignore rhythm, rests and phrase context; this is not whole-melody rarity.',
   'Absent grams yield unknown, not proof of originality. Corpus coverage and expert calibration remain limitations.',
   'Experimental human review order only; no infringement probability or rights clearance.']};
 return output;
}
