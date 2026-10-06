import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
const batch='octave-combination-20-v1',dir='evaluation/reports/'+batch;
const prior=JSON.parse(readFileSync('evaluation/reports/memory-variation-50-v1/suite.json'));
const bases=prior.bases.map((b,i)=>({...b,priorBaseId:b.baseId,baseId:'OCT'+String(i+1).padStart(2,'0')})),cases=[];
function add(b,kind,events,ids,description,transformation={}){
 assert.ok(events.every(e=>e.durationRatio>0&&(e.kind==='rest'||e.pitchMidi>=0&&e.pitchMidi<=127)));
 assert.equal(new Set(events.map(e=>e.id)).size,events.length);
 cases.push({caseId:b.baseId+'-'+kind,baseId:b.baseId,kind,query:{...structuredClone(b.query),events},positive:true,changedSourceIds:ids,description,transformation,originalDuration:b.query.events.reduce((s,e)=>s+e.durationRatio,0),queryDuration:events.reduce((s,e)=>s+e.durationRatio,0),humanReview:'automatic-unreviewed'});
}
for(const b of bases)add(b,'original',structuredClone(b.query.events),[],'원형 대조');
for(const kind of ['local-octave','octave-plus-omission'])for(const [bi,b]of bases.entries()){
 const es=structuredClone(b.query.events),omitted=b.deletion.indices[0];
 // Select a middle note, away from the predefined ornament and its absorption neighbor.
 const candidates=es.map((e,i)=>({e,i})).filter(({e,i})=>e.kind==='note'&&i>0&&i<es.length-1&&Math.abs(i-omitted)>2);
 candidates.sort((a,z)=>Math.abs(a.i-(es.length-1)/2)-Math.abs(z.i-(es.length-1)/2)||a.i-z.i);
 assert.ok(candidates.length);const i=candidates[0].i,delta=bi%2? -12:12,n=es[i],old=n.pitchMidi;
 n.pitchMidi+=delta;delete n.spelling;const ids=[n.id];
 const transformation={octave:{eventId:n.id,originalIndex:i,from:old,to:n.pitchMidi,semitones:delta}};
 if(kind==='octave-plus-omission'){
  assert.equal(es[omitted].kind,'note');assert.equal(es[omitted-1].kind,'note');
  transformation.omission={eventId:es[omitted].id,originalIndex:omitted,duration:es[omitted].durationRatio,absorbedInto:es[omitted-1].id};
  ids.push(es[omitted].id,es[omitted-1].id);es[omitted-1].durationRatio+=es[omitted].durationRatio;es.splice(omitted,1);
 }
 assert.equal(es.reduce((s,e)=>s+e.durationRatio,0),b.query.events.reduce((s,e)=>s+e.durationRatio,0));
 add(b,kind,es,ids,kind==='local-octave'?'중간 음 하나만 '+(delta>0?'+12':'-12')+'반음 이동. 나머지 음높이·음가·쉼표 유지.':'같은 국소 옥타브 이동 + 떨어진 장식음 후보 하나 삭제, 그 길이를 직전 음에 흡수. 후속 도착 시각 유지.',transformation);
}
assert.equal(cases.length,30);mkdirSync(dir,{recursive:false});
const suite={schema:'memory-variation-suite/1',batch,createdAt:new Date().toISOString(),title:'국소 옥타브·장식음 복합 변형 20개 + 원형 대조 10개',selection:'Same 10 bases as memory-variation-50-v1; predefined mid-note selection before search; not independent holdout',bases,cases,enginePolicy:{singleOmission:true,visibleRanking:false},limitations:['Convenience sample: same prior 10 bases, 7 works, 4/4, 16-note originals.','Ornament labels are heuristic candidates, not confirmed harmonic analyses.','No production changes.']};
const raw=JSON.stringify(suite,null,2);writeFileSync(dir+'/suite.json',raw,{flag:'wx'});
writeFileSync(dir+'/selection.json',JSON.stringify({sha256:createHash('sha256').update(raw).digest('hex'),counts:{original:10,'local-octave':10,'octave-plus-omission':10}},null,2),{flag:'wx'});
console.log(JSON.stringify({batch,bases:bases.length,cases:cases.length}));
