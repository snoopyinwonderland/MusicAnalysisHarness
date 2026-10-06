import { readFileSync, writeFileSync } from 'node:fs';
import createModule from 'verovio/wasm';
import { VerovioToolkit } from 'verovio/esm';
import { comparisonNotation, htmlEscape as esc } from '../server/preclearance-report.mjs';
import { namespaceSvg } from './comparison-media.mjs';

const batch = process.argv[2] ?? 'ornament-addition-75-v1';
const reportDir = `evaluation/reports/${batch}`;
const suite = JSON.parse(readFileSync(`${reportDir}/suite.json`, 'utf8'));
const kinds = ['original', 'cluster-3', 'cluster-4', 'distributed-3', 'distributed-4'];
const kindLabels = {
  original: '원형 대조',
  'cluster-3': '국소 장식군 3음',
  'cluster-4': '국소 장식군 4음',
  'distributed-3': '분산 3음 스트레스',
  'distributed-4': '분산 4음 스트레스',
};

function runFor(testCase) {
  const index = suite.cases.findIndex((item) => item.caseId === testCase.caseId);
  const shard = 1 + (index % 3);
  return JSON.parse(readFileSync(`evaluation/runs/${batch}-shard-${shard}/${testCase.caseId}.json`, 'utf8'));
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
  const run = runFor(testCase);
  const matches = run.result ? [...(run.result.exact ?? []), ...(run.result.similar ?? [])] : [];
  const sourceMatch = run.sourceRank ? matches[run.sourceRank - 1] : null;
  return {
    caseId: testCase.caseId,
    baseId: testCase.baseId,
    kind: testCase.kind,
    label: testCase.label,
    title: base.expected.title,
    sourceId: base.expected.sourceId,
    streamId: base.expected.streamId,
    query: testCase.query,
    operations: testCase.operations,
    addedNoteCount: testCase.addedNoteCount,
    finalNoteCount: testCase.finalNoteCount,
    status: run.status,
    sourceRank: run.sourceRank ?? null,
    sourceScore: sourceMatch?.ranking ?? null,
    sourceScores: sourceMatch?.scores ?? null,
    topTitle: matches[0]?.work?.title ?? null,
    topScore: matches[0]?.ranking ?? null,
    scoreMarginFromTop: sourceMatch && matches[0] ? sourceMatch.ranking - matches[0].ranking : null,
    elapsedMs: run.elapsedMs,
    missStage: missStage(run),
  };
});

const stats = Object.fromEntries(kinds.map((kind) => {
  const subset = rows.filter((row) => row.kind === kind);
  const found = subset.filter((row) => row.sourceRank);
  return [kind, {
    total: subset.length,
    found: found.length,
    top10: found.filter((row) => row.sourceRank <= 10).length,
    top5: found.filter((row) => row.sourceRank <= 5).length,
    top1: found.filter((row) => row.sourceRank === 1).length,
    meanSourceScore: found.length ? found.reduce((sum, row) => sum + row.sourceScore, 0) / found.length : null,
    misses: Object.fromEntries([...new Set(subset.filter((row) => !row.sourceRank).map((row) => row.missStage))]
      .map((stage) => [stage, subset.filter((row) => row.missStage === stage).length])),
  }];
}));

const originalByBase = new Map(rows.filter((row) => row.kind === 'original').map((row) => [row.baseId, row]));
for (const row of rows) {
  const original = originalByBase.get(row.baseId);
  row.rankChangeFromOriginal = row.sourceRank && original?.sourceRank ? row.sourceRank - original.sourceRank : null;
  row.scoreChangeFromOriginal = row.sourceScore != null && original?.sourceScore != null ? row.sourceScore - original.sourceScore : null;
}
const recoveredDistributed = rows.filter((row) => row.kind.startsWith('distributed-') && row.sourceRank);
const primaryRows = rows.filter((row) => row.kind === 'cluster-3' || row.kind === 'cluster-4');
const result = {
  schema: 'ornament-addition-results/1',
  generatedAt: new Date().toISOString(),
  interpretation: {
    primary: ['cluster-3', 'cluster-4'],
    stressControls: ['distributed-3', 'distributed-4'],
    note: 'Distributed additions change several local interval chains and are retained as stress/negative controls, not as a production recall requirement.',
  },
  sample: { bases: suite.bases.length, cases: suite.cases.length, uniqueSources: new Set(suite.bases.map((base) => base.expected.sourceId)).size },
  stats,
  recoveredDistributedCaseIds: recoveredDistributed.map((row) => row.caseId),
  rows,
};
writeFileSync(`${reportDir}/results.json`, `${JSON.stringify(result, null, 2)}\n`);

