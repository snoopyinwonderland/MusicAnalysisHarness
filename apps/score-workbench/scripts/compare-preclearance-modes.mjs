import {readFileSync,writeFileSync,mkdirSync,existsSync,statSync} from 'node:fs';
import {join} from 'node:path';
import {runPreclearanceSearch,SELECTION_CONFIG} from '../server/preclearance-search.mjs';
import {createSearchWorker} from '../server/search-worker-client.mjs';
import {structureHash} from '../server/structure-analysis-adapter.mjs';
import {createWorkIdentityResolver,resolveUploadIdentity} from '../server/work-identity.mjs';
const [prepared,out]=process.argv.slice(2);if(!prepared||!out||existsSync(out))throw Error('prepared.json NEW-directory');
const snapshot=JSON.parse(readFileSync(prepared,'utf8')).snapshot,db=statSync(process.env.MUSICANOTE_SEARCH_DB||'data/search-index-v2/search.sqlite'),database={size:db.size,mtimeMs:db.mtimeMs};
const registry=JSON.parse(readFileSync(new URL('../data/work-identities.json',import.meta.url),'utf8')),resolveIdentity=createWorkIdentityResolver(registry,database),excludedCanonicalWorkId=resolveUploadIdentity(registry,database,snapshot.identity);
mkdirSync(out,{recursive:true});process.env.MUSICANOTE_PROFILE_SEARCH='1';process.env.MUSICANOTE_RETRIEVAL_CACHE='1';
const worker=createSearchWorker({timeoutMs:60000}),reports={};
try{for(const mode of ['phrase','combined']){
 const start=performance.now(),config={...SELECTION_CONFIG,kinds:mode==='phrase'?['phrase']:['phrase','motif']};
 const report=await runPreclearanceSearch(snapshot,{config,resolveIdentity,excludedCanonicalWorkId,completedRuns:reports.phrase?.runs??[],search:(q,l)=>worker.search(q,l),onProgress:p=>console.log(JSON.stringify({mode,...p})),onResult:r=>writeFileSync(join(out,mode+'-'+r.taskId+'.json'),JSON.stringify(r))});
 report.runtime={elapsedMs:performance.now()-start,database};reports[mode]=report;writeFileSync(join(out,mode+'.json'),JSON.stringify(report));
}}finally{await worker.close()}
const a=new Set(reports.phrase.works.map(w=>w.key)),b=reports.combined.works;
const summary={snapshotId:snapshot.snapshotId,database,configVersion:SELECTION_CONFIG.version,phraseTasks:reports.phrase.runs.length,combinedTasks:reports.combined.runs.length,
 phraseKeys:reports.phrase.works.map(w=>w.key),combinedKeys:b.map(w=>w.key),addedCandidates:b.filter(w=>!a.has(w.key)).map(w=>({key:w.key,title:w.title,similarity:w.similarity,humanReview:'unreviewed'})),
 phraseElapsedMs:reports.phrase.runtime.elapsedMs,additionalElapsedMs:reports.combined.runtime.elapsedMs,
 statuses:{phrase:reports.phrase.status,combined:reports.combined.status},sharedPhraseResultsReused:true,sharedPhraseTasksPreserved:reports.phrase.runs.every(r=>reports.combined.runs.some(s=>s.taskId===r.taskId)),
 excludedCanonicalWorkId,interpretation:'Additional candidates are not automatically relevant. Shared tasks are reused, so timing is incremental, not an independent cold A/B benchmark.',
 equalBudgetDiagnostic:{phraseLimit:7,combinedPhraseLimit:7,motifExtraLimit:3,performed:false,reason:'This run isolates added motif evidence without displacing phrases; fixed-total-budget comparison remains separate.'},
 codeHashes:Object.fromEntries(['preclearance-search.mjs','structure-analysis-adapter.mjs','search-api.mjs'].map(f=>[f,structureHash(readFileSync(new URL('../server/'+f,import.meta.url),'utf8'))]))};
writeFileSync(join(out,'summary.json'),JSON.stringify(summary,null,2));console.log(JSON.stringify(summary));
