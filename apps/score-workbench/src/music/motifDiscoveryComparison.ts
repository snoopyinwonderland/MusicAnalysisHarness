import type {CorpusNote} from '../types';
import type {MotifSpanMarker} from '../components/FullXmlNotation';
// Pure note/token module: no filesystem/Node APIs in the browser.
// @ts-expect-error The upstream comparison module is plain JavaScript.
import {linkMotifSpanFamilies} from '../../server/motif-discovery.mjs';
export function compareMotifFamilies(work:any,spans:MotifSpanMarker[]){
 const discovery=work?.motifDiscovery,notes:CorpusNote[]=work?.notes||[];
 if(!discovery||discovery.status!=='ready')return {spans,error:discovery?.error||discovery?.skipped||null};
 const bound=discovery.eventBindings;
 if(discovery.provenance?.workId!==work.workId||discovery.provenance?.streamId!==work.streamId||discovery.provenance?.sourceId!==work.sourceId
  ||bound?.length!==notes.length||notes.some((n,i)=>bound[i].id!==n.id||bound[i].onset!==n.onset||bound[i].durationRatio!==n.durationRatio||bound[i].pitchMidi!==n.pitchMidi||bound[i].spelling!==(n.spelling??null)))
  return {spans,error:'source-or-event-snapshot-mismatch'};
 return {spans:linkMotifSpanFamilies(notes,spans,discovery),error:null};
}
export function motifFamilyDisplaySpans(spans:any[],enabled:boolean){
 return enabled?spans.map(s=>({...s,label:'비교 F'+s.linkedFamily+' · '+s.label})):spans;
}
