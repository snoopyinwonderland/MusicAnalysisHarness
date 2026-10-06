import {readFileSync,writeFileSync,existsSync} from 'node:fs';
import assert from 'node:assert/strict';
const batch=process.argv[2]??'double-ornament-trial-v3';
const dir='evaluation/reports/'+batch,runs='evaluation/runs/'+batch;
const suite=JSON.parse(readFileSync(dir+'/suite.json'));
const excluded=JSON.parse(readFileSync('evaluation/reports/double-ornament-trial-v2/suite.json')).bases;
const overlap=(a,b)=>a.expected.workId===b.expected.workId&&a.focus[0].o<b.focus.at(-1).o+b.focus.at(-1).d&&a.focus.at(-1).o+a.focus.at(-1).d>b.focus[0].o;
const diagnostics=[];
for(const b of suite.bases){
 assert.equal(b.query.events.filter(e=>e.kind==='note').length,16);
 assert.equal(b.deletion.indices.length,2);
 assert.ok(!excluded.some(a=>overlap(a,b)),'Overlaps prior trial: '+b.baseId);
 assert.ok(!suite.bases.some(a=>a!==b&&overlap(a,b)),'Overlaps new trial: '+b.baseId);
 for(const count of [0,1,2]){
  const c=suite.cases.find(c=>c.caseId===b.baseId+'-delete'+count);
  assert.deepEqual(c.query.events,b.query.events.filter((e,i)=>!b.deletion.indices.slice(0,count).includes(i)));
  const path=runs+'/'+c.caseId+(existsSync(runs+'/'+c.caseId+'.retry.json')?'.retry':'')+'.json';
  if(!existsSync(path))continue;
  const run=JSON.parse(readFileSync(path)),all=run.result?[...run.result.exact,...run.result.similar]:[];
  const retained=b.indexLinks.filter(l=>!c.changedSourceIds.includes(b.query.events[b.xmlEvents.findIndex(e=>e.id===l.eventId)].id)).map(l=>l.note);
  const sameSource=all.map((m,i)=>({m,rank:i+1})).filter(({m})=>m.work.sourceId===b.expected.sourceId).map(({m,rank})=>{
   const notes=(m.alignment??[]).filter(p=>p.queryIndex!==null&&p.candidateIndex!==null).map(p=>m.work.notes[p.candidateIndex]).filter(Boolean);
   const sameSequence=notes.length===retained.length&&notes.every((n,i)=>n.pitchMidi===retained[i].p&&Math.abs(n.durationRatio-retained[i].d)<1e-6);
   const shifts=notes.length===retained.length?notes.map((n,i)=>n.onset-retained[i].o):[];
   const constantShift=sameSequence&&shifts.every(x=>Math.abs(x-shifts[0])<1e-6)?shifts[0]:null;
   const originalStartInOccurrences=(m.partOccurrences??[]).some(p=>p.streamId===b.expected.streamId&&p.measures?.includes(b.focus[0].m));
   return {rank,workId:m.work.workId,range:[m.startMeasure,m.endMeasure],samePitchDurationSequence:sameSequence,constantOnsetShift:constantShift,pairedNotes:notes.length,originalStartInOccurrences,occurrenceMeasures:m.occurrenceMeasures,partOccurrences:m.partOccurrences};
  });
  diagnostics.push({caseId:c.caseId,status:run.status,originalRange:[b.focus[0].m,b.focus.at(-1).m],sameSource});
 }
}
const result={batch,checkedAt:new Date().toISOString(),bases:suite.bases.length,queries:suite.cases.length,overlapWithPrior:0,overlapWithinBatch:0,diagnostics};
writeFileSync(dir+'/audit.json',JSON.stringify(result,null,2));console.log(JSON.stringify({...result,diagnostics:diagnostics.length}));
