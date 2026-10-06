import {readFileSync,writeFileSync,mkdirSync,statSync,existsSync,readdirSync,renameSync,unlinkSync} from 'node:fs';
import {resolve,dirname} from 'node:path';
import {runPreclearanceSearch,SELECTION_CONFIG} from '../server/preclearance-search.mjs';
import {structureHash} from '../server/structure-analysis-adapter.mjs';
import {createSearchWorker} from '../server/search-worker-client.mjs';
import {createWorkIdentityResolver,resolveUploadIdentity} from '../server/work-identity.mjs';

const [inputPath,outputPath,...flags]=process.argv.slice(2);
if(!inputPath||!outputPath)throw new Error('Usage: node scripts/run-preclearance-search.mjs prepared.json report.json [--resume] [--timeout-ms=N] [--cache=0|1]');
if(flags.some(f=>f!=='--resume'&&!/^--mode=(phrase|combined|motif)$/.test(f)&&!/^--timeout-ms=\d+$/.test(f)&&!/^--cache=[01]$/.test(f)&&!/^--max-tasks=[1-7]$/.test(f)))throw new Error('Unknown option');
const input=JSON.parse(readFileSync(inputPath,'utf8')),resume=flags.includes('--resume');
const timeoutMs=Number(flags.find(f=>f.startsWith('--timeout-ms='))?.split('=')[1]??180000);
if(timeoutMs<1||timeoutMs>86400000)throw new Error('timeout-ms must be 1..86400000');
const mode=flags.find(f=>f.startsWith('--mode='))?.split('=')[1]??'phrase';
const config={...SELECTION_CONFIG,kinds:mode==='combined'?['phrase','motif']:[mode],maximumTasks:Number(flags.find(f=>f.startsWith('--max-tasks='))?.split('=')[1]??7)};
process.env.MUSICANOTE_PROFILE_SEARCH='1';
process.env.MUSICANOTE_RETRIEVAL_CACHE=flags.find(f=>f.startsWith('--cache='))?.split('=')[1]??'1';
const dbPath=resolve(process.env.MUSICANOTE_SEARCH_DB||'data/search-index-v2/search.sqlite'),s=statSync(dbPath);
const identities=JSON.parse(readFileSync(new URL('../data/work-identities.json',import.meta.url),'utf8'));
const resolveIdentity=createWorkIdentityResolver(identities,{size:s.size,mtimeMs:s.mtimeMs});
const excludedCanonicalWorkId=resolveUploadIdentity(identities,{size:s.size,mtimeMs:s.mtimeMs},input.snapshot.identity);
const modules=['search-api.mjs','retrieval-cache.mjs','preclearance-search.mjs','structure-analysis-adapter.mjs','phrase-boundaries.mjs','seed-windows.mjs'];
const fingerprint={snapshotId:input.snapshot.snapshotId,snapshotHash:structureHash(input.snapshot),selection:config,resultLimit:30,includeSelf:false,workIdentitiesHash:structureHash(identities),identityCodeHash:structureHash(readFileSync(new URL('../server/work-identity.mjs',import.meta.url),'utf8')),
  database:{path:dbPath,size:s.size,mtimeMs:s.mtimeMs,wal:existsSync(dbPath+'-wal')?statSync(dbPath+'-wal').mtimeMs:null},
  code:modules.map(name=>[name,structureHash(readFileSync(new URL('../server/'+name,import.meta.url),'utf8'))]),
  searchEnvironment:Object.fromEntries(Object.entries(process.env).filter(([key])=>key.startsWith('MUSICANOTE_')).sort())};
const manifest={schema:'preclearance-job/1',fingerprint,hash:structureHash(fingerprint)};
const dir=outputPath+'.job',manifestPath=dir+'/manifest.json';
mkdirSync(dirname(resolve(outputPath)),{recursive:true});
if(resume){
  const old=JSON.parse(readFileSync(manifestPath,'utf8'));
  if(old.hash!==manifest.hash)throw new Error('Resume refused: input, code, settings or index changed. Use a new output path.');
}else{
  if(existsSync(outputPath)||existsSync(dir))throw new Error('Output already exists. Use --resume or a new output path.');
  mkdirSync(dir);writeFileSync(manifestPath,JSON.stringify(manifest,null,2),{flag:'wx'});
}
// A live (or inaccessible) process always retains its lock. Recover only ESRCH.
const lock=dir+'/running.lock';
if(resume&&existsSync(lock)){
 const owner=JSON.parse(readFileSync(lock,'utf8'));
 if(!Number.isInteger(owner.pid)||owner.pid<=0)throw new Error('Invalid lock: manual inspection required');
 try{process.kill(owner.pid,0);throw new Error('Job is already running');}
 catch(error){if(error.code!=='ESRCH')throw error;unlinkSync(lock);}
}
writeFileSync(lock,JSON.stringify({pid:process.pid,createdAt:new Date().toISOString()}),{flag:'wx'});
const atomic=(path,value)=>{const tmp=path+'.tmp';writeFileSync(tmp,JSON.stringify(value,null,2));renameSync(tmp,path);};
let completedRuns;
try{completedRuns=readdirSync(dir).filter(name=>name.endsWith('.task.json')).map(name=>JSON.parse(readFileSync(dir+'/'+name,'utf8'))).filter(run=>run.status==='completed');}
catch(error){unlinkSync(lock);throw new Error(`Invalid checkpoint: ${error.message}`);}
const controller=new AbortController(),cancel=()=>controller.abort();process.on('SIGINT',cancel);process.on('SIGTERM',cancel);
const worker=createSearchWorker({timeoutMs}),started=performance.now();
try{
  atomic(outputPath,{status:'running',snapshotId:input.snapshot.snapshotId,resumed:completedRuns.length});
  const report=await runPreclearanceSearch(input.snapshot,{config,completedRuns,signal:controller.signal,resolveIdentity,excludedCanonicalWorkId,
    search:(query,limit)=>worker.search(query,limit,{signal:controller.signal}),
    onProgress:p=>console.log(JSON.stringify(p)),onResult:run=>atomic(dir+'/'+run.taskId+'.task.json',run)});
  report.runtime={elapsedMs:performance.now()-started,createdAt:new Date().toISOString(),node:process.version,database:fingerprint.database,manifestHash:manifest.hash,timeoutMs,reused:report.runs.filter(r=>r.reused).length};
  atomic(outputPath,report);console.log(JSON.stringify({status:report.status,tasks:report.runs.length,works:report.works.length,elapsedMs:report.runtime.elapsedMs,reused:report.runtime.reused}));
}catch(error){atomic(outputPath,{status:'failed',error:String(error.message??error),snapshotId:input.snapshot.snapshotId});throw error;}
finally{await worker.close();process.off('SIGINT',cancel);process.off('SIGTERM',cancel);unlinkSync(lock);}
