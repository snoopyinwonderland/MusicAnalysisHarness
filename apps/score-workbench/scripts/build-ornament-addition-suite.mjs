import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';

const outputDir = process.argv[2] ?? 'evaluation/reports/ornament-addition-75-v1';
const source = JSON.parse(readFileSync('evaluation/reports/structural-100-preview-v1/suite.json', 'utf8'));
const NOTE_COUNT = 16;
const excludedBaseIds = new Set(['B14']); // stepwise/repeated source: no defensible distributed insertion sites
const chromatic = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
const spelling = (midi) => `${chromatic[((midi % 12) + 12) % 12]}${Math.floor(midi / 12) - 1}`;
const round = (value) => Math.round(value * 1e6) / 1e6;
const clone = (value) => structuredClone(value);
const noteCount = (events) => events.filter((event) => event.kind === 'note').length;
const totalDuration = (events) => round(events.reduce((sum, event) => sum + Number(event.durationRatio), 0));

function sourceEvents(base) {
  const notes = base.context.slice(0, NOTE_COUNT);
  if (notes.length !== NOTE_COUNT) throw new Error(`${base.baseId}: expected ${NOTE_COUNT} source notes`);
  const events = [];
  for (let index = 0; index < notes.length; index += 1) {
    const current = notes[index];
    events.push({
      id: `${base.baseId.toLowerCase()}-src-${String(index + 1).padStart(2, '0')}`,
      kind: 'note',
      pitchMidi: current.p,
      spelling: current.s ?? spelling(current.p),
      durationRatio: round(current.d),
      source: { measure: current.m, beat: current.b, onset: current.o },
    });
    const next = notes[index + 1];
    if (next) {
      const gap = round(next.o - (current.o + current.d));
      if (gap > 1e-5) events.push({
        id: `${base.baseId.toLowerCase()}-rest-${String(index + 1).padStart(2, '0')}`,
        kind: 'rest',
        pitchMidi: null,
        durationRatio: gap,
        generatedFromSourceGap: true,
      });
      if (gap < -1e-5) throw new Error(`${base.baseId}: overlapping monophonic context at ${index}`);
    }
  }
  return events;
}

function noteTransitions(events) {
  const positions = [];
  for (let index = 0; index < events.length - 1; index += 1) {
    const left = events[index];
    const right = events[index + 1];
    if (right.kind !== 'note' || left.durationRatio < 0.5) continue;
    if (left.kind === 'rest') {
      positions.push({ index, interval: null, strictNeighbor: false, strictPassing: false, restApproach: true, priority: 3 });
      continue;
    }
    if (left.kind !== 'note') continue;
    const interval = right.pitchMidi - left.pitchMidi;
    const strictNeighbor = interval === 0;
    const strictPassing = Math.abs(interval) >= 3;
    positions.push({ index, interval, strictNeighbor, strictPassing, priority: strictNeighbor ? 0 : strictPassing ? 1 : 2 });
  }
  const occupied = new Set(positions.map((position) => position.index));
  for (let index = 0; index < events.length - 1; index += 1) {
    const event = events[index];
    if (event.kind === 'note' && event.durationRatio >= 0.25 && !occupied.has(index)) {
      positions.push({ index, interval: null, strictNeighbor: false, strictPassing: false, hostNeighbor: true, priority: 4, ornamentDuration: event.durationRatio >= 0.5 ? 0.25 : 0.125 });
    }
  }
  return positions;
}

function spread(items, count) {
  if (items.length < count) return [];
  const picked = [];
  for (let index = 0; index < count; index += 1) {
    const slot = Math.round(index * (items.length - 1) / Math.max(1, count - 1));
    if (!picked.includes(items[slot])) picked.push(items[slot]);
  }
  for (const item of items) if (picked.length < count && !picked.includes(item)) picked.push(item);
  return picked.slice(0, count);
}

