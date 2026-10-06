import {createServer} from 'vite';
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
const server=await createServer({server:{middlewareMode:true},appType:'custom'});
try{
 const {suggestQueries}=await server.ssrLoadModule('/src/search/querySuggestions.ts');
 const rows=[];
 for(const batch of ['double-ornament-trial-v2','double-ornament-trial-v3']){
  const suite=JSON.parse(readFileSync('evaluation/reports/'+batch+'/suite.json'));
  for(const c of suite.cases){
   const run=JSON.parse(readFileSync('evaluation/runs/'+batch+'/'+c.caseId+'.json'));
   const suggestions=suggestQueries(c.query,[...(run.result?.exact??[]),...(run.result?.similar??[])]);
   const original=suite.bases.find(b=>b.baseId===c.baseId).query;
   const signature=q=>JSON.stringify(q.events.map(e=>[e.kind,e.pitchMidi,e.durationRatio]));
   rows.push({batch,caseId:c.caseId,deleted:Number(c.caseId.at(-1)),count:suggestions.length,
    restoresOriginal:suggestions.some(s=>signature(s.query)===signature(original)),suggestions});
  }
 }
 const summary=[0,1,2].map(deleted=>({deleted,cases:rows.filter(r=>r.deleted===deleted).length,
  proposed:rows.filter(r=>r.deleted===deleted&&r.count).length,restoresOriginal:rows.filter(r=>r.deleted===deleted&&r.restoresOriginal).length}));
 const dir='evaluation/reports/query-completion-v1';mkdirSync(dir,{recursive:true});
 writeFileSync(dir+'/replay.json',JSON.stringify({version:1,createdAt:new Date().toISOString(),method:'Replay stored search responses, no new search; not human adjudicated.',summary,rows},null,2));
 console.log(JSON.stringify(summary));
}finally{await server.close()}
