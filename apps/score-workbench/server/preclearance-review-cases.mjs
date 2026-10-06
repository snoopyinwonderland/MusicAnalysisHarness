import {structureHash} from './structure-analysis-adapter.mjs';
export function patternClass(notes){
 const d=notes.slice(1).map((n,i)=>n.pitchMidi-notes[i].pitchMidi);
 if(d.length!==7)return null;
 if(d.filter(x=>x===0).length>=4)return 'repeated-note';
 if(d.every(x=>Math.abs(x)>=1&&Math.abs(x)<=2))return 'stepwise';
 if(d.filter(x=>[3,4,5].includes(Math.abs(x))).length>=5)return 'arpeggio-like';
 if(d.some(x=>Math.abs(x)>=7)&&new Set(d).size>=4)return 'mixed-leaps';
 return null;
}
export function buildReviewCases(snapshots){
 const groups=Object.fromEntries(['repeated-note','stepwise','arpeggio-like','mixed-leaps'].map(k=>[k,[]]));
 for(const snapshot of [...snapshots].sort((a,b)=>a.identity.sourceId.localeCompare(b.identity.sourceId)||a.snapshotId.localeCompare(b.snapshotId))){
  const notes=snapshot.events.filter(n=>n.kind!=='rest'&&!n.tieStop&&n.isAttack!==false);
  for(let i=0;i+8<=notes.length;i++){
   const focus=notes.slice(i,i+8),category=patternClass(focus);
   const diversityKey=snapshot.diversityKey??snapshot.identity.sourceId;
   if(!category||groups[category].length>=3||groups[category].some(c=>c.diversityKey===diversityKey))continue;
   if(focus.some(n=>!Number.isFinite(n.onset)||!Number.isFinite(n.durationRatio)||n.durationRatio<=0))continue;
   const meter=focus[0].meter??snapshot.meter;if(!meter||focus.some(n=>n.meter&&n.meter!==meter))continue;
   const events=[];let cursor=focus[0].onset;
   for(const n of focus){if(n.onset>cursor+1e-6)events.push({id:`gap-${n.id}`,kind:'rest',pitchMidi:null,durationRatio:n.onset-cursor});
    events.push({id:n.id,kind:'note',pitchMidi:n.pitchMidi,spelling:n.spelling,durationRatio:n.durationRatio});cursor=n.onset+n.durationRatio;}
   // Reject overlaps: sequential Query must preserve source timing.
   if(focus.some((n,j)=>j&&n.onset<focus[j-1].onset+focus[j-1].durationRatio-1e-6))continue;
   const index=groups[category].length,variant=['source','single-semitone','octave-transposition'][index];
   if(variant==='single-semitone'){const n=events.filter(e=>e.kind==='note')[4];n.pitchMidi+=n.pitchMidi<127?1:-1;delete n.spelling;}
   if(variant==='octave-transposition')for(const n of events.filter(e=>e.kind==='note')){n.pitchMidi+=Math.max(...focus.map(e=>e.pitchMidi))<=115?12:-12;delete n.spelling;}
   const firstOrdinal=focus[0].measureOrdinal,lastOrdinal=focus.at(-1).measureOrdinal;
   const hasMeasures=Number.isFinite(firstOrdinal)&&Number.isFinite(lastOrdinal);
   const context=hasMeasures?snapshot.events.filter(e=>e.measureOrdinal>=firstOrdinal-2&&e.measureOrdinal<=lastOrdinal+2):notes.slice(Math.max(0,i-8),i+16);
   const caseId='PC-REVIEW-'+structureHash({snapshot:snapshot.snapshotId,ids:focus.map(n=>n.id),variant}).slice(0,12);
   groups[category].push({caseId,category,variant,diversityKey,sourceId:snapshot.identity.sourceId,workId:snapshot.identity.workId,streamId:snapshot.identity.streamId,
    snapshotId:snapshot.snapshotId,query:{version:1,mode:'melody_rhythm',meter,startsOnDownbeat:false,includeRests:true,events},
    sourceFocus:focus,context,contextPolicy:hasMeasures?'up-to-two-ordinal-measures-before-and-after':'eight-attacks-before-and-after',
    reconstruction:'logical-event snapshot, not original MusicXML layout',
    knowledgeBase:{classification:{phenomenonTypes:[category,variant],confidence:'automatic-unreviewed'},ruleLearning:{candidateRules:[],counterexamples:[]}},
    humanReview:{status:'unreviewed',reviewer:null,sourceShouldBeRetrieved:null,preferredCandidateIds:[],rankingReason:null,musicalFunction:null}});
  }
 }
 return {schema:'musicanote-preclearance-review-suite/1',selection:'deterministic first eligible per category and distinct source within category; not a random population sample',
  requestedPerCategory:3,counts:Object.fromEntries(Object.entries(groups).map(([k,v])=>[k,v.length])),cases:[0,1,2].flatMap(i=>Object.values(groups).map(g=>g[i]).filter(Boolean))};
}
