import { useEffect, useMemo, useRef, useState } from 'react';
import type { MatchResult, Query } from '../types';
import { suggestQueries, SUGGESTION_VERSION, type QuerySuggestion } from '../search/querySuggestions';
import { Notation } from './Notation';
import { preloadPlayback, schedulePhrase, type ScheduledPlayback } from '../music/audioPlayback';
import { collapseTies } from '../search/features';
import { usePlaybackSoundChange } from './PlaybackSoundControl';
import './query-suggestions.css';

export function QuerySuggestions({query,results,onApply}:{query:Query;results:MatchResult[];onApply:(q:Query)=>void}){
 const suggestions=useMemo(()=>suggestQueries(query,results),[query,results]);
 const [dismissed,setDismissed]=useState<string[]>([]),[confirmed,setConfirmed]=useState<string[]>([]);
 const playback=useRef<ScheduledPlayback|null>(null);
 useEffect(()=>()=>playback.current?.stop(),[]);
 usePlaybackSoundChange(()=>{playback.current?.stop();playback.current=null});
 useEffect(()=>{playback.current?.stop();playback.current=null;void preloadPlayback('piano').catch(()=>false)},[query]);
 const play=(q:Query)=>{playback.current?.stop();playback.current=schedulePhrase(collapseTies(q.events),625,'piano')};
 const exportCase=(s:QuerySuggestion)=>{
  const record={schema:'musicanote-query-suggestion-case',version:1,algorithmVersion:SUGGESTION_VERSION,createdAt:new Date().toISOString(),
    originalQuery:query,proposal:s,userAssessment:confirmed.includes(s.id)?'confirmed-intended-melody':'unreviewed',
    source:'user-export',privacy:'explicit-local-export',limitations:['Recommendation is not a verified correction.','Source note snapshot is not a full MusicXML document.']};
  const url=URL.createObjectURL(new Blob([JSON.stringify(record,null,2)],{type:'application/json'}));
  const a=document.createElement('a');a.href=url;a.download='musicanote-query-suggestion-'+Date.now()+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
 };
 const shown=suggestions.filter(s=>!dismissed.includes(s.id));if(!shown.length)return null;
 return <section className="query-suggestions" aria-label="Query 보완 추천"><h2>이렇게 입력하려던 멜로디인가요?</h2>
  <p>검색된 악보를 참고한 제안입니다. 변경된 음은 붉게 표시됩니다. 듣고 확인한 뒤 적용해 주세요.</p>
  <button onClick={()=>play(query)}>원래 Query 듣기</button><button onClick={()=>playback.current?.stop()}>재생 정지</button>
  {shown.map(s=><article key={s.id}><h3>{s.reason}</h3><p>{s.evidence[0].title} · {s.evidence[0].startMeasure}–{s.evidence[0].endMeasure}마디{s.evidence.length>1?' 외 '+(s.evidence.length-1)+'개 원본':''}</p>
   <Notation query={s.query} highlightIds={s.changedIds}/>
   <button onClick={()=>play(s.query)}>추천 듣기</button>
   <button onClick={()=>{playback.current?.stop();onApply(s.query)}}>Query에 적용</button>
   <button onClick={()=>setDismissed(d=>[...d,s.id])}>추천 숨기기</button>
   <label><input type="checkbox" checked={confirmed.includes(s.id)} onChange={e=>setConfirmed(c=>e.target.checked?[...c,s.id]:c.filter(id=>id!==s.id))}/>찾던 멜로디가 맞아요</label>
   <button onClick={()=>exportCase(s)}>검토 사례 저장 (JSON)</button>
  </article>)}
  <small>적용 후 검색 버튼을 눌러 다시 검색하세요. Undo로 되돌릴 수 있습니다. Query와 확인 내용은 서버로 자동 수집하지 않으며, 사례 저장을 누를 때 파일로 내려받습니다.</small>
 </section>;
}
