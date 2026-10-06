import {analyzeStructureSnapshot,structureHash} from './structure-analysis-adapter.mjs';
import {metricWeightAt} from './search-api.mjs';

export const IMPORTANCE_VERSION='preclearance-importance/1';
const attacks=s=>s.events.filter(e=>e.kind!=='rest'&&e.isAttack!==false&&!e.tieStop);
const round=n=>Math.round(n*1e6)/1e6;
const clamp=n=>Math.max(0,Math.min(1,n));
const weights={repetition:.20,metricalDuration:.15};
function signature(notes){const first=notes[0],unit=first.durationRatio;return JSON.stringify(notes.map(n=>[n.pitchMidi-first.pitchMidi,round(n.durationRatio/unit),round((n.onset-first.onset)/unit)]))}

/** All intervening attacks remain in the span. Shares refer to this stream, not the entire composition. */
export function segmentImportance(snapshot,eventIds){
 const all=attacks(snapshot),wanted=new Set(eventIds),indices=all.flatMap((e,i)=>wanted.has(e.id)?[i]:[]);
 if(!wanted.size||indices.length!==wanted.size)throw new Error('Missing or non-attack event reference');
 const first=indices[0],last=indices.at(-1),notes=all.slice(first,last+1),key=signature(notes),occurrences=[];
 if(notes.length>=4)for(let i=0;i+notes.length<=all.length;i++){
  const window=all.slice(i,i+notes.length);
  if(signature(window)===key){occurrences.push({eventIds:window.map(n=>n.id),startQuarter:window[0].onset,endQuarter:window.at(-1).onset+window.at(-1).durationRatio});i+=notes.length-1}
 }
 const durations=all.map(n=>n.durationRatio).sort((a,b)=>a-b),median=durations[Math.floor(durations.length/2)];
 const metric=notes.map(n=>{const meter=Object.hasOwn(n,'meter')?n.meter:snapshot.meter;
  if(!/^\d+\/\d+$/.test(meter??'')||!Number.isFinite(n.beat)||n.beat<1)return null;
  const [count,unit]=meter.split('/').map(Number);if(!count||!unit)return null;
  return .5*metricWeightAt(n.beat,meter)+.5*clamp(n.durationRatio/(2*median));
 });
 const components={repetition:notes.length>=4?clamp(Math.log2(1+occurrences.length)/Math.log2(9)):null,
  metricalDuration:metric.every(n=>n!==null)?metric.reduce((s,n)=>s+n,0)/metric.length:null,
  melodicProminence:null,structuralPosition:null,cadence:null,structuralTone:null};
 const available=Object.keys(weights).filter(k=>components[k]!==null),weight=available.reduce((s,k)=>s+weights[k],0);
 const ids=new Set(notes.map(n=>n.id)),units=snapshot.units.flatMap(u=>{
  const overlap=u.attackEventIds.filter(id=>ids.has(id)).length;
  return overlap?[{unitId:u.unitId,kind:u.kind,segmentCoverage:overlap/notes.length,unitCoverage:overlap/u.attackEventIds.length,evidenceType:u.evidence.type}]:[];
 });
 return {version:IMPORTANCE_VERSION,snapshotId:snapshot.snapshotId,scope:'source-snapshot-stream',eventIds:[...ids],
  matchedAttackCount:wanted.size,spanAttackCount:notes.length,interveningAttackCount:notes.length-wanted.size,
  durationShare:notes.reduce((s,n)=>s+n.durationRatio,0)/all.reduce((s,n)=>s+n.durationRatio,0),attackShare:notes.length/all.length,
  occurrenceCount:notes.length>=4?occurrences.length:null,occurrences,units,components,availableWeight:weight,
  score:weight?available.reduce((s,k)=>s+weights[k]*components[k],0)/weight:null,calibrated:false};
}
export function compareImportance(query,candidate){
 const keys=Object.keys(weights).filter(k=>query.components[k]!==null&&candidate.components[k]!==null),total=keys.reduce((s,k)=>s+weights[k],0);
 const score=side=>total?keys.reduce((s,k)=>s+weights[k]*side.components[k],0)/total:null;
 const q=score(query),c=score(candidate);
 return {commonComponents:keys,query:q,candidate:c,jointSupport:total?Math.sqrt(q*c):null,calibrated:false,legalProbability:false};
}
export function mapCandidateTargets(snapshot,targets){
 if(!targets?.length)throw new Error('No aligned candidate targets');
 const all=attacks(snapshot),ids=targets.map(t=>{
  const matches=all.filter(n=>n.pitchMidi===t.pitchMidi&&Math.abs(n.onset-t.onset)<1e-6);
  if(matches.length!==1)throw new Error('Missing or ambiguous candidate target');return matches[0].id;
 });
 return [...new Set(ids)];
}

