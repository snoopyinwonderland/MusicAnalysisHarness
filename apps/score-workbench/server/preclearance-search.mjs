import { structureHash, structureSearchQueries } from './structure-analysis-adapter.mjs';
import {buildSearchWindows} from './search-segments.mjs';

export const SELECTION_CONFIG = Object.freeze({ version:'preclearance-selection/3', kinds:['phrase'], motifTasks:3, maximumTasks:7, minimumNotes:7, maximumNotes:48,
  maximumRepeatRatio:.65, minimumIntervalKinds:3, maximumOverlap:.7, minimumKnownMelodyRole:.35,
  weights:{ melodicProminence:.25, repetition:.20, structuralPosition:.20, metricalDuration:.15, cadence:.10, structuralTone:.10 } });
const clamp = n => Math.max(0,Math.min(1,n));
const notesOf = task => task.query.events.filter(e=>e.kind==='note');
const normalized = n => Math.round(n*1000000)/1000000;
function signature(task) {
  const notes=notesOf(task), root=notes[0].pitchMidi, unit=notes[0].durationRatio;
  return structureHash({meter:task.query.meter,phase:Number.isFinite(notes[0].beat)?normalized(notes[0].beat):null,
    events:task.query.events.map(e=>[e.kind,e.kind==='note'?e.pitchMidi-root:null,normalized(e.durationRatio/unit)])});
}

