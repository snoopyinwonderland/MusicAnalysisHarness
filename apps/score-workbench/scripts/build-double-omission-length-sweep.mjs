import {mkdirSync,readFileSync,writeFileSync} from 'node:fs';

const output=process.argv[2]||'evaluation/reports/double-omission-length-sweep-v1';
const sourceSuites=['v2','v3'].map(version=>({
 version,
 suite:JSON.parse(readFileSync(`evaluation/reports/double-ornament-trial-${version}/suite.json`,'utf8')),
}));
const queryLengths=[8,10,12,14,16,18];
const number=value=>value&&typeof value==='object'&&Number.isFinite(value.n)&&Number.isFinite(value.d)?value.n/value.d:Number(value);
const round=value=>Number(Number(value).toFixed(6));
const spelling=event=>{
 const pitch=event.writtenPitch;if(!pitch)return undefined;
 const alter=Number(pitch.alter||0),accidental=alter>0?'#'.repeat(alter):alter<0?'b'.repeat(-alter):'';
 return `${pitch.step}${accidental}${pitch.octave}`;
};
const cleanNote=event=>event?.kind==='note'&&!event.grace&&!event.cue&&!event.tieStart&&!event.tieStop&&!event.tieChainId&&event.isAttack!==false&&number(event.durationQ)>0;

function sourceWindow(context,targetIds,noteCount){
 const noteEventIndexes=context.map((event,index)=>event.kind==='note'?index:-1).filter(index=>index>=0);
 const positions=targetIds.map(id=>noteEventIndexes.findIndex(index=>context[index].id===id));
 if(positions.some(position=>position<0))return null;
 const firstTarget=Math.min(...positions),lastTarget=Math.max(...positions);
 const lower=Math.max(0,lastTarget-noteCount+2),upper=Math.min(firstTarget-1,noteEventIndexes.length-noteCount);
 if(lower>upper)return null;
 const ideal=Math.round((firstTarget+lastTarget-noteCount+1)/2),start=Math.max(lower,Math.min(upper,ideal));
 const firstEvent=noteEventIndexes[start],lastEvent=noteEventIndexes[start+noteCount-1];
 const events=context.slice(firstEvent,lastEvent+1);
 if(events.filter(event=>event.kind==='note').length!==noteCount||events.some(event=>event.kind==='note'&&!cleanNote(event)))return null;
 return events;
}

function toEvents(source,caseId){
 return source.map((event,index)=>({
  id:`${caseId.toLowerCase()}-${String(index+1).padStart(2,'0')}`,
  sourceEventId:event.id,
  kind:event.kind,
  pitchMidi:event.pitchMidi??null,
  durationRatio:round(number(event.durationQ)),
  ...(spelling(event)?{spelling:spelling(event)}:{}),
 }));
}

function omitAndPreserve(events,targetIds){
 const output=events.map(event=>({...event})),removed=[];
 for(const targetId of targetIds){
  const index=output.findIndex(event=>event.sourceEventId===targetId);
  if(index<=0||output[index].kind!=='note')return null;
  let receiver=index-1;while(receiver>=0&&output[receiver].kind!=='note')receiver--;
  if(receiver<0)return null;
  output[receiver].durationRatio=round(output[receiver].durationRatio+output[index].durationRatio);
  removed.push({sourceEventId:targetId,pitchMidi:output[index].pitchMidi,durationRatio:output[index].durationRatio,transferredTo:output[receiver].sourceEventId});
  output.splice(index,1);
 }
 return {events:output.map(({sourceEventId,...event})=>event),removed};
}

const candidates=[],seen=new Set();
for(const {version,suite} of sourceSuites)for(const base of suite.bases){
 if(base.deletion.type!=='separated'||base.deletion.indices[1]-base.deletion.indices[0]>7)continue;
 const targetIds=base.deletion.indices.map(index=>base.xmlEvents[index]?.id),key=`${base.expected.sourceId}|${targetIds.join('|')}`;
 if(targetIds.some(id=>!id)||seen.has(key))continue;
 seen.add(key);candidates.push({version,base,targetIds});
}

const bases=[],cases=[],rejections=[];
for(const candidate of candidates){
 const baseId=`DL${String(bases.length+1).padStart(2,'0')}`,lengthCases=[];
 for(const queryNoteCount of queryLengths){
  const sourceNoteCount=queryNoteCount+2,source=sourceWindow(candidate.base.context,candidate.targetIds,sourceNoteCount);
  if(!source){rejections.push({baseId,sourceId:candidate.base.expected.sourceId,queryNoteCount,reason:'no-clean-bounded-window'});continue}
  const caseId=`${baseId}-Q${String(queryNoteCount).padStart(2,'0')}`,events=toEvents(source,caseId),mutation=omitAndPreserve(events,candidate.targetIds);
  if(!mutation||mutation.events.filter(event=>event.kind==='note').length!==queryNoteCount){rejections.push({baseId,sourceId:candidate.base.expected.sourceId,queryNoteCount,reason:'preserve-time-mutation-failed'});continue}
  const before=round(events.reduce((sum,event)=>sum+event.durationRatio,0)),after=round(mutation.events.reduce((sum,event)=>sum+event.durationRatio,0));
  if(before!==after)throw Error(`Duration changed for ${caseId}: ${before} -> ${after}`);
  const startsOnDownbeat=Math.abs(number(source[0].beatQ)||0)<1e-6;
  const query={version:1,mode:'melody_rhythm',meter:source[0].meter||candidate.base.query.meter,startsOnDownbeat,includeRests:true,absoluteExactOnly:false,events:mutation.events};
  const record={caseId,baseId,kind:'two-qualified-ornaments-omitted-preserve-time',queryNoteCount,sourceNoteCount,query,removed:mutation.removed,totalDuration:after,sourceRange:{firstEventId:source[0].id,lastEventId:source.at(-1).id,startMeasure:source[0].measureOrdinal,endMeasure:source.at(-1).measureOrdinal}};
  cases.push(record);lengthCases.push(caseId);
 }
 if(lengthCases.length===queryLengths.length)bases.push({baseId,priorSuite:candidate.version,priorBaseId:candidate.base.baseId,expected:candidate.base.expected,title:candidate.base.expected.title,targetIds:candidate.targetIds,deletionEvidence:candidate.base.deletion,qualification:candidate.base.qualification,caseIds:lengthCases});
 else {
  for(let index=cases.length-1;index>=0;index--)if(cases[index].baseId===baseId)cases.splice(index,1);
 }
}

mkdirSync(output,{recursive:false});
const suite={schema:'double-omission-length-sweep/1',createdAt:new Date().toISOString(),selection:'Previously XML-audited weak, short, stepwise, separated ornament candidates; search outcomes were not used.',queryLengths,sourceLengths:queryLengths.map(length=>length+2),timing:'Both omitted note durations are transferred to the preceding surviving attack; total query duration is preserved.',decisionRule:'Estimate the first query-note-count bin where Top100 recall no longer drops sharply; do not create a production exception from this small repeated-measures sample alone.',bases,cases,rejections,limitations:['Repeated-measures sample from prior v2/v3 XML-audited cases; several windows share a work and are not independent.','Ornament status is heuristic, not a human-certified Schenkerian judgment.','Shorter and longer windows contain the same two deletion sites but different surrounding context.','No search rule is changed by this experiment.']};
writeFileSync(`${output}/suite.json`,JSON.stringify(suite,null,2),{flag:'wx'});
console.log(JSON.stringify({output,bases:bases.length,cases:cases.length,queryLengths,rejections},null,2));
