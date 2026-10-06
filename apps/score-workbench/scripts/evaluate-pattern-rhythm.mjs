import {readFileSync,writeFileSync,mkdirSync,existsSync,statSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {createSearchWorker} from '../server/search-worker-client.mjs';
const dir=process.argv[2]??'evaluation/reports/pattern-rhythm-v1';mkdirSync(dir,{recursive:true});
const suite=JSON.parse(readFileSync('evaluation/reports/eighth-meter-60-v1/suite.json')),c=suite.cases.find(c=>c.caseId==='EM09-L12-original'),b=suite.bases.find(b=>b.baseId===c.baseId),query={...c.query,allowContinuousStepwise:true,allowContinuousRepeated:true};
const hash=p=>createHash('sha256').update(readFileSync(p)).digest('hex');
if(!existsSync(dir+'/query.json'))writeFileSync(dir+'/query.json',JSON.stringify({schema:'musicanote-query',query},null,2));
const rows=[];
for(const mode of ['baseline','rhythm-priority']){
 const path=dir+'/'+mode+'.json';if(existsSync(path)){rows.push(JSON.parse(readFileSync(path)));continue;}
 process.env.MUSICANOTE_PATTERN_RHYTHM=mode==='baseline'?'0':'1';process.env.MUSICANOTE_SINGLE_OMISSION='1';process.env.MUSICANOTE_VISIBLE_RANKING='0';process.env.MUSICANOTE_RETRIEVAL_CACHE='1';
 const worker=createSearchWorker({timeoutMs:180000}),started=performance.now(),trace={};let row;
 try{const result=await worker.search(query,100,{onProgress:p=>{if(p.stage==='retrieval-inventory'){trace.inHits=p.hitWorks?.includes(b.expected.workId);trace.inCandidates=p.candidateWorks?.includes(b.expected.workId);}}}),all=[...result.exact,...result.similar],i=all.findIndex(m=>m.work.sourceId===b.expected.sourceId);
 row={mode,status:'completed',elapsedMs:performance.now()-started,sourceRank:i<0?null:i+1,trace,result};
 }catch(e){row={mode,status:'failed',error:e.message};}finally{await worker.close();}
 row.provenance={createdAt:new Date().toISOString(),engine:hash('server/search-api.mjs'),pattern:hash('server/pattern-rhythm.mjs'),dbSize:statSync('data/search-index-v2/search.sqlite').size,sourceCase:'eighth-meter-60-v1/EM09-L12-original'};
 writeFileSync(path,JSON.stringify(row),{flag:'wx'});rows.push(row);console.log(JSON.stringify({mode,status:row.status,rank:row.sourceRank,trace:row.trace,ms:row.elapsedMs}));
}
writeFileSync(dir+'/comparison.json',JSON.stringify(rows.map(r=>({mode:r.mode,status:r.status,rank:r.sourceRank,trace:r.trace,elapsedMs:r.elapsedMs,top:[...(r.result?.exact??[]),...(r.result?.similar??[])].slice(0,10).map(m=>({title:m.work.title,score:m.ranking,rhythm:m.scores.rhythm,interval:m.scores.interval,sourceId:m.work.sourceId}))})),null,2));
