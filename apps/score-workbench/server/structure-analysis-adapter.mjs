import { createHash } from 'node:crypto';
import { analyzePhraseBoundaries } from './phrase-boundaries.mjs';

export const STRUCTURE_CONTRACT_VERSION = 'musicanote-structure/1';
export const ADAPTER_VERSION = 'structure-adapter/2';
const stable = value => Array.isArray(value) ? value.map(stable) : value && typeof value === 'object'
  ? Object.fromEntries(Object.keys(value).sort().map(key => [key, stable(value[key])])) : value;
export const structureHash = value => createHash('sha256').update(JSON.stringify(stable(value))).digest('hex');

/** Snapshot-scoped event IDs are not claimed to be durable Canonical IR IDs. */
export function analyzeStructureSnapshot(input, { analyzer = analyzePhraseBoundaries, config = {} } = {}) {
  const { identity, events, sourceHash } = input;
  if (!identity?.sourceId || !identity?.streamId || !sourceHash || !Array.isArray(events) || !events.length)
    throw new Error('sourceHash, identity.sourceId/streamId and nonempty events are required');
  const ids = new Set();
  for (const key of ['partId', 'voice']) {
    const values = new Set(events.map(e => e[key]).filter(v => v !== undefined && v !== null).map(String));
    if (values.size > 1) throw new Error(`Mixed ${key} identities are not supported`);
  }
  const notes = events.map(event => {
    if (typeof event.id !== 'string' || !event.id || ids.has(event.id)) throw new Error('Unique source event IDs are required');
    ids.add(event.id);
    const onset = event.onsetQuarter ?? event.onset, durationRatio = event.durationQuarter ?? event.durationRatio;
    if (!Number.isFinite(onset) || !Number.isFinite(durationRatio) || durationRatio <= 0) throw new Error('Explicit finite quarter timing is required');
    if (event.streamId && event.streamId !== identity.streamId) throw new Error('Mixed streams are not supported');
    if (event.kind !== 'rest' && (!Number.isInteger(event.pitchMidi) || event.pitchMidi < 0 || event.pitchMidi > 127)) throw new Error('Invalid MIDI pitch');
    return { ...event, onset, durationRatio };
  });
  for (let i = 1; i < notes.length; i++) if (notes[i].onset < notes[i - 1].onset) throw new Error('Events must be in source time order');
  // Existing engine expects notes only; explicit onsets preserve intervening rests.
  const attacks = notes.filter(n => n.kind !== 'rest' && n.isAttack !== false && !n.tieStop);
  if (!attacks.length) throw new Error('At least one attack is required');
  for (let i = 1; i < attacks.length; i++) if (attacks[i].onset <= attacks[i - 1].onset)
    throw new Error('Select a single melodic line before structural analysis');
  const analysis = analyzer(attacks, config);
  if (typeof analysis.version !== 'string' || !Array.isArray(analysis.boundaries)) throw new Error('Unsupported analyzer output');
  const dependencies = { contract: STRUCTURE_CONTRACT_VERSION, adapter: ADAPTER_VERSION,
    analyzer: analysis.version, configHash: structureHash(config), sourceHash,
    eventsHash: structureHash(notes), identityHash: structureHash(identity), meterHash:structureHash({meter:input.meter??null,timeline:input.meterTimeline??[]}), parserVersion: input.parserVersion ?? 'unknown' };
  const snapshotId = structureHash(dependencies);
  const units = [];
  function addUnit(kind, start, end, evidence, familyId = null) {
    if (!Number.isInteger(start) || !Number.isInteger(end) || start < 0 || end > attacks.length || start >= end) throw new Error('Invalid analysis span');
    const selected = attacks.slice(start, end), first = selected[0], last = selected.at(-1);
    const startQuarter = first.onset, endQuarter = Math.max(...selected.map(n => n.onset + n.durationRatio));
    const eventIds = notes.filter(n => n.onset >= startQuarter && n.onset < endQuarter).map(n => n.id);
    const unitId = `${kind}-${structureHash({ snapshotId, eventIds, start, end }).slice(0, 24)}`;
    if (units.some(u => u.unitId === unitId)) return;
    units.push({ unitId, kind, streamId: identity.streamId, startEventId: first.id, endEventId: last.id,
      startQuarter, endQuarter, eventIds, attackEventIds: selected.map(n => n.id), familyId,
      confidence: null, calibrated: false, evidence, phraseIds: [],
      location: { startMeasure: first.measure, startOrdinal: first.measureOrdinal, endMeasure: last.measure, endOrdinal: last.measureOrdinal } });
  }
  const cuts = [0, ...new Set(analysis.boundaries.filter(b => b.supported && b.index > 0 && b.index < attacks.length).map(b => b.index)), attacks.length].sort((a,b) => a-b);
  for (let i = 0; i < cuts.length - 1; i++) addUnit('phrase', cuts[i], cuts[i + 1], {
    type: 'boundary-hypothesis', start: analysis.boundaries[cuts[i]], end: analysis.boundaries[cuts[i + 1]], endpointsMayBeCropped: true });
  for (const cell of analysis.motifCells ?? []) addUnit('motif', cell.startIndex, cell.endIndex + 1,
    { type: 'rhythmic-cell', raw: cell }, `rhythm-${structureHash(cell.rhythmFamily).slice(0,16)}`);
  for (const relation of analysis.motifRelations ?? []) {
    for (const start of [relation.previousIndex, relation.currentIndex]) addUnit('motif', start, start + relation.length,
      { type: 'bounded-signature', completeMotifExtent: false, raw: relation }, `signature-${structureHash(relation.signatureKey).slice(0,16)}`);
  }
  for (const motif of units.filter(u => u.kind === 'motif')) motif.phraseIds = units.filter(u => u.kind === 'phrase' && u.startQuarter < motif.endQuarter && motif.startQuarter < u.endQuarter).map(u => u.unitId);
  return { schema: STRUCTURE_CONTRACT_VERSION, snapshotId, dependencies, identity: structuredClone(identity),
    meter: input.meter ?? null, meterTimeline:structuredClone(input.meterTimeline??[]), config: structuredClone(config), events: notes, units,
    rawAnalysis: analysis, warnings: ['Structure strengths are uncalibrated; confidence is unknown.',
      'Bounded signature evidence is not necessarily a complete Motif.',
      'Event references are scoped to this source snapshot; no automatic correction remapping.'] };
}

