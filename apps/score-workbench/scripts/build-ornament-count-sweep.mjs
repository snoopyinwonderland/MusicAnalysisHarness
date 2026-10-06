import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';

const outputDir = process.argv[2] ?? 'evaluation/reports/ornament-count-sweep-v1';
const source = JSON.parse(readFileSync('evaluation/reports/structural-100-preview-v1/suite.json', 'utf8'));
const NOTE_COUNT = 16;
const CLUSTER_SPAN = 0.5;
const chromatic = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
const spelling = (midi) => `${chromatic[((midi % 12) + 12) % 12]}${Math.floor(midi / 12) - 1}`;
const round = (value) => Math.round(value * 1e6) / 1e6;
const totalDuration = (events) => round(events.reduce((sum, event) => sum + Number(event.durationRatio), 0));
const noteCount = (events) => events.filter((event) => event.kind === 'note').length;

function sourceEvents(base) {
  const notes = base.context.slice(0, NOTE_COUNT);
  if (notes.length !== NOTE_COUNT) throw new Error(`${base.baseId}: insufficient source notes`);
  const events = [];
  for (let index = 0; index < notes.length; index += 1) {
    const current = notes[index];
    events.push({ id: `${base.baseId.toLowerCase()}-src-${String(index + 1).padStart(2, '0')}`, kind: 'note', pitchMidi: current.p, spelling: current.s ?? spelling(current.p), durationRatio: round(current.d), source: { measure: current.m, beat: current.b, onset: current.o } });
    const next = notes[index + 1];
    if (!next) continue;
    const gap = round(next.o - (current.o + current.d));
    if (gap > 1e-5) events.push({ id: `${base.baseId.toLowerCase()}-rest-${String(index + 1).padStart(2, '0')}`, kind: 'rest', pitchMidi: null, durationRatio: gap, generatedFromSourceGap: true });
    if (gap < -1e-5) throw new Error(`${base.baseId}: overlapping context`);
  }
  return events;
}

function chooseHost(events) {
  const candidates = events.map((event, index) => ({ event, index }))
    .filter(({ event, index }) => event.kind === 'note' && index > 0 && index < events.length - 1 && event.durationRatio >= CLUSTER_SPAN + 0.25)
    .sort((a, b) => b.event.durationRatio - a.event.durationRatio || a.index - b.index);
  if (!candidates.length) throw new Error('No common 0.5-beat cluster host');
  return candidates[Math.floor(candidates.length / 2)];
}

const patterns = {
  3: [1, -1, 0],
  4: [1, 0, -1, 0],
  5: [1, 0, -1, 1, 0],
  6: [1, 0, -1, 0, 1, 0],
};

function decorate(sourceEventsValue, hostIndex, count, caseId) {
  const events = structuredClone(sourceEventsValue);
  const host = events[hostIndex];
  const hostBefore = host.durationRatio;
  host.durationRatio = round(host.durationRatio - CLUSTER_SPAN);
  const unit = CLUSTER_SPAN / count;
  const durations = Array.from({ length: count }, (_, index) => index === count - 1
    ? round(CLUSTER_SPAN - round(unit) * (count - 1))
    : round(unit));
  const inserted = patterns[count].map((offset, index) => {
    const pitch = host.pitchMidi + offset;
    return { id: `${caseId.toLowerCase()}-orn-${String(index + 1).padStart(2, '0')}`, kind: 'note', pitchMidi: pitch, spelling: spelling(pitch), durationRatio: durations[index], generated: true, ornamentRole: offset === 0 ? 'return-tone' : 'neighbor' };
  });
  events.splice(hostIndex + 1, 0, ...inserted);
  return {
    events,
    operation: { type: 'fixed-span-local-ornament-cluster', hostId: host.id, hostPitchMidi: host.pitchMidi, hostBefore, hostAfter: host.durationRatio, clusterSpan: CLUSTER_SPAN, insertedCount: count, insertedIds: inserted.map((event) => event.id), durations, contourOffsets: patterns[count] },
  };
}