const summaryTable = [
  '| 구분 | 역할 | 회수 | Top 10 | Top 5 | Top 1 | 회수 결과 평균 점수 |',
  '|---|---|---:|---:|---:|---:|---:|',
  ...kinds.map((kind) => {
    const item = stats[kind];
    const role = kind.startsWith('distributed') ? '스트레스 대조군' : kind === 'original' ? '대조군' : '핵심 평가';
    return `| ${kindLabels[kind]} | ${role} | ${item.found}/${item.total} | ${item.top10} | ${item.top5} | ${item.top1} | ${item.meanSourceScore?.toFixed(1) ?? '—'} |`;
  }),
].join('\n');
const baseTable = [
  '| 원형 | 작품 | 원형 | 장식군 3 | 장식군 4 | 분산 3 | 분산 4 |',
  '|---|---|---:|---:|---:|---:|---:|',
  ...suite.bases.map((base) => `| ${base.baseId} | ${String(base.expected.title).replaceAll('|', '/')} | ${kinds.map((kind) => rows.find((row) => row.baseId === base.baseId && row.kind === kind)?.sourceRank ?? '—').join(' | ')} |`),
].join('\n');
const report = `# 짧은 장식음 3·4개 추가 실험\n\n${summaryTable}\n\n## 원형별 순위\n\n${baseTable}\n\n## 해석\n\n` +
  `핵심 평가인 한 위치의 국소 장식군은 3음 ${stats['cluster-3'].found}/15, 4음 ${stats['cluster-4'].found}/15가 Top100에 회수됐고 회수된 결과는 모두 Top10이었다. 분산 삽입은 여러 위치의 음정 연쇄를 동시에 바꾸므로 3음·4음 변형의 일반 성공 조건이 아니라 스트레스 대조군으로 분류한다. 분산형 실패를 근거로 검색 규칙을 완화하지 않는다.\n\n` +
  `국소 장식군도 3개 원형 이상에서 미회수되어, 짧은 삽입음을 무조건 무시하는 방식은 아직 안전하지 않다. 다음 개선 후보는 기둥음 정렬을 먼저 고정하고 동일한 짧은 국소 삽입군만 제한적으로 흡수하는 정렬이다. 오탐 대조군과 함께 검증하기 전에는 운영 규칙을 바꾸지 않는다.\n\n` +
  `## 한계\n\n15개 고유 원본의 편의 표본이다. 장식음 역할은 국소 음정 휴리스틱이며 화성 분석으로 확정하지 않았다. 장식군은 합성 turn-like 패턴이고 모든 작품에서 관습적으로 자연스럽다는 뜻은 아니다. Query와 변형 근거는 [suite.json](suite.json), 기계 판독 결과는 [results.json](results.json)에 저장했다.\n`;
writeFileSync(`${reportDir}/REPORT.md`, report);

