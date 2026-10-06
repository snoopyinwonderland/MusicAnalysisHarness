import { writeFileSync } from 'node:fs';
import { DatabaseSync } from 'node:sqlite';

const workIds = ['work-6eaae4861c93a539', 'work-122b63dc2e7d1ef2'];
const db = new DatabaseSync('data/search-index-v2/search.sqlite', { readOnly: true });
const works = workIds.map((id) => db.prepare('SELECT id,title,notes FROM works WHERE id=?').get(id));
db.close();
if (works.some((work) => !work)) throw new Error('A comparison work is missing from the search DB.');
const streams = works.map((work) => JSON.parse(work.notes));
const anchors = [streams[0].findIndex((n) => n.o === 12.5), streams[1].findIndex((n) => n.o === 88.5)];
const spell = (midi) => `${['C','C#','D','Eb','E','F','Gb','G','Ab','A','Bb','B'][midi % 12]}${Math.floor(midi / 12) - 1}`;
const makeQuery = (notes, label) => ({
  label,
  query: {
    version: 1,
    mode: 'melody_rhythm',
    meter: '4/4',
    startsOnDownbeat: false,
    events: notes.map((note, index) => ({
      id: `${label}-${index}`,
      kind: 'note',
      pitchMidi: note.p,
      spelling: note.s || spell(note.p),
      durationRatio: note.d,
    })),
    absoluteExactOnly: false,
    exactIntervalOnly: process.env.MUSICANOTE_EXACT_INTERVAL === '1',
    ...(process.env.MUSICANOTE_GLOBAL_SEARCH === '1' ? {} : { scopeWorkIds: workIds }),
  },
});

const candidates = [];
for (let source = 0; source < 2; source += 1) {
  for (const before of [0, 2]) {
    for (const length of [7, 8, 10, 12, 14]) {
      const start = anchors[source] - before;
      if (start < 0 || start + length > streams[source].length) continue;
      candidates.push(makeQuery(streams[source].slice(start, start + length), `s${source}-b${before}-l${length}`));
    }
  }
}

const { searchDatabase } = await import('../server/search-api.mjs');
const summarize = (result) => {
  const rows = [...(result.exact || []), ...(result.similar || [])];
  return workIds.map((workId) => {
    const rank = rows.findIndex((row) => row.workId === workId || row.id === workId || row.work?.workId === workId);
    const row = rank < 0 ? null : rows[rank];
    return { workId, rank: rank < 0 ? null : rank + 1, score: row?.ranking ?? row?.score ?? row?.matchScore ?? null };
  });
};

const results = [];
const selectedCandidates = process.argv[2] ? candidates.filter((candidate) => candidate.label === process.argv[2]) : candidates;
if (process.argv[2] && selectedCandidates.length !== 1) throw new Error(`Unknown candidate ${process.argv[2]}`);
for (const candidate of selectedCandidates) {
  const started = performance.now();
  const result = searchDatabase(candidate.query, 200);
  const hits = summarize(result);
  results.push({ label: candidate.label, query: candidate.query, elapsedMs: performance.now() - started, hits });
  console.log(JSON.stringify({ label: candidate.label, hits, elapsedMs: Math.round(results.at(-1).elapsedMs) }));
}
const successful = results.filter((result) => result.hits.every((hit) => hit.rank !== null));
if (!process.argv[2]) writeFileSync('evaluation/runs/when-we-disco-cheoleopdeon-common-query.json', JSON.stringify({ createdAt: new Date().toISOString(), works: works.map(({ id, title }) => ({ id, title })), results, successful }, null, 2));
console.log(JSON.stringify({ total: results.length, successful: successful.length, best: successful.slice(0, 10).map(({ label, hits }) => ({ label, hits })) }, null, 2));
