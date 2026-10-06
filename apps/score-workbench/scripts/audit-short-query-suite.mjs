import {readFileSync,writeFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
const dir='evaluation/reports/short-query-90-v1',raw=readFileSync(dir+'/suite.json'),s=JSON.parse(raw),selection=JSON.parse(readFileSync(dir+'/selection.json'));
assert.equal(createHash('sha256').update(raw).digest('hex'),selection.sha256);
assert.equal(s.cases.length,90);assert.equal(s.bases.length,30);assert.equal(new Set(s.cases.map(c=>c.caseId)).size,90);
const parents=new Set(s.bases.map(b=>b.parentBaseId));assert.equal(parents.size,10);
for(const p of parents){const bs=s.bases.filter(b=>b.parentBaseId===p),long=bs.find(b=>b.length===12).query.events;assert.deepEqual(bs.map(b=>b.length).sort((a,b)=>a-b),[6,8,12]);for(const b of bs){assert.deepEqual(b.query.events,long.slice(0,b.query.events.length));assert.equal(b.query.events.filter(e=>e.kind==='note').length,b.length);}}
for(const c of s.cases){
 const b=s.bases.find(b=>b.baseId===c.baseId),es=b.query.events;assert.ok(c.query.events.every(e=>e.durationRatio>0));assert.equal(c.query.meter,b.query.meter);
 if(c.kind==='original')assert.deepEqual(c.query,b.query);
 if(c.kind==='pitch-change'){
  assert.equal(c.query.events.length,es.length);assert.equal(c.changedSourceIds.length,1);const edit=c.transformation.pitch;
  assert.ok([1,-1,2,-2].includes(edit.semitones));assert.equal(edit.to-edit.from,edit.semitones);
  for(let i=0;i<es.length;i++){const q=c.query.events[i];assert.deepEqual(q,es[i].id===edit.eventId?{...es[i],pitchMidi:edit.to}:es[i]);}
 }
 if(c.kind==='ornament-delete'){
  const edit=c.transformation.omission;assert.deepEqual(c.query.events,es.filter(e=>e.id!==edit.eventId));assert.equal(c.query.events.filter(e=>e.kind==='note').length,b.length-1);
  assert.ok(edit.index>0&&edit.index<es.length-1);assert.equal(es[edit.index].kind,'note');assert.ok(edit.evidence.metric<.5);assert.ok(edit.evidence.duration<=.5);
 }
}
const audit={validatedQueries:90,parents:10,lengths:[12,8,6],meterDistribution:s.meterDistribution,suiteHash:selection.sha256,checkedAt:new Date().toISOString()};
writeFileSync(dir+'/suite-validation.json',JSON.stringify(audit,null,2));console.log(JSON.stringify(audit));
