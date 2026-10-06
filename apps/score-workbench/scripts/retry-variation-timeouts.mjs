import {readFileSync,writeFileSync,mkdirSync,existsSync} from 'node:fs';
import {join} from 'node:path';
import {createSearchWorker} from '../server/search-worker-client.mjs';
const [directory,out]=process.argv.slice(2);if(!directory||!out||existsSync(out))throw Error('Completed suite directory and NEW retry directory required');
const suite=JSON.parse(readFileSync(join(directory,'suite.json'),'utf8')),summary=JSON.parse(readFileSync(join(directory,'summary.json'),'utf8'));
if(summary.remaining!==0)throw Error('Finish primary attempts first');
mkdirSync(out,{recursive:true});process.env.MUSICANOTE_PROFILE_SEARCH='1';process.env.MUSICANOTE_RETRIEVAL_CACHE='1';const worker=createSearchWorker({timeoutMs:180000}),runs=[];
try{for(const r of summary.runs.filter(r=>r.status==='failed'&&String(r.error).includes('timed out'))){const c=suite.cases.find(c=>c.caseId===r.caseId),start=performance.now();let retry;
 try{const result=await worker.search(c.query,30),all=[...(result.exact??[]),...(result.similar??[])],rank=all.findIndex(x=>x.work.sourceId===c.sourceId);retry={caseId:c.caseId,status:'completed',elapsedMs:performance.now()-start,sourceRank:rank<0?null:rank+1,result}}
 catch(e){retry={caseId:c.caseId,status:'failed',elapsedMs:performance.now()-start,error:e.message}}
 writeFileSync(join(out,c.caseId+'.json'),JSON.stringify(retry),{flag:'wx'});const {result,...brief}=retry;runs.push(brief);console.log(JSON.stringify(brief));
}}finally{await worker.close()}
writeFileSync(join(out,'summary.json'),JSON.stringify({primaryDirectory:directory,timeoutMs:180000,originalAttemptsPreserved:true,warning:'Warm caches may differ; retries are not independent performance samples.',runs},null,2),{flag:'wx'});
