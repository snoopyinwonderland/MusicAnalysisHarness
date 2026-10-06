import {readFileSync,writeFileSync} from 'node:fs';
import {join} from 'node:path';
import {annotateStructural,prepareQueryNotes,alignLocal,score} from '../server/search-api.mjs';
const [baseline,references,out]=process.argv.slice(2);
if(!out)throw Error('Baseline report, reference streams, NEW output required');
const report=JSON.parse(readFileSync(join(baseline,'search.json'))),refs=JSON.parse(readFileSync(references));
const convert=ns=>ns.map((n,i)=>({id:String(i),kind:'note',pitchMidi:n.p,spelling:n.s,durationRatio:n.d,onset:n.o,beat:n.b,measure:n.mn??n.m,measureOrdinal:n.m}));
const results=report.runs.map(run=>{
 const q=annotateStructural(prepareQueryNotes(run.query.events),run.query.meter,false);
 const matches=refs.map(r=>{const c=annotateStructural(convert(r.notes),'4/4',true),a=alignLocal(q,c,run.query.mode),pairs=a.path.filter(x=>x.queryIndex!==null&&x.candidateIndex!==null),qq=pairs.map(x=>q[x.queryIndex]),cc=pairs.map(x=>c[x.candidateIndex]);
  const qi=q.slice(1).map((n,i)=>n.pitchMidi-q[i].pitchMidi),ci=c.slice(1).map((n,i)=>n.pitchMidi-c[i].pitchMidi);
  const grams=(v,width)=>v.slice(0,Math.max(0,v.length-width+1)).map((_,i)=>v.slice(i,i+width).join(','));
  const shared=Object.fromEntries([['interval3',qi,ci,3],['interval5',qi,ci,5],['contour3',qi.map(Math.sign),ci.map(Math.sign),3]].map(([name,x,y,w])=>{const reference=new Set(grams(y,w));return[name,grams(x,w).filter(g=>reference.has(g)).length]}));
  return {workId:r.id,sourceId:r.source,streamId:r.stream_id,localSimilarity:a.similarity,coverage:a.coverage,scores:score(qq,cc),sharedGrams:shared,
   startMeasure:c[a.start]?.measure,endMeasure:c[a.end]?.measure,alignment:a,queryEvents:q,candidateEvents:c.slice(a.start,a.end+1)};
 }).sort((a,b)=>b.localSimilarity-a.localSimilarity);
 return {taskId:run.taskId,matches};
});
writeFileSync(out,JSON.stringify({schema:'pair-alignment-diagnostic/1',referenceForcedForDiagnosis:true,countsAsRetrievalSuccess:false,candidateMeterAssumption:'4/4; verify reference before interpreting',results},null,2),{flag:'wx'});
for(const r of results)console.log(JSON.stringify({task:r.taskId.slice(0,8),best:r.matches.slice(0,2).map(({queryEvents,candidateEvents,alignment,...x})=>x)}));
