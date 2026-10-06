// Additive, source-bound research comparison; no legacy span selection here.
import {createHash} from 'node:crypto';
import {discoverMotifs} from './motif-discovery.mjs';
import {indexedQuarter} from './phrase-layer-integration.mjs';
export const MOTIF_DISCOVERY_CONTRACT='motif-family-comparison/1';
export const MOTIF_DISCOVERY_UPSTREAM='81df315959c2bd0e893bdc4119fe3213f71884e2';
export const motifDiscoveryEnabled=value=>String(value??'')==='1';
const hash=v=>createHash('sha256').update(JSON.stringify(v)).digest('hex');
export function createMotifDiscoveryComparison({engineRevision,capacity=16,maxInputNotes=4096,analyze=discoverMotifs}={}){
 if(!engineRevision||!Number.isInteger(capacity)||capacity<1||!Number.isInteger(maxInputNotes)||maxInputNotes<8)throw new Error('Pinned revision and positive limits required');
 const entries=new Map();
 return function compare({notes,identity,sourceSha,renderSourceSha}){
  const started=performance.now();
  if(!sourceSha||!renderSourceSha||!identity?.workId||!identity?.streamId||!identity?.sourceId)throw new Error('Source identity required');
  if(!Array.isArray(notes)||notes.some(n=>!n.id)||new Set(notes.map(n=>n.id)).size!==notes.length)throw new Error('Unique indexed event IDs required');
  const observationSha=hash(notes),cacheKey=hash({contract:MOTIF_DISCOVERY_CONTRACT,engineRevision,identity,sourceSha,renderSourceSha,observationSha,maxInputNotes});
  if(entries.has(cacheKey)){const value=entries.get(cacheKey);entries.delete(cacheKey);entries.set(cacheKey,value);return {...structuredClone(value),runtime:{cacheHit:true,durationMs:performance.now()-started}};}
  const provenance={contract:MOTIF_DISCOVERY_CONTRACT,upstreamCommit:MOTIF_DISCOVERY_UPSTREAM,...identity,sourceSha256:sourceSha,renderSourceSha256:renderSourceSha,observationSha256:observationSha,engineRevision,cacheKey,
   canonicalIrDocumentId:null,alignmentStatus:'indexed-events-not-revalidated-against-xml',confidenceSemantics:'experimental family links, not probability'};
  let skipped=null;
  if(notes.length>maxInputNotes)skipped='input-note-budget-exceeded';
  else if(notes.some((n,i)=>!Number.isFinite(n.onset)||!Number.isFinite(n.durationRatio)||n.durationRatio<0||!Number.isFinite(n.pitchMidi)||(i>0&&n.onset<=notes[i-1].onset)))skipped='invalid-or-nonmonophonic-timeline';
  else if(notes.some(n=>!/^([1-9]\d*)\/([1-9]\d*)$/.test(String(n.meter||''))))skipped='meter-missing';
  // Upstream maxBars uses the first bar duration. Do not misrepresent changing metre as supported.
  else if(new Set(notes.map(n=>n.meter)).size>1)skipped='meter-change-not-yet-supported';
  const discovery=skipped?{families:[],skipped}:analyze(notes);
  const result={...discovery,contract:MOTIF_DISCOVERY_CONTRACT,status:discovery.skipped?'skipped':'ready',provenance,
   eventBindings:notes.map(n=>({id:n.id,onset:n.onset,durationRatio:n.durationRatio,pitchMidi:n.pitchMidi,spelling:n.spelling??null})),
   families:discovery.families.map(f=>({...f,occurrences:f.occurrences.map(o=>({...o,
    occurrenceId:`mdocc_${hash([cacheKey,f.id,o.startIndex,o.endIndex]).slice(0,24)}`,
    startEventId:notes[o.startIndex].id,endEventId:notes[o.endIndex].id,eventIds:notes.slice(o.startIndex,o.endIndex+1).map(n=>n.id),
    span:{start:indexedQuarter(o.start),end:indexedQuarter(o.end),unit:'quarter',convention:'[start,end)',precision:'indexed-float-decimal-not-source-rational'}}))}))};
  entries.set(cacheKey,structuredClone(result));while(entries.size>capacity)entries.delete(entries.keys().next().value);
  return {...structuredClone(result),runtime:{cacheHit:false,durationMs:performance.now()-started}};
 };
}
