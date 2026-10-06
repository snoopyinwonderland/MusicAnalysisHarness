import {readFileSync} from 'node:fs';
import {spawn} from 'node:child_process';
const batch=process.argv[2]||'omission-holdout';
const suite=`evaluation/reports/${batch}-v1/suite.json`;
const prerequisite=process.argv[3]||'structural-next40-omission-v1';
const started=Date.now();
// Sequential to avoid two full-DB workers competing for memory and distorting timing.
while(true){let remaining;try{remaining=JSON.parse(readFileSync(`evaluation/runs/${prerequisite}/summary.json`)).remaining}catch{}
 if(remaining===0)break;if(Date.now()-started>7200000)throw Error('Prerequisite experiment did not complete');await new Promise(r=>setTimeout(r,15000));}
for(const enabled of [false,true]){
 const env={...process.env,MUSICANOTE_SINGLE_OMISSION:enabled?'1':'0'},dir=`evaluation/runs/${batch}-${enabled?'enabled':'baseline'}-v1`;
 await new Promise((resolve,reject)=>{const child=spawn(process.execPath,['scripts/run-structural-next40.mjs',suite,dir],{env,stdio:'inherit',windowsHide:true});child.on('error',reject);child.on('exit',code=>code===0?resolve():reject(Error('Runner failed '+code)))});
}
