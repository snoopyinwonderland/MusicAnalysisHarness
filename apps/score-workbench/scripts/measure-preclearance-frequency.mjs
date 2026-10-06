import {readFileSync,writeFileSync,statSync,existsSync} from 'node:fs';
import {resolve} from 'node:path';
import {createSearchWorker} from '../server/search-worker-client.mjs';
import {intervalTokens,compareCorpusPriority} from '../server/preclearance-frequency.mjs';
import {structureHash} from '../server/structure-analysis-adapter.mjs';
const [input,output]=process.argv.slice(2);if(!input||!output||existsSync(output))throw new Error('Input and NEW output required');
const report=JSON.parse(readFileSync(input,'utf8'));if(!report.priorityReview)throw new Error('Baseline priority report required');
const dbPath=resolve(process.env.MUSICANOTE_SEARCH_DB||'data/search-index-v2/search.sqlite'),before=statSync(dbPath),expected=report.runtime?.database;
if(!expected||expected.size!==before.size||expected.mtimeMs!==before.mtimeMs||existsSync(dbPath+'-wal'))throw new Error('Index differs or has WAL; use a stable matching index');
const tokens=[...new Set(report.runs.flatMap(r=>intervalTokens(r.selection.task.query.events)))];
const client=createSearchWorker({url:new URL('../server/frequency-worker.mjs',import.meta.url),timeoutMs:180000}),controller=new AbortController(),cancel=()=>controller.abort();
process.once('SIGINT',cancel);process.once('SIGTERM',cancel);const started=performance.now();let measured;
try{measured=await client.search({dbPath,tokens},0,{signal:controller.signal});}finally{await client.close();process.off('SIGINT',cancel);process.off('SIGTERM',cancel)}
const after=statSync(dbPath);if(after.size!==before.size||after.mtimeMs!==before.mtimeMs||existsSync(dbPath+'-wal'))throw new Error('Index changed during measurement');
const result=compareCorpusPriority(report,measured);
result.corpusPriorityReview.provenance={input:resolve(input),createdAt:new Date().toISOString(),elapsedMs:performance.now()-started,
 database:{size:before.size,mtimeMs:before.mtimeMs},tokens:tokens.length,
 codeHashes:Object.fromEntries(['preclearance-frequency.mjs','frequency-worker.mjs','search-worker-client.mjs'].map(f=>[f,structureHash(readFileSync(new URL('../server/'+f,import.meta.url),'utf8'))]))};
writeFileSync(output,JSON.stringify(result,null,2),{flag:'wx'});
console.log(JSON.stringify({sources:measured.totalSources,tokens:tokens.length,elapsedMs:result.corpusPriorityReview.provenance.elapsedMs,ranking:result.corpusPriorityReview.ranking.map(({matches,...r})=>r)}));
