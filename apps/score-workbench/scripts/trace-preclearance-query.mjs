import {readFileSync,writeFileSync,appendFileSync,mkdirSync,existsSync,statSync} from 'node:fs';
import {join} from 'node:path';
import {createSearchWorker} from '../server/search-worker-client.mjs';
import {structureHash} from '../server/structure-analysis-adapter.mjs';
const [suitePath,caseId,output]=process.argv.slice(2);if(!suitePath||!caseId||!output||existsSync(output))throw new Error('suite.json caseId NEW-directory required');
const suite=JSON.parse(readFileSync(suitePath,'utf8')),entry=suite.cases.find(c=>c.caseId===caseId);if(!entry)throw new Error('Case not found');
const db=statSync(process.env.MUSICANOTE_SEARCH_DB||'data/search-index-v2/search.sqlite');if(db.size!==suite.provenance.database.size||db.mtimeMs!==suite.provenance.database.mtimeMs)throw new Error('Index changed');
mkdirSync(output);process.env.MUSICANOTE_PROFILE_SEARCH='1';process.env.MUSICANOTE_RETRIEVAL_CACHE='1';
writeFileSync(join(output,'input.json'),JSON.stringify({entry,suitePath,suiteHash:structureHash(suite),database:{size:db.size,mtimeMs:db.mtimeMs},timeoutMs:60000,
 codeHashes:Object.fromEntries(['search-api.mjs','search-worker.mjs','search-worker-client.mjs'].map(f=>[f,structureHash(readFileSync('server/'+f,'utf8'))]))},null,2),{flag:'wx'});
const log=join(output,'progress.jsonl');writeFileSync(log,'',{flag:'wx'});
const client=createSearchWorker({timeoutMs:60000}),controller=new AbortController(),cancel=()=>controller.abort();process.once('SIGINT',cancel);process.once('SIGTERM',cancel);
const totals={},tail=[];let result,error,loggingError;const started=performance.now();
try{result=await client.search(entry.query,20,{signal:controller.signal,onProgress:e=>{
 try{appendFileSync(log,JSON.stringify(e)+'\n')}catch(err){loggingError=String(err.message)}tail.push(e);if(tail.length>20)tail.shift();if(Number.isFinite(e.durationMs))totals[e.stage]=(totals[e.stage]??0)+e.durationMs;
}});}catch(err){error=String(err.message)}finally{await client.close();process.off('SIGINT',cancel);process.off('SIGTERM',cancel)}
writeFileSync(join(output,'result.json'),JSON.stringify({caseId,status:error?'failed':'completed',error,loggingError,elapsedMs:performance.now()-started,totals,tail,result},null,2),{flag:'wx'});
console.log(JSON.stringify({caseId,error,elapsedMs:performance.now()-started,totals,last:tail.at(-1)}));
