import {readFileSync,writeFileSync,mkdirSync,existsSync,copyFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {getWork} from '../server/search-api.mjs';
import {validateEvaluationCase} from './evaluation-case-validation.mjs';
const batch=process.argv[2]??'memory-variation-50-v1',dir='evaluation/reports/'+batch,runs='evaluation/runs/'+batch,out='evaluation/exports/'+batch;
const suite=JSON.parse(readFileSync(dir+'/suite.json')),hash=s=>createHash('sha256').update(s).digest('hex');
const report=existsSync(dir+'/results.json')?JSON.parse(readFileSync(dir+'/results.json')):null;
const reviews=existsSync(dir+'/review.json')?JSON.parse(readFileSync(dir+'/review.json')).cases:[];
const proposalText={
 'articulation-collapsed-to-exact':'Separate tolerant IOI-based retrieval from strict exact duration/rest comparison; retain one shared tempo scale and explicit silence gaps.',
 'exact-variation-needs-duration-audit':'Audit whether compressed long-duration ratios conceal real rhythmic changes; do not reuse tolerant rhythm scores as exact predicates.',
 'execution-error':'Retry execution separately and retain both attempts; do not label timeouts as retrieval failures.',
 'source-candidate-not-returned':'Inspect seed positions, candidate windows and admission trace before changing thresholds.',
 'source-not-in-candidates':'Audit candidate recall using retained anchor runs; avoid globally lowering ranking thresholds.',
 'representative-window-differs':'Compare repeated occurrences and preserve links to the requested source passage.',
 'partial-query-alignment':'Inspect split/merge attack semantics and retain unmatched query attacks explicitly.',
 'invalid-alignment-reference':'Repair alignment coordinate provenance before using it for score highlighting.'
};
mkdirSync(out,{recursive:true});mkdirSync(out+'/cases',{recursive:true});mkdirSync(out+'/base-assets',{recursive:true});
mkdirSync(out+'/runs',{recursive:true});
copyFileSync(dir+'/suite.json',out+'/suite.json');
const supportingFiles=['selection.json','suite-validation.json','review.json','strict-exact-audit.json','user-review-policy.json','timing-comparison.json','TIMING-COMPARISON.md'].filter(name=>existsSync(dir+'/'+name));
for(const name of supportingFiles)copyFileSync(dir+'/'+name,out+'/'+name);
for(const name of ['manifest.json','summary.json'])if(existsSync(runs+'/'+name))copyFileSync(runs+'/'+name,out+'/runs/'+name);
const index=[];
for(const b of suite.bases){
 const assetDir=out+'/base-assets/'+b.baseId;mkdirSync(assetDir,{recursive:true});
 if(!existsSync(assetDir+'/manifest.json')){
  let xml=null,error=null;const start=Math.max(1,b.xmlEvents[0].measureOrdinal-2),end=b.xmlEvents.at(-1).measureOrdinal+2;
  try{xml=getWork(b.expected.workId,{ordinalStart:start,ordinalEnd:end,targets:b.focus.map(n=>n.o+':'+n.p).join(','),excerpt:'1'})?.xml;if(!xml)throw Error('No MusicXML returned')}catch(e){error=e.message}
  if(xml)writeFileSync(assetDir+'/context.musicxml',xml,{flag:'wx'});
  writeFileSync(assetDir+'/events.json',JSON.stringify({identity:b.expected,focus:b.xmlEvents,context:b.context,indexLinks:b.indexLinks,originalQuery:b.query,sourceHash:b.sourceHash},null,2),{flag:'wx'});
  writeFileSync(assetDir+'/manifest.json',JSON.stringify({startOrdinal:start,endOrdinal:end,xmlHash:xml?hash(xml):null,xmlError:error,eventsHash:hash(readFileSync(assetDir+'/events.json')),sourcePath:b.sourcePath,sourceHash:b.sourceHash},null,2),{flag:'wx'});
 }
 const manifest=JSON.parse(readFileSync(assetDir+'/manifest.json'));
 for(const c of suite.cases.filter(c=>c.baseId===b.baseId)){
  const runPath=runs+'/'+c.caseId+'.json',retryPath=runs+'/'+c.caseId+'.retry.json';
  const r=existsSync(retryPath)?JSON.parse(readFileSync(retryPath)):existsSync(runPath)?JSON.parse(readFileSync(runPath)):null;
  if(existsSync(runPath))copyFileSync(runPath,out+'/runs/'+c.caseId+'.json');
  if(existsSync(retryPath))copyFileSync(retryPath,out+'/runs/'+c.caseId+'.retry.json');
  const audit=report?.rows.find(row=>row.caseId===c.caseId);
  const review=reviews.find(row=>row.caseId===c.caseId);
  const record={schema:'musicanote-evaluation-case/v1',caseId:batch+'-'+c.caseId,createdAt:suite.createdAt.slice(0,10),status:'draft',replayable:true,
   query:c.query,originalQuery:b.query,tags:[c.kind,c.positive?'positive-probe':'reversal-control'],description:c.description,changes:{changedSourceIds:c.changedSourceIds,originalDuration:c.originalDuration,queryDuration:c.queryDuration,transformation:c.transformation??null},
   expected:{...b.expected,status:c.positive?'source-retrieval-probe':'not-certified-unrelated'},
   observations:r?[{status:r.status,sourceRank:r.sourceRank??null,elapsedMs:r.elapsedMs,trace:r.trace},...(audit?[{kind:'automated-audit',generatedAt:report.generatedAt,baselineRank:audit.baselineRank,rankChange:audit.rankChange,sourceScore:audit.sourceScore,representativeWindowRank:audit.representativeWindowRank,originalStartInOccurrences:audit.originalStartInOccurrences,sourcePairedNotes:audit.sourcePairedNotes,issues:audit.issues,reviewNotes:audit.reviewNotes,suggestions:audit.suggestions,top:audit.top}]:[])]:[],
   diagnoses:(audit?.issues??[]).map(code=>({code,status:'observation-not-confirmed-cause'})),
   proposals:(audit?.issues??[]).map(code=>({code,text:proposalText[code],status:'proposed-not-implemented'})),
   runs:r?[{status:r.status,resultPath:'../runs/'+c.caseId+(existsSync(retryPath)?'.retry':'')+'.json',initialPath:'../runs/'+c.caseId+'.json'}]:[],
   knowledgeBase:{schema:'musicanote-case-knowledge/v1',identity:b.expected,sourceSnapshot:manifest,focus:{events:b.xmlEvents},
    context:{policy:'original XML up to 2 measures before/after; event snapshot preserves supplied source context'},
    assets:{musicXml:manifest.xmlHash?'../base-assets/'+b.baseId+'/context.musicxml':'',events:'../base-assets/'+b.baseId+'/events.json'},
    classification:{phenomenonTypes:[c.kind],musicalFunctions:[],contextualConditions:[{meter:c.query.meter}],exclusions:['Automated retrieval is not a human relevance judgment'],confidence:'automatic-unreviewed'},
    ruleLearning:{candidateRules:[],counterexamples:[],reusableFor:['retrieval-regression','query-completion','alignment-review']}}};
  if(review){
   record.observations.push({kind:'alignment-evidence-review',details:review.observations});
   record.diagnoses.push({text:review.diagnosis,status:review.status});
   record.proposals.push({text:review.proposal,status:'proposed-not-implemented'});
  }
  if(audit?.changedNoteAlignment)record.observations.push({kind:'changed-note-alignment',...audit.changedNoteAlignment});
  if(audit)record.observations.push({kind:'rank-context',originalNoteLength:audit.originalNoteLength,queryNoteLength:audit.queryNoteLength,returnedCount:audit.returnedCount,exactCount:audit.exactCount,sameScoreBeforeSource:audit.sameScoreBeforeSource});
  validateEvaluationCase(record);writeFileSync(out+'/cases/'+c.caseId+'.json',JSON.stringify(record,null,2));
  index.push({caseId:record.caseId,type:c.kind,path:'cases/'+c.caseId+'.json',baseId:b.baseId,status:r?.status??'pending'});
 }
}
writeFileSync(out+'/index.json',JSON.stringify({schema:'musicanote-case-bundle/v1',batch,updatedAt:new Date().toISOString(),sourceSuite:'suite.json',executionManifest:'runs/manifest.json',supportingFiles,cases:index},null,2));
console.log(JSON.stringify({cases:index.length,assets:suite.bases.length,xmlErrors:suite.bases.map(b=>JSON.parse(readFileSync(out+'/base-assets/'+b.baseId+'/manifest.json'))).filter(m=>m.xmlError)}));
