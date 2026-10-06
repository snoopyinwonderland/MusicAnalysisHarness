// Optional comparison layer. This is a source-bound indexed observation snapshot,
// NOT a fabricated Canonical IR document or a replacement for legacy analysis.
import {createHash} from 'node:crypto';
import {analyzePhraseLayers} from './phrase-breath-layer.mjs';
export const PHRASE_LAYER_CONTRACT='phrase-layer-comparison/1';
export const PHRASE_LAYER_UPSTREAM='650ca3b472be5ac546b77ce91b9d3064e74f6135';
const hash=v=>createHash('sha256').update(typeof v==='string'?v:JSON.stringify(v)).digest('hex');
export const phraseLayersEnabled=value=>String(value??'')==='1';

/** Exact decimal representation of an indexed Number, not reconstructed XML divisions. */
export function indexedQuarter(value){
 if(!Number.isFinite(value))throw new Error('Finite indexed quarter required');
 const [mantissa,exponent='0']=String(value).toLowerCase().split('e');
 const places=(mantissa.split('.')[1]??'').length-Number(exponent);
 let num=BigInt(mantissa.replace('.','')),den=1n;
 if(places>=0)den=10n**BigInt(places);else num*=10n**BigInt(-places);
 let a=num<0n?-num:num,b=den;while(b){[a,b]=[b,a%b];}
 return {num:String(num/a),den:String(den/a)};
}

export function bindPhraseLayerRanges(result,notes,provenance){
 for(const layer of ['breath','phrases']){
  const data=result[layer];if(!data)continue;
  const starts=[0,...new Set(data.starts.filter(i=>Number.isInteger(i)&&i>0&&i<notes.length))].sort((a,b)=>a-b);
  data.boundaries=data.boundaries.map(b=>({...b,startEventId:notes[b.index]?.id,
   previousEventId:notes[b.index-1]?.id,globalQuarter:indexedQuarter(notes[b.index].onset)}));
  data.ranges=notes.length?starts.map((startIndex,k)=>{
   const endIndexExclusive=starts[k+1]??notes.length,first=notes[startIndex],last=notes[endIndexExclusive-1];
   const start=first.onset,end=notes[endIndexExclusive]?.onset??last.onset+last.durationRatio;
   return {rangeId:`plspan_${hash([provenance.cacheKey,layer,first.id,last.id,start,end]).slice(0,24)}`,
    startIndex,endIndexExclusive,startEventId:first.id,endEventId:last.id,
    eventIds:notes.slice(startIndex,endIndexExclusive).map(n=>n.id),
    span:{start:indexedQuarter(start),end:indexedQuarter(end),convention:'[start,end)',unit:'quarter',
     precision:'indexed-float-decimal-not-source-rational'},
    startMeasure:first.measure,endMeasure:last.measure,
    cadence:data.boundaries.find(b=>b.index===endIndexExclusive)?.cadence??null};
  }):[];
 }
 return result;
}

/** Bounded cache; all musical inputs and code revisions participate, returns defensive copies. */
export function createPhraseLayerComparison({engineRevision,harmonyRevision,capacity=32,analyze=analyzePhraseLayers}={}){
 if(!engineRevision||!harmonyRevision)throw new Error('Pinned engine and harmony revisions required');
 if(!Number.isInteger(capacity)||capacity<1)throw new Error('Positive cache capacity required');
 const entries=new Map();
 return function compare({notes,identity,sourceSha,renderSourceSha,key=null,cadenceAt,cadenceMinStrength=0.58}){
  const t=performance.now();
  if(!sourceSha||!identity?.streamId||!identity?.sourceId||!identity?.workId)throw new Error('Source identity required');
  if(notes.some(n=>!n.id)||new Set(notes.map(n=>n.id)).size!==notes.length)throw new Error('Unique indexed event IDs required');
  if(!Number.isFinite(cadenceMinStrength)||cadenceMinStrength<0||cadenceMinStrength>1)throw new Error('Valid cadence gate required');
  if(notes.some(n=>!Number.isFinite(n.onset)||!Number.isFinite(n.durationRatio)||n.durationRatio<0))throw new Error('Invalid indexed onset/duration');
  const observationSha=hash(notes);
  const cacheKey=hash({contract:PHRASE_LAYER_CONTRACT,identity,sourceSha,renderSourceSha,observationSha,
   engineRevision,harmonyRevision,key,cadenceMinStrength,policy:'selected-upper-stream/no-upper-to-harmony'});
  const hit=entries.has(cacheKey);
  if(hit){const value=entries.get(cacheKey);entries.delete(cacheKey);entries.set(cacheKey,value);
   return {...structuredClone(value),runtime:{cacheHit:true,durationMs:performance.now()-t}};}
  const provenance={contract:PHRASE_LAYER_CONTRACT,upstreamCommit:PHRASE_LAYER_UPSTREAM,...identity,
   sourceSha256:sourceSha,renderSourceSha256:renderSourceSha,observationSha256:observationSha,
   observationDocumentId:`indexed_observation_${observationSha}`,canonicalIrDocumentId:null,
   alignmentStatus:'indexed-events-not-revalidated-against-xml',
   eventIdNamespace:'MusicSearch indexed logical attacks; source+snapshot bound, not Canonical note IDs',
   engineRevision,harmonyRevision,cacheKey,cadenceMinStrength,confidenceSemantics:'uncalibrated gate, not probability'};
  const result=bindPhraseLayerRanges({...analyze(notes,{key,cadenceAt,cadenceMinStrength}),provenance},notes,provenance);
  result.cadenceSource='legacy boundary-harmony, all score streams, neutral gap cue; read-only';
  entries.set(cacheKey,structuredClone(result));while(entries.size>capacity)entries.delete(entries.keys().next().value);
  return {...structuredClone(result),runtime:{cacheHit:false,durationMs:performance.now()-t}};
 };
}
