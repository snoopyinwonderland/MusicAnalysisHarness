import {useEffect,useState} from 'react';
import {validateStructurePreview} from '../music/structurePreview';
export function StructurePreviewPanel({work,active,onChange}:{work:any;active:boolean;onChange:(data:any)=>void}){
 const [data,setData]=useState<any>(null),[error,setError]=useState('');
 useEffect(()=>{const controller=new AbortController();setData(null);setError('');fetch(`/api/structure-preview?workId=${encodeURIComponent(work.workId)}`,{signal:controller.signal,cache:'no-store'}).then(async r=>{if(r.status===404)return null;if(!r.ok)throw Error('검토 범위를 불러오지 못했습니다.');return validateStructurePreview(await r.json(),work)}).then(d=>{if(!controller.signal.aborted)setData(d)}).catch(e=>{if(!controller.signal.aborted)setError(String(e))});return()=>controller.abort()},[work]);
 if(error)return <p role="alert">{error}</p>;
 if(!data)return null;
 return <section className="analysis-block"><h3>Phrase 묶음 비교</h3><p>사용자가 제안한 구간의 미리보기입니다. 알고리즘의 최종 선택이 아니며 원래 분석은 바뀌지 않습니다.</p>
 <button type="button" aria-pressed={!active} onClick={()=>onChange(null)}>현재 경계</button> <button type="button" aria-pressed={active} onClick={()=>onChange(data)}>제안 범위 보기</button>
 {active&&<><p>상단 점선은 제안 Phrase, 아래 보라색은 기존 Motif입니다. 비교 중에는 원래 Phrase 띠를 숨깁니다.</p><ol>{data.ranges.map((r:any,i:number)=><li key={r.startEventId}>제안 Phrase {i+1} · {r.startMeasure}–{r.endMeasure}마디 · {work.notes[r.startIndex].spelling} → {work.notes[r.endIndexExclusive-1].spelling}</li>)}</ol></>}
 </section>;
}
