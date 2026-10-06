import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';

const prior = JSON.parse(readFileSync('evaluation/reports/single-note-ablation-cant-smile-v1/suite.json', 'utf8'));
const priorBase = prior.bases[0];
const priorOriginal = prior.cases.find((item) => item.kind === 'original');
const firstRetainedId = 'b06-src-03';
const eventStart = priorOriginal.query.events.findIndex((event) => event.id === firstRetainedId);
const sourceStart = priorBase.sourceEvents.findIndex((event) => event.id === firstRetainedId);
if (eventStart < 0 || sourceStart < 0) throw new Error('Trimmed Query start not found.');
const clone = (value) => JSON.parse(JSON.stringify(value));
const sourceEvents = clone(priorBase.sourceEvents.slice(sourceStart));
const query = clone(priorOriginal.query);
query.events = query.events.slice(eventStart);
query.startsOnDownbeat = false;
const notes = sourceEvents.filter((event) => event.kind === 'note');
const metricClass = (beat) => beat === 1 ? 'primary-downbeat' : beat === 3 ? 'secondary-downbeat' : Number.isInteger(beat) ? 'beat' : 'offbeat';
const contourRole = (index) => {
  const current = notes[index], priorNote = notes[index - 1], next = notes[index + 1];
  if (!priorNote || !next) return 'boundary';
  if (current.pitchMidi === priorNote.pitchMidi || current.pitchMidi === next.pitchMidi) return 'repetition';
  const between = (priorNote.pitchMidi < current.pitchMidi && current.pitchMidi < next.pitchMidi) || (priorNote.pitchMidi > current.pitchMidi && current.pitchMidi > next.pitchMidi);
  if (between && Math.abs(current.pitchMidi - priorNote.pitchMidi) <= 4 && Math.abs(next.pitchMidi - current.pitchMidi) <= 4) return 'passing-candidate';
  if (priorNote.pitchMidi === next.pitchMidi && Math.abs(current.pitchMidi - priorNote.pitchMidi) <= 3) return 'neighbor-candidate';
  if ((current.pitchMidi > priorNote.pitchMidi && current.pitchMidi > next.pitchMidi) || (current.pitchMidi < priorNote.pitchMidi && current.pitchMidi < next.pitchMidi)) return 'local-extreme';
  return 'other';
};
const feature = (note, index) => ({ noteIndex: index + 1, id: note.id, pitchMidi: note.pitchMidi, spelling: note.spelling, durationRatio: note.durationRatio, measure: note.source?.measure ?? null, beat: note.source?.beat ?? null, metricClass: metricClass(note.source?.beat), contourRole: contourRole(index), longRelativeToMedian: note.durationRatio >= 1 });
const cases = [{ caseId: 'CSAT-original', baseId: 'CSAT', kind: 'original', deletedNoteIndex: null, query }];
for (let noteIndex = 0; noteIndex < notes.length; noteIndex += 1) {
  const changed = clone(query), index = changed.events.findIndex((event) => event.id === notes[noteIndex].id);
  const [removed] = changed.events.splice(index, 1), receiver = index > 0 ? index - 1 : 0;
  changed.events[receiver].durationRatio = Number((changed.events[receiver].durationRatio + removed.durationRatio).toFixed(6));
  changed.events[receiver].ablationAbsorbedDuration = removed.durationRatio;
  cases.push({ caseId: `CSAT-delete-${String(noteIndex + 1).padStart(2, '0')}`, baseId: 'CSAT', kind: 'single-note-deletion', deletedNoteIndex: noteIndex + 1, deletedEvent: feature(notes[noteIndex], noteIndex), timePreservation: index > 0 ? 'absorbed-by-previous-event' : 'absorbed-by-next-event', query: changed });
}
const suite = {
  schema: 'musicanote-evaluation-suite/single-note-ablation-trimmed-v2', createdAt: new Date().toISOString(),
  purpose: 'User-requested rerun after removing the preceding-phrase F#-G and leading gap.',
  bases: [{ baseId: 'CSAT', expected: { ...priorBase.expected, baseStartMeasure: 33 }, meter: priorBase.meter, sourceEvents, independentFeatures: notes.map(feature) }],
  controlledVariables: { source: "CAN'T SMILE WITHOUT YOU, violin P1:1:1", removedPrefix: ['b06-src-01', 'b06-src-02', 'b06-rest-02'], queryStart: 'measure 33 beat 1.5, B3', deletion: 'one attack at a time', timing: 'later onsets and total duration preserved by adjacent duration absorption', ranking: 'production full-corpus search, Top100' },
  reviewContext: { precedingPhraseEndingRemoved: true, userReviewedOriginalNote6LowImportance: true, originalMotifEndingNotesAfterRenumbering: [5, 6] },
  limitations: ['The revised Query boundary is user-directed but the complete Phrase extent is not independently adjudicated.', 'Interior deletion still changes two adjacent intervals while edge deletion changes one.', 'Duration absorption changes a neighboring sustain.', 'Search sensitivity is not a pillar label.'],
  cases,
};
const dir = 'evaluation/reports/single-note-ablation-cant-smile-trimmed-v2';
mkdirSync(dir, { recursive: true });
writeFileSync(`${dir}/suite.json`, `${JSON.stringify(suite, null, 2)}\n`);
console.log(JSON.stringify({ dir, cases: cases.length, notes: notes.length, first: notes[0], removedPrefix: priorOriginal.query.events.slice(0, eventStart).map((event) => event.id) }, null, 2));