function query(events, startsOnDownbeat) {
  return { version: 1, mode: 'melody_rhythm', meter: '4/4', startsOnDownbeat, events: events.map(({ source: _source, ...event }) => event), absoluteExactOnly: false, includeRests: true };
}

const selected = source.bases.filter((base) => base.query.meter === '4/4' && base.baseId !== 'B16' && base.context.length >= NOTE_COUNT).slice(0, 15);
if (selected.length !== 15) throw new Error(`Expected 15 controlled bases, got ${selected.length}`);
const bases = [];
const cases = [];
for (let baseIndex = 0; baseIndex < selected.length; baseIndex += 1) {
  const sourceBase = selected[baseIndex];
  const baseId = `OC${String(baseIndex + 1).padStart(2, '0')}`;
  const events = sourceEvents(sourceBase);
  const duration = totalDuration(events);
  const host = chooseHost(events);
  bases.push({ baseId, sourceBaseId: sourceBase.baseId, expected: sourceBase.expected, meter: '4/4', sourceNoteCount: NOTE_COUNT, sourceDuration: duration, host: { eventId: host.event.id, eventIndex: host.index, pitchMidi: host.event.pitchMidi, durationRatio: host.event.durationRatio, source: host.event.source }, sourceEvents: events, qualification: 'Existing XML-audited stream; fixed-span synthetic neighbor cluster, not harmonic adjudication.' });
  const variants = [{ kind: 'original', count: 0, events: structuredClone(events), operation: null }];
  for (const count of [3, 4, 5, 6]) variants.push({ kind: `cluster-${count}`, count, ...decorate(events, host.index, count, `${baseId}-cluster-${count}`) });
  for (const variant of variants) {
    const caseId = `${baseId}-${variant.kind}`;
    if (totalDuration(variant.events) !== duration) throw new Error(`${caseId}: duration changed`);
    if (noteCount(variant.events) !== NOTE_COUNT + variant.count) throw new Error(`${caseId}: note count changed unexpectedly`);
    if (variant.events.some((event) => event.generated && event.durationRatio > 0.25)) throw new Error(`${caseId}: ornament exceeds sixteenth`);
    cases.push({ caseId, baseId, kind: variant.kind, addedNoteCount: variant.count, finalNoteCount: NOTE_COUNT + variant.count, clusterSpan: variant.count ? CLUSTER_SPAN : 0, operation: variant.operation, totalDuration: duration, query: query(variant.events, sourceBase.query.startsOnDownbeat) });
  }
}

const suite = {
  schema: 'ornament-count-sweep/1',
  createdAt: new Date().toISOString(),
  selection: '15 distinct 4/4 XML-audited sources. Same host and fixed 0.5-beat cluster span for 3–6 tones. B16 replaced by B14 before execution because it had no host long enough.',
  controlledVariables: { sourceNotes: NOTE_COUNT, clusterSpan: CLUSTER_SPAN, counts: [3, 4, 5, 6], sameHostWithinBase: true, downstreamOnsetsPreserved: true },
  decisionRule: 'Measure retrieval/admission and score degradation by count. Rank is secondary and corpus-relative.',
  bases,
  cases,
  limitations: ['Synthetic chromatic neighbor figures without harmonic adjudication.', 'Per-note duration changes with count so total ornament span stays fixed.', 'Convenience sample; no production rule changes.'],
};
mkdirSync(outputDir, { recursive: false });
writeFileSync(`${outputDir}/suite.json`, `${JSON.stringify(suite, null, 2)}\n`, { flag: 'wx' });
console.log(JSON.stringify({ outputDir, bases: bases.length, cases: cases.length, byKind: Object.fromEntries(['original', 'cluster-3', 'cluster-4', 'cluster-5', 'cluster-6'].map((kind) => [kind, cases.filter((item) => item.kind === kind).length])) }, null, 2));
