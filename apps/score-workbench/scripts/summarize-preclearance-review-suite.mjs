import {readFileSync,writeFileSync,existsSync} from 'node:fs';
import {join,relative,dirname,resolve} from 'node:path';
const [directory,output]=process.argv.slice(2);if(!directory||!output||existsSync(output))throw new Error('Suite directory and NEW markdown output required');
const suite=JSON.parse(readFileSync(join(directory,'suite.json'),'utf8')),summary=JSON.parse(readFileSync(join(directory,'summary.json'),'utf8'));
const escape=v=>String(v??'').replaceAll('|','\\|').replaceAll('\n',' ');
const label=n=>n.kind==='rest'?`Rest(${n.durationRatio})`:`${n.spelling??(['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'][n.pitchMidi%12]+(Math.floor(n.pitchMidi/12)-1))}(${n.durationRatio})`;
const lines=['# 유형별 사전검토 Query 파일럿','', '음가 단위는 4분음표=1. 원본 순위는 top 20 안의 해당 source 회수 진단이며 정답 순위 라벨이 아니다. 전체 악보/강조 표시는 검증하지 않았다.','',
`유형별 생성: ${JSON.stringify(suite.counts)}. 실행 ${summary.runs.length}개, 미실행 ${summary.notExecuted}개.`, '',
'| 사례 | 유형 / 변형 | Query | 원본 순위 | 상태 |','|---|---|---|---|---|'];
for(const c of suite.cases){const run=summary.runs.find(r=>r.caseId===c.caseId);lines.push(`| ${c.caseId} | ${c.category} / ${c.variant} | ${escape(c.query.events.map(label).join(' '))} | ${run?.sourceRank??'—'} | ${run?.status??'not-executed'} |`)}
lines.push('','## 검토 항목','','각 사례의 suite.json humanReview 필드에 검토자, 원본이 회수되어야 하는 이유, 선호 후보 ID, 순위 이유, 음악적 기능을 별도 복사본으로 기록한다. 원본 측정 결과를 덮어쓰지 않는다. 자동 분류는 모티프/화성 분석 확정이 아니다.','',
'## 출처와 한계','','선별 모집단은 이전 한 업로드 검색의 후보 스냅샷이다. 유형당 작품 다양성은 보강했지만 전체 corpus를 대표하지 않는다. 원형·반음 수정·옥타브 이동은 서로 다른 구간에 적용되어 완전한 paired A/B가 아니다. 본 파일럿의 목적은 Harness 동작과 문제 발견이다.','',
`[전체 Query·문맥·사람 검토 필드](${relative(dirname(resolve(output)),resolve(directory,'suite.json')).replaceAll('\\','/')})`,'',
'## 실패/미회수 확인','');
for(const r of summary.runs.filter(r=>r.status!=='completed'||r.sourceRank===null))lines.push(`- ${r.caseId}: ${escape(r.error??'top 20 내 원본 source 미회수 — 다른 판본/동일 작품 후보는 별도 검토 필요')}`);
writeFileSync(output,lines.join('\n')+'\n',{flag:'wx'});