function distributed(baseEvents, count, variantId) {
  const events = clone(baseEvents);
  const candidates = noteTransitions(events).sort((a, b) => a.priority - b.priority || a.index - b.index);
  const strict = candidates.filter((candidate) => candidate.priority < 2);
  const selected = spread(strict.length >= count ? strict : candidates, count).sort((a, b) => b.index - a.index);
  if (selected.length !== count) throw new Error(`${variantId}: insufficient distributed sites`);
  const operations = [];
  for (const site of selected) {
    const left = events[site.index];
    const right = events[site.index + 1];
    const oldDuration = left.durationRatio;
    const ornamentDuration = site.ornamentDuration ?? 0.25;
    left.durationRatio = round(oldDuration - ornamentDuration);
    let pitch;
    let role;
    if (site.hostNeighbor) {
      pitch = left.pitchMidi + (site.index % 2 ? -1 : 1);
      role = 'host-neighbor-fallback';
    } else if (site.restApproach) {
      pitch = right.pitchMidi + (site.index % 2 ? -1 : 1);
      role = 'rest-approach';
    } else if (site.strictNeighbor) {
      pitch = Math.max(0, Math.min(127, left.pitchMidi + (site.index % 2 ? -1 : 1)));
      role = 'neighbor';
    } else if (site.strictPassing) {
      pitch = left.pitchMidi + Math.sign(site.interval) * Math.min(2, Math.abs(site.interval) - 1);
      role = 'passing';
    } else {
      pitch = right.pitchMidi + (site.interval >= 0 ? -1 : 1);
      role = 'chromatic-approach';
    }
    const inserted = {
      id: `${variantId}-orn-${String(operations.length + 1).padStart(2, '0')}`,
      kind: 'note',
      pitchMidi: pitch,
      spelling: spelling(pitch),
      durationRatio: ornamentDuration,
      generated: true,
      ornamentRole: role,
    };
    events.splice(site.index + 1, 0, inserted);
    operations.push({ type: 'insert-ornament', role, hostKind: left.kind, afterId: left.id, beforeId: right.id, insertedId: inserted.id, durationRatio: ornamentDuration, hostBefore: oldDuration, hostAfter: left.durationRatio });
  }
  return { events, operations: operations.reverse() };
}

function cluster(baseEvents, count, variantId) {
  const events = clone(baseEvents);
  const hostCandidates = events.map((event, index) => ({ event, index }))
    .filter(({ event }) => event.kind === 'note')
    .sort((a, b) => b.event.durationRatio - a.event.durationRatio || a.index - b.index);
  const duration = hostCandidates.some(({ event }) => event.durationRatio >= 0.125 * count + 0.25) ? 0.125 : 0.0625;
  const total = duration * count;
  const candidates = hostCandidates.filter(({ event }) => event.durationRatio >= total + 0.125);
  if (!candidates.length) throw new Error(`${variantId}: no host for cluster`);
  const { event: host, index } = candidates[Math.floor(candidates.length / 2)];
  const oldDuration = host.durationRatio;
  host.durationRatio = round(oldDuration - total);
  const contour = count === 3 ? [1, 0, -1] : [1, 0, -1, 0];
  const inserted = contour.map((offset, itemIndex) => {
    const pitch = Math.max(0, Math.min(127, host.pitchMidi + offset));
    return {
      id: `${variantId}-orn-${String(itemIndex + 1).padStart(2, '0')}`,
      kind: 'note',
      pitchMidi: pitch,
      spelling: spelling(pitch),
      durationRatio: duration,
      generated: true,
      ornamentRole: offset === 0 ? 'return-tone' : 'neighbor',
    };
  });
  events.splice(index + 1, 0, ...inserted);
  return {
    events,
    operations: [{ type: 'insert-ornament-cluster', hostId: host.id, insertedIds: inserted.map((event) => event.id), durationRatio: duration, hostBefore: oldDuration, hostAfter: host.durationRatio, contour }],
  };
}

function query(events, startsOnDownbeat) {
  return {
    version: 1,
    mode: 'melody_rhythm',
    meter: '4/4',
    startsOnDownbeat,
    events: events.map(({ source: _source, ...event }) => event),
    absoluteExactOnly: false,
    includeRests: true,
  };
}

const selected = source.bases
  .filter((base) => base.query.meter === '4/4' && !excludedBaseIds.has(base.baseId) && base.context.length >= NOTE_COUNT)
  .slice(0, 15);
if (selected.length !== 15) throw new Error(`Expected 15 bases, got ${selected.length}`);