export function selectStructureQueries(snapshot, config=SELECTION_CONFIG) {
  const strategy=config.segmentStrategy??'phrase';
  if(!['phrase','windows','hybrid'].includes(strategy))throw Error('Invalid segment strategy');
  if(strategy!=='phrase'){
    const bank=buildSearchWindows(snapshot,config.windowConfig),windowSnapshot={...snapshot,units:bank.units};
    const b=selectStructureQueries(windowSnapshot,{...config,segmentStrategy:'phrase',kinds:['window']});
    if(strategy==='windows')return {...b,config,generatedUnits:bank.units,windowBank:{total:bank.totalPossible,prepared:bank.units.length,omitted:bank.omittedByBudget},selected:b.selected.map(e=>({...e,role:'window'}))};
    const a=selectStructureQueries(snapshot,{...config,segmentStrategy:'phrase'}),keys=new Set(a.selected.map(e=>e.signature));
    return {config,selected:[...a.selected,...b.selected.filter(e=>!keys.has(e.signature)).map(e=>({...e,role:'window-supplement'}))],rejected:[...a.rejected,...b.rejected],totalPrepared:a.totalPrepared+b.totalPrepared,
      generatedUnits:bank.units,windowBank:{total:bank.totalPossible,prepared:bank.units.length,omitted:bank.omittedByBudget},warning:'Overlapping windows are not independent phrase evidence; up to twice the per-strategy task budget.'};
  }
  if (!Number.isInteger(config.maximumTasks)||config.maximumTasks<1||config.maximumTasks>7) throw new Error('maximumTasks must be 1..7');
  const kinds=config.kinds??['phrase'];
  if(!kinds.length||kinds.some(k=>!['phrase','motif','window'].includes(k)))throw new Error('Invalid selection kinds');
  if(!Number.isInteger(config.motifTasks??3)||(config.motifTasks??3)<0||(config.motifTasks??3)>7)throw new Error('motifTasks must be 0..7');
  if(!Number.isInteger(config.maximumNotes)||config.maximumNotes<config.minimumNotes)throw new Error('Invalid note limits');
  // Phrase selection is identical in A and B. Motifs cannot displace it.
  if(kinds.includes('phrase')&&kinds.includes('motif')){
    const a=selectStructureQueries(snapshot,{...config,kinds:['phrase']}), b=selectStructureQueries(snapshot,{...config,kinds:['motif']});
    const signatures=new Set(a.selected.map(e=>e.signature));
    const extra=b.selected.filter(e=>!signatures.has(e.signature)).slice(0,config.motifTasks??3);
    return {config,selected:[...a.selected,...extra.map(e=>({...e,role:'motif-supplement'}))],rejected:[...a.rejected,...b.rejected],totalPrepared:a.totalPrepared+b.totalPrepared,
      phraseTasks:a.selected.length,motifTasks:extra.length};
  }
  const units=snapshot.units.flatMap(u=>{
    if(u.kind!=='phrase'||u.attackEventIds.length<=config.maximumNotes)return [u];
    const windows=[],step=Math.max(1,Math.floor(config.maximumNotes*.75));
    for(let start=0;start<u.attackEventIds.length;start+=step){
      const chosen=u.attackEventIds.slice(start,start+config.maximumNotes);if(chosen.length<config.minimumNotes)break;
      const ns=snapshot.events.filter(n=>chosen.includes(n.id)),first=ns[0],last=ns.at(-1),end=last.onset+last.durationRatio;
      windows.push({...u,parentUnitId:u.unitId,unitId:u.unitId+'-window-'+start,attackEventIds:chosen,startQuarter:first.onset,endQuarter:end,eventIds:snapshot.events.filter(n=>n.onset>=first.onset&&n.onset<end).map(n=>n.id)});
      if(start+config.maximumNotes>=u.attackEventIds.length)break;
    }return windows;
  });
  const all=structureSearchQueries({...snapshot,units},{kinds}), groups=new Map(), rejected=[];
  for(const t of all){const selected=units.filter(u=>t.unitIds.includes(u.unitId));t.parentUnitIds=[...new Set(selected.map(u=>u.parentUnitId??u.unitId))];t.kinds=[...new Set(selected.map(u=>u.kind))];}
  for(const task of all){
    const notes=notesOf(task), intervals=notes.slice(1).map((n,i)=>n.pitchMidi-notes[i].pitchMidi);
    const repeatRatio=intervals.filter(x=>x===0).length/Math.max(1,intervals.length);
    let reason=null;
    if(Number.isFinite(snapshot.identity.melodyRoleScore)&&snapshot.identity.melodyRoleScore<config.minimumKnownMelodyRole)reason='low-melody-role';
    else if(notes.length<config.minimumNotes)reason='too-short';
    else if(notes.length>config.maximumNotes)reason='needs-subdivision';
    else if(repeatRatio>config.maximumRepeatRatio||new Set(intervals).size<config.minimumIntervalKinds)reason='low-information';
    else if(!task.query.meter||!/^\d+\/\d+$/.test(task.query.meter))reason='meter-needs-review';
    if(reason){rejected.push({taskId:task.taskId,unitIds:task.unitIds,reason});continue;}
    const key=signature(task), entry=groups.get(key);
    if(entry)entry.occurrences.push(task);else groups.set(key,{signature:key,task,occurrences:[task]});
  }
  const candidates=[...groups.values()].map(group=>{
    const notes=notesOf(group.task), ids=new Set(notes.map(n=>n.id));
    const knownRole=snapshot.identity.melodyRoleScore;
    const components={melodicProminence:Number.isFinite(knownRole)?clamp(knownRole):null,
      repetition:clamp(Math.log2(1+group.occurrences.length)/Math.log2(9)),
      structuralPosition:null,metricalDuration:null,cadence:null,structuralTone:null};
    const available=Object.entries(config.weights).filter(([key])=>components[key]!==null);
    const weight=available.reduce((sum,[,w])=>sum+w,0);
    const importance=available.reduce((sum,[key,w])=>sum+components[key]*w,0)/weight;
    // Selection heuristic only; unavailable structure components are never imputed.
    const lengthSupport=clamp(notes.length/12), durationShare=clamp(notes.reduce((s,n)=>s+n.durationRatio,0)/Math.max(1,snapshot.events.reduce((s,n)=>s+n.durationRatio,0)));
    const score=.55*importance+.35*lengthSupport+.1*durationShare;
    return {...group,attackIds:ids,selectionScore:score,importance:{score:importance,components,availableWeight:weight,calibrated:false},
      warnings:knownRole===undefined?['Melody role has not been confirmed.']:[]};
  }).sort((a,b)=>b.selectionScore-a.selectionScore||a.task.taskId.localeCompare(b.task.taskId));
  const selected=[];
  for(const candidate of candidates){
    const overlap=selected.some(other=>candidate.occurrences.some(a=>other.occurrences.some(b=>{
      const left=new Set(notesOf(a).map(n=>n.id)),right=notesOf(b).map(n=>n.id);
      return right.filter(id=>left.has(id)).length/Math.min(left.size,right.length)>config.maximumOverlap;
    })));
    if(overlap){rejected.push({taskId:candidate.task.taskId,reason:'overlapping-evidence'});continue;}
    if(selected.length>=config.maximumTasks){rejected.push({taskId:candidate.task.taskId,reason:'task-budget'});continue;}
    const {attackIds,...record}=candidate;
    selected.push({...record,role:selected.length<3?'primary':'secondary'});
  }
  return {config,selected,rejected,totalPrepared:all.length};
}

