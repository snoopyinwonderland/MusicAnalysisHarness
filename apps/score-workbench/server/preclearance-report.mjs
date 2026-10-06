import {toMEI} from '../src/music/mei.ts';
import {sourceAnchors,comparePassages,aggregatePhraseEvidence} from './preclearance-musical-evidence.mjs';
export const REPORT_VERSION='musicanote-copyright-infringement-report/2';
export const htmlEscape=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const values=[4,3,2,1.5,1,.75,.5,.375,.25,.1875,.125,.0625];
function writtenValue(duration){
 if(Math.abs(duration-.375)<1e-6)return {durationRatio:duration,writtenDuration:.25,reportDots:1};
 if(Math.abs(duration-.1875)<1e-6)return {durationRatio:duration,writtenDuration:.125,reportDots:1};
 const exact=values.find(v=>Math.abs(v-duration)<1e-6);if(exact)return {durationRatio:duration};
 const writtenDuration=[.0625,.125,.25,.5,1,2,4].find(v=>v>=duration)??4,ratio=duration/writtenDuration;
 let denominator=1;while(denominator<192&&Math.abs(ratio*denominator-Math.round(ratio*denominator))>1e-4)denominator++;
 return {durationRatio:duration,writtenDuration,actualNotes:denominator,normalNotes:Math.round(ratio*denominator),tuplet:true};
}
/** Comparison transcription. Local bar numbers are not source engraving coordinates. */
export function comparisonNotation(events,meter,prefix,highlightIds=[]){
 const parsed=String(meter??'4/4').split('/').map(Number),length=parsed[0]*4/parsed[1];
 if(!Number.isFinite(length)||length<=0)throw new Error('Invalid comparison meter');
 let time=0,index=0;const output=[],red=[],highlight=new Set(highlightIds);
 for(const event of events){let remaining=Number(event.durationRatio);if(!Number.isFinite(remaining)||remaining<=0)throw new Error('Invalid report duration');
  const chunks=[];while(remaining>1e-6){const offset=time%length,room=length-offset;let part=Math.min(remaining,room<1e-6?length:room);
   if(Math.abs(part*16-Math.round(part*16))<1e-5&&!values.some(v=>Math.abs(v-part)<1e-6))part=values.find(v=>v<=part)??part;
   const id=`${prefix}-n${index++}`;
   const value=writtenValue(part),note={...event,...value,id,measure:Math.floor((time+1e-6)/length)+1};
   if(value.tuplet)note.tupletGroup=id;
   if(highlight.has(event.id))red.push(id);chunks.push(note);output.push(note);remaining-=part;time+=part;
   if(output.length>512)throw new Error('Comparison notation exceeds safety limit');
  }
  if(chunks.length>1&&event.kind==='note')chunks.forEach(n=>n.tieGroup=`${prefix}-tie${index}`);
 }
 let mei=toMEI({version:1,mode:'melody_rhythm',meter,events:output});
 for(const n of output.filter(n=>n.reportDots))mei=mei.replace(new RegExp(`(<(?:note|rest) xml:id="${n.id}"[^>]*)(/>)`),`$1 dots="1"$2`);
 return {mei,redIds:red};
}
export function candidateEvents(snapshot,ids){
 const set=new Set(ids),notes=snapshot.events.filter(e=>set.has(e.id)).sort((a,b)=>a.onset-b.onset);if(notes.length!==set.size)throw new Error('Candidate snapshot references missing');
 const out=[];let cursor=notes[0]?.onset??0;
 for(const n of notes){if(n.onset>cursor+1e-6)out.push({id:'rest-'+n.id,kind:'rest',pitchMidi:null,durationRatio:n.onset-cursor});out.push({...n});cursor=Math.max(cursor,n.onset+n.durationRatio)}
 return out;
}
export function reportModel(input,snapshots,{excludedCanonicalWorkId=null}={}){
 const tasks=new Map(input.runs.map(r=>[r.taskId,r.selection.task]));
 const querySnapshot=snapshots.get(input.snapshotId),anchorCache=new Map();
 const anchors=s=>{if(!s)return [];if(!anchorCache.has(s.snapshotId))anchorCache.set(s.snapshotId,sourceAnchors(s).anchors);return anchorCache.get(s.snapshotId)};
 const excluded=input.works.filter(w=>excludedCanonicalWorkId&&w.canonicalWorkId===excludedCanonicalWorkId||querySnapshot&&w.matches.every(m=>m.sourceId===querySnapshot.identity.sourceId||m.workId===querySnapshot.identity.workId));
 return {schema:REPORT_VERSION,title:'Copyright Infringement Report',createdAt:new Date().toISOString(),sourceSnapshotId:input.snapshotId,
  analysisDependencies:input.dependencies,searchStatus:input.status,structureStatus:input.structureEnrichment?.status??'unknown',
  calibrated:false,legalDetermination:'not-performed',jurisdiction:'not-specified',
  disclosure:'음악적 유사성과 구조 근거를 제공하는 검토용 초안입니다. 침해 확률·법률 판정·이용 허락을 의미하지 않습니다. 권리 상태와 창작 경위·접근 가능성·관할법은 별도 확인이 필요합니다.',
  limitations:['기존 보존 스냅샷으로 만든 오프라인 초안이며 업로드 운영 기능은 아직 연결되지 않았습니다.',
   '악보는 논리 음표·음가의 비교용 재기보입니다. 마디 번호·빔·쉼표 묶음·타이 표기는 원본 판면과 다를 수 있습니다. 원본 위치는 별도 좌표를 확인하세요.',
   '중요도 비중은 해당 성부 스냅샷 기준이며 작품 전체나 전문가 Schenker 분석이 아닙니다.',
   '모든 corpus 검색 결과를 나열한 것이 아니라 선택 Query 및 검색 상한 안의 보존 결과입니다.',
   '75년 경과나 표시용 accessPolicy만으로 권리 만료를 판정하지 않았습니다. 원작/편곡/판본/녹음은 별개입니다.'],
  selfExclusion:{canonicalWorkId:excludedCanonicalWorkId,excluded:excluded.map(w=>({key:w.key,title:w.title,reason:'verified-upload-identity'})),titleOnlyMatching:false},
  works:input.works.filter(w=>!excluded.includes(w)).map(w=>{
   const chosen=w.priorityAssessment?.representativeMatchIndex??0;
   return {key:w.key,title:w.title,artist:w.artist,canonicalWorkId:w.canonicalWorkId,editions:w.editions,editionCount:w.editionCount,
    similarity:w.similarity,coverage:w.coverage,reviewScore:w.priorityAssessment?.score??null,reviewRank:input.priorityReview?.ranking.find(r=>r.key===w.key)?.reviewRank??null,
    corpusReviewScore:input.corpusPriorityReview?.ranking.find(r=>r.key===w.key)?.score??null,representativeMatchIndex:chosen,
    phraseEvidence:querySnapshot?aggregatePhraseEvidence(querySnapshot,w.matches):null,
    rights:{composition:'unknown',arrangement:'unknown',edition:'unknown',recording:'not-assessed'},
    matches:w.matches.map((m,index)=>{
     const task=tasks.get(m.taskId),snapshot=snapshots.get(m.candidateImportance?.snapshotId);
     let candidate=[],warning=null;try{if(snapshot)candidate=candidateEvents(snapshot,m.candidateImportance.eventIds);else warning='Candidate structure snapshot unavailable';}catch(e){warning=e.message}
     const queryIds=new Set(task?.query.events.map(n=>n.id)),candidateIds=new Set(candidate.map(n=>n.id));
     const musicalEvidence=comparePassages(task?.query.events??[],candidate,{queryAnchors:anchors(querySnapshot).filter(n=>queryIds.has(n.eventId)),candidateAnchors:anchors(snapshot).filter(n=>candidateIds.has(n.eventId))});
     return {...m,index,musicalEvidence,queryEvents:task?.query.events??[],queryMeter:task?.query.meter??'4/4',candidateEvents:candidate,
      candidateMeter:candidate.find(n=>n.kind==='note')?.meter??snapshot?.meter??'4/4',notationWarning:warning};
    })};
  })};
}
