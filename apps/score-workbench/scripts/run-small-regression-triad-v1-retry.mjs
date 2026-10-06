#!/usr/bin/env node
// Evidence-only retry for the fixed suite; no production, corpus, or DB writes.
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import createModule from 'verovio/wasm';
import { VerovioToolkit } from 'verovio/esm';
import { createSearchWorker } from '../server/search-worker-client.mjs';
import { getWork } from '../server/search-api.mjs';
import { markXmlTargets } from '../server/xml-target-verification.mjs';

const input = resolve('evaluation/runs/small-regression-triad-v1/suite.json');
const out = resolve(process.argv[2] || 'evaluation/runs/small-regression-triad-v1-retry');
if (existsSync(out)) throw Error(`New output required: ${out}`);
const suite = JSON.parse(readFileSync(input, 'utf8'));
mkdirSync(out, { recursive: true });
writeFileSync(join(out, 'suite.json'), JSON.stringify(suite, null, 2));
const worker = createSearchWorker({ timeoutMs: 60000 });
const tk = new VerovioToolkit(await createModule());
tk.setOptions({ pageWidth: 2400, pageHeight: 1800, scale: 22, breaks: 'auto', header: 'none', footer: 'none', svgViewBox: true });
const brief = [];
try { for (const entry of suite.cases) {
  const started = performance.now(); let row;
  try {
    const response = await worker.search(entry.query, 100), all = [...response.exact, ...response.similar];
    const targetIndex = all.findIndex(match => match.work.workId === suite.source.workId && match.work.streamId === suite.source.streamId);
    const target = targetIndex < 0 ? null : all[targetIndex];
    const audit = { status: target ? 'no-aligned-targets' : 'target-not-returned', requested: 0, resolved: [], unresolved: [], renderedTargets: 0, pages: 0, visualListeningReview: false };
    if (target) {
      const notes = target.alignment.filter(pair => pair.queryIndex !== null && pair.candidateIndex !== null).map(pair => target.work.notes[pair.candidateIndex]).filter(Boolean);
      audit.requested = notes.length;
      if (notes.length) {
        const ordinals = notes.map(note => note.measureOrdinal), start = Math.min(...ordinals), end = Math.max(...ordinals);
        const work = getWork(target.work.workId, { ordinalStart: start, ordinalEnd: end, targets: notes.map(note => `${note.onset}:${note.pitchMidi}`).join(','), excerpt: '1' });
        const marked = markXmlTargets(work?.xml || '', target.work.streamId, notes, Number(work?.previewOrdinalStart || start) - 1);
        const loaded = tk.loadData(marked.xml), pages = loaded ? tk.getPageCount() : 0; let svg = '';
        for (let page = 1; page <= pages; page++) svg += tk.renderToSVG(page);
        Object.assign(audit, { status: loaded ? 'rendered' : 'load-failed', resolved: marked.resolved, unresolved: marked.unresolved, renderedTargets: marked.ids.filter(id => svg.includes(`id="${id}"`)).length, pages });
      }
    }
    row = { schema: 'musicanote-small-regression-result/v1', caseId: entry.caseId, category: entry.category, expectation: entry.expectation, status: 'completed', elapsedMs: Math.round(performance.now() - started), query: entry.query, source: suite.source, targetRank: targetIndex < 0 ? null : targetIndex + 1, targetCandidate: target ? { ranking: target.ranking, scores: target.scores, localSimilarity: target.localSimilarity, alignment: target.alignment, startMeasure: target.startMeasure, startBeat: target.startBeat, endMeasure: target.endMeasure } : null, response, renderingAudit: audit };
  } catch (error) { row = { caseId: entry.caseId, category: entry.category, status: 'failed', elapsedMs: Math.round(performance.now() - started), query: entry.query, source: suite.source, error: error.stack || error.message }; }
  writeFileSync(join(out, `${entry.caseId}.json`), JSON.stringify(row, null, 2));
  brief.push({ caseId: row.caseId, category: row.category, status: row.status, targetRank: row.targetRank ?? null, elapsedMs: row.elapsedMs, renderingAudit: row.renderingAudit ?? null });
  writeFileSync(join(out, 'summary.json'), JSON.stringify({ schema: 'musicanote-small-regression-summary/v1', completed: brief.length, total: suite.cases.length, summary: brief, limitations: ['Offline local index only; no collection or DB sync.', 'SVG audit checks target IDs, not human layout or listening.'] }, null, 2));
  console.log(JSON.stringify(brief.at(-1)));
} } finally { tk.destroy(); await worker.close(); }
