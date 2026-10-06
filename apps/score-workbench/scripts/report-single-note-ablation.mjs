import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import createModule from 'verovio/wasm';
import { VerovioToolkit } from 'verovio/esm';
import { getWork } from '../server/search-api.mjs';
import { markXmlTargets } from '../server/xml-target-verification.mjs';

const reportDir = process.argv[2] || 'evaluation/reports/single-note-ablation-cant-smile-v1';
const runSlug = process.argv[3] || 'single-note-ablation-cant-smile-v1';
const suite = JSON.parse(readFileSync(`${reportDir}/suite.json`, 'utf8'));
const trimmed = suite.schema.includes('trimmed-v2');
const base = suite.bases[0];
const notes = base.independentFeatures;
const loadRun = (item) => {
  const shard = Number(item.deletedNoteIndex || 0) % 2 === 0 ? 1 : 2;
  return JSON.parse(readFileSync(`evaluation/runs/${runSlug}-shard-${shard}/${item.caseId}.json`, 'utf8'));
};
const rows = suite.cases.map((item) => {
  const run = loadRun(item);
  const hit = [...(run.result?.exact || []), ...(run.result?.similar || [])]
    .find((result) => result.work?.sourceId === base.expected.sourceId);
  return {
    caseId: item.caseId,
    noteIndex: item.deletedNoteIndex,
    note: item.deletedEvent || null,
    rank: run.sourceRank,
    ranking: hit?.ranking ?? null,
    local: hit?.localSimilarity ?? null,
    scores: hit?.scores ?? null,
    rejections: run.trace?.rejections || {},
    elapsedMs: run.elapsedMs,
    query: item.query,
  };
});
const original = rows[0];
for (const row of rows.slice(1)) {
  row.scoreDrop = row.ranking === null ? null : original.ranking - row.ranking;
  row.sensitivity = row.ranking === null ? 'not-returned' : row.scoreDrop >= 15 ? 'high' : row.scoreDrop >= 8 ? 'medium' : row.scoreDrop >= 3 ? 'low' : 'stable';
}
const byIndex = new Map(rows.slice(1).map((row) => [row.noteIndex, row]));
const fmt = (value, digits = 1) => value === null || value === undefined ? '—' : Number(value).toFixed(digits);
const color = (row) => ({ 'not-returned': '#a21d25', high: '#d84a32', medium: '#e69a35', low: '#7a9a77', stable: '#57718f' }[row?.sensitivity] || '#222');
const escapeHtml = (value) => String(value).replace(/[&<>"']/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[character]));

const firstMeasure = Math.min(...notes.map((note) => note.measure));
const lastMeasure = Math.max(...notes.map((note) => note.measure));
const sourceWork = getWork(base.expected.workId, { ordinalStart: firstMeasure, ordinalEnd: lastMeasure, excerpt: '1' });
if (!sourceWork?.xml) throw new Error('Original MusicXML excerpt is unavailable.');
const targets = notes.map((note) => ({ measureOrdinal: note.measure, beat: note.beat, pitchMidi: note.pitchMidi }));
const marked = markXmlTargets(sourceWork.xml, base.expected.streamId, targets, Number(sourceWork.previewOrdinalStart || firstMeasure) - 1);
if (marked.resolved !== notes.length) throw new Error(`MusicXML target mapping ${marked.resolved}/${notes.length}`);
const toolkit = new VerovioToolkit(await createModule());
toolkit.setOptions({ scale: 34, pageWidth: 1700, pageHeight: 2200, adjustPageHeight: true, breaks: 'auto', header: 'none', footer: 'none', svgViewBox: true });
if (!toolkit.loadData(marked.xml)) throw new Error('Verovio could not load the original MusicXML excerpt.');
let originalScoreSvg = '';
for (let page = 1; page <= toolkit.getPageCount(); page += 1) originalScoreSvg += `<section class="score-page">${toolkit.renderToSVG(page)}</section>`;
for (const id of marked.ids) if (!originalScoreSvg.includes(`id="${id}"`)) throw new Error(`Rendered MusicXML note is missing: ${id}`);
const notationStyles = marked.ids.map((id, index) => `#${id},#${id} *{fill:${color(byIndex.get(index + 1))}!important;stroke:${color(byIndex.get(index + 1))}!important}`).join('');
toolkit.destroy();

const onset = [];
let cursor = 0;
for (const event of base.sourceEvents) {
  if (event.kind === 'note') onset.push(cursor);
  cursor += event.durationRatio;
}
const width = 1120;
const x = (index) => 55 + (onset[index] / Math.max(1, cursor)) * 1010;
const y = (pitch) => 121 - (pitch - 59) * 5;
const staff = Array.from({ length: 5 }, (_, index) => `<line x1="35" y1="${80 + index * 10}" x2="1090" y2="${80 + index * 10}"/>`).join('');
const noteSvg = notes.map((note, index) => {
  const row = byIndex.get(index + 1);
  const cx = x(index), cy = y(note.pitchMidi), stem = note.durationRatio < 4 ? `<line x1="${cx + 6}" y1="${cy}" x2="${cx + 6}" y2="${cy - 30}" stroke="${color(row)}" stroke-width="2"/>` : '';
  return `<g><ellipse cx="${cx}" cy="${cy}" rx="7" ry="5" transform="rotate(-18 ${cx} ${cy})" fill="${note.durationRatio >= 2 ? '#fff' : color(row)}" stroke="${color(row)}" stroke-width="2"/>${stem}<text x="${cx}" y="150" text-anchor="middle" class="n">${index + 1}</text><text x="${cx}" y="166" text-anchor="middle" class="d">${row.rank === null ? '미회수' : `−${fmt(row.scoreDrop)}`}</text></g>`;
}).join('');
const scoreKey = notes.map((note, index) => `<span style="border-color:${color(byIndex.get(index + 1))}"><b>${index + 1}</b> ${escapeHtml(note.spelling)} · ${note.measure}마디 ${fmt(note.beat, 2)}박</span>`).join('');

const summaryRows = rows.slice(1).map((row) => `<tr>
  <td>${row.noteIndex}</td><td><b>${escapeHtml(row.note.spelling)}</b></td><td>${fmt(row.note.durationRatio, 3)}</td><td>${row.note.measure}:${fmt(row.note.beat, 2)}</td>
  <td>${escapeHtml(row.note.metricClass)}</td><td>${escapeHtml(row.note.contourRole)}</td><td>${row.rank ?? 'Top100 밖'}</td><td>${fmt(row.ranking)}</td><td class="drop" style="color:${color(row)}">${row.ranking === null ? '미회수' : `−${fmt(row.scoreDrop)}`}</td>
  <td>${fmt(row.scores?.rhythm)}</td><td>${fmt(row.scores?.meter)}</td><td>${fmt(row.scores?.structural)}</td><td><button data-copy="${row.caseId}">Query 복사</button></td>
</tr>`).join('');
const queryMap = Object.fromEntries(rows.map((row) => [row.caseId, { schema: 'musicanote-query', query: row.query }]));
const interpretation = trimmed ? {
  reviewStatus: 'diagnostic-rerun-after-user-boundary-correction',
  removedPrecedingPhraseNotes: ['F#4', 'G4'],
  resultShift: 'Deleting the former critical B4 now keeps rank 1; deleting note 12 A4 is the only Top100 miss.',
  userMusicalReview: {
    downbeatG: 'A large change after deleting the G between the upbeat A and F# is musically plausible.',
    repeatedFSharp: 'The measure-34 F# is preceded by the same pitch, so its deletion can have less effect.',
    laterLongNotes: 'The later long notes are reasonably expected to affect the result more.',
    conclusion: 'Leave-one-note-out sensitivity is not reliable enough to identify important and unimportant notes by itself.',
  },
  confounds: ['edge-vs-interior-interval-count', 'duration-absorption-changes-neighbor-sustain', 'complete-phrase-extent-not-independently-adjudicated'],
  caution: 'Boundary correction materially changed sensitivity. Do not treat raw score drop as pillar truth.',
} : {
  reviewStatus: 'inconclusive-invalid-query-boundary',
  userReviewedPhraseEndingNotes: [1, 2],
  userReviewedLowImportanceNote: 6,
  userReviewedMotifEndingNotes: [7, 8],
  confounds: ['query-crosses-a-phrase-boundary', 'edge-deletion-changes-one-interval-but-interior-deletion-changes-two', 'duration-absorption-changes-the-preceding-sustain'],
  caution: 'Sensitivity is an engine-response diagnostic, not a pillar label. This pilot must not train or calibrate the search rules.',
};
const results = {
  schema: 'musicanote-single-note-ablation-result/v1',
  createdAt: new Date().toISOString(),
  work: base.expected,
  original: { rank: original.rank, ranking: original.ranking, scores: original.scores },
  rows,
  interpretation,
};
mkdirSync(reportDir, { recursive: true });
writeFileSync(`${reportDir}/results.json`, `${JSON.stringify(results, null, 2)}\n`);

const md = trimmed ? `# 앞 Phrase 종결 제거 후 단일 음 삭제 — CAN'T SMILE WITHOUT YOU\n\n앞의 F♯–G와 선행 쉼표를 제거해 33마디 B3부터 시작하는 14음 Query로 다시 실행했다. 원형은 1위·100점이다.\n\n- 새 12번 A4(36마디 3박)를 삭제했을 때만 원곡이 Top100에서 사라졌다.\n- 이전 실행에서 미회수였던 B4(이제 7번)는 삭제해도 1위를 유지하고 총점 80.5였다.\n- 사용자가 낮은 중요도로 검토한 33마디 마지막 F♯(이제 4번)는 삭제해도 1위를 유지하고 5.9점만 하락했다. 이전 18.2점 하락보다 크게 완화됐다.\n- upbeat 라–파♯ 사이의 솔이 빠질 때 큰 변화가 생기는 것은 음악적으로 타당할 수 있다.\n- 34마디 파♯은 직전의 같은 파♯과 반복되므로 하나가 빠져도 영향이 작은 것이 설명된다. 뒤의 긴 음들은 상대적으로 영향이 커질 가능성이 있다.\n\n앞 경계를 고친 것만으로 음별 민감도 지도가 크게 바뀌었다. 일부 반응은 음악적으로 설명되지만, 박자 위치·반복음·긴 음가·앞뒤 interval 변화·sustain 흡수가 한꺼번에 섞인다. 따라서 이 방법만으로 중요한 음과 중요하지 않은 음을 판정하지 않으며, 독립 Phrase·metric·화성 분석 뒤의 보조 진단으로만 보존한다.\n` : `# 단일 음 삭제 민감도 — CAN'T SMILE WITHOUT YOU\n\n상태: **판정 불가 파일럿(inconclusive-invalid-query-boundary)**. 원형은 1위·100점이며 각 음을 하나씩 제거했지만, Query 자체가 하나의 완결된 Phrase/Motif가 아니다.\n\n- 1·2번 F♯–G는 사용자 악보 검토상 앞 Phrase의 종결이다.\n- 33마디에서 Query를 시작한다고 보면 6번의 마지막 짧은 F♯는 없어도 무방한 낮은 중요도 음이다. 그러나 삭제 시 18.2점 하락해 검색 민감도가 음악적 중요도를 과장했다.\n- 7·8번(34마디)은 Motif의 마지막 부분이라는 사용자 검토와 높은 민감도가 같은 방향이지만, 잘못된 시작 경계와 위치별 interval 변화량 차이 때문에 이것만으로 신뢰성을 주장할 수 없다.\n- 시작·끝 음 삭제는 interval 하나만 바꾸지만 내부 음 삭제는 앞뒤 interval 두 개를 바꾼다. 또한 삭제 음가를 앞 이벤트에 흡수하는 방식은 앞 음의 sustain도 바꾼다.\n\n따라서 이 실행은 기둥음 정답이나 검색 규칙 학습에 사용하지 않고, 경계 및 삭제 연산 설계의 실패 사례로 보존한다. 다음 실험은 사람이 확인한 완전한 Phrase 안에서 위치 편향을 통제한 대조군과 함께 수행해야 한다.\n`;
writeFileSync(`${reportDir}/REPORT.md`, md);

const headerSummary = trimmed
  ? `<p>Vln. · 앞 Phrase 종결 제거 · 원형 ${notes.length}음 · 33마디 B3 시작 · 원형 검색 1위 / 100점</p>`
  : `<p>Vln. · 원형 ${notes.length}음 · 원형 검색 1위 / 100점</p>`;
const warningHtml = trimmed
  ? `<div class="card warning"><b>경계 수정 재실험입니다.</b> 앞 Phrase의 종결 F♯–G와 선행 쉼표를 제거했습니다. 경계 수정만으로 음별 민감도가 크게 달라졌으므로, 색과 점수 하락은 기둥음 판정이 아니라 검색기 반응 진단으로만 봅니다.</div>`
  : `<div class="card warning"><b>판정 불가 파일럿입니다.</b> Query가 Phrase 경계를 가로지르며, 1·2번은 앞 Phrase의 종결입니다. 색은 검색기 민감도일 뿐 기둥음 중요도가 아니며 이 결과는 학습·점수 보정에 사용하지 않습니다.</div>`;
const interpretationHtml = trimmed
  ? `<div class="card"><h2>경계 수정 후 해석</h2><p><b>4번 F♯(33마디 마지막 음)</b>는 사용자가 낮은 중요도로 검토한 음입니다. 삭제해도 1위를 유지했고 총점 하락은 5.9점으로, 이전 경계의 18.2점보다 크게 줄었습니다.</p><p><b>upbeat 라–파♯ 사이의 솔</b>이 빠졌을 때 큰 변화가 생기는 것은 그 솔의 박자 위치를 고려하면 타당할 수 있습니다. <b>34마디 파♯</b>은 바로 앞의 같은 파♯과 반복되므로 하나가 빠져도 영향이 작은 것으로 설명할 수 있고, 뒤의 긴 음들은 상대적으로 큰 영향을 줄 가능성이 있습니다.</p><p>이전 실행에서 Top100 밖이었던 <b>7번 B4</b>는 이번에는 1위·80.5점으로 회수됐고, <b>12번 A4</b>만 Top100 밖이 됐습니다. 시작 경계를 두 음 고친 것만으로 민감도 지도가 바뀐 것은 Phrase 경계의 중요성을 확인하는 동시에, 이 방법 단독으로 기둥음을 판정하기 어렵다는 증거입니다.</p><p><b>결론:</b> 일부 반응은 음악적으로 납득되지만 박자 위치, 동일음 반복, 음가, 앞뒤 interval 변화와 sustain 흡수가 섞여 있습니다. 단일 음 삭제는 중요음 판별기가 아니라 독립 분석 결과를 점검하는 보조 진단으로만 사용합니다. 약박 시작 때문에 이번 Downbeat 점수도 모두 0이며 검색 규칙은 변경하지 않았습니다.</p></div>`
  : `<div class="card"><h2>검토 후 해석</h2><p><b>1·2번 F♯–G</b>는 앞 Phrase에서 끝나는 부분이므로 이 Query의 시작 자체가 실제 사용자 입력을 잘 대표하지 않습니다.</p><p><b>6번 F♯</b>는 33마디 끝의 낮은 중요도 음인데도 삭제 시 18.2점 하락했습니다. 이는 기둥음 검출 성공이 아니라 내부 음 삭제가 앞뒤 interval 두 개와 앞 음 sustain을 함께 바꾸면서 생긴 거짓 양성에 가깝습니다.</p><p><b>7·8번</b>은 34마디 Motif 종결부라는 검토와 높은 민감도가 일치하지만, 표본 경계와 삭제 위치의 기계적 비용이 통제되지 않아 신뢰성 근거로 사용하지 않습니다.</p></div>`;

const html = `<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>단일 음 삭제 민감도</title><style>
body{margin:0;background:#f5f2e9;color:#17201d;font:14px/1.55 system-ui,'Noto Sans KR',sans-serif}main{max-width:1220px;margin:auto;padding:48px 24px 90px}h1{font:42px Georgia,'Noto Serif KR',serif;margin:8px 0}h2{margin-top:38px}.k{color:#c6533f;font:12px monospace}.card{background:#fff;border:1px solid #d9d4c8;padding:22px;margin:22px 0}.warning{border-left:5px solid #d84a32}.legend{display:flex;gap:18px;flex-wrap:wrap}.legend i{width:12px;height:12px;display:inline-block;margin-right:5px}svg{width:100%;height:auto;background:#fffdf7}svg line{stroke:#817d73;stroke-width:1}.n{font:11px monospace}.d{font:9px monospace;fill:#555}table{width:100%;border-collapse:collapse;background:#fff;font-size:12px}th,td{border-bottom:1px solid #e1ddd2;padding:8px;text-align:left;white-space:nowrap}th{position:sticky;top:0;background:#ebe7dc}.drop{font-weight:800}button{border:1px solid #aaa;background:#fff;padding:5px 8px;cursor:pointer}.scroll{overflow:auto;max-height:650px}code{background:#ece8dc;padding:2px 5px}</style></head><body><main>
<div class="k">LEAVE-ONE-NOTE-OUT · DIAGNOSTIC ONLY</div><h1>CAN'T SMILE WITHOUT YOU</h1>${headerSummary}
${warningHtml}
<div class="legend"><span><i style="background:#a21d25"></i>미회수</span><span><i style="background:#d84a32"></i>15점 이상 하락</span><span><i style="background:#e69a35"></i>8점 이상</span><span><i style="background:#7a9a77"></i>약 3점</span><span><i style="background:#57718f"></i>안정</span></div>
<style>.xml-score{overflow:auto;border:1px solid #ddd8ca;background:#fff}.score-page{min-width:900px}.score-page+.score-page{border-top:2px dashed #d4cec0}.score-page svg{display:block}.score-key{display:flex;flex-wrap:wrap;gap:7px;margin-top:14px}.score-key span{border-left:6px solid;padding:5px 8px;background:#f3f0e8;font-size:11px}</style>
<div class="card"><h2>원본 MusicXML 악보</h2><p>원본의 실제 파트·마디·음가·쉼표·보표를 Verovio로 렌더링했습니다. 색은 각 실제 notehead의 삭제 민감도이며, 아래 번호표로 음을 확인할 수 있습니다.</p><div class="xml-score"><style>${notationStyles}</style>${originalScoreSvg}</div><div class="score-key">${scoreKey}</div></div>
<details class="card"><summary>간이 민감도 축 보기</summary><svg viewBox="0 0 ${width} 185" role="img" aria-label="음별 삭제 민감도 간이 축">${staff}${noteSvg}</svg></details>
${interpretationHtml}
<h2>음별 결과</h2><div class="scroll"><table><thead><tr><th>#</th><th>음</th><th>음가</th><th>마디:박</th><th>박자 위치</th><th>윤곽 역할</th><th>순위</th><th>총점</th><th>하락</th><th>Rhythm</th><th>Downbeat</th><th>Schenker</th><th></th></tr></thead><tbody>${summaryRows}</tbody></table></div>
<p>MusicXML 매핑 ${marked.resolved}/${marked.requested}, Verovio ${toolkit ? '검증 완료' : '실패'} · 재현 자료: <code>suite.json</code>, <code>results.json</code>, <code>REPORT.md</code></p>
</main><script>const q=${JSON.stringify(queryMap).replace(/</g, '\\u003c')};document.addEventListener('click',async e=>{const id=e.target.dataset.copy;if(!id)return;await navigator.clipboard.writeText(JSON.stringify(q[id],null,2));e.target.textContent='복사됨';setTimeout(()=>e.target.textContent='Query 복사',1000)});</script></body></html>`;
writeFileSync(`${reportDir}/index.html`, html);
console.log(JSON.stringify({ reportDir, rows: rows.length, missing: rows.filter((row) => row.rank === null).map((row) => row.noteIndex) }, null, 2));
