import {readFileSync,writeFileSync,mkdirSync,existsSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {DatabaseSync} from 'node:sqlite';
import assert from 'node:assert/strict';
import {metricSupport} from '../server/structural-reduction.mjs';
const batch='eighth-meter-60-v1',dir='evaluation/reports/'+batch;
assert.ok(!existsSync(dir),'Existing batch must not be overwritten');
const old=JSON.parse(readFileSync('evaluation/runs/harder-100-2026-09-15/suite.json'));
const prior=JSON.parse(readFileSync('evaluation/reports/short-query-90-v1/suite.json'));
const triple=JSON.parse(readFileSync('evaluation/reports/triple-meter-60-v1/suite.json'));
const excluded=new Set([...old.bases,...prior.bases,...triple.bases].map(b=>b.expected.title.toLowerCase()));
const db=new DatabaseSync('data/search-index-v2/search.sqlite',{readOnly:true});
const rows=db.prepare("SELECT id,title,source,stream_id,composer,role FROM works WHERE source NOT LIKE 'kysing/%' AND source NOT LIKE '%.mxl' ORDER BY source,role DESC LIMIT 100000").all();
const get=db.prepare('SELECT notes FROM works WHERE id=?'),seen=new Set(),pool=[],rejections=[];
const num=q=>q.n/q.d,clean=e=>e?.kind==='note'&&!e.grace&&!e.cue&&!e.tieStart&&!e.tieStop&&!e.tieChainId&&e.isAttack!==false&&num(e.durationQ)>0;
const contiguous=(a,b)=>Math.abs(num(a.onsetQ)+num(a.durationQ)-num(b.onsetQ))<1e-6;
const step=(a,b)=>Math.abs(a.diatonicPitch-b.diatonicPitch)===1&&Math.abs(a.pitchMidi-b.pitchMidi)<=2;
function ornament(es,i){const [l,m,r]=es.slice(i-1,i+2);if(![l,m,r].every(clean)||!contiguous(l,m)||!contiguous(m,r)||!step(l,m)||!step(m,r))return null;const w=metricSupport(m),d=num(m.durationQ);if(w===null||w>=.5||d>.5||d>Math.min(num(l.durationQ),num(r.durationQ)))return null;const passing=Math.sign(m.pitchMidi-l.pitchMidi)===Math.sign(r.pitchMidi-m.pitchMidi),neighbor=l.pitchMidi===r.pitchMidi;if(!(passing||neighbor)||![l,r].some(e=>metricSupport(e)>=.55||num(e.durationQ)>=2*d))return null;return {index:i,type:passing?'passing':'neighbor',metric:w,duration:d,endpoints:[l.id,r.id]};}
let inspected=0;
for(const row of rows){
 if(seen.has(row.source)||excluded.has(row.title.toLowerCase()))continue;seen.add(row.source);
 if(inspected++>=20000)break;
 const sourcePath='K:/Music Analysis/musicxml/'+row.source;if(!existsSync(sourcePath))continue;
 const xmlText=readFileSync(sourcePath,'utf8');if(!/<beats>\s*(6|3)\s*<\/beats>\s*<beat-type>\s*8\s*<\/beat-type>/.test(xmlText))continue;
 const parsed=spawnSync('K:/Music Analysis/.venv/Scripts/python.exe',['scripts/structural-xml-source.py',sourcePath],{encoding:'utf8',maxBuffer:96*1024*1024});
 if(parsed.status!==0){rejections.push({source:row.source,reason:'parse-failed',error:parsed.stderr.slice(0,400)});continue;}
 const source=JSON.parse(parsed.stdout),[part,staff,voice]=row.stream_id.split(':'),lane=source.events.filter(e=>e.partId===part&&e.staffId===staff&&e.voiceId===voice),raw=JSON.parse(get.get(row.id).notes);
 const byCoordinate=new Map();for(const [i,n]of raw.entries()){const k=n.m+':'+n.p;const a=byCoordinate.get(k)??[];a.push({i,n});byCoordinate.set(k,a);}
 let candidate=null;
 for(let start=0;start<lane.length-12;start++){
  if(!clean(lane[start])||num(lane[start].beatQ)!==0)continue;
  const es=[];let end=start,count=0;while(end<lane.length&&count<12){const e=lane[end++];es.push(e);if(e.kind==='note')count++;}
  if(count!==12||es.some(e=>e.kind==='note'&&!clean(e))||new Set(es.map(e=>e.meter)).size!==1||!['6/8','3/8'].includes(es[0].meter)||es.slice(1).some((e,i)=>!contiguous(es[i],e)))continue;
  if(es.some(e=>e.kind==='rest'&&num(e.durationQ)>1)||es.reduce((s,e)=>s+num(e.durationQ),0)>16)continue;
  const notes=es.filter(e=>e.kind==='note');if(new Set(notes.slice(0,6).map(e=>e.pitchMidi)).size<3)continue;
  const sixth=es.indexOf(notes[5]),eligible=es.map((_,i)=>i>0&&i<sixth?ornament(es,i):null).filter(Boolean);if(!eligible.length)continue;
  const links=notes.map(e=>(byCoordinate.get(e.measureOrdinal+':'+e.pitchMidi)??[]).filter(({n})=>Math.abs(n.b-1-num(e.beatQ))<1e-6));
  if(links.some(a=>a.length!==1)||links.some((a,i)=>i&&a[0].i!==links[i-1][0].i+1))continue;
  candidate={row,sourcePath,sourceHash:source.sourceHash,es,links:links.map(a=>a[0]),context:lane.slice(Math.max(0,start-8),end+8),ornament:eligible[0]};break;
 }
 if(candidate&&!pool.some(b=>b.row.title.toLowerCase()===row.title.toLowerCase())){pool.push(candidate);console.log(JSON.stringify({candidate:row.title,meter:candidate.es[0].meter,pool:pool.length}));}
 const meters=m=>pool.filter(b=>b.es[0].meter===m).length;if(meters('6/8')>=5&&meters('3/8')>=5)break;
}
db.close();
const chosen=[];for(const [meter,n]of [['6/8',5],['3/8',5]])chosen.push(...pool.filter(b=>b.es[0].meter===meter).slice(0,n));

assert.equal(chosen.length,10,'Insufficient source-qualified examples; do not relax musical filters');
const bases=[],cases=[];
for(const [bi,s]of chosen.entries())for(const length of [12,8]){
 const parent='EM'+String(bi+1).padStart(2,'0'),baseId=parent+'-L'+length;let count=0;const es=[];for(const e of s.es){es.push(e);if(e.kind==='note'&&++count===length)break;}
 const events=es.map((e,i)=>({id:parent+'-e'+i,kind:e.kind,pitchMidi:e.pitchMidi??null,durationRatio:num(e.durationQ)})),focus=s.links.slice(0,length).map(l=>l.n);
 const expected={workId:s.row.id,sourceId:s.row.source,streamId:s.row.stream_id,title:s.row.title,composer:s.row.composer,baseStartIndex:s.links[0].i,baseStartMeasure:focus[0].m,baseEndMeasure:focus.at(-1).m,baseTargets:focus.map(n=>({onset:n.o,pitchMidi:n.p,measure:n.m,beat:n.b}))};
 const query={version:1,mode:'melody_rhythm',meter:es[0].meter,startsOnDownbeat:true,includeRests:true,absoluteExactOnly:false,events};
 bases.push({baseId,parentBaseId:parent,length,query,expected,focus,sourceHash:s.sourceHash,sourcePath:s.sourcePath,xmlEvents:es,context:s.context,indexLinks:es.filter(e=>e.kind==='note').map((e,i)=>({eventId:e.id,index:s.links[i].i,note:s.links[i].n})),deletion:{indices:[s.ornament.index],evidence:[s.ornament]}});
 for(const kind of ['original','ornament-delete','ornament-delete-preserve-time']){
  const ev=structuredClone(events),ids=[],transformation={};let description=length+'음 원형 대조';
  if(kind==='ornament-delete'){const i=s.ornament.index,e=ev[i];ids.push(e.id);transformation.omission={eventId:e.id,index:i,evidence:s.ornament,timing:'delete-note-and-duration'};ev.splice(i,1);description=length+'음에서 약박·짧은 순차진행 장식음 후보 1개와 그 음가 삭제 → '+(length-1)+'음. 이후 시작 시각 당겨짐.';}
  if(kind==='ornament-delete-preserve-time'){const i=s.ornament.index,e=ev[i],prev=ev[i-1];ids.push(e.id,prev.id);transformation.omission={eventId:e.id,index:i,evidence:s.ornament,timing:'absorb-duration-into-previous',absorbedBy:prev.id,previousDuration:prev.durationRatio,deletedDuration:e.durationRatio};prev.durationRatio+=e.durationRatio;ev.splice(i,1);description=length+'음에서 장식음 후보 삭제, 앞 음으로 음가 흡수: 뒤 음 시작 시각 유지';}
  cases.push({caseId:baseId+'-'+kind,baseId,kind,length,query:{...query,events:ev},positive:true,description,changedSourceIds:ids,transformation,originalDuration:events.reduce((a,e)=>a+e.durationRatio,0),queryDuration:ev.reduce((a,e)=>a+e.durationRatio,0),humanReview:'automatic-unreviewed'});
 }
}
cases.sort((a,b)=>b.length-a.length||['original','ornament-delete','ornament-delete-preserve-time'].indexOf(a.kind)-['original','ornament-delete','ornament-delete-preserve-time'].indexOf(b.kind)||a.baseId.localeCompare(b.baseId));
const suite={schema:'memory-variation-suite/1',batch,title:'6/8·3/8 원형·장식음 삭제 시간 조건 비교 60개',createdAt:new Date().toISOString(),selection:'Source-only deterministic scan; excludes titles from harder-100 pool; no retrieval outcomes used',inspectedSources:inspected,candidateCount:pool.length,meterDistribution:Object.fromEntries(['6/8','3/8'].map(m=>[m,chosen.filter(s=>s.es[0].meter===m).length])),bases,cases,rejections,limitations:['Convenience source sample, not population accuracy.','Nested lengths are paired, not 60 independent melodies.','Ornament evidence is local heuristic, not confirmed harmonic analysis.','No negative relevance labels or production changes.']};
assert.equal(cases.length,60);mkdirSync(dir,{recursive:false});const raw=JSON.stringify(suite,null,2);writeFileSync(dir+'/suite.json',raw,{flag:'wx'});writeFileSync(dir+'/selection.json',JSON.stringify({sha256:createHash('sha256').update(raw).digest('hex'),meterDistribution:suite.meterDistribution,cases:60},null,2));console.log(JSON.stringify({selected:chosen.map(s=>[s.row.title,s.es[0].meter]),cases:60}));


