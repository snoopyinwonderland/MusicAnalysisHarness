import {readFileSync,writeFileSync,mkdirSync,existsSync} from 'node:fs';
import {resolve,join} from 'node:path';
import {DatabaseSync} from 'node:sqlite';
import {createSearchWorker} from '../server/search-worker-client.mjs';
import {structureHash} from '../server/structure-analysis-adapter.mjs';
const [suitePath,caseId,dir]=process.argv.slice(2);if(!dir||existsSync(dir))throw new Error('suite caseId NEW-directory required');
const entry=JSON.parse(readFileSync(suitePath,'utf8')).cases.find(c=>c.caseId===caseId);if(!entry)throw new Error('Unknown case');mkdirSync(dir);
process.env.MUSICANOTE_PROFILE_SEARCH='1';process.env.MUSICANOTE_RETRIEVAL_CACHE='1';
const runs=[];
for(const step of [{name:'legacy-cold',cache:'legacy',checkpoint:'0',timeout:120000},{name:'checkpoint-interrupted',cache:'batch',checkpoint:'1',timeout:15000,abortOnCommitted:true},{name:'checkpoint-resume',cache:'batch',checkpoint:'1',timeout:120000}]){
 process.env.MUSICANOTE_METER_CONTEXT_DB=resolve(dir,step.cache+'.sqlite');process.env.MUSICANOTE_METER_CHECKPOINT=step.checkpoint;
 const worker=createSearchWorker({timeoutMs:step.timeout}),started=performance.now(),controller=new AbortController();let result,error,observedBeforeAbort=null;
 const timer=step.abortOnCommitted?setInterval(()=>{if(!existsSync(process.env.MUSICANOTE_METER_CONTEXT_DB))return;let probe;try{probe=new DatabaseSync(process.env.MUSICANOTE_METER_CONTEXT_DB,{readOnly:true});const count=Number(probe.prepare('SELECT COUNT(*) AS n FROM contexts').get().n);if(count>=32){observedBeforeAbort=count;controller.abort()}}catch{}finally{probe?.close()}},100):null;
 try{result=await worker.search(entry.query,20,{signal:controller.signal})}catch(e){error=String(e.message)}finally{clearInterval(timer);await worker.close()}
 let committed=null;if(existsSync(process.env.MUSICANOTE_METER_CONTEXT_DB)){const db=new DatabaseSync(process.env.MUSICANOTE_METER_CONTEXT_DB,{readOnly:true});try{committed=Number(db.prepare('SELECT COUNT(*) AS n FROM contexts').get().n)}finally{db.close()}}
 const strip=r=>{const {profile,...body}=r;return body},run={...step,error,observedBeforeAbort,status:error?'failed':'completed',elapsedMs:performance.now()-started,committed,profile:result?.profile,resultHash:result?structureHash(strip(result)):null};
 writeFileSync(join(dir,step.name+'.json'),JSON.stringify({run,result},null,2),{flag:'wx'});runs.push(run);console.log(JSON.stringify(run));
}
writeFileSync(join(dir,'summary.json'),JSON.stringify({caseId,runs,identical:runs[0].resultHash!==null&&runs[0].resultHash===runs[2].resultHash,checkpointSurvivedInterruption:runs[1].status==='failed'&&runs[1].committed>0,
 warning:'Sequential OS-cache states differ; this proves reuse and equivalence, not a causal latency ratio.'},null,2),{flag:'wx'});
