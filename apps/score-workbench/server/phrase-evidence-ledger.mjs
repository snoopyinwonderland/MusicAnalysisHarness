import {createHash} from 'node:crypto';
const hash=value=>createHash('sha256').update(value).digest('hex');
/** Read-only adapter: records actual emitted cues, never re-runs or edits rules. */
export function phraseEvidenceLedger(notes,analysis,{xml,streamId,analyzerRevision,gapTraces=[]}={}){
 const sourceRevision=typeof xml==='string'?hash(xml):null;
 const inputRevision=hash(JSON.stringify({notes,streamId:streamId??null}));
 const runId=hash(JSON.stringify({inputRevision,sourceRevision,version:analysis.version,analyzerRevision:analyzerRevision??null}));
 const observations=new Map(),records=[];
 const observe=(index,field)=>{
  const n=notes[index];if(!n)return null;
  const present=Object.prototype.hasOwnProperty.call(n,field)&&n[field]!==undefined,value=present?n[field]:null;
  const key=`${inputRevision}:note:${index}:${field}`;
  observations.set(key,{key,index,noteId:n.id??null,field,present,value});return key;
 };
 const attackSelectionRefs=gapTraces.length?notes.flatMap((_,i)=>['isAttack','tieStop'].map(field=>observe(i,field))):[];
 for(const boundary of analysis.boundaries??[])for(const [ordinal,cue] of (boundary.cues??[]).entries()){
  const i=boundary.index,observationRefs=[];
  // These are real inputs of the gap numerator. The local-unit normalization,
  // guards and later grouping rules are NOT silently treated as fully traced.
  if(['observed-gap','observed-continuity'].includes(cue.name)&&i>0&&i<notes.length){
   for(const [index,field] of [[i,'onset'],[i-1,'onset'],[i-1,'durationRatio']]){
    if(typeof notes[index]?.[field]!=='number'||!Number.isFinite(notes[index][field]))continue;
    const ref=observe(index,field);if(ref)observationRefs.push(ref);
   }
  }
  const trace=cue.name==='observed-gap'?gapTraces.find(t=>t.boundaryIndex===i&&t.ruleId===cue.name):null;
  const complete=Boolean(trace?.complete&&sourceRevision&&streamId&&analyzerRevision);
  if(trace)for(const read of trace.reads){const ref=observe(read.index,read.field);if(ref&&!observationRefs.includes(ref))observationRefs.push(ref);}
  records.push({evidenceId:`${runId}:boundary:${i}:cue:${ordinal}`,boundaryIndex:i,ruleId:cue.name,
   strength:cue.strength,payload:structuredClone(cue.evidence??{}),observationRefs,
   traceStatus:complete?'complete-rule':observationRefs.length>=3?'partial':'unmapped',
   scope:'cue-only-not-final-boundary',selectionObservationRefs:trace?attackSelectionRefs:[],trace:trace?structuredClone(trace):null,
   missing:complete?[]:observationRefs.length>=3?['local-unit-and-guards','rule-parent-dependencies']:['rule-input-mapping'],complete});
 }
 return {schemaVersion:'phrase-evidence-ledger-0.2',sourceRevision,inputRevision,runId,streamId:streamId??null,
  engineVersion:analysis.version,analyzerRevision:analyzerRevision??null,observations:[...observations.values()],records,
  completeRuleCount:records.filter(r=>r.complete).length,tracedCueCount:records.filter(r=>r.traceStatus==='partial').length,unmappedCueCount:records.filter(r=>r.traceStatus==='unmapped').length,
  complete:false,reviewEligibility:'blocked-incomplete-lineage',autoApply:false};
}
