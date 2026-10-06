import type {CorpusNote} from '../types';
import type {PillarCandidate} from './pillarCandidates';
export type PhraseGapLedger={runId:string;engineVersion:string;streamId:string;inputRevision:string;sourceRevision:string;completeRuleCount:number;tracedCueCount:number;unmappedCueCount:number;
 observations:{key:string;index:number;field:string;present:boolean;value:unknown}[];
 records:{boundaryIndex:number;ruleId:string;complete:boolean;observationRefs:string[];selectionObservationRefs:string[]}[]};
export type GapComparison={noteId:string;measure:number;beat:number;status:'compared'|'unverified';shared:string[];outsideGapScope:string[];message:string};
async function sha(text:string){return [...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(text)))].map(v=>v.toString(16).padStart(2,'0')).join('');}
/** Compare observations only within the traced observed-gap rule, never score votes. */
export async function comparePillarGaps(notes:CorpusNote[],candidates:PillarCandidate[],ledger:PhraseGapLedger|undefined,xml:string,streamId:string):Promise<GapComparison[]>{
 const gaps=candidates.filter(c=>c.evidence.some(e=>e.ruleId==='following-gap'));
 if(!gaps.length)return [];
 const valid=ledger&&ledger.streamId===streamId&&ledger.inputRevision===await sha(JSON.stringify({notes,streamId}))&&ledger.sourceRevision===await sha(xml);
 return gaps.map(c=>{
  const base={noteId:c.note.id,measure:c.note.measure,beat:c.note.beat};
  const unknown=(message:string):GapComparison=>({...base,status:'unverified',shared:[],outsideGapScope:[],message});
  if(!valid)return unknown('입력/악보 revision 또는 성부 확인 불가');
  const record=ledger.records.find(r=>r.boundaryIndex===c.index+1&&r.ruleId==='observed-gap');
  if(!record?.complete)return unknown('같은 위치의 프레이즈 쉼 규칙 전체 추적 없음');
  const used=new Set([...record.observationRefs,...record.selectionObservationRefs]);
  const observations=new Map(ledger.observations.map(o=>[o.key,o]));
  if([...used].some(key=>!observations.has(key)))return unknown('프레이즈 관찰 참조 누락');
  const required=new Set<string>();
  const add=(index:number,field:string)=>required.add(`${ledger.inputRevision}:note:${index}:${field}`);
  add(c.index,'onset');add(c.index+1,'onset');add(c.index,'durationRatio');
  for(let i=Math.max(0,c.index-4);i<Math.min(notes.length,c.index+5);i++)add(i,'durationRatio');
  return {...base,status:'compared' as const,shared:[...required].filter(k=>used.has(k)),outsideGapScope:[...required].filter(k=>!used.has(k)),
   message:'쉼 규칙끼리의 관찰 비교만 완료. 범위 밖 관찰은 전체 프레이즈의 새 증거로 인정하지 않음.'};
 });
}