/** Offline enrichment preserves original ranking/alignment. Every analyzed stream gets a reproducible snapshot. */
export async function enrichPreclearanceImportance(querySnapshot,report,{loadSource,analyzeSource,maxNotes=5000,signal,onProgress=()=>{}}){
 if(report.snapshotId!==querySnapshot.snapshotId)throw new Error('Query snapshot mismatch');
 const result=structuredClone(report),cache=new Map(),snapshots=[],tasks=new Map(report.runs.map(r=>[r.taskId,r.selection.task]));
 let completed=0,failed=0;
 for(const group of result.works){
  for(const match of group.matches){
   if(signal?.aborted){match.structureStatus='cancelled';continue;}
   try{
    if(!cache.has(match.workId)){
     try{let snapshot;
      if(analyzeSource)snapshot=await analyzeSource(match.workId,{maxNotes,signal});
      else{const source=await loadSource(match.workId);
      if(source.events.length>maxNotes)throw new Error(`Stream exceeds ${maxNotes} attack budget; deferred, not truncated`);
      snapshot=analyzeStructureSnapshot({...source,sourceHash:structureHash(source)});
      snapshot.warnings.push(...(source.warnings??[]));}
      cache.set(match.workId,{snapshot});snapshots.push(snapshot);
     }catch(error){cache.set(match.workId,{error:String(error.message)})}
    }
    const entry=cache.get(match.workId);if(entry.error)throw new Error(entry.error);
    if(entry.snapshot.identity.streamId!==match.streamId||entry.snapshot.identity.sourceId!==match.sourceId)throw new Error('Candidate identity mismatch');
    const queryIds=tasks.get(match.taskId)?.query.events.filter(n=>n.kind!=='rest').map(n=>n.id);
    if(!queryIds)throw new Error('Query task unavailable');
    match.selectionImportance=match.queryImportance;
    match.queryImportance=segmentImportance(querySnapshot,queryIds);
    match.candidateImportance=segmentImportance(entry.snapshot,mapCandidateTargets(entry.snapshot,match.targets));
    match.importanceComparison=compareImportance(match.queryImportance,match.candidateImportance);
    match.structureStatus='completed';completed++;
   }catch(error){match.structureStatus='needs-review';match.structureError=String(error.message);failed++}
  }
  group.bestMatch=group.matches[0];onProgress({groups:result.works.indexOf(group)+1,total:result.works.length,completed,failed});
 }
 result.structureEnrichment={version:IMPORTANCE_VERSION,completed,failed,streams:cache.size,snapshots:snapshots.map(s=>({snapshotId:s.snapshotId,identity:s.identity,dependencies:s.dependencies})),rankingChanged:false,
  status:signal?.aborted?'cancelled':failed?'partial':'completed',cancelled:result.works.flatMap(g=>g.matches).filter(m=>m.structureStatus==='cancelled').length,
  warnings:['Heuristic evidence, not a Schenkerian analysis or infringement probability.','Shares are within the indexed melodic stream, not all parts of the work.','Unavailable form, cadence, structural-tone and melody-role evidence stays null.']};
 return {report:result,snapshots};
}
