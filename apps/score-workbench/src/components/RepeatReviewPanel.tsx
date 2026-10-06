import {useState} from 'react';
import {validateRepeatReview} from '../music/repeatReviewImport';
export function RepeatReviewPanel({work,onSelect}:{work:any;onSelect:(row:any)=>void}){
 const [report,setReport]=useState<any>(null),[error,setError]=useState(''),[selected,setSelected]=useState('');
 return <section className="analysis-block"><h3>반복 경계 검토 · 실험</h3><p>review-ui.json을 불러온 뒤 후보를 선택하세요. 현재 Phrase는 유지됩니다. 보고서는 저장 당시 경계 기준입니다.</p>
 <input aria-label="반복 검토 보고서 불러오기" type="file" accept=".json" onChange={async e=>{const f=e.target.files?.[0];onSelect(null);setSelected('');setReport(null);setError('');if(!f)return;try{if(f.size>10000000)throw Error('10MB 이하 보고서를 선택하세요.');setReport(validateRepeatReview(JSON.parse(await f.text()),work));}catch(err){setError(String(err));}}}/>
 {error&&<p role="alert">{error}</p>}{report&&<><p>검색: {report.discoveryStatus} · 범위 검토: {report.status}. 미검토 구간이 있을 수 있습니다.</p><select aria-label="반복 경계 검토 후보" value={selected} onChange={e=>{setSelected(e.target.value);onSelect(e.target.value===''?null:report.rows[Number(e.target.value)]);}}><option value="">검토 표시 끄기</option>{report.rows.map((r:any,i:number)=><option key={i} value={i}>후보 {i+1} · 원형 {r.left.startMeasure}–{r.left.endMeasure}마디 ↔ 재등장 {r.right.startMeasure}–{r.right.endMeasure}마디</option>)}</select>{selected!==''&&<p>점선: 원형 / 재등장 검토 범위. 대응 위치 경계 차이 {report.rows[Number(selected)].correspondingBoundaryDifferences.length}곳. 병합·종지 판정은 보류입니다.</p>}</>}
 </section>;
}
