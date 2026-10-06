import {readFileSync,writeFileSync,mkdirSync,existsSync,statSync} from 'node:fs';
import {join,resolve} from 'node:path';
import {DatabaseSync} from 'node:sqlite';
import {createHash} from 'node:crypto';
import {createSearchWorker} from '../server/search-worker-client.mjs';
import {harderVariation,harderKinds} from './harder-variation.mjs';
const out=resolve(process.argv[2]||''),resume=process.argv.includes('--resume');if(!process.argv[2])throw Error('Output required');
const dbPath=process.env.MUSICANOTE_SEARCH_DB||'data/search-index-v2/search.sqlite';
const hash=x=>createHash('sha256').update(x).digest('hex');
const fingerprint=()=>({database:{size:statSync(dbPath).size,mtimeMs:statSync(dbPath).mtimeMs},code:Object.fromEntries(['server/search-api.mjs','server/phrase-boundaries.mjs','server/seed-windows.mjs','scripts/harder-variation.mjs'].map(p=>[p,hash(readFileSync(p))]))});
let suite;
if(resume)suite=JSON.parse(readFileSync(join(out,'suite.json')));
else{
 if(existsSync(out))throw Error('New directory required');mkdirSync(out,{recursive:true});const db=new DatabaseSync(dbPath,{readOnly:true}),get=db.prepare('SELECT * FROM works WHERE id=?'),bases=[],seen=new Set();
 for(const sourceSuite of ['motif-350','motif-300','motif-200','motif-100']){const path=`evaluation/${sourceSuite}/cases.jsonl`;if(!existsSync(path))continue;
  for(const line of readFileSync(path,'utf8').trim().split('\n')){const old=JSON.parse(line),e=old.expected,title=e.title.toLowerCase().replace(/[^\p{L}\p{N}]/gu,'');if(seen.has(title))continue;const row=get.get(e.workId);if(!row||row.source!==e.sourceId)continue;const all=JSON.parse(row.notes),focus=all.slice(e.baseStartIndex,e.baseStartIndex+10);if(focus.length!==10||focus.some((n,i)=>n.p!==e.baseTargets[i]?.pitchMidi||Math.abs(n.o-e.baseTargets[i]?.onset)>1e-5))continue;
  const events=[];let cursor=focus[0].o;for(const [i,n]of focus.entries()){if(n.o>cursor+1e-6)events.push({id:'gap'+i,kind:'rest',pitchMidi:null,durationRatio:n.o-cursor});events.push({id:'note'+i,kind:'note',pitchMidi:n.p,spelling:n.s,durationRatio:n.d});cursor=n.o+n.d;}
  if(events.some(n=>n.durationRatio<=0||n.kind==='rest'&&n.durationRatio>2))continue;
  try{harderVariation(events,'two-leaps')}catch{continue}
  seen.add(title);bases.push({baseId:'B'+String(bases.length+1).padStart(2,'0'),previousCaseId:old.caseId,expected:e,selection:old.selection,focus,context:all.filter(n=>n.m>=focus[0].m-2&&n.m<=focus.at(-1).m+2),query:{...old.query,events,includeRests:true}});if(bases.length===20)break;
  }if(bases.length===20)break;
 }db.close();if(bases.length!==20)throw Error('Only '+bases.length+' eligible bases');
 const cases=bases.flatMap((b,i)=>harderKinds.map((kind,j)=>{const mutation=harderVariation(b.query.events,kind);return{caseId:'Q-H100-'+String(i*5+j+1).padStart(3,'0'),baseId:b.baseId,kind,changes:mutation.changes,query:{...b.query,events:mutation.events},expected:b.expected,humanReview:{status:'unreviewed',higherRanksJustified:null}}}));
 suite={schema:'harder-melody-100/1',createdAt:new Date().toISOString(),selection:'20 distinct normalized titles from earlier motif suites; two separated leaps and no gap >2 required; paired convenience sample, not population sample',fingerprint:fingerprint(),bases,cases};writeFileSync(join(out,'suite.json'),JSON.stringify(suite,null,2));
}
if(JSON.stringify(suite.fingerprint)!==JSON.stringify(fingerprint()))throw Error('Fingerprint changed');
process.env.MUSICANOTE_PROFILE_SEARCH='1';process.env.MUSICANOTE_RETRIEVAL_CACHE='1';delete process.env.MUSICANOTE_CONTOUR_SIDECAR;
const tasks=suite.bases.flatMap(b=>[{caseId:'CTRL-'+b.baseId,baseId:b.baseId,kind:'control',query:b.query,expected:b.expected},...suite.cases.filter(c=>c.baseId===b.baseId)]),runs=[],worker=createSearchWorker({timeoutMs:60000});
try{for(const c of tasks){const file=join(out,c.caseId+'.json');if(existsSync(file)){runs.push(JSON.parse(readFileSync(file)));continue}if(JSON.stringify(suite.fingerprint)!==JSON.stringify(fingerprint()))throw Error('Engine or DB changed during run');let r,lastStage;const start=performance.now();try{
 const result=await worker.search(c.query,100,{onProgress:e=>{lastStage={stage:e.stage,elapsedMs:e.elapsedMs}}}),all=[...result.exact,...result.similar],base=suite.bases.find(b=>b.baseId===c.baseId);
 const rank=all.findIndex(x=>x.work.sourceId===c.expected.sourceId),window=all.findIndex(x=>x.work.sourceId===c.expected.sourceId&&x.work.streamId===c.expected.streamId&&x.alignment.filter(p=>p.queryIndex!==null&&p.candidateIndex!==null).map(p=>x.work.notes[p.candidateIndex]).filter(n=>n&&base.focus.some(o=>o.p===n.pitchMidi&&Math.abs(o.o-n.onset)<1e-5)).length>=5);
 const invalid=all.flatMap((x,i)=>x.alignment.some(p=>p.queryIndex!==null&&p.candidateIndex!==null&&!x.work.notes[p.candidateIndex])?[i+1]:[]);
 r={caseId:c.caseId,baseId:c.baseId,kind:c.kind,status:'completed',elapsedMs:performance.now()-start,sourceRank:rank<0?null:rank+1,sourceWindowProxyRank:window<0?null:window+1,invalidAlignmentRanks:invalid,issues:rank<0?['Source absent in top 100; inspect retrieval/admission and alternative editions']:rank>=5?['Source below top 5; higher candidates need musical review']:[],highlightValidation:'API indices only; SVG and listening not verified',result};
 }catch(e){r={caseId:c.caseId,baseId:c.baseId,kind:c.kind,status:'failed',error:e.message,elapsedMs:performance.now()-start,lastStage};}
 writeFileSync(file,JSON.stringify(r),{flag:'wx'});runs.push(r);const brief=runs.map(({result,...x})=>x);writeFileSync(join(out,'summary.json'),JSON.stringify({executed:runs.length,total:tasks.length,remaining:tasks.length-runs.length,variantCount:100,controlCount:20,runs:brief},null,2));console.log(JSON.stringify(brief.at(-1)));
}}finally{await worker.close()}
