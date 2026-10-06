import {readFileSync,writeFileSync,existsSync} from 'node:fs';
const batch=process.argv[2]??'short-query-90-v1',dir='evaluation/reports/'+batch;
const report=JSON.parse(readFileSync(dir+'/results.json')),path=dir+'/review.json';
const review=existsSync(path)?JSON.parse(readFileSync(path)):{schema:'musicanote-evaluation-review/v1',createdAt:'2026-09-17',cases:[]};
review.cases=review.cases.filter(c=>c.provenance!=='automated-trace-review');
for(const r of report.rows){
 if(r.status!=='completed'||review.cases.some(c=>c.caseId===r.caseId))continue;
 if(r.sourceRank&&r.sourceRank<=10&&!r.issues.includes('partial-query-alignment'))continue;
 const gate=r.trace?.rejections?.['low-information-floors'],best=[...(r.trace?.scored??[])].sort((a,b)=>b.local-a.local)[0];
 const evidence=best?{local:best.local,pitch:best.scores.pitch,interval:best.scores.interval,rhythm:best.scores.rhythm,meter:best.metric.score,equality:best.equality,coverage:best.alignment?.coverage,gaps:best.alignment?.path.filter(p=>p.queryIndex===null||p.candidateIndex===null).length}:null;
 const observations=[{originalNotes:r.originalNoteLength,queryNotes:r.queryNoteLength,sourceRank:r.sourceRank,baselineRank:r.baselineRank,exactCount:r.exactCount,sameScoreBeforeSource:r.sameScoreBeforeSource,inCandidates:r.trace?.inCandidates,rejections:r.trace?.rejections,bestScoredTrace:evidence}];
 let diagnosis='Rank/coverage needs review; this is not a confirmed relevance error.',proposal='Inspect the source passage and preceding candidates; do not require rank 1.';
 if(!r.sourceRank&&gate){diagnosis='Expected stream entered scoring and has low-information-floor rejection evidence. Other traced rejections may also apply.';proposal='Compare deletion-induced onset shifts and strict metrical/equality floors using repetitive-query negative controls; do not globally relax admission.';}
 else if(!r.sourceRank){diagnosis='Expected source is absent from returned results; candidate and rejection trace retained, cause not yet confirmed.';proposal='Separate candidate retrieval, window selection, admission and result limit before modifying ranking.';}
 else if(r.sourceRank>10&&r.sameScoreBeforeSource){diagnosis='Expected source ranks below Top10 with earlier equal-score candidates; source identity and tie ordering need review.';proposal='Audit equal-score alternatives and confirmed work identity before treating this as bad similarity scoring.';}
 else if(r.issues.includes('partial-query-alignment')){diagnosis='Source retrieved but some query attacks remain unmatched.';proposal='Check which changed/retained notes were excluded, separately from successful work retrieval.';}
 review.cases.push({caseId:r.caseId,observations,diagnosis,proposal,status:'observed-not-fixed',provenance:'automated-trace-review'});
}
writeFileSync(path,JSON.stringify(review,null,2));console.log(JSON.stringify({reviewed:review.cases.length,complete:report.complete}));
