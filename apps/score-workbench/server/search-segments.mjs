import {structureHash} from './structure-analysis-adapter.mjs';
/** Consecutive attacks only: no target-driven reduction and no skipped inner notes. */
export function buildSearchWindows(snapshot,{lengths=[8,12,16,24],maximumWindows=400}={}){
 if(!lengths.length||lengths.some(n=>!Number.isInteger(n)||n<4||n>48)||!Number.isInteger(maximumWindows)||maximumWindows<1)throw Error('Invalid window configuration');
 const attacks=snapshot.events.filter(e=>e.kind!=='rest'&&e.isAttack!==false&&!e.tieStop),windows=[];let total=0;
 // Round-robin lengths prevents a long stream exhausting the budget on one scale.
 const queues=[...new Set(lengths)].map(length=>{const starts=[];for(let i=0;i+length<=attacks.length;i+=Math.max(1,Math.floor(length/2)))starts.push(i);const tail=attacks.length-length;if(tail>=0&&!starts.includes(tail))starts.push(tail);return{length,starts}});
 for(const q of queues)total+=q.starts.length;
 for(let round=0;queues.some(q=>round<q.starts.length);round++)for(const q of queues){if(round>=q.starts.length||windows.length>=maximumWindows)continue;
  const notes=attacks.slice(q.starts[round],q.starts[round]+q.length),first=notes[0],last=notes.at(-1),end=Math.max(...notes.map(n=>n.onset+n.durationRatio));
  const attackEventIds=notes.map(n=>n.id),chosen=new Set(attackEventIds),eventIds=snapshot.events.filter(e=>chosen.has(e.id)||(e.kind==='rest'&&e.onset>=first.onset&&e.onset<end)).map(e=>e.id);
  windows.push({unitId:'window-'+structureHash({snapshotId:snapshot.snapshotId,attackEventIds}).slice(0,24),kind:'window',streamId:snapshot.identity.streamId,
   startEventId:first.id,endEventId:last.id,startQuarter:first.onset,endQuarter:end,eventIds,attackEventIds,phraseIds:[],familyId:null,
   confidence:null,calibrated:false,evidence:{type:'contiguous-overlapping-window',notes:q.length,phraseBoundaryRequired:false},
   location:{startMeasure:first.measure,endMeasure:last.measure,startOrdinal:first.measureOrdinal,endOrdinal:last.measureOrdinal}});
 }
 return {units:windows,totalPossible:total,omittedByBudget:Math.max(0,total-windows.length),fullCoverageGuaranteed:false};
}
