#!/usr/bin/env node
// Evidence-only offline regression runner. It does not modify search code, corpus, or DB.
import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, statSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import createModule from 'verovio/wasm';
import { VerovioToolkit } from 'verovio/esm';
import { createSearchWorker } from '../server/search-worker-client.mjs';
import { getWork } from '../server/search-api.mjs';
import { markXmlTargets } from '../server/xml-target-verification.mjs';

const out = resolve(process.argv[2] || 'evaluation/runs/small-regression-triad-v1');
const sourceCase = resolve('evaluation/exports/duple-meter-15-v1/cases/DM02-L12-original.json');
const sourceAssets = resolve('evaluation/exports/duple-meter-15-v1/base-assets/DM02-L12');
const dbPath = process.env.MUSICANOTE_SEARCH_DB || 'data/search-index-v2/search.sqlite';
const hash = value => createHash('sha256').update(value).digest('hex');
const source = JSON.parse(readFileSync(sourceCase, 'utf8'));
const identity = source.base;
const base = source.query;
const clone = value => JSON.parse(JSON.stringify(value));
const scale = (events, factor) => events.map(event => ({ ...event, durationRatio: event.durationRatio * factor }));
const mutateRhythm = events => events.map((event, index) => ({ ...event, durationRatio: index === 1 ? .5 : index === 2 ? 1 : event.durationRatio }));
const mutateMelody = events => events.map((event, index) => event.kind === 'note' ? ({ ...event, pitchMidi: event.pitchMidi + [0, 4, -3, 5, -4, 3, -5, 2, 6, -2, 4, -6][index] }) : event);
const weakStart = base.events.slice(1).map((event, index) => ({ ...event, id: `TRIAD-04-e${index}` }));
const makeQuery = (events, startsOnDownbeat) => ({ ...clone(base), startsOnDownbeat, events });
const cases = [
  { caseId: 'TRIAD-01-exact-corpus', category: 'global-tempo-scaling', expectation: 'Baseline corpus query; target source should be returned and aligned.', query: makeQuery(clone(base.events), true) },
  { caseId: 'TRIAD-02-global-tempo-x2', category: 'global-tempo-scaling', expectation: 'Uniformly doubled durations should be equivalent to baseline for scale-normalized rhythm evidence.', query: makeQuery(scale(base.events, 2), true) },
  { caseId: 'TRIAD-03-local-duration-rest-mismatch', category: 'global-tempo-scaling', expectation: 'A local duration change plus an inserted rest is not exact-equivalent; preserve its observed rank and score rather than asserting a rule.', query: makeQuery([{ id: 'TRIAD-03-rest', kind: 'rest', pitchMidi: null, durationRatio: .25 }, ...mutateRhythm(base.events)], true) },
  { caseId: 'TRIAD-04-pickup-weak-beat-bar-crossing', category: 'start-context', expectation: 'Actual pickup-origin source, weak-beat query start, and cross-bar span are retained as context; no rank assertion.', query: makeQuery(weakStart, false) },
  { caseId: 'TRIAD-05-same-intervals-different-rhythm', category: 'negative-control', expectation: 'Pitch intervals are retained while rhythm changes locally; inspect whether score is lower than the exact control without claiming a threshold.', query: makeQuery(mutateRhythm(base.events), true) },
  { caseId: 'TRIAD-06-same-rhythm-different-melody', category: 'negative-control', expectation: 'Rhythm is retained while melody changes; inspect whether score is lower than the exact control without claiming a threshold.', query: makeQuery(mutateMelody(base.events), true) },
];
const fingerprint = () => ({
  database: { path: dbPath, size: statSync(dbPath).size, mtimeMs: statSync(dbPath).mtimeMs },
  files: Object.fromEntries(['server/search-api.mjs', 'server/search-worker.mjs', 'server/xml-target-verification.mjs', 'scripts/run-small-regression-triad-v1.mjs'].map(path => [path, hash(readFileSync(path))])),
  sourceCase: { path: 'evaluation/exports/duple-meter-15-v1/cases/DM02-L12-original.json', sha256: hash(readFileSync(sourceCase)) },
});
if (existsSync(out)) throw new Error(`Output directory already exists: ${out}`);
mkdirSync(out, { recursive: true });
writeFileSync(join(out, 'source-context.json'), JSON.stringify({ identity, sourceCase: 'evaluation/exports/duple-meter-15-v1/cases/DM02-L12-original.json', sourceAssets: 'evaluation/exports/duple-meter-15-v1/base-assets/DM02-L12', context: JSON.parse(readFileSync(join(sourceAssets, 'events.json'), 'utf8')) }, null, 2));
writeFileSync(join(out, 'suite.json'), JSON.stringify({ schema: 'musicanote-small-regression-triad/v1', createdAt: new Date().toISOString(), selection: 'One actual 2/4 corpus source from duple-meter-15-v1; policy-eligible mixed contour with leaps/repetition, not an entirely stepwise or repeated-pitch query. Variants are fixed before execution.', policy: 'evaluation/query-selection-policy.json', fingerprint: fingerprint(), source: identity, cases }, null, 2));
process.env.MUSICANOTE_PROFILE_SEARCH = '1'; process.env.MUSICANOTE_RETRIEVAL_CACHE = '1';
const worker = createSearchWorker({ timeoutMs: 60000 });
const tk = new VerovioToolkit(await createModule());
tk.setOptions({ pageWidth: 2400, pageHeight: 1800, scale: 22, breaks: 'auto', header: 'none', footer: 'none', svgViewBox: true });
const summary = [];
try {
  for (const entry of cases) {
    const started = performance.now(); let record;
    try {
      const result = await worker.search(entry.query, 100);
      const all = [...result.exact, ...result.similar];
      const targetIndex = all.findIndex(match => match.work.workId === identity.workId && match.work.streamId === identity.streamId);
      const target = targetIndex < 0 ? null : all[targetIndex];
      const audit = { status: target ? 'not-rendered' : 'target-not-returned', workId: target?.work.workId ?? null, requested: 0, resolved: [], unresolved: [], renderedTargets: 0, pages: 0, visualListeningReview: false };
      if (target) {
        const targets = target.alignment.filter(pair => pair.queryIndex !== null && pair.candidateIndex !== null).map(pair => target.work.notes[pair.candidateIndex]).filter(Boolean);
        audit.requested = targets.length;
        if (targets.length) {
          const ordinals = targets.map(note => note.measureOrdinal).filter(Number.isFinite);
          const start = Math.min(...ordinals), end = Math.max(...ordinals);
          const work = getWork(target.work.workId, { ordinalStart: start, ordinalEnd: end, targets: targets.map(note => `${note.onset}:${note.pitchMidi}`).join(','), excerpt: '1' });
          const marked = markXmlTargets(work?.xml || '', target.work.streamId, targets, Number(work?.previewOrdinalStart || start) - 1);
          const loaded = tk.loadData(marked.xml); const pages = loaded ? tk.getPageCount() : 0;
          let svg = ''; for (let page = 1; page <= pages; page++) svg += tk.renderToSVG(page);
          Object.assign(audit, { status: loaded ? 'rendered' : 'load-failed', resolved: marked.resolved, unresolved: marked.unresolved, renderedTargets: marked.ids.filter(id => svg.includes(`id="${id}"`)).length, pages });
        }
      }
      record = { schema: 'musicanote-small-regression-result/v1', caseId: entry.caseId, category: entry.category, expectation: entry.expectation, status: 'completed', elapsedMs: Math.round(performance.now() - started), query: entry.query, source: identity, targetRank: targetIndex < 0 ? null : targetIndex + 1, targetCandidate: target ? { ranking: target.ranking, scores: target.scores, localSimilarity: target.localSimilarity, alignment: target.alignment, startMeasure: target.startMeasure, startBeat: target.startBeat, endMeasure: target.endMeasure } : null, response: result, renderingAudit: audit };
    } catch (error) { record = { caseId: entry.caseId, category: entry.category, status: 'failed', elapsedMs: Math.round(performance.now() - started), query: entry.query, source: identity, error: error.stack || error.message }; }
    writeFileSync(join(out, `${entry.caseId}.json`), JSON.stringify(record, null, 2));
    summary.push({ caseId: record.caseId, category: record.category, status: record.status, targetRank: record.targetRank ?? null, elapsedMs: record.elapsedMs, renderingAudit: record.renderingAudit ?? null });
    writeFileSync(join(out, 'summary.json'), JSON.stringify({ schema: 'musicanote-small-regression-summary/v1', completed: summary.length, total: cases.length, summary, limitations: ['Offline local index only; no corpus collection or DB sync.', 'SVG audit verifies target IDs in rendered SVG, not human layout quality or listening.', 'Ranks are raw stream results; edition duplicates are retained.'] }, null, 2));
    console.log(JSON.stringify(summary.at(-1)));
  }
} finally { tk.destroy(); await worker.close(); }
