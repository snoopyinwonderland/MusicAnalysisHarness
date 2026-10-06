import {readFileSync,writeFileSync,existsSync} from 'node:fs';
const batch=process.argv[2]??'short-query-90-v1',dir='evaluation/reports/'+batch,suite=JSON.parse(readFileSync(dir+'/suite.json'));
const median=a=>{const b=[...a].sort((a,b)=>a-b);return b.length%2?b[(b.length-1)/2]:(b[b.length/2-1]+b[b.length/2])/2;},rows=[];
for(const c of suite.cases){
 const p='evaluation/runs/'+batch+'/'+c.caseId,run=existsSync(p+'.retry.json')?p+'.retry.json':p+'.json';if(!existsSync(run))continue;
 const r=JSON.parse(readFileSync(run));if(r.status!=='completed')continue;
 let onset=0;const q=c.query.events.flatMap(e=>{const start=onset;onset+=e.durationRatio;return e.kind==='note'?[{p:e.pitchMidi,d:e.durationRatio,o:start}]:[];});
 for(const [i,m]of r.result.exact.slice(0,10).entries()){
  const pairs=m.alignment.filter(a=>a.queryIndex!==null&&a.candidateIndex!==null).sort((a,b)=>a.queryIndex-b.queryIndex);
  if(pairs.length!==q.length||pairs.some((a,i)=>a.queryIndex!==i)||new Set(pairs.map(a=>a.candidateIndex)).size!==q.length){rows.push({caseId:c.caseId,rank:i+1,title:m.work.title,status:'incomplete-one-to-one'});continue;}
  const ns=pairs.map(a=>m.work.notes[a.candidateIndex]),ratios=q.slice(1).map((e,j)=>(ns[j+1].onset-ns[j].onset)/(e.o-q[j].o)).filter(n=>n>0&&Number.isFinite(n)),scale=median(ratios),offset=median(ns.map((n,j)=>n.pitchMidi-q[j].p));
  const pitchResidual=Math.max(...ns.map((n,j)=>Math.abs(n.pitchMidi-q[j].p-offset))),onsetResidual=Math.max(...ns.map((n,j)=>Math.abs((n.onset-ns[0].onset)/scale-(q[j].o-q[0].o)))),durationResidual=Math.max(...ns.map((n,j)=>Math.abs(n.durationRatio/scale-q[j].d)));
  rows.push({caseId:c.caseId,rank:i+1,title:m.work.title,sourceId:m.work.sourceId,scale,offset,pitchResidual,onsetResidual,durationResidual,status:pitchResidual<1e-6&&onsetResidual<=1/64&&durationResidual<=1/64?'passes-audit':'exact-label-needs-review'});
 }
}
const result={schema:'musicanote-strict-exact-audit/v1',generatedAt:new Date().toISOString(),toleranceInQueryBeats:1/64,scope:'Diagnostic of default Exact labels, not exact-option regression or human relevance judgment; median tempo normalization and explicit attack duration.',checked:rows.length,flagged:rows.filter(r=>r.status!=='passes-audit').length,rows};
writeFileSync(dir+'/strict-exact-audit.json',JSON.stringify(result,null,2));console.log(JSON.stringify({checked:result.checked,flagged:result.flagged}));
