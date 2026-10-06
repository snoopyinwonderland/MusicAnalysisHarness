import {readFileSync,writeFileSync,mkdirSync,existsSync,statSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {createSearchWorker} from '../server/search-worker-client.mjs';
const [suitePath,dir]=process.argv.slice(2);if(!dir)throw Error('suite output required');
const suite=JSON.parse(readFileSync(suitePath)),hash=p=>createHash('sha256').update(readFileSync(p)).digest('hex'),db='data/search-index-v2/search.sqlite';
const timeoutMs=Number(process.env.MUSICANOTE_EVAL_TIMEOUT_MS??60000);
// Historical baseline runs must remain opt-in after the production default changed.
process.env.MUSICANOTE_SINGLE_OMISSION??='0';
const fingerprint=()=>({suite:hash(suitePath),engine:hash('server/search-api.mjs'),dbSize:statSync(db).size,dbTime:statSync(db).mtimeMs,omission:process.env.MUSICANOTE_SINGLE_OMISSION==='1'}),fp=fingerprint();
mkdirSync(dir,{recursive:true});if(existsSync(dir+'/manifest.json')){if(JSON.stringify(JSON.parse(readFileSync(dir+'/manifest.json')).fingerprint)!==JSON.stringify(fp))throw Error('Changed fingerprint')}else writeFileSync(dir+'/manifest.json',JSON.stringify({fingerprint:fp,timeoutMs,limit:100},null,2));
process.env.MUSICANOTE_RETRIEVAL_CACHE='1';delete process.env.MUSICANOTE_CONTOUR_SIDECAR;
const worker=createSearchWorker({timeoutMs}),runs=[];
function save(){writeFileSync(dir+'/summary.json',JSON.stringify({attempted:runs.length,total:suite.cases.length,remaining:suite.cases.length-runs.length,byType:Object.fromEntries([...new Set(suite.cases.map(c=>c.kind))].map(k=>{const a=runs.filter(r=>r.kind===k);return[k,{attempted:a.length,completed:a.filter(r=>r.status==='completed').length,found:a.filter(r=>r.sourceRank).length,top5:a.filter(r=>r.sourceRank&&r.sourceRank<=5).length}]})),runs},null,2))}
try{for(const c of suite.cases){const path=dir+'/'+c.caseId+'.json';if(existsSync(path)){const {result,...r}=JSON.parse(readFileSync(path));runs.push(r);continue}if(JSON.stringify(fingerprint())!==JSON.stringify(fp))throw Error('Engine changed');const b=suite.bases.find(b=>b.baseId===c.baseId),trace={rejections:{},scored:[]},t=performance.now();let r;
 try{const result=await worker.search(c.query,100,{onProgress:p=>{if(p.stage==='retrieval-inventory'){trace.inHits=p.hitWorks?.includes(b.expected.workId);trace.inCandidates=p.candidateWorks?.includes(b.expected.workId)}if(p.key?.split('\u0000')[0]===b.expected.workId){if(p.stage==='candidate-rejected')trace.rejections[p.reason]=(trace.rejections[p.reason]||0)+1;if(p.stage==='candidate-scored'&&trace.scored.length<12)trace.scored.push(p)}}}),all=[...result.exact,...result.similar],rank=all.findIndex(m=>m.work.sourceId===b.expected.sourceId);
 r={caseId:c.caseId,kind:c.kind,status:'completed',sourceRank:rank<0?null:rank+1,elapsedMs:performance.now()-t,trace,result};
 }catch(e){r={caseId:c.caseId,kind:c.kind,status:'failed',error:e.message,elapsedMs:performance.now()-t,trace}}
 writeFileSync(path,JSON.stringify(r),{flag:'wx'});const {result,...brief}=r;runs.push(brief);save();console.log(JSON.stringify({caseId:r.caseId,status:r.status,rank:r.sourceRank,ms:Math.round(r.elapsedMs)}));
}}finally{await worker.close();save()}
