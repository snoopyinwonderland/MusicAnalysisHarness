import {readFileSync,writeFileSync} from 'node:fs';
const [inputPath,outputPath]=process.argv.slice(2);
if(!inputPath||!outputPath)throw new Error('Usage: node scripts/summarize-preclearance-search.mjs report.json NEW-summary.md');
const report=JSON.parse(readFileSync(inputPath,'utf8'));
const cell=value=>String(value??'unknown').replaceAll('|','/').replaceAll('\n',' ');
const lines=['# Creator Pre-clearance 실제 검색 검증','',`상태: ${report.status}. Snapshot: ${report.snapshotId}.`,
 '',`총 실행 시간: ${(report.runtime.elapsedMs/1000).toFixed(1)}초. 검색 ${report.runs.length}개, 작품 그룹 ${report.works.length}개.`,
 '','이 실행은 자동 검증이며, 상위 결과에 대한 전문가의 음악적 적절성 판정은 아직 없다. 검토 우선순위는 미보정이다.',
 '','## 검색 Query와 결과','', '| 번호 | Query: pitch / quarter duration | 결과 수 | 시간(초) | 상태 |','|---|---|---:|---:|---|'];
report.runs.forEach((run,i)=>lines.push(`| ${i+1} | ${cell(run.query.events.map(e=>`${e.kind==='rest'?'rest':e.spelling??e.pitchMidi}/${e.durationRatio}`).join(' '))} | ${(run.result?.exact?.length??0)+(run.result?.similar?.length??0)} | ${(run.elapsedMs/1000).toFixed(1)} | ${run.status} |`));
lines.push('','## 작품별 상위 결과','', '| 순위 | 제목 | 작곡가/아티스트 | 최고 유사도 | 마디 | 대응 Query coverage |','|---|---|---|---:|---|---:|');
report.works.slice(0,20).forEach((work,i)=>lines.push(`| ${i+1} | ${cell(work.title)} | ${cell(work.artist)} | ${work.similarity.toFixed(2)} | ${cell(work.bestMatch.startMeasure)}–${cell(work.bestMatch.endMeasure)} | ${(work.coverage*100).toFixed(1)}% |`));
lines.push('','## 제한과 다음 검토','', '- 동일 source의 여러 성부를 묶었다. canonical work ID가 없는 서로 다른 판본은 별개다.', '- 반복/중첩 일치를 점수에 더하지 않는다. coverage는 검색한 대표 Query의 정렬 이벤트 합집합이다.', '- query importance는 관측 가능한 일부 요소만 사용하며 candidate importance와 희소성은 아직 미정이다.', '- 한 작품의 단일 실행 시간이다. 전체 코퍼스 p50/p95 또는 일반화 정확도 수치가 아니다.', '- 다음 검토: 상위 결과 적절성, 누락된 중요 Phrase/Motif, 선정 임계값, candidate retrieval 시간.','');
writeFileSync(outputPath,lines.join('\n'),{flag:'wx'});
