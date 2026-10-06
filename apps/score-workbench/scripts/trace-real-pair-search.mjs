import {readFileSync,writeFileSync,mkdirSync,existsSync,statSync} from 'node:fs';
import {join} from 'node:path';
import {DatabaseSync} from 'node:sqlite';
import {createSearchWorker} from '../server/search-worker-client.mjs';
import {structureHash} from '../server/structure-analysis-adapter.mjs';
const [baseline,inputFile,out]=process.argv.slice(2);if(!out||existsSync(out))throw Error('Baseline case, prepared input and NEW output required');
mkdirSync(out,{recursive:true});const save=(f,x)=>writeFileSync(join(out,f),JSON.stringify(x,null,2),{flag:'wx'});
const input=JSON.parse(readFileSync(inputFile)),report=JSON.parse(readFileSync(join(baseline,'search.json')));
const sourceStat=statSync('data/search-index-v2/search.sqlite');
save('provenance.json',{createdAt:new Date().toISOString(),source:{size:sourceStat.size,mtimeMs:sourceStat.mtimeMs},baseline,inputFile,
 codeHashes:Object.fromEntries(['server/search-api.mjs','server/contour-seeds.mjs','scripts/trace-real-pair-search.mjs'].map(f=>[f,structureHash(readFileSync(f,'utf8'))])),
 contourSidecar:process.env.MUSICANOTE_CONTOUR_SIDECAR??null,expectedIdsUsedOnlyInObserver:true});
const db=new DatabaseSync('data/search-index-v2/search.sqlite',{readOnly:true});db.exec('PRAGMA query_only=ON');
const sources=input.case.existingReferenceSources;
const rows=db.prepare(`SELECT id,source,stream_id,title,role,notes FROM works WHERE source IN (${sources.map(()=>'?').join(',')})`).all(...sources);
db.close();save('reference-streams.json',rows.map(r=>({...r,notes:JSON.parse(r.notes)})));
const watched=new Set(rows.map(r=>r.id)),worker=createSearchWorker({timeoutMs:180000}),summary=[];
process.env.MUSICANOTE_RETRIEVAL_CACHE='1';
try{for(const run of report.runs){
 console.log(JSON.stringify({stage:'query',index:summary.length+1,total:report.runs.length,taskId:run.taskId}));
 const diagnostics=[],stages={},started=Date.now();let result,error;
 try{result=await worker.search(run.query,30,{onProgress:e=>{
  stages[e.stage]=(stages[e.stage]||0)+1;
  if(e.stage==='contour-supplement-error')diagnostics.push(e);
  else if(e.stage==='contour-supplement')diagnostics.push({...e,candidates:e.candidates.filter(r=>watched.has(r.id))});
  else if(e.stage==='retrieval-inventory')diagnostics.push({stage:e.stage,hitWorks:e.hitWorks.filter(id=>watched.has(id)),candidateWorks:e.candidateWorks.filter(id=>watched.has(id))});
  else if(e.stage==='ranked-inventory')diagnostics.push({...e,rows:e.rows.filter(r=>watched.has(r.workId))});
  else if(e.key&&watched.has(e.key.split('\u0000')[0]))diagnostics.push(e);
 }});}catch(e){error=String(e.message)}
 // Baseline removed known self sources after retrieval. Reproduce only that evaluator filter.
 if(result)for(const kind of ['exact','similar'])result[kind]=result[kind].filter(r=>!input.case.excludeExistingSources.includes(r.work.sourceId));
 const same=result?structureHash({exact:result.exact,similar:result.similar})===structureHash({exact:run.result?.exact,similar:run.result?.similar}):null;
 const record={taskId:run.taskId,query:run.query,elapsedMs:Date.now()-started,error,diagnostics,stages,result,baselineResultsIdentical:same,referenceUsedForSearch:false};save(run.taskId+'.json',record);
 summary.push({taskId:run.taskId,elapsedMs:record.elapsedMs,error,baselineResultsIdentical:same,diagnostics});console.log(JSON.stringify({stage:'done',taskId:run.taskId,same,error,referenceDiagnostics:diagnostics.length}));
}}finally{await worker.close()}
save('summary.json',summary);
