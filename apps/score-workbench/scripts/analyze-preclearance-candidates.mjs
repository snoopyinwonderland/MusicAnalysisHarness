import {readFileSync,writeFileSync,statSync,mkdirSync,existsSync} from 'node:fs';
import {resolve} from 'node:path';
import {createSearchWorker} from '../server/search-worker-client.mjs';
import {enrichPreclearanceImportance} from '../server/preclearance-importance.mjs';
import {structureHash} from '../server/structure-analysis-adapter.mjs';
const [prepared,input,output,...flags]=process.argv.slice(2);
if(flags.some(f=>!/^--(?:timeout-ms|max-notes)=\d+$/.test(f)))throw new Error('Unknown option');
const option=(key,fallback)=>Number(flags.find(f=>f.startsWith(`--${key}=`))?.split('=')[1]??fallback);
const timeoutMs=option('timeout-ms',60000),maxNotes=option('max-notes',50000);
if(timeoutMs<1||timeoutMs>300000||maxNotes<1||maxNotes>100000)throw new Error('timeout-ms must be 1..300000; max-notes must be 1..100000');
if(!prepared||!input||!output)throw new Error('Usage: prepared.json report.json NEW-output.json');
const out=resolve(output),assets=out+'.assets';
if(existsSync(out)||existsSync(assets))throw new Error('Output and assets must be new; previous evidence is immutable');
const snapshot=JSON.parse(readFileSync(prepared,'utf8')).snapshot,report=JSON.parse(readFileSync(input,'utf8'));
const db=statSync(process.env.MUSICANOTE_SEARCH_DB||new URL('../data/search-index-v2/search.sqlite',import.meta.url)),expected=report.runtime?.database;
if(!expected||db.size!==expected.size||db.mtimeMs!==expected.mtimeMs)throw new Error('Index differs from search report; rerun search before enrichment');
const started=performance.now();
const client=createSearchWorker({url:new URL('../server/structure-worker.mjs',import.meta.url),timeoutMs}),controller=new AbortController();
const cancel=()=>controller.abort();process.once('SIGINT',cancel);process.once('SIGTERM',cancel);
let enriched;
try{enriched=await enrichPreclearanceImportance(snapshot,report,{maxNotes,signal:controller.signal,
 analyzeSource:(workId,{signal})=>client.search({workId,maxNotes},0,{signal}),onProgress:p=>console.log(JSON.stringify(p))});}
finally{await client.close();process.off('SIGINT',cancel);process.off('SIGTERM',cancel);}
const after=statSync(process.env.MUSICANOTE_SEARCH_DB||new URL('../data/search-index-v2/search.sqlite',import.meta.url));
if(db.size!==after.size||db.mtimeMs!==after.mtimeMs)throw new Error('Index changed during analysis');
mkdirSync(assets);
for(const s of [snapshot,...enriched.snapshots])writeFileSync(resolve(assets,s.snapshotId+'.json'),JSON.stringify(s,null,2),{flag:'wx'});
enriched.report.structureEnrichment.provenance={inputReport:resolve(input),inputHash:structureHash(report),querySnapshot:snapshot.snapshotId,
 assetsDirectory:assets,createdAt:new Date().toISOString(),elapsedMs:performance.now()-started,worker:{timeoutMs,maxNotes},
 codeHashes:Object.fromEntries(['preclearance-importance.mjs','structure-worker.mjs','search-worker-client.mjs','structure-analysis-adapter.mjs','phrase-boundaries.mjs','search-api.mjs'].map(f=>[f,structureHash(readFileSync(new URL('../server/'+f,import.meta.url),'utf8'))]))};
writeFileSync(out,JSON.stringify(enriched.report,null,2),{flag:'wx'});
console.log(JSON.stringify(enriched.report.structureEnrichment));
