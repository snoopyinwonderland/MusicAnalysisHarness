import {readFileSync,writeFileSync,mkdirSync,existsSync,statSync} from 'node:fs';
import {join} from 'node:path';
import {createHash} from 'node:crypto';
import {createSearchWorker} from '../server/search-worker-client.mjs';
const dir=process.argv[2];if(!dir)throw Error('Output directory required');
const suitePath='evaluation/reports/structural-100-preview-v1/suite.json',suite=JSON.parse(readFileSync(suitePath));
const hash=p=>createHash('sha256').update(readFileSync(p)).digest('hex');
const db=process.env.MUSICANOTE_SEARCH_DB||'data/search-index-v2/search.sqlite';
const fingerprint=()=>({suite:hash(suitePath),engine:hash('server/search-api.mjs'),dbSize:statSync(db).size,dbMtime:statSync(db).mtimeMs});
const initial=fingerprint();mkdirSync(dir,{recursive:true});const meta=join(dir,'manifest.json');
if(existsSync(meta)){if(JSON.stringify(JSON.parse(readFileSync(meta)).fingerprint)!==JSON.stringify(initial))throw Error('Fingerprint changed')}
else writeFileSync(meta,JSON.stringify({schema:'structural-baseline/1',fingerprint:initial,limit:100,timeoutMs:60000,createdAt:new Date().toISOString(),variantCount:100,controlCount:20,review:'User accepted preview for staged testing, not expert anchor ground truth'},null,2),{flag:'wx'});
process.env.MUSICANOTE_RETRIEVAL_CACHE='1';delete process.env.MUSICANOTE_CONTOUR_SIDECAR;
const tasks=suite.bases.flatMap(b=>[{caseId:'CONTROL-'+b.baseId,baseId:b.baseId,kind:'original-control',query:b.query},...suite.cases.filter(c=>c.baseId===b.baseId)]);
const worker=createSearchWorker({timeoutMs:60000}),runs=[];
function summarize(){const done=runs.filter(r=>r.status==='completed'),variants=done.filter(r=>r.kind!=='original-control');const summary={updatedAt:new Date().toISOString(),attempted:runs.length,total:tasks.length,remaining:tasks.length-runs.length,completed:done.length,failed:runs.length-done.length,variantsCompleted:variants.length,sourceFound:variants.filter(r=>r.sourceRank).length,byType:Object.fromEntries([...new Set(variants.map(r=>r.kind))].map(k=>{const xs=variants.filter(r=>r.kind===k);return[k,{completed:xs.length,sourceFound:xs.filter(r=>r.sourceRank).length,top5:xs.filter(r=>r.sourceRank&&r.sourceRank<=5).length}]})),runs:runs.map(({result,...r})=>r)};writeFileSync(join(dir,'summary.json'),JSON.stringify(summary,null,2));return summary}
try{for(const c of tasks){const file=join(dir,c.caseId+'.json');if(existsSync(file)){runs.push(JSON.parse(readFileSync(file)));continue}
 if(JSON.stringify(fingerprint())!==JSON.stringify(initial))throw Error('Source or engine changed');
 const base=suite.bases.find(b=>b.baseId===c.baseId),start=performance.now();let record,lastStage;
 try{const result=await worker.search(c.query,100,{onProgress:p=>{lastStage=p.stage}}),matches=[...result.exact,...result.similar];
 const rank=matches.findIndex(m=>m.work.sourceId===base.expected.sourceId),window=matches.findIndex(m=>m.work.sourceId===base.expected.sourceId&&m.work.streamId===base.expected.streamId&&new Set(m.alignment.filter(p=>p.candidateIndex!==null).map(p=>m.work.notes[p.candidateIndex]).filter(Boolean).flatMap(n=>base.focus.map((f,i)=>Math.abs(f.o-n.onset)<1e-5&&f.p===n.pitchMidi?i:null).filter(i=>i!==null))).size>=5);
 record={caseId:c.caseId,baseId:c.baseId,kind:c.kind,status:'completed',elapsedMs:performance.now()-start,sourceRank:rank<0?null:rank+1,sourceWindowProxyRank:window<0?null:window+1,query:c.query,result,humanRankingReview:'not-reviewed',highlightReview:'not-rendered',issues:rank<0?['Source absent in top100; retrieval/admission tracing required']:rank>=5?['Higher competitors require review']:[]};
 }catch(e){record={caseId:c.caseId,baseId:c.baseId,kind:c.kind,status:'failed',elapsedMs:performance.now()-start,error:e.message,lastStage,query:c.query}}
 writeFileSync(file,JSON.stringify(record),{flag:'wx'});runs.push(record);summarize();console.log(JSON.stringify({caseId:record.caseId,status:record.status,sourceRank:record.sourceRank,elapsedMs:record.elapsedMs}));
}}finally{await worker.close();summarize()}
console.log('FINISHED');
