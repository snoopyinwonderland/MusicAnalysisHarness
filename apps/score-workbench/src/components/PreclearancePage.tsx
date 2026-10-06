import {useState} from 'react';
import './preclearance.css';
const REPORT='/evaluation/reports/copyright-infringement-report-2026-09-16-v2/index.html';
export function PreclearancePage(){
 const [shown,setShown]=useState(false);
 return <div className="preclearance-page"><header><a href="/" className="brand">MUSICANOTE</a><nav><a href="/">Search</a><a href="/preclearance" aria-current="page">Copyright Check</a></nav></header><main>
 <p className="kicker">CREATOR PRECLEARANCE · LOCAL PREVIEW</p><h1>음악 유사성 사전 검토</h1><p>Phrase와 경계에 구애받지 않는 연속 구간을 비교하고, 구조적 골격과 Contour·리듬형·음형을 별도 근거로 검토합니다.</p>
 <section><h2>검토 방식</h2><dl><dt>기본</dt><dd>Phrase 중심 · 긴 프레이즈는 문맥을 유지하는 검색 창으로 나눕니다.</dd><dt>비교 실험</dt><dd>같은 Phrase 검색에 Motif를 추가합니다. Motif가 Phrase를 밀어내지 않습니다.</dd><dt>복수 구간</dt><dd>같은 Phrase의 반복과 판본 중복을 구분하고, 서로 다른 Phrase의 추가 근거를 제한적으로 집계합니다.</dd></dl></section>
 <section><h2>프레이즈 밖의 구간도 비교</h2><p>오프라인 검사 도구에 Phrase / 연속 구간 / 혼합 방식을 추가했습니다. 연속 구간은 8·12·16·24음의 겹치는 창으로, 프레이즈 중간이나 경계를 넘는 음형도 비교합니다. 쉼표와 원래 음표 순서를 유지합니다.</p><p className="notice">준비된 모든 구간을 검사한 것은 아닙니다. 검사 예산과 미검사 범위를 별도로 기록하며, 겹친 창을 독립적인 여러 일치로 세지 않습니다. 화면에서 새 검사를 실행하는 선택 기능은 아직 연결되지 않았습니다.</p></section>
 <section><h2>샘플 보고서</h2><p>Endless Love의 보존된 분석 사례입니다. 업로드 원곡으로 확인된 작품은 제외했습니다. 점수는 침해 확률이 아니며, 권리 상태와 전문가 판단은 별도로 확인해야 합니다.</p>
 <button onClick={()=>setShown(s=>!s)} aria-expanded={shown}>{shown?'보고서 접기':'분석 보고서 보기'}</button> <a href={REPORT} target="_blank" rel="noreferrer">큰 화면으로 열기</a>
 <p className="notice">새 파일 업로드·서버 분석은 아직 제공하지 않습니다. 인증·비공개 보관·삭제 정책 연결 전인 로컬 검토 화면입니다.</p></section>
 {shown&&<iframe className="preclearance-report" src={REPORT} title="Copyright Infringement Report"/>}
 </main></div>;
}
