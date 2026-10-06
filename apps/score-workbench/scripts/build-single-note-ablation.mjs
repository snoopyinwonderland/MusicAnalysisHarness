import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';

const sourcePath = 'evaluation/reports/ornament-count-sweep-v1/suite.json';
const outputDir = 'evaluation/reports/single-note-ablation-cant-smile-v1';
const sourceSuite = JSON.parse(readFileSync(sourcePath, 'utf8'));
const sourceBase = sourceSuite.bases.find((base) => base.baseId === 'OC05');
const original = sourceSuite.cases.find((item) => item.caseId === 'OC05-original');
if (!sourceBase || !original) throw new Error('OC05 source case is unavailable.');

const clone = (value) => JSON.parse(JSON.stringify(value));
const notes = sourceBase.sourceEvents.filter((event) => event.kind === 'note');
const metricClass = (beat) => beat === 1 ? 'primary-downbeat' : beat === 3 ? 'secondary-downbeat' : Number.isInteger(beat) ? 'beat' : 'offbeat';
const contourRole = (index) => {
  const current = notes[index];
  const prior = notes[index - 1];
  const next = notes[index + 1];
  if (!prior || !next) return 'boundary';
  if (current.pitchMidi === prior.pitchMidi || current.pitchMidi === next.pitchMidi) return 'repetition';
  const between = (prior.pitchMidi < current.pitchMidi && current.pitchMidi < next.pitchMidi)
    || (prior.pitchMidi > current.pitchMidi && current.pitchMidi > next.pitchMidi);
  if (between && Math.abs(current.pitchMidi - prior.pitchMidi) <= 4 && Math.abs(next.pitchMidi - current.pitchMidi) <= 4) return 'passing-candidate';
  if (prior.pitchMidi === next.pitchMidi && Math.abs(current.pitchMidi - prior.pitchMidi) <= 3) return 'neighbor-candidate';
  if ((current.pitchMidi > prior.pitchMidi && current.pitchMidi > next.pitchMidi)
    || (current.pitchMidi < prior.pitchMidi && current.pitchMidi < next.pitchMidi)) return 'local-extreme';
  return 'other';
};
const independentFeature = (note, index) => ({
  noteIndex: index + 1,
  id: note.id,
  pitchMidi: note.pitchMidi,
  spelling: note.spelling,
  durationRatio: note.durationRatio,
  measure: note.source?.measure ?? null,
  beat: note.source?.beat ?? null,
  metricClass: metricClass(note.source?.beat),
  contourRole: contourRole(index),
  longRelativeToMedian: note.durationRatio >= 1,
});

const cases = [{
  caseId: 'CSA-original',
  baseId: 'CSA',
  kind: 'original',
  deletedNoteIndex: null,
  query: clone(original.query),
}];
for (let noteIndex = 0; noteIndex < notes.length; noteIndex += 1) {
  const query = clone(original.query);
  const eventIndex = query.events.findIndex((event) => event.id === notes[noteIndex].id);
  if (eventIndex < 0) throw new Error(`Missing source event ${notes[noteIndex].id}`);
  const [removed] = query.events.splice(eventIndex, 1);
  // Preserve total query time. Interior deletions sustain the immediately
  // preceding note/rest; the first deletion is absorbed by the new first event.
  const receiverIndex = eventIndex > 0 ? eventIndex - 1 : 0;
  query.events[receiverIndex].durationRatio = Number((query.events[receiverIndex].durationRatio + removed.durationRatio).toFixed(6));
  query.events[receiverIndex].ablationAbsorbedDuration = removed.durationRatio;
  cases.push({
    caseId: `CSA-delete-${String(noteIndex + 1).padStart(2, '0')}`,
    baseId: 'CSA',
    kind: 'single-note-deletion',
    deletedNoteIndex: noteIndex + 1,
    deletedEvent: independentFeature(notes[noteIndex], noteIndex),
    timePreservation: eventIndex > 0 ? 'absorbed-by-previous-event' : 'absorbed-by-next-event',
    query,
  });
}

const suite = {
  schema: 'musicanote-evaluation-suite/single-note-ablation-v1',
  createdAt: new Date().toISOString(),
  purpose: 'Diagnostic leave-one-note-out sensitivity; search response is not a music-theory ground truth label.',
  bases: [{
    baseId: 'CSA',
    expected: sourceBase.expected,
    meter: sourceBase.meter,
    sourceEvents: sourceBase.sourceEvents,
    independentFeatures: notes.map(independentFeature),
  }],
  controlledVariables: {
    source: 'CAN\'T SMILE WITHOUT YOU, violin P1:1:1',
    deletion: 'one attack at a time',
    timing: 'total duration and every later onset preserved by duration absorption',
    ranking: 'production full-corpus search, Top100',
  },
  limitations: [
    'Search sensitivity is evidence about this engine, not proof of Schenkerian importance.',
    'Absorbing duration changes the preceding sustain and can affect rhythm independently of pitch removal.',
    'The first-note deletion necessarily changes the query opening context.',
    'Corpus-relative rank can move when the database changes.',
  ],
  cases,
};
mkdirSync(outputDir, { recursive: true });
writeFileSync(`${outputDir}/suite.json`, `${JSON.stringify(suite, null, 2)}\n`);
console.log(JSON.stringify({ output: `${outputDir}/suite.json`, cases: cases.length, notes: notes.length }, null, 2));
