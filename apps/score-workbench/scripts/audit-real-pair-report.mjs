import {readFileSync,writeFileSync} from 'node:fs';
import {join} from 'node:path';
import assert from 'node:assert/strict';
const [dir]=process.argv.slice(2);
if(!dir)throw Error('Case report directory required');
const read=name=>JSON.parse(readFileSync(join(dir,name),'utf8'));
const {snapshot}=read('prepared.json'),report=read('search.json');
assert.equal(report.snapshotId,snapshot.snapshotId);
const events=new Map(snapshot.events.map(e=>[e.id,e])),direct=new Set(),represented=new Set();
const location=task=>{
 const notes=task.query.events.filter(e=>e.kind==='note');
 for(const e of notes)assert(events.has(e.id),'Query event missing from source snapshot');
 const first=events.get(notes[0]?.id),last=events.get(notes.at(-1)?.id);
 return {taskId:task.taskId,attackIds:notes.map(e=>e.id),startMeasure:first?.measure,endMeasure:last?.measure,startQuarter:first?.onset,endQuarter:last?last.onset+last.durationRatio:null};
};
const tasks=report.runs.map(r=>{
 const span=location(r.selection.task),occurrences=(r.selection.occurrences||[]).map(location);
 if(r.status==='completed'){
  span.attackIds.forEach(id=>direct.add(id));
  for(const s of [span,...occurrences])s.attackIds.forEach(id=>represented.add(id));
 }
 const results=[...(r.result?.exact||[]),...(r.result?.similar||[])];
 return {...span,status:r.status,error:r.error,elapsedMs:r.elapsedMs,returnedResults:results.length,occurrences,
  returnedSources:[...new Set(results.map(x=>x.work.sourceId))]};
});
const noteCount=snapshot.events.filter(e=>e.kind==='note').length;
const audit={schema:'musicanote-real-pair-coverage/v1',snapshotId:snapshot.snapshotId,
 selectedStream:snapshot.identity.streamId,sourceAttackCount:noteCount,
 directlySearchedAttackCount:direct.size,representedIncludingRepeatAttackCount:represented.size,
 directlySearchedFraction:direct.size/Math.max(1,noteCount),representedIncludingRepeatFraction:represented.size/Math.max(1,noteCount),
 unrepresentedAttackIds:[...events.values()].filter(e=>e.kind==='note'&&!represented.has(e.id)).map(e=>e.id),tasks,
 warnings:['Coverage denominator is one selected stream, not the full work.','Repeat representatives are not independently searched or independent evidence.','No returned match is not proof of absence; retrieval and result limits apply.','Measures are parser coordinates, not verified against another score edition.']};
assert(direct.size<=represented.size&&represented.size<=noteCount);
writeFileSync(join(dir,'coverage-audit.json'),JSON.stringify(audit,null,2),{flag:'wx'});
console.log(JSON.stringify({sourceAttackCount:noteCount,directlySearched:direct.size,representedIncludingRepeats:represented.size,tasks:tasks.length}));
