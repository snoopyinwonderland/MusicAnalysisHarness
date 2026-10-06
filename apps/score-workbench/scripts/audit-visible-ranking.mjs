import {readFileSync,readdirSync,writeFileSync,mkdirSync} from 'node:fs';
import {calibratedResultRanking} from '../server/search-api.mjs';
const dir='evaluation/runs/structural-baseline-v1',rows=[];
for(const file of readdirSync(dir).filter(x=>/^S100-.*\.json$/.test(x))){
 const run=JSON.parse(readFileSync(`${dir}/${file}`));if(!run.result)continue;
 const all=[...run.result.exact,...run.result.similar];
 const target=run.sourceRank?all[run.sourceRank-1]?.work.sourceId:null;
 const revised=all.map(x=>({...x,newScore:calibratedResultRanking(x.kind==='exact',x.localSimilarity,x.scores,run.query.mode,0,true)})).sort((a,b)=>b.newScore-a.newScore);
 rows.push({caseId:run.caseId,oldSourceRank:run.sourceRank,newSourceRank:target?revised.findIndex(x=>x.work.sourceId===target)+1:null,top:revised.slice(0,3).map(x=>({title:x.work.title,source:x.work.sourceId,oldScore:x.ranking,newScore:x.newScore}))});
}
const report={limitation:'Saved returned candidates only; hidden final adjustment unavailable, set to zero. Not a full retrieval rerun.',count:rows.length,improved:rows.filter(x=>x.newSourceRank&&x.newSourceRank<x.oldSourceRank).length,worsened:rows.filter(x=>x.newSourceRank>x.oldSourceRank).length,oldTop5:rows.filter(x=>x.oldSourceRank&&x.oldSourceRank<=5).length,newTop5:rows.filter(x=>x.newSourceRank&&x.newSourceRank<=5).length,rows};
mkdirSync('evaluation/reports/visible-ranking-v1',{recursive:true});writeFileSync('evaluation/reports/visible-ranking-v1/replay.json',JSON.stringify(report,null,2));console.log(JSON.stringify({...report,rows:undefined}));
