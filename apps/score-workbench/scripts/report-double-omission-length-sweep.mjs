import { existsSync, readFileSync, writeFileSync } from 'node:fs';

const batch = process.argv[2] ?? 'double-omission-length-sweep-v1';
const reportDir = `evaluation/reports/${batch}`;
const runDir = `evaluation/runs/${batch}`;
const suite = JSON.parse(readFileSync(`${reportDir}/suite.json`, 'utf8'));

const esc = (value) => String(value ?? '')
  .replaceAll('&', '&amp;')
  .replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;')
  .replaceAll('"', '&quot;');
const pct = (value, total) => total ? `${Math.round(value * 100 / total)}%` : '—';
const rankLabel = (row) => row.status !== 'completed' ? '실행 오류' : (row.sourceRank ?? 'Top 100 밖');
const missStage = (run) => {
  if (run.status !== 'completed') return 'execution';
  if (run.sourceRank) return 'found';
  if (!run.trace?.inHits) return 'retrieval';
  if (!run.trace?.inCandidates) return 'candidate';
  if (Object.keys(run.trace?.rejections ?? {}).length) return `rejected:${Object.keys(run.trace.rejections).join(',')}`;
  return 'ranking';
};

const casesById = new Map(suite.cases.map((item) => [item.caseId, item]));
const basesById = new Map(suite.bases.map((item) => [item.baseId, item]));
const rows = suite.cases.map((testCase) => {
  const runPath = `${runDir}/${testCase.caseId}.json`;
  const firstFailurePath = `${runDir}/${testCase.caseId}.first-failed.json`;
  const run = JSON.parse(readFileSync(runPath, 'utf8'));
  const initial = existsSync(firstFailurePath) ? JSON.parse(readFileSync(firstFailurePath, 'utf8')) : null;
  const all = run.result ? [...(run.result.exact ?? []), ...(run.result.similar ?? [])] : [];
  return {
    caseId: testCase.caseId,
    baseId: testCase.baseId,
    title: basesById.get(testCase.baseId)?.expected?.title ?? testCase.baseId,
    queryNoteCount: testCase.queryNoteCount,
    sourceNoteCount: testCase.sourceNoteCount,
    status: run.status,
    sourceRank: run.sourceRank ?? null,
    elapsedMs: run.elapsedMs,
    missStage: missStage(run),
    retriedAfterTimeout: initial?.status === 'failed',
    initialElapsedMs: initial?.elapsedMs ?? null,
    query: testCase.query,
    removed: testCase.removed,
    sourceRange: testCase.sourceRange,
    top: all.slice(0, 3).map((match, index) => ({
      rank: index + 1,
      title: match.work?.title,
      sourceId: match.work?.sourceId,
      score: match.ranking,
    })),
  };
});

const byLength = suite.queryLengths.map((length) => {
  const subset = rows.filter((row) => row.queryNoteCount === length);
  const ranks = subset.map((row) => row.sourceRank).filter(Number.isFinite).sort((a, b) => a - b);
  const found = ranks.length;
  return {
    queryNoteCount: length,
    total: subset.length,
    completed: subset.filter((row) => row.status === 'completed').length,
    executionFailures: subset.filter((row) => row.status !== 'completed').length,
    top1: ranks.filter((rank) => rank <= 1).length,
    top5: ranks.filter((rank) => rank <= 5).length,
    top10: ranks.filter((rank) => rank <= 10).length,
    top20: ranks.filter((rank) => rank <= 20).length,
    top100: found,
    top100Rate: found / subset.length,
    medianFoundRank: found ? ranks[Math.floor((found - 1) / 2)] : null,
    meanElapsedMs: Math.round(subset.reduce((sum, row) => sum + row.elapsedMs, 0) / subset.length),
    misses: Object.fromEntries([...new Set(subset.filter((row) => !row.sourceRank).map((row) => row.missStage))]
      .map((stage) => [stage, subset.filter((row) => row.missStage === stage).length])),
  };
});

const maxLength = Math.max(...suite.queryLengths);
const recoverableBases = suite.bases.filter((base) => rows.some((row) => row.baseId === base.baseId && row.queryNoteCount === maxLength && row.sourceRank));
const recoverableIds = new Set(recoverableBases.map((base) => base.baseId));
const byLengthRecoverable = byLength.map((bucket) => {
  const subset = rows.filter((row) => row.queryNoteCount === bucket.queryNoteCount && recoverableIds.has(row.baseId));
  const found = subset.filter((row) => row.sourceRank).length;
  return { queryNoteCount: bucket.queryNoteCount, total: subset.length, top100: found, top100Rate: subset.length ? found / subset.length : null };
});

