import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
import {DatabaseSync} from 'node:sqlite';
import {metricSupport} from '../server/structural-reduction.mjs';
const out=process.argv[2];if(!out)throw Error('Output required');
const exclusionPath=process.argv[3],excluded=exclusionPath?JSON.parse(readFileSync(exclusionPath)).bases:[];
const occupied=excluded.map(b=>({workId:b.expected.workId,start:b.focus[0].o,end:b.focus.at(-1).o+b.focus.at(-1).d}));
const old=JSON.parse(readFileSync('evaluation/runs/harder-100-2026-09-15/suite.json'));
const db=new DatabaseSync('data/search-index-v2/search.sqlite',{readOnly:true}),get=db.prepare('SELECT notes FROM works WHERE id=?');
const bases=[],cases=[],rejections=[],counts={separated:0,adjacent:0},num=q=>q.n/q.d;
const contiguous=(a,b)=>Math.abs(num(a.onsetQ)+num(a.durationQ)-num(b.onsetQ))<1e-6;
const clean=e=>e?.kind==='note'&&!e.grace&&!e.cue&&!e.tieStart&&!e.tieStop&&!e.tieChainId&&e.isAttack!==false&&num(e.durationQ)>0;
const step=(a,b)=>Math.abs(a.diatonicPitch-b.diatonicPitch)===1&&Math.abs(a.pitchMidi-b.pitchMidi)<=2;
const weak=e=>clean(e)&&metricSupport(e)!==null&&metricSupport(e)<.5&&num(e.durationQ)<=.5;
function single(ns,i){
 const [l,m,r]=ns.slice(i-1,i+2);if(![l,m,r].every(clean)||!weak(m)||!contiguous(l,m)||!contiguous(m,r)||!step(l,m)||!step(m,r))return null;
 const passing=Math.sign(m.pitchMidi-l.pitchMidi)===Math.sign(r.pitchMidi-m.pitchMidi),neighbor=l.pitchMidi===r.pitchMidi;
 if(!(passing||neighbor)||num(m.durationQ)>Math.min(num(l.durationQ),num(r.durationQ)))return null;
 if(![l,r].some(e=>metricSupport(e)>=.55||num(e.durationQ)>=2*num(m.durationQ)))return null;
 return {type:passing?'passing':'neighbor',index:i,metric:metricSupport(m),duration:num(m.durationQ),endpoints:[l.id,r.id]};
}
for(const prior of old.bases){
 if(Object.values(counts).every(x=>x===10))break;
 const audit=JSON.parse(readFileSync(`evaluation/runs/structural-source-audit-v2/${prior.baseId}.json`));
 const parsed=spawnSync('K:/Music Analysis/.venv/Scripts/python.exe',['scripts/structural-xml-source.py',audit.input.sourcePath],{encoding:'utf8',maxBuffer:96*1024*1024});
 if(parsed.status!==0){rejections.push({baseId:prior.baseId,error:parsed.stderr});continue;}
 const source=JSON.parse(parsed.stdout),[part,staff,voice]=prior.expected.streamId.split(':'),lane=source.events.filter(e=>e.partId===part&&e.staffId===staff&&e.voiceId===voice),raw=JSON.parse(get.get(prior.expected.workId).notes);
 const linked=lane.map(e=>e.kind==='note'?raw.map((n,i)=>({n,i})).filter(({n})=>n.m===e.measureOrdinal&&n.p===e.pitchMidi&&Math.abs(n.b-1-num(e.beatQ))<1e-6):[]);
 const seen=new Set();
 for(let start=0;start<lane.length-16;start++){
  if(!clean(lane[start])||num(lane[start].beatQ)!==0)continue;
  const window=[];let end=start;
  for(;end<lane.length&&window.filter(e=>e.kind==='note').length<16;end++)window.push(lane[end]);
  if(window.filter(e=>e.kind==='note').length!==16||window.some(e=>e.kind==='note'&&!clean(e))||new Set(window.map(e=>e.meter)).size!==1||!['2/4','3/4','4/4','6/8','9/8','12/8'].includes(window[0].meter))continue;
  if(window.slice(1).some((e,i)=>!contiguous(window[i],e)))continue;
  // Keep a motif-sized contiguous context, not isolated attacks over long rests.
  if(window.some(e=>e.kind==='rest'&&num(e.durationQ)>1)||window.reduce((sum,e)=>sum+num(e.durationQ),0)>24)continue;
  const notes=window.filter(e=>e.kind==='note');if(new Set(notes.map(e=>e.pitchMidi)).size<4)continue;
  const indices=window.flatMap((e,i)=>e.kind==='note'?[start+i]:[]),links=indices.map(i=>linked[i]);
  if(links.some(x=>x.length!==1)||links.some((x,i)=>i&&x[0].i!==links[i-1][0].i+1))continue;
  // Compare index coordinates with index coordinates: XML onset origins may differ.
  if(exclusionPath&&occupied.some(w=>w.workId===prior.expected.workId&&links[0][0].n.o<w.end&&links.at(-1)[0].n.o+links.at(-1)[0].n.d>w.start))continue;
  const ns=window,eligible=ns.map((_,i)=>i>0&&i<ns.length-1?single(ns,i):null).filter(Boolean),pairs=[];
  for(const a of eligible)for(const b of eligible)if(b.index-a.index>=3&&b.index<ns.length-2&&a.index>=2)pairs.push({type:'separated',indices:[a.index,b.index],evidence:[a,b]});
  for(let i=2;i<ns.length-3;i++){
   const four=ns.slice(i-1,i+3),[l,a,b,r]=four;
   if(!four.every(clean)||!weak(a)||!weak(b)||!four.slice(1).every((e,j)=>contiguous(four[j],e)&&step(four[j],e)))continue;
   if(new Set(four.slice(1).map((e,j)=>Math.sign(e.pitchMidi-four[j].pitchMidi))).size!==1)continue;
   const d=Math.max(num(a.durationQ),num(b.durationQ));if(d>Math.min(num(l.durationQ),num(r.durationQ))||![l,r].some(e=>metricSupport(e)>=.55||num(e.durationQ)>=2*d))continue;
   pairs.push({type:'adjacent',indices:[i,i+1],evidence:[{type:'two-passing-notes',metric:[metricSupport(a),metricSupport(b)],endpoints:[l.id,r.id]}]});
  }
  for(const pair of pairs){
   if((!exclusionPath&&seen.has(pair.type))||counts[pair.type]>=10)continue;
   const id='ORN'+String(bases.length+1).padStart(2,'0'),events=ns.map((e,i)=>({id:`${id}-e${i}`,kind:e.kind,pitchMidi:e.pitchMidi??null,durationRatio:num(e.durationQ),...(e.writtenPitch?{spelling:e.writtenPitch.step+(Number(e.writtenPitch.alter)>0?'#'.repeat(Number(e.writtenPitch.alter)):'b'.repeat(-Number(e.writtenPitch.alter)))+e.writtenPitch.octave}:{})}));
   const query={version:1,mode:'melody_rhythm',meter:ns[0].meter,startsOnDownbeat:true,includeRests:true,absoluteExactOnly:false,events};
   const focus=links.map(x=>x[0].n),expected={...prior.expected,baseStartIndex:links[0][0].i,baseStartMeasure:focus[0].m,baseEndMeasure:focus.at(-1).m,baseTargets:focus.map(n=>({onset:n.o,pitchMidi:n.p,measure:n.m,beat:n.b}))};
   const base={baseId:id,expected,query,focus,sourceHash:source.sourceHash,sourcePath:source.sourcePath,xmlEvents:ns,context:lane.slice(Math.max(0,start-8),Math.min(lane.length,end+8)),indexLinks:indices.map((i,j)=>({eventId:lane[i].id,index:links[j][0].i,note:links[j][0].n})),deletion:pair,qualification:'Provisional local stepwise/weak/short evidence; harmony and perceptual importance not adjudicated.'};
   bases.push(base);
   if(exclusionPath)occupied.push({workId:expected.workId,start:focus[0].o,end:focus.at(-1).o+focus.at(-1).d});
   for(const count of [0,1,2]){const removed=pair.indices.slice(0,count),changedSourceIds=removed.map(i=>events[i].id);cases.push({caseId:`${id}-delete${count}`,baseId:id,kind:`${pair.type}-delete${count}`,query:{...query,events:events.filter((_,i)=>!removed.includes(i))},changes:removed.map(i=>({type:'delete-note-and-duration',event:events[i],xmlEvent:ns[i]})),changedSourceIds});}
   counts[pair.type]++;seen.add(pair.type);break;
  }
  if(!exclusionPath&&seen.size===2)break;
 }
}
db.close();mkdirSync(out,{recursive:false});
writeFileSync(out+'/suite.json',JSON.stringify({schema:'double-ornament-trial/1',createdAt:new Date().toISOString(),selection:'Deterministic source-only; no search outcome used.',timing:'Delete note AND its duration, preserve all existing rests; later onsets shift.',decisionGate:'Defer dedicated two-deletion support if paired original-success recall loses >=20 percentage points or falls below70%; pilot only.',counts,bases,cases,rejections,limitations:['Convenience corpus from20 previously XML-audited works.','Two forms may share a work; not independent population samples.','Local ornament candidates, not certified Schenkerian reductions.','No production algorithm changes.']},null,2),{flag:'wx'});console.log(JSON.stringify({counts,bases:bases.length,queries:cases.length,rejections}));
