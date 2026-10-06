import {createHash} from 'node:crypto';
import {positionedXmlNotes} from './xml-target-verification.mjs';

const tag=(s,name)=>s.match(new RegExp(`<${name}[^>]*>([^<]*)</${name}>`))?.[1]??null;
const attr=(s,name)=>s.match(new RegExp(`\\b${name}=["']([^"']*)["']`))?.[1]??null;
const fraction=(n,d)=>{let a=Math.abs(n),b=d;while(b){[a,b]=[b,a%b]}return {n:n/(a||1),d:d/(a||1)}};

/** Source-linked observation adapter; does NOT infer Phrase, beat grouping or key.
 * IDs are stable for identical source bytes, not guaranteed across XML revisions.
 */
export function notationStructureEvidence(xml,streamId,notes=[]){
 const sourceHash=createHash('sha256').update(xml).digest('hex');
 const [part,staff='1',voice='1']=streamId.split(':');
 const warnings=[];
 const observed=positionedXmlNotes(xml,streamId).filter(n=>n.voice===voice).map(n=>{
  const id=`notation:${sourceHash.slice(0,16)}:${n.start}`;
  const beams=[...n.block.matchAll(/<beam\b([^>]*)>([^<]*)<\/beam>/g)].map(m=>({level:Number(attr(m[1],'number')||1),value:m[2].trim()}));
  const tie=[...n.block.matchAll(/<tie\b([^>]*)(?:\/>|>)/g)].map(m=>attr(m[1],'type'));
  return {id,source:{hash:sourceHash,start:n.start,end:n.end,part,voice:n.voice,staff:n.staff,measureOrdinal:n.measureOrdinal},
   quarterPositionInMeasure:n.beat-1,positionPrecision:'legacy-numeric',kind:n.isRest?'rest':'note',pitchMidi:n.pitchMidi,
   pitch:n.isRest?null:{step:tag(n.block,'step'),alter:tag(n.block,'alter')??'0',octave:tag(n.block,'octave')},
   durationQuarter:fraction(n.durationDivisions,n.divisions),type:tag(n.block,'type'),dots:[...n.block.matchAll(/<dot\b/g)].length,
   grace:n.grace,chord:n.chord,beams,tie,breathSymbols:['fermata','breath-mark','caesura'].filter(t=>new RegExp(`<${t}\\b`).test(n.block))};
 });
 const groups=[],open=new Map();
 for(const n of observed){
  for(const beam of n.beams){
   const key=String(beam.level);
   if(beam.value==='begin'){
    if(open.has(key))warnings.push({code:'unclosed-beam',eventId:n.id});
    const group={id:`beam:${n.id}:${key}`,level:beam.level,eventIds:[n.id],complete:false};groups.push(group);open.set(key,group);
   }else if(['continue','end'].includes(beam.value)){
    const group=open.get(key);
    if(!group)warnings.push({code:'orphan-beam',eventId:n.id});
    else{group.eventIds.push(n.id);if(beam.value==='end'){group.complete=true;open.delete(key)}}
   }else if(!['forward hook','backward hook'].includes(beam.value))warnings.push({code:'unknown-beam-value',eventId:n.id});
  }
 }
 for(const group of open.values())warnings.push({code:'unclosed-beam',groupId:group.id});
 const mappings=notes.map((note,index)=>{
  const candidates=observed.filter(n=>n.kind==='note'&&n.source.staff===staff&&!n.tie.includes('stop')&&n.source.measureOrdinal===Number(note.measureOrdinal??note.measure)&&Math.abs(n.quarterPositionInMeasure-(Number(note.beat)-1))<1e-6&&n.pitchMidi===note.pitchMidi);
  if(candidates.length!==1)warnings.push({code:candidates.length?'ambiguous-mapping':'unmapped-event',index,eventId:note.id});
  return {eventId:note.id,index,sourceEventId:candidates.length===1?candidates[0].id:null,status:candidates.length===1?'mapped':'unresolved'};
 });
 return {schema:'notation-structure-evidence/v0.1',sourceHash,streamId,observed,beamGroups:groups,mappings,warnings,
  limitations:['quarter positions use legacy numeric adapter; mid-measure divisions changes need canonical parser validation','tie marks retained; tie-chain reconstruction and performed duration are not implemented','meter timeline/grouping not inferred','cross-staff source groups retained; selected-stream mapping is staff scoped']};
}