const baseRows = suite.bases.map((base) => {
  const ranks = Object.fromEntries(suite.queryLengths.map((length) => {
    const row = rows.find((item) => item.baseId === base.baseId && item.queryNoteCount === length);
    return [length, row?.sourceRank ?? null];
  }));
  const firstRecoveredLength = suite.queryLengths.find((length) => ranks[length]) ?? null;
  return {
    baseId: base.baseId,
    title: base.expected.title,
    sourceId: base.expected.sourceId,
    streamId: base.expected.streamId,
    deletionType: base.deletionEvidence.type,
    ranks,
    firstRecoveredLength,
    recoveredAtMaximum: Boolean(ranks[maxLength]),
  };
});

const largestGain = byLength.slice(1).map((bucket, index) => ({
  from: byLength[index].queryNoteCount,
  to: bucket.queryNoteCount,
  gain: bucket.top100Rate - byLength[index].top100Rate,
})).sort((a, b) => b.gain - a.gain)[0];

const results = {
  schema: 'double-omission-length-sweep-results/1',
  generatedAt: new Date().toISOString(),
  engineMode: { singleOmission: true, doubleOmissionRuleAdded: false, visibleRanking: false },
  sample: {
    cases: rows.length,
    bases: suite.bases.length,
    uniqueSources: new Set(suite.bases.map((base) => base.expected.sourceId)).size,
    uniqueWorks: new Set(suite.bases.map((base) => base.expected.workId)).size,
    queryLengths: suite.queryLengths,
  },
  byLength,
  byLengthRecoverable,
  baseRows,
  largestObservedGain: largestGain,
  interpretation: {
    observedCliff: largestGain ? `${largestGain.from}→${largestGain.to} notes` : null,
    conservativeMinimum: 16,
    conditionalRange: '10–14',
    highRiskRange: '8–14',
    caveat: 'Four bases were not recovered even at 18 notes, so length alone cannot authorize two-note omission.',
  },
  rows,
};
writeFileSync(`${reportDir}/results.json`, `${JSON.stringify(results, null, 2)}\n`);

const summaryTable = [
  '| 최종 Query 음표 수 | 사례 | Top 1 | Top 5 | Top 10 | Top 100 | Top 100 비율 | 평균 시간 |',
  '|---:|---:|---:|---:|---:|---:|---:|---:|',
  ...byLength.map((bucket) => `| ${bucket.queryNoteCount} | ${bucket.total} | ${bucket.top1} | ${bucket.top5} | ${bucket.top10} | ${bucket.top100} | ${pct(bucket.top100, bucket.total)} | ${(bucket.meanElapsedMs / 1000).toFixed(1)}초 |`),
].join('\n');
const pairedTable = [
  '| 원형 | 작품 | 8 | 10 | 12 | 14 | 16 | 18 | 최초 회복 |',
  '|---|---|---:|---:|---:|---:|---:|---:|---:|',
  ...baseRows.map((base) => `| ${base.baseId} | ${String(base.title).replaceAll('|', '/')} | ${suite.queryLengths.map((length) => base.ranks[length] ?? '—').join(' | ')} | ${base.firstRecoveredLength ?? '미회수'} |`),
].join('\n');
const markdown = `# 긴 Query에서 장식음 2개 생략 — 길이 임계값 실험\n\n` +
  `- 11개 원형 × 최종 Query 길이 6구간 = 66개 검색\n` +
  `- 최종 길이: 8, 10, 12, 14, 16, 18음(원형은 각각 2음 더 김)\n` +
  `- 같은 원형의 같은 두 장식음 후보를 삭제하고, 삭제 음가는 직전 생존음에 합쳐 전체 박자 길이를 보존\n` +
  `- 현재 운영 검색(single omission 활성)만 사용했으며 2음 생략 전용 규칙은 추가하지 않음\n\n` +
  `${summaryTable}\n\n## 원형별 짝 비교\n\n${pairedTable}\n\n` +
  `## 판단\n\n` +
  `가장 큰 Top 100 회수율 증가는 ${largestGain.from}음에서 ${largestGain.to}음으로 늘 때(${pct(byLength.find((x) => x.queryNoteCount === largestGain.from).top100, 11)} → ${pct(byLength.find((x) => x.queryNoteCount === largestGain.to).top100, 11)})였다. 최종 16음에서는 7/11, 18음에서도 7/11이 회수됐다. 18음에서 회수된 7개 원형만 보면 16·18음은 7/7, 12·14음은 5/7, 10음은 4/7, 8음은 4/7이었다.\n\n` +
  `따라서 이번 표본에서는 **16음 이상을 보수적 허용 구간**, **10–14음을 고유성과 리듬 정보가 충분할 때만 허용하는 조건부 구간**, **8음은 기본적으로 2음 생략 확장을 하지 않는 구간**으로 보는 것이 합리적이다. 다만 4개 원형은 18음에서도 회수되지 않았으므로, 음표 수만으로 2음 생략을 허용해서는 안 된다. 이들은 후보 생성 또는 admission/sparse-alignment 단계의 별도 문제다.\n\n` +
  `## 한계\n\n` +
  `서로 다른 원본 파일은 ${results.sample.uniqueSources}개뿐이고 같은 곡의 반복 구간이 포함된 편의 표본이다. 삭제 대상은 짧고 약박에 있으며 순차진행인 음을 휴리스틱으로 고른 것이지, 화성·프레이즈·청취로 확정한 장식음 판정이 아니다. 따라서 이 수치를 전체 데이터베이스 성능으로 일반화하지 않는다. 시간 초과 2건은 원본 기록을 보존하고 한 번 재시도했으며, 8음은 미회수, 18음은 3위였다.\n\n` +
  `원본·Query·삭제 좌표는 [suite.json](suite.json), 기계 판독 결과는 [results.json](results.json), 전체 검색 응답은 \`evaluation/runs/${batch}\`에 있다.\n`;
