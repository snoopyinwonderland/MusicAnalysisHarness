import {readFileSync,writeFileSync,mkdirSync,existsSync,statSync} from 'node:fs';
import {join} from 'node:path';
import {createSearchWorker} from '../server/search-worker-client.mjs';
import {structureHash} from '../server/structure-analysis-adapter.mjs';
const [suitePath,out,...flags]=process.argv.slice(2),resume=flags.includes('--resume');
if(!suitePath||!out||flags.some(f=>f!=='--resume'))throw Error('suite.json NEW-directory [--resume]');
const suite=JSON.parse(readFileSync(suitePath,'utf8')),sources=[];
for(const c of suite.cases)if(!sources.some(s=>s.sourceId===c.sourceId)){sources.push(c);if(sources.length===5)break}
if(sources.length!==5)throw Error('Five distinct source examples required');
const variants=['source','transpose-2','transpose-octave','one-note-octave','one-semitone','two-pitches','tempo-double','local-duration','insert-rest','delete-inner-note'];
const cases=sources.flatMap(s=>variants.map(variant=>{
 const events=[];let cursor=s.sourceFocus[0].onset;
 for(const n of s.sourceFocus){if(n.onset>cursor+1e-6)events.push({id:'gap-'+n.id,kind:'rest',pitchMidi:null,durationRatio:n.onset-cursor});events.push({id:n.id,kind:'note',pitchMidi:n.pitchMidi,durationRatio:n.durationRatio});cursor=n.onset+n.durationRatio}
 const ns=events.filter(e=>e.kind==='note');
 if(variant.startsWith('transpose')){const delta=variant==='transpose-2'?2:12;const d=Math.max(...ns.map(n=>n.pitchMidi))+delta<=127?delta:-delta;ns.forEach(n=>n.pitchMidi+=d)}
 if(variant==='one-note-octave')ns[3].pitchMidi+=ns[3].pitchMidi<=115?12:-12;
 if(variant==='one-semitone')ns[3].pitchMidi+=ns[3].pitchMidi<127?1:-1;
 if(variant==='two-pitches'){ns[2].pitchMidi=Math.min(127,ns[2].pitchMidi+1);ns[5].pitchMidi=Math.max(0,ns[5].pitchMidi-2)}
 if(variant==='tempo-double')events.forEach(n=>n.durationRatio*=2);
 if(variant==='local-duration')ns[3].durationRatio*=1.5;
 if(variant==='insert-rest')events.splice(events.indexOf(ns[4]),0,{id:'added-rest',kind:'rest',pitchMidi:null,durationRatio:.5});
 if(variant==='delete-inner-note')events.splice(events.indexOf(ns[3]),1);
 const query={version:1,mode:'melody_rhythm',meter:s.query.meter,startsOnDownbeat:false,includeRests:true,events};
 return {caseId:'PC50-'+structureHash([s.snapshotId,s.sourceFocus.map(n=>n.id),variant]).slice(0,12),category:s.category,variant,query,sourceId:s.sourceId,workId:s.workId,streamId:s.streamId,sourceFocus:s.sourceFocus,context:s.context,
  humanReview:{status:'unreviewed',rankingJustification:null},knowledgeBase:{phenomenonTypes:[s.category,variant],ruleLearning:{candidateRules:[],counterexamples:[]}},reconstruction:'logical events with surrounding source context; not original engraving'};
}));
const db=statSync(process.env.MUSICANOTE_SEARCH_DB||'data/search-index-v2/search.sqlite');
const fingerprint=structureHash({cases,db:{size:db.size,mtimeMs:db.mtimeMs},code:['search-api.mjs','preclearance-search.mjs','phrase-boundaries.mjs','preclearance-musical-evidence.mjs'].map(f=>structureHash(readFileSync(new URL('../server/'+f,import.meta.url),'utf8')))});
if(resume){if(JSON.parse(readFileSync(join(out,'suite.json'),'utf8')).fingerprint!==fingerprint)throw Error('Resume fingerprint differs')}
else{if(existsSync(out))throw Error('New output required');mkdirSync(out,{recursive:true});writeFileSync(join(out,'suite.json'),JSON.stringify({schema:'musicanote-variation50/1',fingerprint,selection:'5 distinct source excerpts x 10 paired variants; not representative corpus sample',cases},null,2))}
process.env.MUSICANOTE_PROFILE_SEARCH='1';process.env.MUSICANOTE_RETRIEVAL_CACHE='1';
const worker=createSearchWorker({timeoutMs:60000}),runs=[];
try{for(const c of cases){
 const path=join(out,c.caseId+'.json');if(resume&&existsSync(path)){runs.push(JSON.parse(readFileSync(path,'utf8')));continue}
 const start=performance.now();let r;
 try{const result=await worker.search(c.query,30),results=[...(result.exact??[]),...(result.similar??[])];
  const aligned=x=>(x.alignment??[]).filter(p=>p.queryIndex!==null&&p.candidateIndex!==null&&p.type!=='insertion'&&p.type!=='deletion').map(p=>x.work.notes?.[p.candidateIndex]);
  const rank=results.findIndex(x=>x.work.sourceId===c.sourceId),window=results.findIndex(x=>x.work.sourceId===c.sourceId&&aligned(x).filter(n=>n&&c.sourceFocus.some(o=>Math.abs(n.onset-o.onset)<1e-5&&n.pitchMidi===o.pitchMidi)).length>=Math.ceil(c.sourceFocus.length/2));
  const invalidAlignment=results.flatMap((x,i)=>aligned(x).some(n=>!n||!Number.isFinite(n.onset)||!Number.isFinite(n.pitchMidi))?[i+1]:[]);
  const issues=[];if(rank<0)issues.push('Original source absent within returned results; edition alternatives need review');if(rank>=5)issues.push('Original source below rank 5; higher candidates require musical review');
  r={caseId:c.caseId,status:'completed',elapsedMs:performance.now()-start,sourceRank:rank<0?null:rank+1,sourceWindowProxyRank:window<0?null:window+1,
   invalidAlignmentRanks:invalidAlignment,issues:[...issues,...(invalidAlignment.length?['Invalid aligned candidate references; inspect highlighting']:[])],improvementDirections:rank<0?['Inspect retrieval vs reranking before changing thresholds; compare paired source case']:rank>=5?['Review competing passages; do not force source rank']:[],
   highlightValidation:'API targets retained; actual Verovio SVG visual correctness not verified by this runner',result};
 }catch(e){r={caseId:c.caseId,status:'failed',elapsedMs:performance.now()-start,error:String(e.message),issues:['Search did not complete'],improvementDirections:['Inspect timeout trace and cold cache before scoring changes']}}
 writeFileSync(path,JSON.stringify(r),{flag:'wx'});runs.push(r);console.log(JSON.stringify({caseId:c.caseId,variant:c.variant,status:r.status,rank:r.sourceRank,elapsedMs:r.elapsedMs}));
 writeFileSync(join(out,'summary.json'),JSON.stringify({fingerprint,executed:runs.length,remaining:cases.length-runs.length,runs:runs.map(({result,...rest})=>rest)},null,2));
}}finally{await worker.close()}
const labels=es=>es.map(e=>e.kind==='rest'?`Rest(${e.durationRatio})`:`${['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'][e.pitchMidi%12]}${Math.floor(e.pitchMidi/12)-1}(${e.durationRatio})`).join(' ');
const lines=['# 50개 paired 멜로디 변형 검색','', '음가: 4분음표=1. 순위는 source 회수 진단이지 음악적 정답 판정이 아니다. JSON에 전체 Query/문맥/검색 결과를 보존했다. 실제 SVG 강조와 상위 후보의 음악적 정당성은 사람 검토가 필요하다.','', '| 사례 | 유형 / 변형 | Query | 순위 | 시간 | 문제·개선 |','|---|---|---|---|---|---|'];
for(const c of cases){const r=runs.find(r=>r.caseId===c.caseId);lines.push(`| ${c.caseId} | ${c.category} / ${c.variant} | ${labels(c.query.events)} | ${r.sourceRank??'미회수/실패'} | ${(r.elapsedMs/1000).toFixed(2)}s | ${[...r.issues,...r.improvementDirections].join('; ')} |`)}
writeFileSync(join(out,'report.md'),lines.join('\n'));
