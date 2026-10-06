import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {DatabaseSync} from 'node:sqlite';

const API='https://www.googleapis.com/youtube/v3';
const inventoryPath=process.env.MUSIC_ANALYSIS_INVENTORY||'K:/Music Analysis/output/corpus_inventory.json';
const cachePath=path.resolve('data/youtube-matches.json');
const statePath=path.resolve('data/youtube-backfill-state.json');
const searchDbPath=path.resolve('data/search-index-v2/search.sqlite');
const validationVersion=2;
const maxDaily=Math.min(100,Math.max(1,Number(process.env.YOUTUBE_DAILY_SEARCH_LIMIT||100)));
const watch=process.argv.includes('--watch');
const priorityAt=process.argv.indexOf('--priority-title');
const priorityTitle=priorityAt>=0?process.argv[priorityAt+1]?.trim():'';
const priorityWorkAt=process.argv.indexOf('--priority-work-id');
const priorityWorkId=priorityWorkAt>=0?process.argv[priorityWorkAt+1]?.trim():'';
const priorityComposerAt=process.argv.indexOf('--priority-composer');
const priorityComposer=priorityComposerAt>=0?process.argv[priorityComposerAt+1]?.trim():'';
const rejectAt=process.argv.indexOf('--reject-video-id');
const rejectedVideoId=rejectAt>=0?process.argv[rejectAt+1]?.trim():'';
const arrangement=/\b(?:piano\s+(?:solo|duet|trio|quartet|quintet)|melody|violin|viola|cello|contrabass|duet|trio|quartet|string\s+orchestra)\b/gi;
export const normalizeWorkTitle=name=>path.basename(name).replace(/\.musicxml(?:\.xml)?$|\.xml$/i,'').replace(/^\s*\d+\.\s+/,'').replace(arrangement,' ').replace(/[,_]+/g,' ').replace(/\s+/g,' ').trim().replace(/\s+(?:and|&)\s*$/i,'').trim();
const keyFor=title=>normalizeWorkTitle(title).toLocaleLowerCase('en-US');
const streamOrder=streamId=>{const [part='P9999',staff='9999',voice='9999']=String(streamId||'').split(':'),number=value=>Number(String(value).replace(/^\D+/,''))||9999;return [number(part),number(staff),number(voice),String(streamId)]};
const compareStream=(left,right)=>{const a=streamOrder(left),b=streamOrder(right);for(let index=0;index<a.length;index++){if(a[index]<b[index])return-1;if(a[index]>b[index])return 1}return 0};
const indexedWorks=()=>{
 if(!fs.existsSync(searchDbPath))return[];
 const db=new DatabaseSync(searchDbPath,{readOnly:true});db.exec('PRAGMA query_only=ON');
 try{const rows=db.prepare('SELECT id,title,composer,source,stream_id FROM works ORDER BY source').all(),primary=new Map();for(const row of rows){const prior=primary.get(row.source);if(!prior||compareStream(row.stream_id,prior.stream_id)<0)primary.set(row.source,row)}return[...primary.values()].map(row=>[row.id,normalizeWorkTitle(row.title),normalizeComposer(row.composer),row.id,row.source])}finally{db.close()}
};
const pacificDate=()=>new Intl.DateTimeFormat('en-CA',{timeZone:'America/Los_Angeles',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
const load=(file,fallback)=>fs.existsSync(file)?JSON.parse(fs.readFileSync(file,'utf8')):fallback;
const transientStorageError=error=>['UNKNOWN','EBUSY','EPERM','EACCES'].includes(error?.code)||/unknown error.*(?:open|rename)/i.test(String(error?.message||''));
const storageDetails=(error,phase,file,attempt)=>({phase,file,attempt,code:error?.code||'UNKNOWN',errno:error?.errno??null,syscall:error?.syscall||null,message:error?.message||String(error),at:new Date().toISOString()});
const pause=milliseconds=>Atomics.wait(new Int32Array(new SharedArrayBuffer(4)),0,0,milliseconds);
const save=(file,value,phase='checkpoint')=>{
 const content=JSON.stringify(value,null,2)+'\n';let lastError;
 for(let attempt=1;attempt<=3;attempt++){
  const temp=`${file}.${process.pid}.${Date.now()}.${Math.random().toString(16).slice(2)}.tmp`;let fd;
  try{fd=fs.openSync(temp,'wx');fs.writeFileSync(fd,content,'utf8');fs.fsyncSync(fd);fs.closeSync(fd);fd=null;fs.renameSync(temp,file);return}
  catch(error){lastError=Object.assign(error,{storage:storageDetails(error,phase,file,attempt)});if(fd!==undefined)try{fs.closeSync(fd)}catch{};try{fs.unlinkSync(temp)}catch{};if(!transientStorageError(error)||attempt===3)throw lastError;pause(125*2**(attempt-1))}
 }
 throw lastError;
};
const api=async(endpoint,params)=>{params.set('key',process.env.YOUTUBE_API_KEY);const response=await fetch(`${API}/${endpoint}?${params}`);if(!response.ok)throw new Error(`${endpoint} ${response.status}: ${(await response.text()).slice(0,300)}`);return response.json()};
const tokens=s=>new Set(s.toLowerCase().replace(/[^\p{L}\p{N}]+/gu,' ').trim().split(/\s+/).filter(Boolean));
// A highly viewed, embeddable video is not evidence that it belongs to this work.
// Keep only title terms that identify a work before scoring the API's candidates.
const titleStopWords=new Set(['a','an','and','at','by','for','from','in','of','on','or','the','to','with','official','video','music','audio','lyrics','lyric','mv','hd','4k','no','number','op','opus']);
const identifyingTokens=value=>new Set([...tokens(value)].filter(token=>!titleStopWords.has(token)));
const composerStopWords=new Set(['arranged','arranger','arr','composed','composer','composition','lyrics','lyric','music','words','written','performed','performance','by','and','the','unknown']);
export const normalizeComposer=value=>String(value||'').split(/\r?\n/).find(line=>/composed\s+by/i.test(line))?.replace(/^.*?composed\s+by\s*/i,'').trim()||String(value||'').split(/\r?\n/)[0]?.replace(/^.*?(?:composer|music)\s*(?:by)?\s*[:：-]?\s*/i,'').trim()||'';
export const arrangementIdentity=(title,composer)=>`${keyFor(title)}\u0000${normalizeComposer(composer).toLocaleLowerCase('en-US').replace(/\s+/g,' ').trim()}`;
const composerTokens=value=>new Set([...tokens(normalizeComposer(value))].filter(token=>!composerStopWords.has(token)&&!/^(?:18|19|20)\d{2}$/.test(token)));
export const titleRelevance=(work,videoTitle)=>{
 const expected=identifyingTokens(work),actual=identifyingTokens(videoTitle),matched=[...expected].filter(token=>actual.has(token)).length;
 const coverage=matched/Math.max(1,expected.size);
 // Short titles are especially vulnerable to false positives: require every
 // identifying word. For longer titles, one non-essential article/subtitle can differ.
 const minimumCoverage=expected.size<=2?1:.75;
 return {matched,expected:expected.size,coverage,accepted:matched>0&&coverage>=minimumCoverage};
};
export const composerRelevance=(composer,...candidateText)=>{
 const expected=composerTokens(composer);if(!expected.size)return {matched:0,expected:0,coverage:1,accepted:true,required:false};
 const actual=tokens(candidateText.join(' ')),matchedTokens=[...expected].filter(token=>actual.has(token)),coverage=matchedTokens.length/expected.size,last=[...expected].at(-1);
 return {matched:matchedTokens.length,expected:expected.size,coverage,accepted:matchedTokens.length>0&&(actual.has(last)||coverage>=.5),required:true};
};
export const candidateRelevance=(work,composer,videoTitle,...creatorEvidence)=>{const title=titleRelevance(work,videoTitle),creator=composerRelevance(composer,videoTitle,...creatorEvidence);return {title,composer:creator,accepted:title.accepted&&creator.accepted}};
const spamVideoTitle=/#(?:shorts?|shortvideo|funnyvideo|viral|trending|subscribers?)\b|viralhog|finger\s*dance|tutting/iu;
const musicEvidence=/\b(?:official|music|audio|lyrics?|song|soundtrack|ost|topic|vevo|piano|orchestra|quartet|concerto|sonata|symphony|performed?|performance)\b/iu;
const durationSeconds=value=>{const match=String(value||'').match(/^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$/);return match?Number(match[1]||0)*3600+Number(match[2]||0)*60+Number(match[3]||0):0};
export const candidateEligibility=(work,composer,video)=>{
 const text=`${video?.snippet?.title||''} ${video?.snippet?.channelTitle||''} ${video?.snippet?.description||''}`,relevance=candidateRelevance(work,composer,video?.snippet?.title||'',video?.snippet?.channelTitle||'',video?.snippet?.description||''),creatorRequired=composerTokens(composer).size>0,seconds=durationSeconds(video?.contentDetails?.duration);
 const accepted=relevance.title.accepted&&!spamVideoTitle.test(video?.snippet?.title||'')&&seconds>=90&&(creatorRequired?relevance.composer.accepted:musicEvidence.test(text));
 return {...relevance,accepted,seconds,creatorRequired};
};
const titleScore=(work,composer,video)=>{const relevance=candidateRelevance(work,composer,video.snippet.title,video.snippet.channelTitle);const official=/official|topic|vevo|soundtrack|ost/i.test(`${video.snippet.title} ${video.snippet.channelTitle}`)?.16:0;return relevance.title.coverage+relevance.composer.coverage*.65+official+Math.log10(Number(video.statistics.viewCount||0)+1)/100};

async function searchRepresentative(title,composer='',rejectedIds=new Set()){
  const creator=normalizeComposer(composer),query=`${title}${creator?` ${creator}`:''} official music`;
  const found=await api('search',new URLSearchParams({part:'snippet',q:query,type:'video',maxResults:'10',order:'viewCount',videoEmbeddable:'true',videoSyndicated:'true',safeSearch:'moderate'}));
  const ids=found.items.map(x=>x.id.videoId).filter(Boolean);if(!ids.length)return null;
  const details=await api('videos',new URLSearchParams({part:'snippet,status,statistics,contentDetails',id:ids.join(',')}));
  const eligible=details.items.filter(v=>!rejectedIds.has(v.id)&&v.status?.embeddable===true&&v.status?.privacyStatus==='public'&&!v.contentDetails?.regionRestriction?.blocked?.includes('KR')&&(!v.contentDetails?.regionRestriction?.allowed||v.contentDetails.regionRestriction.allowed.includes('KR'))&&candidateEligibility(title,creator,v).accepted);
  eligible.sort((a,b)=>titleScore(title,creator,b)-titleScore(title,creator,a));const best=eligible[0];if(!best)return null;
  const relevance=candidateRelevance(title,creator,best.snippet.title,best.snippet.channelTitle,best.snippet.description||''),eligibility=candidateEligibility(title,creator,best);
  return {videoId:best.id,url:`https://www.youtube.com/watch?v=${best.id}`,title:best.snippet.title,channelTitle:best.snippet.channelTitle,viewCount:Number(best.statistics.viewCount||0),durationSeconds:eligibility.seconds,embeddable:true,validationVersion,titleMatchCoverage:relevance.title.coverage,titleMatchTerms:`${relevance.title.matched}/${relevance.title.expected}`,composer:creator||null,composerVerified:relevance.composer.accepted,composerMatchCoverage:relevance.composer.coverage,composerMatchTerms:`${relevance.composer.matched}/${relevance.composer.expected}`,selectedAt:new Date().toISOString(),query};
}

function quarantineUnverifiedCache(){
 const cache=load(cachePath,{schemaVersion:validationVersion,updatedAt:null,rejectedVideoIds:[],works:{}}),matched=Object.values(cache.works||{}).filter(item=>item?.videoId).length,dir=path.resolve('data/youtube-quarantine');fs.mkdirSync(dir,{recursive:true});
 const stamp=new Date().toISOString().replace(/[:.]/g,'-'),archive=path.join(dir,`youtube-matches-${stamp}.json`);save(archive,cache,'quarantine-cache');
 save(cachePath,{schemaVersion:validationVersion,updatedAt:new Date().toISOString(),rejectedVideoIds:[...new Set(cache.rejectedVideoIds||[])],works:{}},'reset-cache');
 const state=load(statePath,{pacificDate:null,searchCalls:0,cursor:0});state.cursor=0;save(statePath,state,'reset-cursor');
 console.log(`Quarantined ${matched} cached matches to ${archive}; active cache reset.`);
}

function auditCachedTitleMatches(cache){
 let removed=0;
 for(const [key,item] of Object.entries(cache.works||{})){
  if(!item?.videoId||!item?.title)continue;
  const relevance=candidateRelevance(item.normalizedTitle||key,item.composer||'',item.title,item.channelTitle||'');
  if(relevance.title.accepted&&(item.composerVerified===true||relevance.composer.accepted))continue;
  cache.works[key]={normalizedTitle:item.normalizedTitle||key,titleKey:item.titleKey||key,videoId:null,reason:'automatic-title-mismatch',previousVideoId:item.videoId,lastAttemptPacificDate:null};
  removed++;
 }
 return removed;
}

async function runOnce(){
  const inventory=load(inventoryPath,{files:[]});const cache=load(cachePath,{schemaVersion:1,updatedAt:null,rejectedVideoIds:[],works:{}});cache.rejectedVideoIds=[...new Set(cache.rejectedVideoIds||[])];
  if(process.argv.includes('--audit-cache')){const removed=auditCachedTitleMatches(cache);save(cachePath,{...cache,updatedAt:new Date().toISOString()},'audit-cache');console.log(`YouTube title audit: removed ${removed} automatic mismatches.`);return}
  if(!process.env.YOUTUBE_API_KEY){console.log('YOUTUBE_API_KEY is not set; no API calls were made.');return}
  if(rejectedVideoId){cache.rejectedVideoIds=[...new Set([...cache.rejectedVideoIds,rejectedVideoId])];for(const [key,item] of Object.entries(cache.works)){if(item?.videoId!==rejectedVideoId)continue;cache.works[key]={normalizedTitle:item.normalizedTitle||key,titleKey:item.titleKey||key,videoId:null,reason:'manually-rejected-not-embeddable',rejectedVideoId,lastAttemptPacificDate:null}}}
  const rejectedIds=new Set(cache.rejectedVideoIds);let state=load(statePath,{pacificDate:null,searchCalls:0,cursor:0});const today=pacificDate();if(state.pacificDate!==today)state={pacificDate:today,searchCalls:0,cursor:state.cursor||0};
  const databaseWorks=indexedWorks(),inventoryWorks=databaseWorks.length?databaseWorks:[...new Map(inventory.files.filter(f=>!f.duplicate_of&&!f.excluded_reason).map(f=>{const title=normalizeWorkTitle(f.relative_path);return[keyFor(title),[keyFor(title),title,'','','']]})).values()],priority=priorityTitle?[priorityWorkId||keyFor(priorityTitle),normalizeWorkTitle(priorityTitle),priorityComposer,priorityWorkId,'']:null,works=priority?[priority,...inventoryWorks.filter(([key])=>key!==priority[0])]:inventoryWorks;
  const sharedByArrangement=new Map();
  for(const [cachedKey,item] of Object.entries(cache.works||{})){
    if(!item)continue;
    const reusableVideo=item.videoId&&item.validationVersion===validationVersion;
    const reusableNoMatch=!item.videoId&&item.reason==='no-embeddable-title-composer-result'&&item.lastAttemptPacificDate===today;
    if(reusableVideo||reusableNoMatch)sharedByArrangement.set(arrangementIdentity(item.normalizedTitle||cachedKey,item.composer||''),item);
  }
  const persist=phase=>{try{save(statePath,state,`${phase}:state`);save(cachePath,{...cache,updatedAt:new Date().toISOString()},`${phase}:cache`);return true}catch(error){const detail=error.storage||storageDetails(error,phase,'unknown',1);state.lastError={at:new Date().toISOString(),message:detail.message,storage:detail};console.error(`Storage checkpoint ${phase} failed: ${detail.code} ${detail.message}`);try{save(statePath,state,'record-storage-error:state')}catch(stateError){console.error(JSON.stringify({storageError:detail,stateSaveError:stateError.storage||storageDetails(stateError,'record-storage-error',statePath,1)}))}return false}};
  const transientRateLimit=/rateLimitExceeded|Search Queries per minute/i.test(state.lastError?.message||'');
  if(state.exhausted||(state.lastError&&!transientRateLimit)){console.log('Prior non-transient error in current Pacific day; no retry.');return}
  if(transientRateLimit)state.lastError=null;
  let handled=0;while(state.searchCalls<maxDaily&&handled<works.length){const selected=priority&&handled===0?priority:works[state.cursor%works.length];const [key,title,composer,workId,sourceId]=selected;if(!(priority&&handled===0))state.cursor=(state.cursor+1)%works.length;handled++;const prior=cache.works[key];if(prior?.videoId||prior?.lastAttemptPacificDate===today)continue;
    const identity=arrangementIdentity(title,composer),shared=sharedByArrangement.get(identity);
    if(shared){cache.works[key]={...shared,normalizedTitle:title,titleKey:key,...(workId?{workId}:{}),...(sourceId?{sourceId}:{}),...(composer?{composer:normalizeComposer(composer)}:{}),arrangementShared:true,lastAttemptPacificDate:today};console.log(`reused ${title}${composer?` / ${normalizeComposer(composer)}`:''}: ${shared.videoId||'no match'}`);if(!persist('after-shared-outcome'))break;continue}
    state.searchCalls++;if(!persist('before-request'))break;
    try{const match=await searchRepresentative(title,composer,rejectedIds);cache.works[key]={normalizedTitle:title,titleKey:key,...(workId?{workId}:{}),...(sourceId?{sourceId}:{}),...(composer?{composer:normalizeComposer(composer)}:{}),...(match||{videoId:null,reason:'no-embeddable-title-composer-result'}),arrangementShared:true,lastAttemptPacificDate:today};sharedByArrangement.set(identity,cache.works[key]);state.lastError=null;console.log(`${state.searchCalls}/${maxDaily} ${title}${composer?` / ${normalizeComposer(composer)}`:''}: ${match?.videoId||'no match'}`)}catch(error){state.lastError={at:new Date().toISOString(),message:error.message};if(/quotaExceeded|dailyLimitExceeded/i.test(error.message))state.exhausted=true;console.error(`${title}: ${error.message}`);break}save(statePath,state);save(cachePath,{...cache,updatedAt:new Date().toISOString()});
    if(!persist('after-outcome'))break;
  }
  persist('final');console.log(`Backfill complete: ${state.searchCalls}/${maxDaily} search calls for ${today} PT.`)
}

async function lockedRun(){
 const lockPath=path.resolve('data/youtube-backfill.lock');let fd;
 try{fd=fs.openSync(lockPath,'wx')}catch(e){if(e.code==='EEXIST'){console.log('YouTube collection already locked; no requests.');return}throw e}
 try{await runOnce()}finally{fs.closeSync(fd);fs.unlinkSync(lockPath)}
}
// Keep the exported scoring helper safe to import from tests or maintenance tools.
// Only a direct script invocation may spend YouTube API quota.
const isDirectInvocation=Boolean(process.argv[1])&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url);
if(isDirectInvocation){
 if(process.argv.includes('--quarantine-unverified')){quarantineUnverifiedCache();process.exit(0)}
 await lockedRun();
 if(watch)setInterval(lockedRun,30*60*1000);
}