writeFileSync(`${reportDir}/REPORT.md`, markdown);

const lengthRows = byLength.map((bucket) => `<tr><td>${bucket.queryNoteCount}</td><td>${bucket.total}</td><td>${bucket.top1}</td><td>${bucket.top5}</td><td>${bucket.top10}</td><td>${bucket.top100}</td><td>${pct(bucket.top100, bucket.total)}</td><td>${(bucket.meanElapsedMs / 1000).toFixed(1)}초</td></tr>`).join('');
const matrixRows = baseRows.map((base) => `<tr><td>${esc(base.baseId)}</td><td>${esc(base.title)}</td>${suite.queryLengths.map((length) => `<td>${base.ranks[length] ?? '—'}</td>`).join('')}<td>${base.firstRecoveredLength ?? '미회수'}</td></tr>`).join('');
const cards = rows.map((row) => `<article><h3>${esc(row.caseId)} · ${esc(row.title)}</h3><p><b>${row.queryNoteCount}음 Query</b> · 원형 ${row.sourceNoteCount}음 · 지정 원본 ${esc(rankLabel(row))} · ${(row.elapsedMs / 1000).toFixed(1)}초</p><p>미회수 단계: ${esc(row.missStage)}${row.retriedAfterTimeout ? ' · 시간 초과 후 재시도' : ''}</p><button data-copy="${esc(row.caseId)}">Query 복사</button><details><summary>Query JSON / 삭제 좌표</summary><pre id="${esc(row.caseId)}">${esc(JSON.stringify({ schema: 'musicanote-query', query: row.query, removed: row.removed, sourceRange: row.sourceRange }, null, 2))}</pre></details></article>`).join('');
const html = `<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>2음 생략 길이 임계값</title><style>body{font:15px system-ui;color:#203044;background:#edf1f5;margin:0}header,main{max-width:1280px;margin:18px auto;padding:22px;background:#fff;border-radius:14px}table{border-collapse:collapse;width:100%;margin:16px 0}th,td{border:1px solid #d7dee6;padding:8px;text-align:center}th:nth-child(2),td:nth-child(2){text-align:left}article{border:1px solid #d7dee6;border-radius:10px;padding:14px;margin:12px 0}pre{white-space:pre-wrap;font-size:12px}button{padding:8px 12px}mark{background:#fff1a8}@media(max-width:800px){header,main{margin:0;border-radius:0;padding:14px;overflow-x:auto}}</style><header><h1>긴 Query에서 장식음 2개 생략</h1><p>11개 원형 · 66개 실제 검색 · 현재 운영 엔진 · 2음 생략 전용 규칙 없음</p><p><mark>관측된 경계: 14→16음</mark> · 보수적 허용 16음 이상 · 10–14음 조건부 · 8음 기본 제외</p><a href="REPORT.md">보고서</a> · <a href="suite.json">Suite</a> · <a href="results.json">Results</a></header><main><h2>길이별 결과</h2><table><thead><tr><th>Query 음표</th><th>사례</th><th>Top 1</th><th>Top 5</th><th>Top 10</th><th>Top 100</th><th>회수율</th><th>평균 시간</th></tr></thead><tbody>${lengthRows}</tbody></table><h2>같은 원형의 길이별 순위</h2><table><thead><tr><th>원형</th><th>작품</th>${suite.queryLengths.map((length) => `<th>${length}</th>`).join('')}<th>최초 회복</th></tr></thead><tbody>${matrixRows}</tbody></table><h2>Query와 실행 기록</h2>${cards}</main><script>document.querySelectorAll('[data-copy]').forEach((button)=>button.addEventListener('click',async()=>{const data=JSON.parse(document.getElementById(button.dataset.copy).textContent);await navigator.clipboard.writeText(JSON.stringify({schema:data.schema,query:data.query},null,2));const old=button.textContent;button.textContent='복사됨';setTimeout(()=>button.textContent=old,1200)}));</script></html>`;
writeFileSync(`${reportDir}/index.html`, html);
console.log(JSON.stringify({ batch, byLength, largestGain, recoverableBases: recoverableBases.length }, null, 2));
