import {readFileSync,writeFileSync,mkdirSync,existsSync,statSync} from 'node:fs';
import {join} from 'node:path';
import {createSearchWorker} from '../server/search-worker-client.mjs';
import {structureHash} from '../server/structure-analysis-adapter.mjs';
const [suitePath,out,...ids]=process.argv.slice(2);if(!suitePath||!out||!ids.length||existsSync(out))throw Error('suite NEW-output caseIds...');
const suite=JSON.parse(readFileSync(suitePath,'utf8')),db=statSync(process.env.MUSICANOTE_SEARCH_DB||'data/search-index-v2/search.sqlite');
mkdirSync(out,{recursive:true});process.env.MUSICANOTE_PROFILE_SEARCH='1';process.env.MUSICANOTE_RETRIEVAL_CACHE??='1';
// Only persist benchmark switches, never arbitrary environment values/API keys.
const environment=Object.fromEntries(['MUSICANOTE_PROFILE_SEARCH','MUSICANOTE_RETRIEVAL_CACHE','MUSICANOTE_SQL_SEED_AGGREGATION','MUSICANOTE_PHRASE_CACHE'].filter(k=>process.env[k]!==undefined).map(k=>[k,process.env[k]]));
const manifest={suitePath,suiteHash:structureHash(suite),database:{size:db.size,mtimeMs:db.mtimeMs},environment,codeHash:structureHash(readFileSync('server/search-api.mjs','utf8')),timeoutMs:180000};
writeFileSync(join(out,'manifest.json'),JSON.stringify(manifest,null,2),{flag:'wx'});
const worker=createSearchWorker({timeoutMs:180000}),runs=[];
try{for(const id of ids){const c=suite.cases.find(c=>c.caseId===id);if(!c)throw Error('Unknown case '+id);
 for(let attempt=1;attempt<=2;attempt++){const start=performance.now();let value;try{const result=await worker.search(c.query,30);const {profile,...payload}=result;value={caseId:id,attempt,status:'completed',elapsedMs:performance.now()-start,profile,hash:structureHash(payload),result}}catch(e){value={caseId:id,attempt,status:'failed',elapsedMs:performance.now()-start,error:e.message}}
 writeFileSync(join(out,id+'-'+attempt+'.json'),JSON.stringify(value),{flag:'wx'});const {result,...brief}=value;runs.push(brief);console.log(JSON.stringify(brief));
 }}}finally{await worker.close()}
writeFileSync(join(out,'summary.json'),JSON.stringify({manifest,runs},null,2),{flag:'wx'});
