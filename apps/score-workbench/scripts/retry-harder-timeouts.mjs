import {readFileSync,writeFileSync,mkdirSync,existsSync} from 'node:fs';
import {join} from 'node:path';
import {createSearchWorker} from '../server/search-worker-client.mjs';
const dir=process.argv[2],suite=JSON.parse(readFileSync(join(dir,'suite.json'))),summary=JSON.parse(readFileSync(join(dir,'summary.json')));if(summary.remaining)throw Error('Finish primary attempts');const out=join(dir,'retry-180s');if(!existsSync(out))mkdirSync(out);
process.env.MUSICANOTE_PROFILE_SEARCH='1';process.env.MUSICANOTE_RETRIEVAL_CACHE='1';delete process.env.MUSICANOTE_CONTOUR_SIDECAR;
const worker=createSearchWorker({timeoutMs:180000}),rows=[];
try{for(const old of summary.runs.filter(r=>r.status==='failed'&&/timed out/.test(r.error))){const file=join(out,old.caseId+'.json');if(existsSync(file)){rows.push(JSON.parse(readFileSync(file)));continue}const c=old.kind==='control'?suite.bases.find(b=>b.baseId===old.baseId):suite.cases.find(c=>c.caseId===old.caseId);const start=performance.now();let r;
try{const result=await worker.search(c.query,100),all=[...result.exact,...result.similar],rank=all.findIndex(x=>x.work.sourceId===c.expected.sourceId);r={caseId:old.caseId,kind:old.kind,status:'completed',elapsedMs:performance.now()-start,sourceRank:rank<0?null:rank+1,result};}catch(e){r={caseId:old.caseId,kind:old.kind,status:'failed',elapsedMs:performance.now()-start,error:e.message}}
writeFileSync(file,JSON.stringify(r),{flag:'wx'});rows.push(r);const{result,...brief}=r;console.log(JSON.stringify(brief));
}}finally{await worker.close()}
writeFileSync(join(out,'summary.json'),JSON.stringify({timeoutMs:180000,primaryUnchanged:true,warning:'Separate retry with different warm-cache conditions, not primary latency samples',runs:rows.map(({result,...r})=>r)},null,2));