const toolkit = new VerovioToolkit(await createModule());
toolkit.setOptions({ scale: 30, pageWidth: 1600, pageHeight: 1500, adjustPageHeight: true, breaks: 'auto', header: 'none', footer: 'none', svgViewBox: true });
let renderIndex = 0;
function draw(query, highlightedIds = []) {
  const prefix = `oa-${renderIndex += 1}-`;
  const notation = comparisonNotation(query.events, query.meter, prefix, highlightedIds);
  if (!toolkit.loadData(notation.mei)) throw new Error(`Verovio load failed for ${prefix}`);
  let svg = '';
  for (let page = 1; page <= toolkit.getPageCount(); page += 1) svg += toolkit.renderToSVG(page);
  svg = namespaceSvg(svg, prefix);
  const style = notation.redIds.map((id) => `[id="${prefix}${id}"],[id="${prefix}${id}"] *{fill:#b52d27!important;stroke:#b52d27!important}`).join('');
  return `<div class="notation"><style>${style}</style>${svg}</div>`;
}
const recoveredCards = recoveredDistributed.map((row) => {
  const original = originalByBase.get(row.baseId);
  const generated = row.query.events.filter((event) => event.generated).map((event) => event.id);
  const queryJson = JSON.stringify({ schema: 'musicanote-query', query: row.query }, null, 2);
  return `<article><h3>${esc(row.caseId)} · ${esc(row.title)}</h3><p>${esc(kindLabels[row.kind])} · 지정 원본 ${row.sourceRank}위 · 점수 ${row.sourceScore?.toFixed(1) ?? '—'} · 원형 ${original.sourceRank}위/${original.sourceScore?.toFixed(1) ?? '—'}점</p><div class="pair"><div><h4>원형 16음</h4>${draw(original.query)}</div><div><h4>분산 장식 Query ${row.finalNoteCount}음 · 붉은 음이 추가음</h4>${draw(row.query, generated)}</div></div><button data-copy="${esc(row.caseId)}">Query 복사</button><details><summary>Query JSON과 삽입 근거</summary><pre id="${esc(row.caseId)}">${esc(queryJson)}</pre><pre>${esc(JSON.stringify(row.operations, null, 2))}</pre></details></article>`;
}).join('');
const htmlSummaryRows = kinds.map((kind) => { const item = stats[kind]; return `<tr><td>${esc(kindLabels[kind])}</td><td>${kind.startsWith('distributed') ? '스트레스 대조군' : kind === 'original' ? '대조군' : '핵심 평가'}</td><td>${item.found}/${item.total}</td><td>${item.top10}</td><td>${item.top5}</td><td>${item.top1}</td><td>${item.meanSourceScore?.toFixed(1) ?? '—'}</td></tr>`; }).join('');
const html = `<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>짧은 장식음 3·4개 추가</title><style>body{font:15px system-ui;color:#203044;background:#edf1f5;margin:0}header,main{max-width:1400px;margin:18px auto;padding:22px;background:white;border-radius:14px}table{border-collapse:collapse;width:100%}th,td{border:1px solid #d7dee6;padding:8px;text-align:center}article{border:1px solid #d7dee6;border-radius:12px;padding:16px;margin:16px 0}.pair{display:grid;grid-template-columns:1fr 1fr;gap:18px}.notation{overflow-x:auto}.notation>svg{display:block;width:100%;min-width:520px;height:auto}button{padding:8px 12px}pre{white-space:pre-wrap;font-size:12px}@media(max-width:1000px){.pair{grid-template-columns:1fr}header,main{margin:0;border-radius:0;overflow-x:auto}}</style><header><h1>짧은 장식음 3·4개 추가 실험</h1><p>15개 고유 4/4 원형 · 75개 실제 검색</p><p>국소 장식군이 핵심 평가이며, 분산형은 강한 스트레스 대조군입니다.</p><a href="REPORT.md">보고서</a> · <a href="suite.json">Suite</a> · <a href="results.json">Results</a></header><main><h2>요약</h2><table><thead><tr><th>구분</th><th>역할</th><th>회수</th><th>Top10</th><th>Top5</th><th>Top1</th><th>평균 점수</th></tr></thead><tbody>${htmlSummaryRows}</tbody></table><h2>회수된 분산 3·4음 Query (${recoveredDistributed.length}건)</h2><p>분산형 성공을 권장 입력으로 간주하지 않습니다. 요청에 따라 회수된 사례를 원형과 나란히 표시합니다.</p>${recoveredCards}</main><script>document.querySelectorAll('[data-copy]').forEach((button)=>button.addEventListener('click',async()=>{await navigator.clipboard.writeText(document.getElementById(button.dataset.copy).textContent);const old=button.textContent;button.textContent='복사됨';setTimeout(()=>button.textContent=old,1200)}));</script></html>`;
writeFileSync(`${reportDir}/index.html`, html);
toolkit.destroy();
console.log(JSON.stringify({ stats, recoveredDistributed: recoveredDistributed.length, primaryFound: primaryRows.filter((row) => row.sourceRank).length }, null, 2));
