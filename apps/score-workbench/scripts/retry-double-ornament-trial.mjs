import {readFileSync,writeFileSync,existsSync,statSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {createSearchWorker} from '../server/search-worker-client.mjs';
const batch=process.argv[2]??'double-ornament-trial-v2',dir='evaluation/runs/'+batch,suitePath='evaluation/reports/'+batch+'/suite.json';
let ready=false;for(let i=0;i<240;i++){if(existsSync(dir+'/summary.json')&&JSON.parse(readFileSync(dir+'/summary.json')).remaining===0){ready=true;break;}await new Promise(r=>setTimeout(r,15000));}if(!ready)throw Error('Initial trial not complete');
const hash=p=>createHash('sha256').update(readFileSync(p)).digest('hex'),fp=JSON.parse(readFileSync(dir+'/manifest.json')).fingerprint,db=statSync('data/search-index-v2/search.sqlite');
if(fp.engine!==hash('server/search-api.mjs')||fp.suite!==hash(suitePath)||fp.dbTime!==db.mtimeMs||fp.dbSize!==db.size)throw Error('Trial fingerprint changed');
process.env.MUSICANOTE_SINGLE_OMISSION='1';process.env.MUSICANOTE_VISIBLE_RANKING='0';process.env.MUSICANOTE_RETRIEVAL_CACHE='1';delete process.env.MUSICANOTE_CONTOUR_SIDECAR;
const suite=JSON.parse(readFileSync(suitePath)),summary=JSON.parse(readFileSync(dir+'/summary.json')),worker=createSearchWorker({timeoutMs:180000}),retried=[];
try{for(const failed of summary.runs.filter(r=>r.status==='failed')){
 const path=dir+'/'+failed.caseId+'.retry.json';if(existsSync(path)){retried.push({caseId:failed.caseId,status:'already-recorded'});continue;}
 const c=suite.cases.find(c=>c.caseId===failed.caseId),b=suite.bases.find(b=>b.baseId===c.baseId),trace={rejections:{},scored:[]},start=performance.now();let row;
 try{const result=await worker.search(c.query,100,{onProgress:p=>{if(p.stage==='retrieval-inventory'){trace.inHits=p.hitWorks?.includes(b.expected.workId);trace.inCandidates=p.candidateWorks?.includes(b.expected.workId)}if(p.key?.split('\u0000')[0]===b.expected.workId){if(p.stage==='candidate-rejected')trace.rejections[p.reason]=(trace.rejections[p.reason]||0)+1;if(p.stage==='candidate-scored'&&trace.scored.length<12)trace.scored.push(p)}}});const all=[...result.exact,...result.similar],i=all.findIndex(m=>m.work.sourceId===b.expected.sourceId);row={caseId:c.caseId,status:'completed',sourceRank:i<0?null:i+1,elapsedMs:performance.now()-start,result,trace};}
 catch(e){row={caseId:c.caseId,status:'failed',error:e.message,elapsedMs:performance.now()-start,trace};}
 row.retryOf=failed.caseId;row.timeoutMs=180000;writeFileSync(path,JSON.stringify(row),{flag:'wx'});retried.push({caseId:row.caseId,status:row.status,sourceRank:row.sourceRank,elapsedMs:row.elapsedMs});console.log(JSON.stringify(retried.at(-1)));
}}finally{await worker.close();writeFileSync(dir+'/retry-summary.json',JSON.stringify({fingerprint:fp,initialTimeoutMs:60000,retryTimeoutMs:180000,retried},null,2));}
