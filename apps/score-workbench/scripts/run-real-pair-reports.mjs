import {readFileSync,writeFileSync,mkdirSync,existsSync,statSync} from 'node:fs';
import {join,resolve} from 'node:path';
import {execFileSync} from 'node:child_process';
import {analyzeStructureSnapshot,structureHash} from '../server/structure-analysis-adapter.mjs';
import {runPreclearanceSearch,SELECTION_CONFIG} from '../server/preclearance-search.mjs';
import {createSearchWorker} from '../server/search-worker-client.mjs';
import {enrichPreclearanceImportance} from '../server/preclearance-importance.mjs';
import {createWorkIdentityResolver} from '../server/work-identity.mjs';
const [inputs,out]=process.argv.slice(2);if(!out||existsSync(out))throw Error('Inputs and NEW output required');
const caseIds=process.argv[4]?process.argv[4].split(','):['RC-004','RC-003','RC-005'];
const segmentStrategy=process.argv[5]??'phrase';
if(!['phrase','windows','hybrid'].includes(segmentStrategy))throw Error('Invalid segment strategy');
if(!caseIds.length||caseIds.some(id=>!/^RC-\d{3}$/.test(id)))throw Error('Invalid case IDs');
mkdirSync(out,{recursive:true});
const save=(p,v)=>writeFileSync(p,JSON.stringify(v,null,2),{flag:'wx'});
process.env.MUSICANOTE_PROFILE_SEARCH='1';process.env.MUSICANOTE_RETRIEVAL_CACHE='1';
const stat=statSync('data/search-index-v2/search.sqlite'),database={size:stat.size,mtimeMs:stat.mtimeMs};
const registry=JSON.parse(readFileSync('data/work-identities.json','utf8')),resolveIdentity=createWorkIdentityResolver(registry,database);
const searchWorker=createSearchWorker({timeoutMs:180000}),structureWorker=createSearchWorker({url:new URL('../server/structure-worker.mjs',import.meta.url),timeoutMs:20000});
const summaries=[];
try{
 for(const id of caseIds){
  const item=JSON.parse(readFileSync(join(inputs,id+'.json'),'utf8')),dir=join(out,id);mkdirSync(dir);
  const snapshot=analyzeStructureSnapshot(item.input);save(join(dir,'prepared.json'),{snapshot});
  const selfMatches=[],excluded=new Set(item.case.excludeExistingSources);
  console.log(JSON.stringify({case:id,stage:'start',events:snapshot.events.length,units:snapshot.units.length}));
  const report=await runPreclearanceSearch(snapshot,{resolveIdentity,config:{...SELECTION_CONFIG,segmentStrategy},
   search:async(query,limit)=>{
    const result=await searchWorker.search(query,limit);
    for(const kind of ['exact','similar'])result[kind]=(result[kind]||[]).filter(r=>{
     if(excluded.has(r.work.sourceId)){selfMatches.push({queryHash:structureHash(query),result:r});return false}return true;
    });return result;
   },
   onProgress:p=>console.log(JSON.stringify({case:id,...p})),
   onResult:run=>save(join(dir,run.taskId+'.task.json'),run)
  });
  report.runtime={createdAt:new Date().toISOString(),database,node:process.version};
  report.inspectionScope={selectedStream:item.selectedStream,allStreams:item.streamAudit,fullScoreExamined:false,segmentStrategy,maximumTasksPerStrategy:7,knownRegionUsedForSelection:false,knownReferenceUsedForRanking:false};
  save(join(dir,'search.json'),report);save(join(dir,'self-matches.json'),selfMatches);
  const display={...report,works:report.works.slice(0,10)};
  const enriched=await enrichPreclearanceImportance(snapshot,display,{maxNotes:5000,
   analyzeSource:(workId)=>structureWorker.search({workId,maxNotes:5000},0),
   onProgress:p=>console.log(JSON.stringify({case:id,stage:'candidate-structure',...p}))
  });
  const assets=resolve(dir,'evidence.assets');mkdirSync(assets);
  for(const s of [snapshot,...enriched.snapshots])save(join(assets,s.snapshotId+'.json'),s);
  enriched.report.structureEnrichment.provenance={assetsDirectory:assets};
  save(join(dir,'evidence.json'),enriched.report);
  execFileSync(process.execPath,['scripts/export-preclearance-report.mjs',join(dir,'evidence.json'),join(dir,'report')],{stdio:'inherit'});
  const expected=report.works.filter(w=>w.matches.some(m=>item.case.existingReferenceSources.includes(m.sourceId)));
  const summary={caseId:id,input:item.case.upload,reference:item.case.reference,selectedStream:item.selectedStream,
   segmentStrategy,tasks:report.runs.length,failed:report.runs.filter(r=>r.status!=='completed').length,status:report.status,
   candidateGroups:report.works.length,displayedGroups:display.works.length,selfMatches:selfMatches.length,
   expectedReferenceResults:expected.map(w=>({title:w.title,rank:report.works.indexOf(w)+1,matches:w.matches.length,similarity:w.similarity})),
   fullScoreExamined:false,legalFinding:'not-determined'};
  summaries.push(summary);save(join(dir,'summary.json'),summary);console.log(JSON.stringify(summary));
 }
}finally{await searchWorker.close();await structureWorker.close()}
save(join(out,'summary.json'),summaries);
writeFileSync(join(out,'index.html'),'<!doctype html><meta charset="utf-8"><title>실제 사례 검토</title><h1>실제 사례 — 기존 DB 검토 초안</h1><p>각 파일에서 자동 선택한 한 성부, 최대 7개 Phrase를 검사했습니다. 전곡 검사 완료나 법적 침해 판정이 아닙니다. 원곡명·기존 주석은 검색 점수에 사용하지 않았습니다. 상세 악보 비교는 상위 10개 후보 그룹입니다.</p>'+summaries.map(s=>'<section><h2>'+s.input+'</h2><p>검색 '+s.tasks+'개 / 실패 '+s.failed+'개 / 후보 '+s.candidateGroups+'그룹 / 자기 일치 별도 '+s.selfMatches+'건</p><a href="'+s.caseId+'/report/index.html">리포트 열기</a> · <a href="'+s.caseId+'/search.json">전체 검색 근거 JSON</a><p>기대 비교곡: '+s.reference+' — '+(s.expectedReferenceResults.length?s.expectedReferenceResults.map(r=>r.rank+'위, '+r.matches+'개 task 일치').join('; '):'선택 Query 결과에서 미회수 — 전곡 부재 판정 아님')+'</p></section>').join(''),{flag:'wx'});
