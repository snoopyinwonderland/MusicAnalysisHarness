// Conservative offline policy, not a cadence classifier or permission to merge.
export function sourceMeterTimeline(xml,partId){
 const part=[...xml.matchAll(/<part\b[^>]*\bid=["']([^"']+)["'][^>]*>([\s\S]*?)<\/part>/g)].find(m=>m[1]===partId);
 if(!part)return [];
 let meter=null;
 return [...part[2].matchAll(/<measure\b[^>]*?\/>|<measure\b[^>]*>([\s\S]*?)<\/measure>/g)].map((m,i)=>{
  m[1]??='';
  const times=[...m[1].matchAll(/<time\b([^>]*)>([\s\S]*?)<\/time>/g)];
  if(times.length){
   const t=times[0],beats=[...t[2].matchAll(/<beats>([^<]+)<\/beats>/g)],units=[...t[2].matchAll(/<beat-type>([^<]+)<\/beat-type>/g)];
   const firstNote=m[1].search(/<(?:note|forward|backup)\b/);
   meter=times.length===1&&!/\bnumber=/.test(t[1])&&(firstNote<0||t.index<firstNote)&&beats.length===1&&units.length===1&&/^\d+$/.test(beats[0][1])?{count:Number(beats[0][1]),unit:Number(units[0][1])}:null;
  }
  return {measureOrdinal:i+1,meter:meter?{...meter}:null};
 });
}
export function reviewClosureInMeter(closure,evidence,timeline){
 const unknown=reason=>({status:'unknown',reason,decision:'cannot_judge'});
 if(closure.status!=='observed'||!closure.durationMatches||!closure.gapMatches)return unknown('source-disagreement');
 const first=evidence.observed.find(n=>n.id===closure.sourceNoteIds[0]);
 const nextId=evidence.mappings.find(m=>m.eventId===closure.nextEventId)?.sourceEventId;
 const next=evidence.observed.find(n=>n.id===nextId);
 if(!first||!next)return unknown('missing-source-reference');
 const meters=timeline.filter(t=>t.measureOrdinal>=first.source.measureOrdinal&&t.measureOrdinal<=next.source.measureOrdinal);
 if(meters.length!==next.source.measureOrdinal-first.source.measureOrdinal+1||meters.some(t=>!t.meter))return unknown('missing-or-unsupported-meter');
 const {count,unit}=meters[0].meter;
 if(meters.some(t=>t.meter.count!==count||t.meter.unit!==unit))return unknown('meter-change-across-closure');
 const compound=[6,9,12].includes(count)&&unit===8;
 const beatQuarter=compound?1.5:([2,3,4].includes(count)&&[2,4,8].includes(unit)?4/unit:null);
 if(!beatQuarter)return unknown('unsupported-beat-grouping');
 const durationBeats=closure.sourceDuration/beatQuarter,restBeats=closure.explicitRestDuration/beatQuarter;
 const reasons=[];
 if(closure.breathSymbols.length)reasons.push('notated-breath');
 if(restBeats>=4)reasons.push('long-rest');
 if(durationBeats>=2&&restBeats>=2)reasons.push('sustained-arrival-and-rest');
 return {status:'normalized',meter:{count,unit},beatQuarter,beatConvention:compound?'compound-dotted-quarter':'denominator-beat',durationBeats,restBeats,
  decision:reasons.length?'protect-boundary':'cannot_judge',reasons,policy:'existing-v1.14-protection-shadow',
  limitation:'No protection is not merge approval; conventional beat grouping is not inferred performed pulse'};
}
