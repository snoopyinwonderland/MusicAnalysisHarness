import {readFileSync,writeFileSync,mkdirSync,existsSync,statSync} from 'node:fs';
import {resolve,join} from 'node:path';
import {buildReviewCases} from '../server/preclearance-review-cases.mjs';
import {createSearchWorker} from '../server/search-worker-client.mjs';
import {structureHash} from '../server/structure-analysis-adapter.mjs';
const [input,output,limitFlag]=process.argv.slice(2);if(!input||!output||existsSync(output))throw new Error('Structure report and NEW directory required');
if(limitFlag&&!/^--max-cases=(?:[1-9]|1[0-2])$/.test(limitFlag))throw new Error('max-cases must be 1..12');
const maximum=limitFlag?Number(limitFlag.split('=')[1]):12;
const report=JSON.parse(readFileSync(input,'utf8')),assets=report.structureEnrichment.provenance.assetsDirectory;
const dbPath=resolve(process.env.MUSICANOTE_SEARCH_DB||'data/search-index-v2/search.sqlite'),db=statSync(dbPath);
if(db.size!==report.runtime.database.size||db.mtimeMs!==report.runtime.database.mtimeMs||existsSync(dbPath+'-wal'))throw new Error('Index mismatch or active WAL');
const snapshots=report.structureEnrichment.snapshots.map(s=>JSON.parse(readFileSync(join(assets,s.snapshotId+'.json'),'utf8')));
for(const s of snapshots){const group=report.works.find(w=>w.matches.some(m=>m.sourceId===s.identity.sourceId));s.diversityKey=group?.canonicalWorkId??(group?.title?`${group.title.trim().toLowerCase()}|${String(group.artist??'').trim().toLowerCase()}`:s.identity.sourceId);}
process.env.MUSICANOTE_RETRIEVAL_CACHE='1';
const suite=buildReviewCases(snapshots);suite.provenance={input:resolve(input),inputHash:structureHash(report),createdAt:new Date().toISOString(),database:{size:db.size,mtimeMs:db.mtimeMs},maximum,
 diversityPolicy:'canonical identity when verified, otherwise title/artist proxy for sampling only; no search merging',
 codeHashes:Object.fromEntries(['server/preclearance-review-cases.mjs','server/search-api.mjs','server/search-worker-client.mjs','scripts/run-preclearance-review-suite.mjs'].map(f=>[f,structureHash(readFileSync(f,'utf8'))]))};
mkdirSync(output);writeFileSync(join(output,'suite.json'),JSON.stringify(suite,null,2),{flag:'wx'});
const client=createSearchWorker({timeoutMs:60000}),controller=new AbortController(),cancel=()=>controller.abort();process.once('SIGINT',cancel);process.once('SIGTERM',cancel);
const runs=[];
try{for(const c of suite.cases.slice(0,maximum)){
 if(controller.signal.aborted)break;
 const started=performance.now();let run;
 try{const result=await client.search(c.query,20,{signal:controller.signal});
  const candidates=[...(result.exact??[]),...(result.similar??[])];
  const ordinal=candidates.findIndex(r=>r.work.sourceId===c.sourceId),target=candidates.findIndex(r=>r.work.workId===c.workId&&r.alignment?.some(p=>p.candidateIndex!=null&&p.queryIndex!=null&&c.sourceFocus.some(f=>{const n=r.work.notes?.[p.candidateIndex];return n&&Math.abs(f.onset-n.onset)<1e-6&&f.pitchMidi===n.pitchMidi})));
  run={caseId:c.caseId,status:'completed',elapsedMs:performance.now()-started,sourceRank:ordinal<0?null:ordinal+1,sourceWindowRank:target<0?null:target+1,windowRankMeaning:'same indexed stream and at least one aligned original attack; not full-span correctness',
   result,humanReview:c.humanReview};
 }catch(error){run={caseId:c.caseId,status:'failed',error:String(error.message),elapsedMs:performance.now()-started};}
 writeFileSync(join(output,c.caseId+'.json'),JSON.stringify(run,null,2),{flag:'wx'});runs.push({caseId:run.caseId,status:run.status,sourceRank:run.sourceRank,sourceWindowRank:run.sourceWindowRank,elapsedMs:run.elapsedMs,error:run.error});console.log(JSON.stringify(runs.at(-1)));
}}finally{await client.close();process.off('SIGINT',cancel);process.off('SIGTERM',cancel)}
const after=statSync(dbPath);
writeFileSync(join(output,'summary.json'),JSON.stringify({counts:suite.counts,runs,cancelled:controller.signal.aborted,indexUnchanged:after.size===db.size&&after.mtimeMs===db.mtimeMs&&!existsSync(dbPath+'-wal'),notExecuted:suite.cases.length-runs.length,warning:'Source recovery within top 20 is a diagnostic, not expert relevance or engraving correctness.'},null,2),{flag:'wx'});
