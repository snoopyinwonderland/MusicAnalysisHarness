import { existsSync, readFileSync, readdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';

const batch = process.argv[2] ?? 'ornament-count-sweep-v1';
const reportDir = `evaluation/reports/${batch}`;
const suite = JSON.parse(readFileSync(`${reportDir}/suite.json`, 'utf8'));
const runDirs = readdirSync('evaluation/runs').filter((name) => name.startsWith(`${batch}-`) && !name.includes('interrupted'));
const kinds = ['original', 'cluster-3', 'cluster-4', 'cluster-5', 'cluster-6'];
const esc = (value) => String(value ?? '').replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;');

function bestRun(testCase) {
  const runs = runDirs.flatMap((dir) => {
    const file = path.join('evaluation/runs', dir, `${testCase.caseId}.json`);
    return existsSync(file) ? [{ dir, ...JSON.parse(readFileSync(file, 'utf8')) }] : [];
  });
  return runs.find((run) => run.status === 'completed') ?? runs[0];
}

function missStage(run) {
  if (run.status !== 'completed') return 'execution';
  if (run.sourceRank) return 'found';
  if (!run.trace?.inHits) return 'retrieval';
  if (!run.trace?.inCandidates) return 'candidate';
  const rejected = Object.keys(run.trace?.rejections ?? {});
  return rejected.length ? `rejected:${rejected.join(',')}` : 'ranking';
}

const rows = suite.cases.map((testCase) => {
  const base = suite.bases.find((item) => item.baseId === testCase.baseId);
  const run = bestRun(testCase);
  const matches = run.result ? [...(run.result.exact ?? []), ...(run.result.similar ?? [])] : [];
  const sourceMatch = run.sourceRank ? matches[run.sourceRank - 1] : null;
  return { caseId: testCase.caseId, baseId: testCase.baseId, kind: testCase.kind, addedNoteCount: testCase.addedNoteCount, title: base.expected.title, query: testCase.query, operation: testCase.operation, sourceRank: run.sourceRank ?? null, sourceScore: sourceMatch?.ranking ?? null, sourceScores: sourceMatch?.scores ?? null, status: run.status, elapsedMs: run.elapsedMs, runDir: run.dir, missStage: missStage(run) };
});
const originals = new Map(rows.filter((row) => row.kind === 'original').map((row) => [row.baseId, row]));
const evaluableBaseIds = new Set([...originals.values()].filter((row) => row.sourceRank).map((row) => row.baseId));
for (const row of rows) {
  const original = originals.get(row.baseId);
  row.rankChangeFromOriginal = row.sourceRank && original?.sourceRank ? row.sourceRank - original.sourceRank : null;
  row.scoreChangeFromOriginal = row.sourceScore != null && original?.sourceScore != null ? row.sourceScore - original.sourceScore : null;
}
const stats = Object.fromEntries(kinds.map((kind) => {
  const all = rows.filter((row) => row.kind === kind);
  const subset = all.filter((row) => kind === 'original' ? row.sourceRank : evaluableBaseIds.has(row.baseId));
  const found = subset.filter((row) => row.sourceRank);
  return [kind, { all: all.length, evaluable: subset.length, found: found.length, rate: subset.length ? found.length / subset.length : null, top10: found.filter((row) => row.sourceRank <= 10).length, top5: found.filter((row) => row.sourceRank <= 5).length, top1: found.filter((row) => row.sourceRank === 1).length, meanScore: found.length ? found.reduce((sum, row) => sum + row.sourceScore, 0) / found.length : null, meanScoreChange: found.length ? found.reduce((sum, row) => sum + (row.scoreChangeFromOriginal ?? 0), 0) / found.length : null, misses: Object.fromEntries([...new Set(subset.filter((row) => !row.sourceRank).map((row) => row.missStage))].map((stage) => [stage, subset.filter((row) => row.missStage === stage).length])) }];
}));
const baseRows = suite.bases.map((base) => ({ baseId: base.baseId, title: base.expected.title, originalFound: Boolean(originals.get(base.baseId)?.sourceRank), ranks: Object.fromEntries(kinds.map((kind) => [kind, rows.find((row) => row.baseId === base.baseId && row.kind === kind)?.sourceRank ?? null])) }));
const results = { schema: 'ornament-count-sweep-results/1', generatedAt: new Date().toISOString(), runDirs, controlledVariables: suite.controlledVariables, sample: { bases: suite.bases.length, evaluableBases: evaluableBaseIds.size, cases: rows.length }, stats, baseRows, rows, interpretation: { primaryCliff: '5→6 added tones', note: 'Rank is corpus-relative; retrieval/admission and absolute score are primary.' } };
writeFileSync(`${reportDir}/results.json`, `${JSON.stringify(results, null, 2)}\n`);

const pct = (value) => `${Math.round(value * 100)}%`;
const summary = [
  '| 추가 장식음 | 평가 가능 원형 | 회수 | 회수율 | Top 10 | 평균 점수 | 원형 대비 평균 점수 변화 |',
  '|---:|---:|---:|---:|---:|---:|---:|',
  ...[3, 4, 5, 6].map((count) => { const item = stats[`cluster-${count}`]; return `| ${count} | ${item.evaluable} | ${item.found} | ${pct(item.rate)} | ${item.top10} | ${item.meanScore?.toFixed(1) ?? '—'} | ${item.meanScoreChange?.toFixed(1) ?? '—'} |`; }),
].join('\n');
const matrix = [
  '| 원형 | 작품 | 원형 | +3 | +4 | +5 | +6 |',
  '|---|---|---:|---:|---:|---:|---:|',
  ...baseRows.map((base) => `| ${base.baseId} | ${String(base.title).replaceAll('|', '/')} | ${kinds.map((kind) => base.ranks[kind] ?? '—').join(' | ')} |`),
].join('\n');
writeFileSync(`${reportDir}/REPORT.md`, `# 국소 장식음 수 3–6개 임계값 실험\n\n${summary}\n\n## 원형별 순위\n\n${matrix}\n\n## 결론\n\n같은 0.5박 구간과 같은 host를 유지한 통제 조건에서 회수율은 3음 12/14, 4음 11/14, 5음 9/14, 6음 3/14로 내려갔다. 가장 큰 하락은 5→6음이다. 3–4음은 비교적 안정적이고 5음은 조건부 경계, 6음은 현재 검색에서 강한 변형으로 보는 것이 적절하다.\n\n원형 자체가 미회수된 OC11은 변형 성공률 분모에서 제외했다. 초기 60초 시간 초과는 최대 180초 재시도로 완료 결과를 확보했으며 검색 실패와 구분했다. 순위는 DB 규모에 따라 변하므로 후보 진입, admission, 절대 점수를 우선한다.\n\n## 한계\n\n총 장식 구간은 0.5박으로 고정했기 때문에 음 수가 늘수록 개별 음가는 짧아진다. 각 개수의 음형은 모두 국소 보조음형이지만 완전히 동일한 pitch sequence의 prefix는 아니어서 음 수와 종결 음형 효과가 일부 섞인다. 화성 분석으로 장식음을 확정하지 않은 합성 테스트이며 운영 검색 규칙은 변경하지 않았다.\n`);

const summaryRows = [3, 4, 5, 6].map((count) => { const item = stats[`cluster-${count}`]; return `<tr><td>${count}</td><td>${item.evaluable}</td><td>${item.found}</td><td><b>${pct(item.rate)}</b></td><td>${item.top10}</td><td>${item.meanScore?.toFixed(1) ?? '—'}</td><td>${item.meanScoreChange?.toFixed(1) ?? '—'}</td></tr>`; }).join('');
const matrixRows = baseRows.map((base) => `<tr><td>${esc(base.baseId)}</td><td>${esc(base.title)}</td>${kinds.map((kind) => `<td>${base.ranks[kind] ?? '—'}</td>`).join('')}</tr>`).join('');
const cards = rows.filter((row) => row.kind !== 'original').map((row) => `<article><h3>${esc(row.caseId)} · ${esc(row.title)}</h3><p>${row.addedNoteCount}음 추가 · 지정 원본 ${row.sourceRank ?? 'Top100 밖'} · 점수 ${row.sourceScore?.toFixed(1) ?? '—'} · ${esc(row.missStage)}</p><button data-copy="${esc(row.caseId)}">Query 복사</button><details><summary>Query와 변형 근거</summary><pre id="${esc(row.caseId)}">${esc(JSON.stringify({ schema: 'musicanote-query', query: row.query }, null, 2))}</pre><pre>${esc(JSON.stringify(row.operation, null, 2))}</pre></details></article>`).join('');
const html = `<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>장식음 수 3–6개 임계값</title><style>body{font:15px system-ui;color:#203044;background:#edf1f5;margin:0}header,main{max-width:1300px;margin:18px auto;padding:22px;background:white;border-radius:14px}table{border-collapse:collapse;width:100%;margin:16px 0}th,td{border:1px solid #d7dee6;padding:8px;text-align:center}th:nth-child(2),td:nth-child(2){text-align:left}article{border:1px solid #d7dee6;border-radius:10px;padding:14px;margin:12px 0}pre{white-space:pre-wrap;font-size:12px}button{padding:8px 12px}.bar{display:flex;gap:12px;align-items:end;height:150px}.bar div{background:#52736a;color:white;width:80px;text-align:center;padding-top:8px;border-radius:6px 6px 0 0}@media(max-width:800px){header,main{margin:0;border-radius:0;overflow-x:auto}}</style><header><h1>국소 장식음 수 3–6개 임계값</h1><p>15개 고유 4/4 원형 · 같은 host · 같은 0.5박 구간 · 75개 검색</p><p><b>가장 큰 하락: 5→6음</b></p><a href="REPORT.md">보고서</a> · <a href="suite.json">Suite</a> · <a href="results.json">Results</a></header><main><h2>회수율</h2><div class="bar">${[3,4,5,6].map((count)=>{const rate=stats[`cluster-${count}`].rate;return `<div style="height:${Math.round(rate*120)}px">+${count}<br>${pct(rate)}</div>`}).join('')}</div><table><thead><tr><th>추가음</th><th>평가 가능 원형</th><th>회수</th><th>회수율</th><th>Top10</th><th>평균 점수</th><th>원형 대비</th></tr></thead><tbody>${summaryRows}</tbody></table><h2>원형별 순위</h2><table><thead><tr><th>원형</th><th>작품</th><th>원형</th><th>+3</th><th>+4</th><th>+5</th><th>+6</th></tr></thead><tbody>${matrixRows}</tbody></table><h2>전체 변형 Query</h2>${cards}</main><script>document.querySelectorAll('[data-copy]').forEach((button)=>button.addEventListener('click',async()=>{await navigator.clipboard.writeText(document.getElementById(button.dataset.copy).textContent);const old=button.textContent;button.textContent='복사됨';setTimeout(()=>button.textContent=old,1200)}));</script></html>`;
writeFileSync(`${reportDir}/index.html`, html);
console.log(JSON.stringify({ stats, evaluableBases: evaluableBaseIds.size }, null, 2));
