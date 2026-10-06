import {readFileSync,writeFileSync} from 'node:fs';
import {structureHash} from '../server/structure-analysis-adapter.mjs';
const [input,output]=process.argv.slice(2);if(!input||!output)throw new Error('input report and NEW output required');
const original=JSON.parse(readFileSync(input,'utf8'));writeFileSync(output,'[]',{flag:'wx'});
process.env.MUSICANOTE_PROFILE_SEARCH='1';
const {searchDatabase}=await import('../server/search-api.mjs');const rows=[];
const digest=result=>structureHash({exact:result.exact,similar:result.similar});
for(const [i,run] of original.runs.entries()){
 const row={task:i+1,variants:[]};
 for(const mode of ['0','1','1']){
  process.env.MUSICANOTE_RETRIEVAL_CACHE=mode;const start=performance.now(),result=searchDatabase(run.query,30);
  row.variants.push({cache:mode,elapsedMs:performance.now()-start,digest:digest(result),profile:result.profile});
 }
 row.identical=new Set(row.variants.map(v=>v.digest)).size===1;rows.push(row);writeFileSync(output,JSON.stringify(rows,null,2));console.log(JSON.stringify({task:row.task,identical:row.identical,times:row.variants.map(v=>Math.round(v.elapsedMs))}));
 if(!row.identical)throw new Error('Cache changed results');
}
