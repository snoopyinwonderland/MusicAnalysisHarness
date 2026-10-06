import {existsSync,readFileSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
const batch='short-query-90-v1',dir='evaluation/runs/'+batch;
let ready=false;
for(let i=0;i<360;i++){
 if(existsSync(dir+'/summary.json')&&JSON.parse(readFileSync(dir+'/summary.json')).remaining===0&&existsSync(dir+'/retry-summary.json')){ready=true;break;}
 await new Promise(r=>setTimeout(r,15000));
}
if(!ready)throw Error('Search/retry did not finish; no final report claimed');
for(const [script,args]of [['report-memory-variation.mjs',[batch]],['audit-short-exact-results.mjs',[]],['review-short-query-results.mjs',[]],['package-memory-variation.mjs',[batch]],['audit-evaluation-bundle.mjs',[batch]]]){
 const result=spawnSync(process.execPath,['scripts/'+script,...args],{encoding:'utf8',maxBuffer:8*1024*1024});
 process.stdout.write(result.stdout??'');process.stderr.write(result.stderr??'');if(result.status!==0)throw Error(script+' failed');
}
console.log('Final short-query report and case bundle completed.');
