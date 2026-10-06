import {readFileSync,writeFileSync} from 'node:fs';
import {structureHash} from '../server/structure-analysis-adapter.mjs';
const [input,baseline,output]=process.argv.slice(2);
if(!input||!baseline||!output)throw new Error('original report, baseline and NEW output required');
const original=JSON.parse(readFileSync(input,'utf8')),before=JSON.parse(readFileSync(baseline,'utf8'));
process.env.MUSICANOTE_PROFILE_SEARCH='1';process.env.MUSICANOTE_RETRIEVAL_CACHE='1';
const {searchDatabase}=await import('../server/search-api.mjs');
const report={codeHash:structureHash(readFileSync(new URL('../server/search-api.mjs',import.meta.url),'utf8')),rows:[]};
writeFileSync(output,JSON.stringify(report),{flag:'wx'});
for(const [i,run] of original.runs.entries()){
 const row={task:i+1,variants:[]};
 for(let repeat=0;repeat<2;repeat++){
  const start=performance.now(),result=searchDatabase(run.query,30),digest=structureHash({exact:result.exact,similar:result.similar});
  row.variants.push({elapsedMs:performance.now()-start,digest,profile:result.profile});
 }
 row.identical=row.variants.every(v=>v.digest===before[i].variants[0].digest);report.rows.push(row);
 writeFileSync(output,JSON.stringify(report,null,2));console.log(JSON.stringify({task:row.task,identical:row.identical,times:row.variants.map(v=>Math.round(v.elapsedMs))}));
 if(!row.identical)throw new Error('Final cache changed results');
}
