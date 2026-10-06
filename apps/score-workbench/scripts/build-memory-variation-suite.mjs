import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
const batch='memory-variation-50-v1',dir='evaluation/reports/'+batch;
const pool=['double-ornament-trial-v2','double-ornament-trial-v3'].flatMap(name=>JSON.parse(readFileSync('evaluation/reports/'+name+'/suite.json')).bases.map(b=>({...b,priorBatch:name})));
const seen=new Set(),bases=[];
for(const b of pool){
 const signature=JSON.stringify(b.query.events.map(e=>[e.kind,e.pitchMidi,e.durationRatio]));
 if(seen.has(signature))continue;seen.add(signature);
 const id='MEM'+String(bases.length+1).padStart(2,'0');bases.push({...b,priorBaseId:b.baseId,baseId:id});
 if(bases.length===10)break;
}
assert.equal(bases.length,10);
const cases=[],clone=x=>structuredClone(x),total=es=>es.reduce((s,e)=>s+e.durationRatio,0);
function add(b,kind,events,description,changedSourceIds=[],positive=true){
 assert.ok(events.every(e=>Number.isFinite(e.durationRatio)&&e.durationRatio>0));
 assert.equal(new Set(events.map(e=>e.id)).size,events.length);
 cases.push({caseId:b.baseId+'-'+kind,baseId:b.baseId,kind,query:{...clone(b.query),events},description,changedSourceIds,positive,
  originalDuration:total(b.query.events),queryDuration:total(events),humanReview:'automatic-unreviewed'});
}
for(const b of bases)add(b,'original',clone(b.query.events),'원형 대조');
for(const b of bases){
 const es=clone(b.query.events),i=b.deletion.indices[0],deleted=es[i];
 assert.equal(es[i-1].kind,'note');es[i-1].durationRatio+=deleted.durationRatio;es.splice(i,1);
 assert.equal(total(es),total(b.query.events));
 add(b,'absorb-ornament',es,'장식음 후보 1개를 삭제하고 그 음가를 직전 음에 합침. 후속 도착 시각 유지.',[deleted.id,b.query.events[i-1].id]);
}
for(const b of bases){
 const es=clone(b.query.events),i=es.findIndex((e,i)=>i>0&&i<es.length-1&&e.kind==='note'&&e.durationRatio>=1);
 assert.ok(i>=0);const n=es[i],half=n.durationRatio/2;
 es.splice(i,1,{...n,durationRatio:half},{...n,id:n.id+'-repeat',durationRatio:half});
 add(b,'repeat-split',es,'지속음 1개를 같은 음높이의 두 번 공격으로 나눔. 타이 아님.',[n.id,n.id+'-repeat']);
}
for(const b of bases){
 const es=clone(b.query.events),i=es.findIndex((e,i)=>i>0&&i<es.length-2&&e.kind==='note'&&es[i+1].kind==='note'&&e.durationRatio!==es[i+1].durationRatio&&e.durationRatio+es[i+1].durationRatio<=4);
 assert.ok(i>=0);const average=(es[i].durationRatio+es[i+1].durationRatio)/2;es[i].durationRatio=average;es[i+1].durationRatio=average;
 add(b,'rhythm-even',es,'인접한 서로 다른 두 음가를 같은 길이로 균등화. 합계 유지.',[es[i].id,es[i+1].id]);
}
for(const b of bases){
 const es=clone(b.query.events),i=es.findIndex((e,i)=>i>0&&i<es.length-1&&e.kind==='note'&&e.durationRatio>=1);
 assert.ok(i>=0);es[i].durationRatio-=.5;const id=es[i].id+'-rest';
 es.splice(i+1,0,{id,kind:'rest',pitchMidi:null,durationRatio:.5});
 add(b,'articulation-rest',es,'긴 음의 끝 0.5박을 쉼표로 교체. 다음 음의 도착 시각 유지.',[es[i].id,id]);
}
for(const b of bases){
 const es=clone(b.query.events),removed=es.shift();assert.equal(removed.kind,'note');
 add(b,'start-shift',es,'첫 음부터 입력하지 않고 두 번째 음에서 시작. startsOnDownbeat 기본 true 유지의 영향도 관찰.',[removed.id]);
}
for(const b of bases.slice(0,5)){
 const es=clone(b.query.events),notes=es.filter(e=>e.kind==='note'),rotated=notes.map(e=>e.pitchMidi).reverse();
 notes.forEach((e,i)=>{e.pitchMidi=rotated[i];delete e.spelling});
 add(b,'reversed-control',es,'음가·쉼표는 그대로 두고 음높이 순서를 역순으로 바꾼 도전 대조군. 음악적 무관함을 확정하지 않음.',notes.map(e=>e.id),false);
}
mkdirSync(dir,{recursive:false});
const suite={schema:'memory-variation-suite/1',createdAt:new Date().toISOString(),batch,selection:'10 distinct exact original event sequences from prior XML-audited convenience corpus; selected before new search',bases,cases,
  enginePolicy:{singleOmission:true,visibleRanking:false},limitations:['Convenience sample, repeated works and all 4/4.','Controls are reversal challenges, not certified unrelated music.','No new production search changes.']};
writeFileSync(dir+'/suite.json',JSON.stringify(suite,null,2),{flag:'wx'});
writeFileSync(dir+'/selection.json',JSON.stringify({sha256:createHash('sha256').update(JSON.stringify(suite)).digest('hex'),counts:Object.fromEntries([...new Set(cases.map(c=>c.kind))].map(k=>[k,cases.filter(c=>c.kind===k).length]))},null,2));
console.log(JSON.stringify({bases:bases.length,cases:cases.length,kinds:[...new Set(cases.map(c=>c.kind))]}));
