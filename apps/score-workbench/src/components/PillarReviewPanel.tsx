import {useEffect,useMemo,useState} from 'react';
import type {CorpusNote} from '../types';
import {pillarCandidates,type PillarHarmonyEvidence,type PillarMeter,type PillarPhraseStart} from '../music/pillarCandidates';
import {selectPillarView,type PillarView} from '../music/pillarView';
import {composePillarDisplay} from '../music/pillarDisplay';
import {groupPillarEvidence} from '../music/pillarEvidence';
import {comparePillarGaps,type GapComparison,type PhraseGapLedger} from '../music/pillarGapAudit';

export function PillarReviewPanel({notes,xml,streamId,harmonyEvidence,phraseStarts,phraseLedger}:{notes:CorpusNote[];xml:string;streamId:string;harmonyEvidence?:PillarHarmonyEvidence[];phraseStarts?:PillarPhraseStart[];phraseLedger?:PhraseGapLedger}){
 const [enabled,setEnabled]=useState(false),[mapped,setMapped]=useState(0);
 const [view,setView]=useState<PillarView>('surface');
 const meters=useMemo(()=>{
  const doc=new DOMParser().parseFromString(xml,'application/xml');
  const part=[...doc.getElementsByTagName('part')].find(p=>p.getAttribute('id')===streamId.split(':')[0]);
  const result:Record<number,PillarMeter>={};let current:PillarMeter|undefined;
  for(const [i,m] of [...(part?.children??[])].filter(e=>e.tagName==='measure').entries()){
   const times=[...m.getElementsByTagName('time')];
   if(times.length){const t=times[0],b=t.getElementsByTagName('beats'),u=t.getElementsByTagName('beat-type');
    current=times.length===1&&b.length===1&&u.length===1&&/^\d+$/.test(b[0].textContent??'')?{count:Number(b[0].textContent),unit:Number(u[0].textContent)}:undefined;
   }
   if(current)result[i+1]=current;
  }return result;
 },[xml,streamId]);
 const independentCandidates=useMemo(()=>pillarCandidates(notes,{harmonyEvidence,meters}),[notes,harmonyEvidence,meters]);
 const [gapAudit,setGapAudit]=useState<GapComparison[]>([]);
 useEffect(()=>{let live=true;setGapAudit([]);comparePillarGaps(notes,independentCandidates,phraseLedger,xml,streamId).then(value=>{if(live)setGapAudit(value);}).catch(()=>{if(live)setGapAudit([]);});return()=>{live=false;};},[notes,independentCandidates,phraseLedger,xml,streamId]);
 const allCandidates=useMemo(()=>composePillarDisplay(notes,independentCandidates,phraseStarts),[notes,independentCandidates,phraseStarts]);
 const candidates=useMemo(()=>selectPillarView(allCandidates,view),[allCandidates,view]);
 const noteById=useMemo(()=>new Map(notes.map(n=>[n.id,n])),[notes]);
 useEffect(()=>{
  if(!enabled){setMapped(0);return;}
  const doc=new DOMParser().parseFromString(xml,'application/xml');
  const all=[...doc.getElementsByTagName('note')],globalIndex=new Map(all.map((n,i)=>[n,i]));
  const [partId,staff,voice]=streamId.split(':');
  const part=[...doc.getElementsByTagName('part')].find(p=>p.getAttribute('id')===partId);
  const targets=new Map<string,{color:string;label:string}>();let divisions=1;
  for(const [mi,measure] of [...(part?.children??[])].filter(e=>e.tagName==='measure').entries()){
   let cursor=0,last=0;
   const div=measure.getElementsByTagName('divisions')[0]?.textContent;if(div)divisions=Number(div);
   for(const el of [...measure.children]){
    const text=(tag:string)=>el.getElementsByTagName(tag)[0]?.textContent;
    const d=Number(text('duration')??0)/divisions;
    if(el.tagName==='backup'){cursor-=d;continue;}if(el.tagName==='forward'){cursor+=d;continue;}if(el.tagName!=='note')continue;
    const chord=!!el.getElementsByTagName('chord').length,onset=chord?last:cursor;
    if(!chord){last=cursor;if(!el.getElementsByTagName('grace').length)cursor+=d;}
    const pc:Record<string,number>={C:0,D:2,E:4,F:5,G:7,A:9,B:11};
    const pitch=pc[text('step')??'']+Number(text('alter')??0)+(Number(text('octave'))+1)*12;
    if((text('staff')??'1')!==staff||(text('voice')??'1')!==voice)continue;
    const c=candidates.find(c=>(c.note.measureOrdinal??c.note.measure)===mi+1&&Math.abs(c.note.beat-1-onset)<1e-6&&c.note.pitchMidi===pitch);
    if(c)targets.set(String(globalIndex.get(el)),{color:c.origin==='phrase-hint-only'?'#7651ad':c.level==='combined'?'#087f8c':'#b56a00',label:`${c.origin==='phrase-hint-only'?'시작음 표시 힌트':'독립 기둥 후보'} · ${c.reasons.join(' / ')}${c.phraseHints.length?` · Phrase ${c.phraseHints.map(h=>h.phraseNumber).join(', ')} 시작 (표시용)` : ''} · 화성 미검증`});
   }
  }
  const host=document.querySelector('.score-main .xml-score');if(!host)return;
  const cleanups:(()=>void)[]=[];
  const paint=()=>{
   while(cleanups.length)cleanups.pop()!();let count=0;
   for(const el of host.querySelectorAll<SVGElement>('g.note[id]')){
    const target=targets.get(el.getAttribute('data-source-note-index')??'');if(!target)continue;count++;
    const old=el.getAttribute('style');el.style.setProperty('fill',target.color,'important');el.style.setProperty('color',target.color,'important');
    const title=document.createElementNS('http://www.w3.org/2000/svg','title');title.textContent=target.label;el.appendChild(title);
    cleanups.push(()=>{if(old===null)el.removeAttribute('style');else el.setAttribute('style',old);title.remove();});
   }
   setMapped(count);
  };
  const observer=new MutationObserver(()=>{observer.disconnect();paint();observer.observe(host,{childList:true,subtree:true});});
  paint();observer.observe(host,{childList:true,subtree:true});
  return()=>{observer.disconnect();while(cleanups.length)cleanups.pop()!();};
 },[enabled,candidates,xml,streamId]);
 return <section className="analysis-block">
  <h3>기둥음 후보 · 실험</h3>
  <button type="button" aria-pressed={enabled} onClick={()=>setEnabled(v=>!v)}>{enabled?'Hide Pillar Highlights':'Highlight Pillar Notes'}</button>
  <p><label>기둥음 보기 <select aria-label="기둥음 보기" value={view} onChange={e=>setView(e.target.value as PillarView)}>
   <option value="surface">전체 기둥 후보</option>
   <option value="shared">반복 공통 골격 후보</option>
  </select></label></p>
  <p>{view==='shared'?'전체 후보 중 반복·변형 대응 근거가 있는 음만 표시합니다. 깊은 구조음으로 확정한 것이 아니며, 한 번만 등장하는 중요한 음은 제외될 수 있습니다.':'박 단위 지속·진입·왕복·반복 근거를 모은 전체 후보입니다.'}</p>
  <p>청록·황토: 독립 후보의 근거 등급 · 보라: 프레이즈 시작으로만 추가한 표시 힌트. 시작 힌트는 독립 등급을 올리지 않습니다. 독립은 프레이즈 입력 없이 계산했다는 뜻이며 정확성을 보장하지 않습니다.</p>
  <p>독립 후보 {independentCandidates.length}개 · 시작 힌트로만 추가 {allCandidates.filter(c=>c.origin==='phrase-hint-only').length}개.</p>
  <p>전체 {allCandidates.length}개 중 현재 보기 후보 {candidates.length}개 · 현재 렌더링된 표시 {mapped}개. 지연 로딩된 페이지는 표시 수가 달라집니다.</p>
  {!candidates.length&&<p>이 보기에 해당하는 후보가 없습니다. 중요 음이 없다는 뜻은 아닙니다.</p>}
  <p>원본·Phrase·Motif 경계는 유지합니다. 화성적 연장·Urlinie 분석은 아직 하지 않습니다.</p>
  <p>프레이즈 사용 근거와의 중복 확인 미완료 — 경계 판단에 재사용하지 않습니다. 아래 근거 묶음 수는 독립 증거 수나 신뢰확률이 아닙니다.</p>
  {phraseLedger&&<details><summary>프레이즈 근거 연결 상태</summary><p>실제 분석 기록: {phraseLedger.engineVersion}</p><p>단일 쉼 규칙 추적 {phraseLedger.completeRuleCount??0}개 · 일부 추적 {phraseLedger.tracedCueCount}개 · 규칙 출처 미연결 {phraseLedger.unmappedCueCount}개. 최종 경계의 전체 판단 경로 검증 완료가 아닙니다.</p><p>실행 참조: {phraseLedger.runId}</p></details>}
  <details><summary>쉼 근거 중복 검토 · {gapAudit.filter(a=>a.status==='compared').length}개 비교 / {gapAudit.filter(a=>a.status==='unverified').length}개 확인 불가</summary><p>중복 관찰은 새 근거로 세지 않습니다. 비교 범위 밖 관찰도 전체 프레이즈에서는 사용됐을 수 있어 가산하지 않습니다.</p>{!gapAudit.length&&<p>비교 결과가 아직 없거나 대상 쉼 근거가 없습니다.</p>}<ul>{gapAudit.map(a=><li key={a.noteId}>{a.measure}마디 {a.beat}박 — {a.status==='compared'?`기존 쉼 근거와 중복 ${a.shared.length}개 · 추가 관찰(비교 범위 밖) ${a.outsideGapScope.length}개`:'확인 불가'} · {a.message}</li>)}</ul></details>
  <details><summary>후보별 근거</summary><ul>{candidates.map(c=><li key={c.index}>
   {c.note.measure}마디 {c.note.beat}박 {c.note.spelling} — {c.origin==='independent'?'독립 후보':'시작음 표시 힌트만'} · {c.reasons.join(' / ')}
   {c.phraseHints.length>0&&<span> · Phrase {c.phraseHints.map(h=>h.phraseNumber).join(', ')} 시작 (표시용·독립 등급에 미반영)</span>}
   {c.evidence.length>0&&<details><summary>근거 출처 · {groupPillarEvidence(c.evidence).length}개 묶음 (중복 확인 전)</summary><ul>{groupPillarEvidence(c.evidence).map(g=><li key={g.family}>{({timing:'음가·시간',metric:'박 위치',melodic:'선율 관계',recurrence:'반복 대응'})[g.family]} — {g.rules.map(e=>`${e.label} [${e.ruleId}]`).join(' / ')}</li>)}</ul><p>규칙 버전: pillar-evidence-0.1 · 입력 주변음 참조만 기록된 상태이며 원본 revision 및 전체 부모 근거 감사는 아직 연결되지 않았습니다.</p></details>}
   {c.correspondences.length>0&&<details><summary>대응 음 {c.correspondences.length}개 보기</summary><ul>{c.correspondences.map(e=>{
    const other=noteById.get(e.otherNoteId);
    return <li key={e.otherNoteId}>{other?`${other.measure}마디 ${other.beat}박 ${other.spelling??''}`:e.otherNoteId} · 조옮김 {e.transposition>0?'+':''}{e.transposition}반음 · 대응 구간 시간 배율 {Number(e.timeScale.toFixed(3))}배 · {e.ruleVersion}</li>;
   })}</ul></details>}
  </li>)}</ul></details>
 </section>;
}
