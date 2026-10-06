import {readFileSync,writeFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
const dir='evaluation/reports/eighth-meter-60-v1',raw=readFileSync(dir+'/suite.json'),s=JSON.parse(raw),selection=JSON.parse(readFileSync(dir+'/selection.json'));
assert.equal(createHash('sha256').update(raw).digest('hex'),selection.sha256);
assert.equal(s.cases.length,60);assert.equal(s.bases.length,20);assert.equal(new Set(s.cases.map(c=>c.caseId)).size,60);
assert.equal(new Set(s.bases.map(b=>b.parentBaseId)).size,10);
for(const meter of ['6/8','3/8'])assert.equal(s.bases.filter(b=>b.length===12&&b.query.meter===meter).length,5);
const onsets=es=>{let t=0;return new Map(es.map(e=>{const p=[e.id,t];t+=e.durationRatio;return p}));};
for(const b of s.bases){assert.ok(['6/8','3/8'].includes(b.query.meter));assert.equal(b.query.events.filter(e=>e.kind==='note').length,b.length);}
for(const c of s.cases){
 const b=s.bases.find(b=>b.baseId===c.baseId),es=b.query.events;
 assert.equal(c.query.meter,b.query.meter);assert.ok(c.query.events.every(e=>e.durationRatio>0));
 if(c.kind==='original'){assert.deepEqual(c.query,b.query);continue;}
 const edit=c.transformation.omission,i=edit.index;
 assert.equal(es[i].id,edit.eventId);assert.equal(es[i].kind,'note');assert.equal(es[i-1].kind,'note');assert.ok(edit.evidence.metric<.5);
 const expected=structuredClone(es);expected.splice(i,1);
 if(c.kind==='ornament-delete-preserve-time')expected[i-1].durationRatio+=es[i].durationRatio;
 else assert.equal(c.kind,'ornament-delete');
 assert.deepEqual(c.query.events,expected);assert.equal(c.query.events.filter(e=>e.kind==='note').length,b.length-1);
 const old=onsets(es),now=onsets(c.query.events);
 for(let j=i+1;j<es.length;j++)assert.ok(Math.abs(now.get(es[j].id)-old.get(es[j].id)+(c.kind==='ornament-delete'?es[i].durationRatio:0))<1e-8);
}
const audit={validatedQueries:60,parents:10,lengths:[12,8],meterDistribution:s.meterDistribution,timingVerified:true,suiteHash:selection.sha256,checkedAt:new Date().toISOString()};
writeFileSync(dir+'/suite-validation.json',JSON.stringify(audit,null,2));console.log(JSON.stringify(audit));

