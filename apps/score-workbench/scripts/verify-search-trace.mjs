import {readFileSync,writeFileSync,statSync,existsSync} from 'node:fs';
import {join} from 'node:path';
import assert from 'node:assert/strict';
import {createSearchWorker} from '../server/search-worker-client.mjs';
import {structureHash} from '../server/structure-analysis-adapter.mjs';
const [directory,output]=process.argv.slice(2);if(!directory||!output||existsSync(output))throw new Error('Trace directory and NEW verification output required');
const input=JSON.parse(readFileSync(join(directory,'input.json'),'utf8')),traced=JSON.parse(readFileSync(join(directory,'result.json'),'utf8'));
if(traced.status!=='completed'||traced.loggingError)throw new Error('A completed trace without logging errors is required');
const db=statSync(process.env.MUSICANOTE_SEARCH_DB||'data/search-index-v2/search.sqlite');if(db.size!==input.database.size||db.mtimeMs!==input.database.mtimeMs)throw new Error('Index changed');
for(const [file,hash] of Object.entries(input.codeHashes))if(structureHash(readFileSync('server/'+file,'utf8'))!==hash)throw new Error('Code changed since trace');
process.env.MUSICANOTE_RETRIEVAL_CACHE='1';process.env.MUSICANOTE_PROFILE_SEARCH='1';
const client=createSearchWorker({timeoutMs:60000});
try{const off=await client.search(input.entry.query,20),strip=({profile,...r})=>JSON.parse(JSON.stringify(r));
 assert.equal(structureHash(strip(off)),structureHash(strip(traced.result)),'Serialized API result differs');
 const verification={identical:true,comparison:'full JSON-serialized exact/similar API payload excluding timings only',caseId:input.entry.caseId,
  tracedHash:structureHash(strip(traced.result)),offHash:structureHash(strip(off)),traceProfile:traced.result.profile,offProfile:off.profile,
  warning:'Sequential warm runs: elapsed differences do not establish a causal speedup.'};
 writeFileSync(output,JSON.stringify(verification,null,2),{flag:'wx'});console.log(JSON.stringify(verification));
}finally{await client.close()}