export function aggregatePreclearanceResults(snapshot, runs, resolveIdentity=()=>null) {
  const groups=new Map(), allQueryIds=new Set(runs.flatMap(r=>notesOf(r.selection.task).map(n=>n.id)));
  for(const run of runs)for(const result of [...(run.result?.exact??[]),...(run.result?.similar??[])]){
    const work=result.work,identity=resolveIdentity(work),canonicalWorkId=identity?.status==='verified'?identity.canonicalWorkId:work.canonicalWorkId,
      key=canonicalWorkId?`canonical:${canonicalWorkId}`:work.sourceId?`source:${work.sourceId}`:`work:${work.workId}`;
    const queryNotes=notesOf(run.selection.task);
    const aligned=(result.alignment??[]).filter(p=>p.queryIndex!==null&&p.candidateIndex!==null&&p.type!=='insertion'&&p.type!=='deletion');
    const queryIds=aligned.map(p=>queryNotes[p.queryIndex]?.id).filter(Boolean);
    const targets=aligned.map(p=>work.notes?.[p.candidateIndex]).filter(Boolean);
    const match={taskId:run.taskId,unitIds:run.selection.task.unitIds,queryIds,
      similarity:result.localSimilarity,kind:result.kind,queryImportance:run.selection.importance,
      candidateImportance:null,candidateOccurrenceProxy:result.occurrenceImportance??null,
      sourceId:work.sourceId,workId:work.workId,streamId:work.streamId,identity,
      edition:identity?.edition??null,rightsStatus:identity?.edition?.rightsStatus??work.rightsStatus??'unknown',accessPolicy:work.accessPolicy??null,
      startMeasure:result.startMeasure,endMeasure:result.endMeasure,targets,
      scores:result.scores,alignment:result.alignment,why:result.why,
      occurrenceCount:result.occurrenceCount,partOccurrences:result.partOccurrences};
    let group=groups.get(key);
    if(!group){group={key,canonicalWorkId:canonicalWorkId??null,groupingBasis:canonicalWorkId?'canonical-work':work.sourceId?'source-file':'work-id',title:work.title,artist:work.artist,matches:[]};groups.set(key,group);}
    group.matches.push(match);
  }
  return [...groups.values()].map(group=>{
    group.matches.sort((a,b)=>b.similarity-a.similarity||a.workId.localeCompare(b.workId));
    const covered=new Set(group.matches.flatMap(m=>m.queryIds));
    const editions=[...new Set(group.matches.map(m=>m.sourceId))].map(sourceId=>({sourceId,matches:group.matches.filter(m=>m.sourceId===sourceId).map(m=>({workId:m.workId,streamId:m.streamId,startMeasure:m.startMeasure,endMeasure:m.endMeasure,taskId:m.taskId})),metadata:group.matches.find(m=>m.sourceId===sourceId)?.edition??null}));
    return {...group,editions,editionCount:editions.length,bestMatch:group.matches[0],similarity:group.matches[0].similarity,
      coverage:covered.size/Math.max(1,allQueryIds.size),reviewPriority:null,reviewLevel:'not-calibrated',
      warnings:['Candidate structural importance and corpus distinctiveness are not calibrated.','Repeated or overlapping matches are not summed.']};
  }).sort((a,b)=>b.similarity-a.similarity||a.key.localeCompare(b.key));
}

export async function runPreclearanceSearch(snapshot,{search,config=SELECTION_CONFIG,resultLimit=30,includeSelf=false,excludedCanonicalWorkId=null,onProgress=()=>{},onResult=()=>{},completedRuns=[],signal,resolveIdentity=()=>null}={}) {
  if(typeof search!=='function')throw new Error('A search engine is required');
  if(!Number.isInteger(resultLimit)||resultLimit<1||resultLimit>100)throw new Error('resultLimit must be 1..100');
  const selection=selectStructureQueries(snapshot,config),runs=[];
  for(const entry of selection.selected){
    if(signal?.aborted)break;
    const completed=completedRuns.find(run=>run.taskId===entry.task.taskId&&run.status==='completed');
    if(completed){runs.push({...completed,reused:true});onProgress({stage:'reused',index:runs.length,total:selection.selected.length});continue;}
    const task=entry.task, query=structuredClone(task.query);
    // Existing engine derives time from sequential durations. Preserve metric phase
    // via a leading rest when the source beat is known (beat is quarter-based).
    const first=notesOf(task)[0], phase=Number(first.beat)-1;
    if(Number.isFinite(phase)&&phase>0)query.events.unshift({id:`phase-${task.taskId}`,kind:'rest',pitchMidi:null,durationRatio:phase});
    query.startsOnDownbeat=phase===0;
    if(!includeSelf&&snapshot.identity.workId)query.excludeWorkIds=[snapshot.identity.workId];
    const started=performance.now();onProgress({stage:'search',index:runs.length+1,total:selection.selected.length});
    try{
      const result=await search(query,resultLimit);
      // Enforce self exclusion after search too: other streams share a source.
      for(const kind of ['exact','similar'])result[kind]=(result[kind]??[]).filter(r=>includeSelf||
        (r.work.sourceId!==snapshot.identity.sourceId&&r.work.workId!==snapshot.identity.workId&&(!excludedCanonicalWorkId||resolveIdentity(r.work)?.canonicalWorkId!==excludedCanonicalWorkId)));
      runs.push({taskId:task.taskId,selection:entry,query,status:'completed',elapsedMs:performance.now()-started,result});
    }catch(error){runs.push({taskId:task.taskId,selection:entry,query,status:'failed',elapsedMs:performance.now()-started,error:String(error.message??error)});}
    await onResult(runs.at(-1));
  }
  return {schema:'musicanote-preclearance-search/1',snapshotId:snapshot.snapshotId,dependencies:snapshot.dependencies,
    selectionConfigHash:structureHash(config),selection,runs,works:aggregatePreclearanceResults(snapshot,runs,resolveIdentity),
    status:signal?.aborted?'cancelled':runs.some(r=>r.status==='failed')?'partial':runs.length?'completed':'needs-review'};
}
