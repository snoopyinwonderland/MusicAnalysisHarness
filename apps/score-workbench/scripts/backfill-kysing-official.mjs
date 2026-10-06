import { existsSync } from 'node:fs';
import { mkdir, readFile, readdir, open, rename, unlink } from 'node:fs/promises';
import { resolve } from 'node:path';

const metadataPath=resolve(process.argv[2]||'data/kysing-metadata/kumyoung-2026-09-03-all.json');
const xmlRoot=resolve(process.argv[3]||'U:/KYSing_MusicXML');
const outputDir=resolve(process.argv[4]||'data/kysing-metadata');
const limit=Math.max(1,Number(process.env.KYSING_BACKFILL_LIMIT)||100),delay=Math.max(750,Number(process.env.KYSING_BACKFILL_DELAY_MS)||1500);
const retryToday=process.env.KYSING_RETRY_TODAY==='1';
await mkdir(outputDir,{recursive:true});
const lockPath=resolve(outputDir,'official-backfill.lock');
const lock=await open(lockPath,'wx');
try {
const snapshot=JSON.parse(await readFile(metadataPath,'utf8')),known=new Set(snapshot.songs.map(song=>String(Number(song.no))));
const pending=(await readdir(xmlRoot)).filter(name=>/^\d+\.xml$/i.test(name)).map(name=>String(Number(name.replace(/\.xml$/i,'')))).filter(number=>!known.has(number)).sort((a,b)=>Number(a)-Number(b));
await mkdir(outputDir,{recursive:true});
const dataPath=resolve(outputDir,'kumyoung-official-backfill.json'),statePath=resolve(outputDir,'kumyoung-official-backfill-state.json');
const records=existsSync(dataPath)?JSON.parse(await readFile(dataPath,'utf8')):{},state=existsSync(statePath)?JSON.parse(await readFile(statePath,'utf8')):{cursor:0,totalRequests:0};
const decode=value=>String(value||'').replace(/&amp;/g,'&').replace(/&quot;/g,'"').replace(/&#0?39;/g,"'").replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&nbsp;/g,' ').trim();
const visibleText=html=>String(html).replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi,' ').replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi,' ').replace(/<[^>]+>/g,' ').replace(/\s+/g,' ');
const parse=(html,number)=>{for(const chunk of html.split('search_chart_num">').slice(1)){const no=chunk.match(/^\s*(\d+)/)?.[1];if(no!==number)continue;return{brand:'kumyoung',no,title:decode(chunk.match(/<span title="([^"]*)"\s+class="tit">/)?.[1]),singer:decode(chunk.match(/<span title="([^"]*)"\s+class="tit mo-art">/)?.[1]),source:'https://kysing.kr/search/',verifiedAt:new Date().toISOString()}}return null};
const transientStorageError=error=>['UNKNOWN','EBUSY','EPERM','EACCES'].includes(error?.code)||/unknown error.*(?:open|rename)/i.test(String(error?.message||''));
const storageDetails=(error,phase,path,attempt)=>({phase,path,attempt,code:error?.code||'UNKNOWN',errno:error?.errno??null,syscall:error?.syscall||null,message:error?.message||String(error),at:new Date().toISOString()});
const wait=ms=>new Promise(done=>setTimeout(done,ms));
const atomicWrite=async(path,content,phase)=>{
 let lastError;
 for(let attempt=1;attempt<=3;attempt++){
  const tempPath=`${path}.${process.pid}.${Date.now()}.${Math.random().toString(16).slice(2)}.tmp`;
  let handle;
  try{
   handle=await open(tempPath,'wx');
   await handle.writeFile(content,'utf8');
   await handle.sync();
   await handle.close();handle=null;
   await rename(tempPath,path);
   return;
  }catch(error){
   lastError=Object.assign(error,{storage:storageDetails(error,phase,path,attempt)});
   if(handle)await handle.close().catch(()=>{});
   await unlink(tempPath).catch(()=>{});
   if(!transientStorageError(error)||attempt===3)throw lastError;
   await wait(125*2**(attempt-1));
  }
 }
 throw lastError;
};
const stateContent=()=>JSON.stringify({...state,pending:pending.length,updatedAt:new Date().toISOString()},null,2);
const saveState=phase=>atomicWrite(statePath,stateContent(),phase);
const saveDataAndState=async phase=>{try{await atomicWrite(dataPath,JSON.stringify(records),'data');await saveState(phase)}catch(error){state.lastError=error.storage||storageDetails(error,phase,dataPath,1);try{await saveState('record-storage-error')}catch(stateError){console.error(JSON.stringify({storageError:state.lastError,stateSaveError:stateError.storage||storageDetails(stateError,'record-storage-error',statePath,1)}))}throw error}};
let attempted=0,found=0;
const dateOf=value=>new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Seoul'}).format(new Date(value));
const today=dateOf(Date.now());
if(state.koreanDate!==today){state.dailyRequests=state.updatedAt&&dateOf(state.updatedAt)===today?100:0;state.koreanDate=today;}
state.outcomes??={};
for(;state.cursor<pending.length&&state.dailyRequests<Math.min(100,limit)&&(!state.lastError?.at||dateOf(state.lastError.at)!==today||retryToday);state.cursor++){
 const number=pending[state.cursor],url=`https://kysing.kr/search/?category=1&keyword=${encodeURIComponent(number)}`;
 if(records[number]?.title)continue;
 if(state.outcomes[number]?.date===today&&!retryToday)continue;
 state.dailyRequests++;state.totalRequests++;attempted++;await saveState('before-request');
 try{const response=await fetch(url,{signal:AbortSignal.timeout(30000),headers:{accept:'text/html','accept-language':'ko','user-agent':'MUSICANOTE metadata verifier/1.0'}});if(!response.ok)throw new Error(`HTTP ${response.status}`);const html=await response.text();if(/captcha|access denied|too many requests/i.test(visibleText(html)))throw new Error('Possible block page');const item=parse(html,number);if(item?.title){item.source=url;records[number]=item;found++}state.outcomes[number]={date:today,status:item?.title?'matched':'not-found',retryable:!item?.title};state.lastError=null;}
 catch(error){state.lastError={number,message:error.message,at:new Date().toISOString()};state.outcomes[number]={date:today,status:'error',retryable:true,message:error.message};await saveDataAndState('fetch-error');break;}
 await saveDataAndState('after-outcome');if(state.cursor+1<pending.length&&state.dailyRequests<Math.min(100,limit))await new Promise(resolve=>setTimeout(resolve,delay));
}
await saveDataAndState('final');console.log(JSON.stringify({attempted,found,cursor:state.cursor,pending:pending.length,totalCollected:Object.keys(records).length,dataPath,statePath},null,2));
} finally {await lock.close();await unlink(lockPath);}
