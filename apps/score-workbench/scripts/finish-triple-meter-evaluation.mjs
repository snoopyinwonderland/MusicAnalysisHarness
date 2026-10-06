import {spawnSync} from 'node:child_process';
const batch='triple-meter-60-v1';
for(const script of ['retry-double-ornament-trial.mjs','report-memory-variation.mjs','audit-short-exact-results.mjs','review-short-query-results.mjs','package-memory-variation.mjs','audit-evaluation-bundle.mjs']){
 const r=spawnSync(process.execPath,['scripts/'+script,batch],{stdio:'inherit'});
 if(r.status!==0)throw Error(script+' failed');
}
