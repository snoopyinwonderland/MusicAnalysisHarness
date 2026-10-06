#!/usr/bin/env node

import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, renameSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { getWork } from '../server/search-api.mjs';
import { positionedXmlNotes } from '../server/xml-target-verification.mjs';

const sha256 = value => createHash('sha256').update(value).digest('hex');
const atomicWrite = (path, value) => { mkdirSync(dirname(path), { recursive: true }); const temporary = `${path}.${process.pid}.tmp`; writeFileSync(temporary, value, 'utf8'); renameSync(temporary, path); };
const option = (argv, name, fallback = null) => { const index = argv.indexOf(`--${name}`); return index >= 0 ? argv[index + 1] : fallback; };
const xmlText = (block, tag) => block.match(new RegExp(`<${tag}[^>]*>([\\s\\S]*?)<\\/${tag}>`))?.[1]?.replace(/<[^>]+>/g, '').trim() ?? null;
const baseKey = item => `${item.expected.workId}:${item.expected.streamId}:${item.expected.baseStartIndex}`;

export function captureMotifContexts({ suite = 'motif-350', before = 2, after = 2 } = {}) {
  if (!/^motif-\d+$/.test(suite)) throw new Error('suite must look like motif-350');
  const casePath = resolve(`evaluation/${suite}/cases.jsonl`);
  if (!existsSync(casePath)) throw new Error(`Missing ${casePath}`);
  const cases = readFileSync(casePath, 'utf8').trim().split(/\r?\n/).filter(Boolean).map(JSON.parse);
  const groups = new Map();
  for (const item of cases) if (!groups.has(baseKey(item))) groups.set(baseKey(item), []); else void 0;
  for (const item of cases) groups.get(baseKey(item)).push(item);
  let baseNumber = 0;
  for (const group of groups.values()) {
    baseNumber += 1;
    const first = group[0], expected = first.expected;
    const start = Math.max(1, Number(expected.baseStartMeasure) - before), end = Number(expected.baseEndMeasure) + after;
    const targets = expected.baseTargets.map(target => `${target.onset}:${target.pitchMidi}`).join(',');
    const work = getWork(expected.workId, { ordinalStart: start, ordinalEnd: end, targets, excerpt: '1' });
    if (!work?.xml) throw new Error(`Could not create context for ${first.caseId}`);
    const assetId = `B${String(baseNumber).padStart(3, '0')}`, directory = resolve(`evaluation/${suite}/base-assets/${assetId}`);
    const xml = work.xml.endsWith('\n') ? work.xml : `${work.xml}\n`;
    const [, defaultStaff = '1', defaultVoice = '1'] = String(work.streamId).split(':');
    const soundingEvents = (work.notes || []).filter(note => Number(note.measureOrdinal) >= start && Number(note.measureOrdinal) <= end).map(note => ({
      id: note.id ?? null, kind: note.kind ?? 'note', pitchMidi: note.pitchMidi ?? null, spelling: note.spelling ?? null,
      durationQuarter: Number(note.durationRatio ?? note.duration ?? 0), onsetQuarter: Number(note.onset), measure: note.measure,
      measureOrdinal: Number(note.measureOrdinal), beat: Number(note.beat), partName: note.partName ?? work.partName,
      staff: String(note.staff ?? defaultStaff), voice: String(note.voice ?? defaultVoice), tie: note.tie ?? null,
    }));
    const notationEvents = positionedXmlNotes(xml, work.streamId, start - 1).map(note => ({
      partId: note.partId, staff: note.staff, voice: note.voice, measureOrdinal: note.measureOrdinal, beat: note.beat,
      pitchMidi: note.pitchMidi, isRest: note.isRest, chord: note.chord, durationDivisions: Number(xmlText(note.block, 'duration') || 0),
      noteType: xmlText(note.block, 'type'), dots: (note.block.match(/<dot\b/g) || []).length,
      timeModification: note.block.match(/<time-modification\b[\s\S]*?<\/time-modification>/)?.[0] ?? null,
      ties: [...note.block.matchAll(/<tie\s+type=["']([^"']+)["']/g)].map(match => match[1]),
      slurs: [...note.block.matchAll(/<slur\b[^>]*type=["']([^"']+)["'][^>]*>/g)].map(match => match[1]),
    }));
    const snapshot = {
      schema: 'musicanote-case-events/v1', suite, assetId, capturedAt: new Date().toISOString(),
      identity: { workId: work.workId, sourceId: work.sourceId, streamId: work.streamId, partName: work.partName },
      range: { focusStartMeasureOrdinal: expected.baseStartMeasure, focusEndMeasureOrdinal: expected.baseEndMeasure, contextStartMeasureOrdinal: start, contextEndMeasureOrdinal: end, beforeMeasures: before, afterMeasures: after },
      meter: work.meter, keyFifths: work.keyFifths, clef: { shape: work.clefShape, line: work.clefLine },
      targets: expected.baseTargets, soundingEvents, notationEvents,
    };
    atomicWrite(resolve(directory, 'context.musicxml'), xml);
    atomicWrite(resolve(directory, 'events.json'), `${JSON.stringify(snapshot, null, 2)}\n`);
    for (const item of group) item.knowledgeBase = {
      schema: 'musicanote-case-knowledge/v1', status: 'automatically-captured', capturedAt: snapshot.capturedAt,
      identity: snapshot.identity,
      sourceSnapshot: { xmlSha256: sha256(xml), eventsSha256: sha256(JSON.stringify(snapshot)), searchDatabaseWorkId: work.workId },
      focus: { startMeasureOrdinal: expected.baseStartMeasure, endMeasureOrdinal: expected.baseEndMeasure, targets: expected.baseTargets },
      context: { beforeMeasures: before, afterMeasures: after, startMeasureOrdinal: start, endMeasureOrdinal: end },
      assets: { musicXml: `base-assets/${assetId}/context.musicxml`, events: `base-assets/${assetId}/events.json`, sharedAssetId: assetId },
      classification: {
        phenomenonTypes: [`automatic-${item.mutation.kind}-variation`], musicalFunctions: [],
        contextualConditions: [`original motif selected by ${suite} heuristic`], exclusions: ['not a human-confirmed motif or musical-function judgment'], confidence: 'automatic-unreviewed',
      },
      ruleLearning: { candidateRules: [], counterexamples: [], reusableFor: ['retrieval-regression', 'ranking-regression', 'highlight-regression', 'mutation-robustness'] },
    };
  }
  atomicWrite(casePath, `${cases.map(item => JSON.stringify(item)).join('\n')}\n`);
  return { suite, cases: cases.length, baseAssets: groups.size, before, after };
}

function main(argv = process.argv.slice(2)) {
  const result = captureMotifContexts({ suite: option(argv, 'suite', 'motif-350'), before: Number(option(argv, 'before', 2)), after: Number(option(argv, 'after', 2)) });
  console.log(JSON.stringify(result, null, 2));
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) main();
