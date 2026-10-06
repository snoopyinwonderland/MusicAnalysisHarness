import {readFileSync,writeFileSync,mkdirSync,existsSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {discoverRepeats} from '../server/repeat-first.mjs';
import {reviewRepeatExtents} from '../server/repeat-extent-review.mjs';
import {reviewElasticExtents} from '../server/repeat-elastic-extent.mjs';
import {compareRepeatBoundaries} from '../server/repeat-boundary-review.mjs';
const [caseId,run]=process.argv.slice(2);if(!/^S-STRUCT-\d+$/.test(caseId??'')||!/^[-a-z0-9]+$/.test(run??''))throw Error('case and run required');
const out=`evaluation/reports/${run}`;if(existsSync(out))throw Error('Refusing overwrite');
const root=`evaluation/case-assets/${caseId}`,bytes=readFileSync(root+'/review-snapshot.json'),snapshot=JSON.parse(bytes),xml=readFileSync(root+'/context.musicxml'),hash=x=>createHash('sha256').update(x).digest('hex');
if(hash(xml)!==snapshot.xmlSha256)throw Error('Source mismatch');
const before=JSON.stringify(snapshot.work.notes),result=discoverRepeats(snapshot.work.notes);if(before!==JSON.stringify(snapshot.work.notes))throw Error('Mutation');
const extentReview=reviewRepeatExtents(snapshot.work.notes,result);
const elasticReview=reviewElasticExtents(snapshot.work.notes,extentReview.groups);
if(!snapshot.work.phraseAnalysis?.boundaries)throw Error('Snapshot baseline boundaries missing');
const boundaryReview=compareRepeatBoundaries(snapshot.work.notes,snapshot.work.phraseAnalysis.boundaries,elasticReview);
const paths=['server/repeat-first.mjs','server/repeat-extent-review.mjs','server/repeat-elastic-extent.mjs','server/repeat-boundary-review.mjs','src/music/structureTemplateAlignment.ts','src/music/motifSimilarity.ts','scripts/evaluate-repeat-first.mjs'];
mkdirSync(out,{recursive:true});writeFileSync(out+'/report.json',JSON.stringify({caseId,sourceHash:hash(xml),snapshotHash:hash(bytes),codeHashes:Object.fromEntries(paths.map(p=>[p,hash(readFileSync(p))])),...result},null,2));
const variants=result.candidates.flatMap(c=>c.variants.map(v=>({pair:[c.left.startIndex,c.right.startIndex],...v})));
writeFileSync(out+'/extent-review.json',JSON.stringify(extentReview,null,2));
writeFileSync(out+'/elastic-review.json',JSON.stringify(elasticReview,null,2));
writeFileSync(out+'/boundary-review.json',JSON.stringify({...boundaryReview,baseline:'saved-snapshot-not-live',baselineEngineHash:snapshot.engineHash??null},null,2));
writeFileSync(out+'/review-ui.json',JSON.stringify({schema:'repeat-review-ui/v1',workId:snapshot.work.workId,streamId:snapshot.work.streamId,sourceHash:hash(xml),discoveryStatus:result.status,status:boundaryReview.status,noteIdentity:snapshot.work.notes.map(n=>[n.id,n.pitchMidi,n.onset,n.durationRatio,n.measure,n.beat]),rows:boundaryReview.rows.filter(r=>r.correspondingBoundaryDifferences.length)},null,2));
const lines=['# 경계 독립 반복 탐색',`사례 ${caseId} · ${result.status} · seed검사 ${result.seedChecks} · 정렬 ${result.alignments}`,`음가/쉼 치환 관찰 ${variants.length}건(겹친 창 중복 포함, 독립 occurrence 수 아님)`, '기존 Phrase 경계를 입력하지 않았다. 운영 경계/UI 변경 없음. 창 끝은 Motif 또는 Phrase 종결이 아니다.',...variants.slice(0,20).map(v=>`- ${v.leftEventId} ↔ ${v.rightEventId}: ${v.leftDuration}+쉼${v.leftInferredGap} → ${v.rightDuration}+쉼${v.rightInferredGap}, 다음 attack 간격 ${v.ioiQuarter}`)];
lines.push('',`## 구간 후보 정리: ${result.candidates.length}개 창 → ${extentReview.groups.length}개 포함관계 그룹`, '동일 모티프 가족의 개수가 아니다. 시작 준비부/화성 완결성은 미확정. 다음 표는 앞10개 그룹의 종결 후보이다.', '| 시작 index쌍 | 원래 창 수 | 끝 exclusive index쌍 | 상태 |','|---|---:|---|---|',...extentReview.groups.slice(0,10).flatMap(g=>g.endpoints.map(e=>`| ${g.anchor.left.startIndex}/${g.anchor.right.startIndex} | ${g.windowCount} | ${e.left.endExclusiveIndex}/${e.right.endExclusiveIndex} | ${e.status} |`)));
lines.push('',`## 가변 범위 리뷰`, `정렬 ${elasticReview.alignments} · ${elasticReview.status} · 후보 ${elasticReview.reviews.reduce((s,r)=>s+r.proposals.length,0)}개. 후보 수는 독립 등장 수가 아니다. 운영 변경 없음.`);
lines.push('','## 저장 당시 Phrase 경계와의 비교','반복 후보 생성 뒤에만 저장된 경계를 대조했다. 아래는 병합 지시가 아닌 검토 목록이다.',
  '| 원형 마디 | 재등장 마디 | 내부 경계 수(원형/재등장) | 대응 위치 경계 차이 |','|---|---|---:|---:|',
  ...boundaryReview.rows.filter(r=>r.correspondingBoundaryDifferences.length).slice(0,20).map(r=>`| ${r.left.startMeasure}–${r.left.endMeasure} | ${r.right.startMeasure}–${r.right.endMeasure} | ${r.left.internalCuts.length}/${r.right.internalCuts.length} | ${r.correspondingBoundaryDifferences.length} |`));
writeFileSync(out+'/review.md',lines.join('\n'));console.log(lines.slice(-25).join('\n'));