const bases = [];
const cases = [];
for (let baseIndex = 0; baseIndex < selected.length; baseIndex += 1) {
  const sourceBase = selected[baseIndex];
  const baseId = `OA${String(baseIndex + 1).padStart(2, '0')}`;
  const events = sourceEvents(sourceBase);
  const duration = totalDuration(events);
  const variants = [
    { kind: 'original', label: '원형 대조', events: clone(events), operations: [] },
    { kind: 'distributed-3', label: '분산된 보조음·경과음 3개 추가', ...distributed(events, 3, `${baseId.toLowerCase()}-d3`) },
    { kind: 'cluster-3', label: '32분·64분음표 장식군 3개 추가', ...cluster(events, 3, `${baseId.toLowerCase()}-c3`) },
    { kind: 'distributed-4', label: '분산된 보조음·경과음 4개 추가', ...distributed(events, 4, `${baseId.toLowerCase()}-d4`) },
    { kind: 'cluster-4', label: '32분·64분음표 장식군 4개 추가', ...cluster(events, 4, `${baseId.toLowerCase()}-c4`) },
  ];
  bases.push({
    baseId,
    sourceBaseId: sourceBase.baseId,
    expected: sourceBase.expected,
    meter: '4/4',
    sourceNoteCount: NOTE_COUNT,
    sourceDuration: duration,
    sourceRange: {
      startMeasure: sourceBase.context[0].m,
      endMeasure: sourceBase.context[NOTE_COUNT - 1].m,
      firstOnset: sourceBase.context[0].o,
      lastOnset: sourceBase.context[NOTE_COUNT - 1].o,
    },
    sourceEvents: events,
    qualification: 'Existing XML-audited melodic stream; phrase/harmonic ornament identity is not certified.',
  });
  for (const variant of variants) {
    const caseId = `${baseId}-${variant.kind}`;
    if (totalDuration(variant.events) !== duration) throw new Error(`${caseId}: duration changed`);
    const added = noteCount(variant.events) - NOTE_COUNT;
    const expectedAdded = variant.kind === 'original' ? 0 : Number(variant.kind.at(-1));
    if (added !== expectedAdded) throw new Error(`${caseId}: expected ${expectedAdded} additions, got ${added}`);
    if (variant.events.some((event) => event.generated && event.durationRatio > 0.25)) throw new Error(`${caseId}: ornament longer than sixteenth`);
    cases.push({
      caseId,
      baseId,
      kind: variant.kind,
      label: variant.label,
      addedNoteCount: added,
      finalNoteCount: noteCount(variant.events),
      totalDuration: duration,
      operations: variant.operations,
      query: query(variant.events, sourceBase.query.startsOnDownbeat),
    });
  }
}

const suite = {
  schema: 'ornament-addition-suite/1',
  createdAt: new Date().toISOString(),
  selection: 'Deterministic reuse of 15 distinct 4/4 XML-audited sources; no search outcome used. B14 excluded before execution because it lacked defensible distributed sites.',
  timing: 'All inserted attacks are <= 0.25 quarter-note beats. Host durations are shortened so all later source onsets and total query duration remain fixed.',
  variants: {
    original: '16-note control',
    'distributed-3': 'three separated 16th-note passing/neighbor/approach tones',
    'cluster-3': 'three adjacent 32nd-note turn-like tones, with a 64th-note fallback when no host is long enough',
    'distributed-4': 'four separated 16th-note passing/neighbor/approach tones',
    'cluster-4': 'four adjacent 32nd-note turn-like tones, with a 64th-note fallback when no host is long enough',
  },
  decisionRule: 'Evaluate retrieval/admission, absolute scores, score margin, and structural preservation; raw rank alone is not a stable corpus-size metric.',
  bases,
  cases,
  limitations: [
    'Convenience sample of 15 distinct previously audited files, not a population estimate.',
    'Passing and neighbor labels are local pitch-motion heuristics without harmonic adjudication.',
    'Cluster variants are synthetic turn-like figures and may not be idiomatic in every source.',
    'No production search rule changes are made by this suite.',
  ],
};
mkdirSync(outputDir, { recursive: false });
writeFileSync(`${outputDir}/suite.json`, `${JSON.stringify(suite, null, 2)}\n`, { flag: 'wx' });
console.log(JSON.stringify({ outputDir, bases: bases.length, cases: cases.length, byKind: Object.fromEntries(Object.keys(suite.variants).map((kind) => [kind, cases.filter((item) => item.kind === kind).length])) }, null, 2));