/** Pure invalidation plan; previous reports and corrections remain immutable. */
export function structureRefreshPlan(previous, next) {
  const changed = Object.keys(next.dependencies).filter(key => previous?.dependencies?.[key] !== next.dependencies[key]);
  return { status: !previous ? 'new' : changed.length ? 'reanalysis_available' : 'current', changed,
    previousSnapshotId: previous?.snapshotId ?? null, nextSnapshotId: next.snapshotId,
    invalidate: changed.length ? ['structure', 'selection', 'search', 'aggregation', 'report'] : [],
    preservePrevious: true, correctionsRequireReview: Boolean(previous && changed.length) };
}

/** Phrase/Motif overlap is metadata, never a summed importance bonus. */
export function structureSearchQueries(snapshot, { kinds = ['phrase', 'motif'], minimumNotes = 4 } = {}) {
  if (!kinds.every(kind => ['phrase','motif','window'].includes(kind))) throw new Error('Unknown structure kind');
  const tasks = new Map();
  for (const unit of snapshot.units.filter(u => kinds.includes(u.kind))) {
    if (unit.attackEventIds.length < minimumNotes) continue;
    const selectedIds = new Set(unit.eventIds), selected = snapshot.events.filter(n => selectedIds.has(n.id));
    const meters=new Set(selected.filter(n=>n.kind!=='rest').map(n=>n.meter??snapshot.meter));
    const ordinals=selected.map(n=>n.measureOrdinal).filter(Number.isFinite);
    if(ordinals.length)for(const change of snapshot.meterTimeline??[]){if(change.measureOrdinal>=Math.min(...ordinals)&&change.measureOrdinal<=Math.max(...ordinals))meters.add(change.meter);}
    const unitMeter=meters.size===1?[...meters][0]:'unknown';
    const events = []; let cursor = unit.startQuarter;
    for (const note of selected) {
      if (note.onset > cursor + 1e-6) events.push({ id: `gap-${note.id}`, kind: 'rest', pitchMidi: null, durationRatio: note.onset - cursor });
      events.push({ ...note, onset: note.onset - unit.startQuarter });
      cursor = Math.max(cursor, note.onset + note.durationRatio);
    }
    const key = structureHash(unit.eventIds);
    if (tasks.has(key)) { tasks.get(key).unitIds.push(unit.unitId); continue; }
    tasks.set(key, { taskId: key, snapshotId: snapshot.snapshotId, unitIds: [unit.unitId],
      overlappingUnitIds: snapshot.units.filter(other => other.unitId !== unit.unitId && other.startQuarter < unit.endQuarter && unit.startQuarter < other.endQuarter).map(other => other.unitId),
      query: { version: 1, mode: 'melody_rhythm', meter: unitMeter, startsOnDownbeat: false, includeRests: true, events },
      warnings: /^\d+\/\d+$/.test(unitMeter??'') ? [] : ['Meter must be confirmed before search.'] });
  }
  return [...tasks.values()];
}
