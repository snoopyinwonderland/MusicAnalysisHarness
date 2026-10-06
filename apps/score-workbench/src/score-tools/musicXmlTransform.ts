import { UNASSIGNED_VOICE_ID, recipeHash, rational, sha256Text, type DerivedScore, type ExcerptRecipe, type PartSelection, type ScoreEventRef, type ScoreMeasureRef, type ScorePartRef, type ScoreSnapshot, type SourceMapEntry, type ViewRecipe } from './model';
import { transposeRecipe } from './transposition';

const parserError = (doc: XMLDocument) => doc.getElementsByTagName('parsererror')[0]?.textContent?.trim() || '';
export const parseMusicXml = (xml: string): XMLDocument => {
  const doc = new DOMParser().parseFromString(xml.replace(/^\uFEFF/, ''), 'application/xml'), error = parserError(doc);
  if (error) throw new Error(`MusicXML parsing failed: ${error}`);
  if (doc.documentElement?.localName !== 'score-partwise') throw new Error('현재 1차 악보 도구는 score-partwise MusicXML만 지원합니다.');
  return doc;
};

const directChildren = (element: Element, tagName: string) => [...element.children].filter(child => child.localName === tagName);
const firstDirect = (element: Element, tagName: string) => directChildren(element, tagName)[0];
const textOf = (element: Element | undefined, tagName: string) => element?.getElementsByTagName(tagName)[0]?.textContent?.trim() || '';
const explicitVoiceIdOf = (note: Element) => firstDirect(note, 'voice')?.textContent?.trim() || undefined;

/**
 * A MusicXML chord continuation shares the chord head's voice when the head
 * encodes one explicitly. We deliberately do not infer a voice from nearby
 * independent notes (or from another chord member), because MIDI-derived XML
 * often omits voice data inconsistently.
 */
const resolvedVoiceIdsForMeasure = (measure: Element) => {
  const result = new Map<Element, string>();
  let chordHeadExplicitVoice: string | undefined;
  for (const child of [...measure.children]) {
    if (child.localName !== 'note') { chordHeadExplicitVoice = undefined; continue; }
    const explicitVoice = explicitVoiceIdOf(child), chordContinuation = Boolean(firstDirect(child, 'chord'));
    if (!chordContinuation) chordHeadExplicitVoice = explicitVoice;
    result.set(child, explicitVoice || (chordContinuation ? chordHeadExplicitVoice : undefined) || UNASSIGNED_VOICE_ID);
  }
  return result;
};

const resolvedVoiceIdsForPart = (part: Element) => {
  const result = new Map<Element, string>();
  for (const measure of directChildren(part, 'measure')) for (const [note, voiceId] of resolvedVoiceIdsForMeasure(measure)) result.set(note, voiceId);
  return result;
};

const resolvedVoiceIdOf = (note: Element, resolved?: ReadonlyMap<Element, string>) => resolved?.get(note) || explicitVoiceIdOf(note) || UNASSIGNED_VOICE_ID;
export const measureRefId = (ordinal: number) => `measure:${ordinal}`;
export const eventRefId = (partId: string, measureOrdinal: number, eventOrdinal: number) => `event:${partId}:${measureOrdinal}:${eventOrdinal}`;

const partMetadata = (doc: XMLDocument) => {
  const result = new Map<string, { name: string; abbreviation?: string }>();
  for (const scorePart of [...doc.getElementsByTagName('score-part')]) {
    const id = scorePart.getAttribute('id') || '';
    if (id) result.set(id, { name: textOf(scorePart, 'part-name') || id, abbreviation: textOf(scorePart, 'part-abbreviation') || undefined });
  }
  return result;
};

const partInventory = (doc: XMLDocument): ScorePartRef[] => {
  const metadata = partMetadata(doc);
  return [...doc.documentElement.children].filter(element => element.localName === 'part').map((part, sourceIndex) => {
    const id = part.getAttribute('id') || `P${sourceIndex + 1}`, staves = new Set<string>(), voices = new Set<string>();
    const resolvedVoices = resolvedVoiceIdsForPart(part);
    for (const note of [...part.getElementsByTagName('note')]) { staves.add(textOf(note, 'staff') || '1'); voices.add(resolvedVoiceIdOf(note, resolvedVoices)); }
    const declaredStaves = Math.max(1, ...[...part.getElementsByTagName('staves')].map(node => Number(node.textContent)).filter(Number.isFinite));
    for (let staff = 1; staff <= declaredStaves; staff++) staves.add(String(staff));
    const detail = metadata.get(id);
    return { id, name: detail?.name || id, abbreviation: detail?.abbreviation, sourceIndex, staves: [...staves].sort((a, b) => Number(a) - Number(b)), voices: [...voices].sort((a, b) => Number(a) - Number(b)) };
  });
};

const measureInventory = (doc: XMLDocument): ScoreMeasureRef[] => {
  const parts = [...doc.documentElement.children].filter(element => element.localName === 'part');
  const maximum = Math.max(0, ...parts.map(part => directChildren(part, 'measure').length)), primary = directChildren(parts[0], 'measure');
  return Array.from({ length: maximum }, (_, index) => {
    const measure = primary[index] || parts.map(part => directChildren(part, 'measure')[index]).find(Boolean);
    return { id: measureRefId(index + 1), ordinal: index + 1, displayNumber: measure?.getAttribute('number') || String(index + 1), implicit: measure?.getAttribute('implicit')?.toLowerCase() === 'yes' };
  });
};

const eventInventory = (doc: XMLDocument): ScoreEventRef[] => {
  const events: ScoreEventRef[] = [];
  for (const [partIndex, part] of [...doc.documentElement.children].filter(element => element.localName === 'part').entries()) {
    const partId = part.getAttribute('id') || `P${partIndex + 1}`;
    let divisions = 1;
    for (const [measureIndex, measure] of directChildren(part, 'measure').entries()) {
      const declared = Number(textOf(firstDirect(measure, 'attributes'), 'divisions')); if (declared > 0) divisions = declared;
      const resolvedVoices = resolvedVoiceIdsForMeasure(measure);
      let cursor = 0, lastOnset = 0, eventOrdinal = 0;
      for (const element of [...measure.children]) {
        const duration = Number(textOf(element, 'duration')) || 0;
        if (element.localName === 'backup') { cursor -= duration; continue; }
        if (element.localName === 'forward') { cursor += duration; continue; }
        if (element.localName !== 'note') continue;
        eventOrdinal++;
        const chord = Boolean(element.getElementsByTagName('chord').length), grace = Boolean(element.getElementsByTagName('grace').length), onset = chord ? lastOnset : cursor;
        events.push({ id: eventRefId(partId, measureIndex + 1, eventOrdinal), partId, measureId: measureRefId(measureIndex + 1), measureOrdinal: measureIndex + 1, eventOrdinal, staffId: textOf(element, 'staff') || '1', voiceId: resolvedVoiceIdOf(element, resolvedVoices), onset: rational(onset, divisions), duration: rational(duration, divisions), kind: element.getElementsByTagName('rest').length ? 'rest' : 'note' });
        if (!chord) lastOnset = onset;
        if (!chord && !grace) cursor += duration;
      }
    }
  }
  return events;
};

export const createScoreSnapshot = async (xml: string, sourceId: string): Promise<ScoreSnapshot> => {
  const doc = parseMusicXml(xml), sourceHash = await sha256Text(xml);
  return { schemaVersion: '1.1.0', sourceId, sourceHash, sourceVersionId: `${sourceId}@${sourceHash.slice(0, 16)}`, createdAt: new Date().toISOString(), parts: partInventory(doc), measures: measureInventory(doc), events: eventInventory(doc) };
};

/**
 * Rebuilds a legacy snapshot from its authoritative MusicXML. A 1.0.0 event
 * does not retain enough information to distinguish an explicit Voice 1 from
 * an omitted voice, so a data-only migration would be unsafe.
 */
export const migrateScoreSnapshot = async (snapshot: ScoreSnapshot, xml: string): Promise<ScoreSnapshot> => {
  const sourceHash = await sha256Text(xml);
  if (sourceHash !== snapshot.sourceHash) throw new Error('원본 악보가 legacy snapshot 이후 변경되어 snapshot을 마이그레이션할 수 없습니다.');
  const doc = parseMusicXml(xml);
  return { ...snapshot, schemaVersion: '1.1.0', parts: partInventory(doc), measures: measureInventory(doc), events: eventInventory(doc) };
};

export const defaultViewRecipe = (snapshot: ScoreSnapshot): ViewRecipe => ({ schemaVersion: '1.1.0', sourceVersionId: snapshot.sourceVersionId, sourceHash: snapshot.sourceHash, transpose: transposeRecipe(''), selections: snapshot.parts.map(part => ({ partId: part.id, scope: 'whole_part' })) });
export const defaultExcerptRecipe = (snapshot: ScoreSnapshot, startOrdinal = 1, endOrdinal = Math.min(snapshot.measures.length, startOrdinal + 3)): ExcerptRecipe => {
  const start = snapshot.measures[Math.max(0, Math.min(snapshot.measures.length - 1, startOrdinal - 1))], end = snapshot.measures[Math.max(0, Math.min(snapshot.measures.length - 1, endOrdinal - 1))];
  return { schemaVersion: '1.4.0', sourceVersionId: snapshot.sourceVersionId, sourceHash: snapshot.sourceHash, source: 'current_view', view: { transpose: transposeRecipe('') }, range: { kind: 'measures', startMeasureId: start?.id || 'measure:1', endMeasureId: end?.id || start?.id || 'measure:1' }, selections: snapshot.parts.map(part => ({ partId: part.id, scope: 'whole_part' })), presentation: { layout: 'single_system', imageWidthPx: 1200, targetSystemCount: 2, systemBreakBeforeMeasureIds: [], showMeasureNumbers: true, removeLyrics: false, removeDynamics: false } };
};

export const migrateViewRecipe = (recipe: ViewRecipe): ViewRecipe => ({ ...recipe, schemaVersion: '1.1.0', selections: recipe.selections.map(cloneSelection) });
export const migrateExcerptRecipe = (recipe: ExcerptRecipe): ExcerptRecipe => ({ ...recipe, schemaVersion: '1.4.0', selections: recipe.selections.map(cloneSelection) });

const cloneSelection = (selection: PartSelection): PartSelection => selection.scope === 'whole_part'
  ? { ...selection }
  : selection.scope === 'staves'
    ? { ...selection, staffIds: [...selection.staffIds] }
    : { ...selection, voiceIds: [...selection.voiceIds] };

const ordinalFromMeasureId = (id: string) => Number(id.split(':').at(-1));
const EFFECTIVE_ATTRIBUTE_TAGS = ['divisions', 'key', 'time', 'staves', 'clef', 'staff-details', 'transpose'] as const;
const attributeIdentity = (element: Element) => `${element.localName}:${element.getAttribute('number')?.trim() || 'default'}`;
const attributeOrder = new Map<string, number>([
  'divisions', 'key', 'time', 'staves', 'part-symbol', 'instruments', 'clef', 'staff-details', 'transpose', 'directive', 'measure-style',
].map((tag, index) => [tag, index]));
const insertAttributeChild = (target: Element, node: Node) => {
  const rank = attributeOrder.get((node as Element).localName) ?? Number.MAX_SAFE_INTEGER;
  const successor = [...target.children].find(child => (attributeOrder.get(child.localName) ?? Number.MAX_SAFE_INTEGER) > rank);
  target.insertBefore(node, successor || null);
};

const copyEffectiveAttributes = (doc: XMLDocument, allMeasures: Element[], firstKept: Element) => {
  let target = firstDirect(firstKept, 'attributes');
  if (!target) { target = doc.createElement('attributes'); firstKept.insertBefore(target, firstKept.firstChild); }
  const firstKeptIndex = allMeasures.indexOf(firstKept), effective = new Map<string, Element>();
  const priorAttributes = allMeasures.slice(0, firstKeptIndex).flatMap(measure => directChildren(measure, 'attributes'));
  for (const attributes of priorAttributes) for (const tag of EFFECTIVE_ATTRIBUTE_TAGS) {
    for (const node of directChildren(attributes, tag)) effective.set(attributeIdentity(node), node);
  }
  const targetIdentities = new Set<string>();
  for (const tag of EFFECTIVE_ATTRIBUTE_TAGS) for (const node of directChildren(target, tag)) targetIdentities.add(attributeIdentity(node));
  for (const [identity, node] of effective) if (!targetIdentities.has(identity)) insertAttributeChild(target, node.cloneNode(true));
};

const cleanPartList = (doc: XMLDocument, selected: Set<string>) => {
  const partList = doc.getElementsByTagName('part-list')[0]; if (!partList) return;
  for (const scorePart of [...partList.getElementsByTagName('score-part')]) if (!selected.has(scorePart.getAttribute('id') || '')) scorePart.remove();
  for (const group of [...partList.getElementsByTagName('part-group')]) group.remove();
};

export const normalizePartViewSelection = (availablePartIds: readonly string[], requestedPartIds: readonly string[]) => {
  const requested = new Set(requestedPartIds), selected = availablePartIds.filter(partId => requested.has(partId));
  return selected.length === 0 || selected.length === availablePartIds.length ? [] : selected;
};

// Mutates only the temporary render document. An empty return value means the
// original full-score view (zero selected and all selected are both full view).
export const applyPartViewSelection = (doc: XMLDocument, requestedPartIds: readonly string[]) => {
  const parts = [...doc.documentElement.children].filter(element => element.localName === 'part');
  const available = parts.map(part => part.getAttribute('id') || '').filter(Boolean), selected = normalizePartViewSelection(available, requestedPartIds);
  if (!selected.length) return selected;
  const keep = new Set(selected); cleanPartList(doc, keep);
  for (const part of parts) if (!keep.has(part.getAttribute('id') || '')) part.remove();
  return selected;
};

const staffIdOf = (element: Element) => textOf(element, 'staff') || '1';
const valuesForSelection = (selection: PartSelection) => selection.scope === 'staves' ? selection.staffIds : selection.scope === 'voices' ? selection.voiceIds : [];
const matchesSelection = (selection: PartSelection, staffId: string, voiceId: string) => selection.scope === 'whole_part'
  || (selection.scope === 'staves' ? selection.staffIds.includes(staffId) : selection.voiceIds.includes(voiceId));
const matchesEventSelection = (selection: PartSelection, event: ScoreEventRef) => matchesSelection(selection, event.staffId, event.voiceId);
const stableIdSort = (left: string, right: string) => {
  const leftNumber = Number(left), rightNumber = Number(right);
  return Number.isFinite(leftNumber) && Number.isFinite(rightNumber) ? leftNumber - rightNumber : left.localeCompare(right, undefined, { numeric: true });
};

const validateSelectionsForParts = (parts: readonly ScorePartRef[], selections: readonly PartSelection[]) => {
  if (!selections.length) throw new Error('한 개 이상의 Part, Staff 또는 Voice를 선택해 주세요.');
  const byPart = new Map(parts.map(part => [part.id, part])), seen = new Set<string>();
  for (const selection of selections) {
    const part = byPart.get(selection.partId);
    if (!part) throw new Error(`원본에 없는 Part입니다: ${selection.partId}`);
    if (seen.has(selection.partId)) throw new Error(`Part별 선택 범위는 하나만 지정할 수 있습니다: ${selection.partId}`);
    seen.add(selection.partId);
    if (selection.scope === 'whole_part') continue;
    const values = valuesForSelection(selection);
    if (!values.length) throw new Error(`${selection.partId}에서 한 개 이상의 ${selection.scope === 'staves' ? 'Staff' : 'Voice'}를 선택해 주세요.`);
    if (new Set(values).size !== values.length) throw new Error(`${selection.partId}의 ${selection.scope === 'staves' ? 'Staff' : 'Voice'} 선택에 중복 ID가 있습니다.`);
    const available = new Set(selection.scope === 'staves' ? part.staves : part.voices);
    const unknown = values.filter(value => !available.has(value));
    if (unknown.length) throw new Error(`${selection.partId}에 없는 ${selection.scope === 'staves' ? 'Staff' : 'Voice'}입니다: ${unknown.join(', ')}`);
  }
};

const durationOf = (note: Element) => Number(textOf(note, 'duration')) || 0;
const isChordNote = (note: Element) => Boolean(firstDirect(note, 'chord'));
const isGraceNote = (note: Element) => Boolean(firstDirect(note, 'grace'));
const removeChordMarker = (note: Element) => firstDirect(note, 'chord')?.remove();
const materializeInheritedVoice = (doc: XMLDocument, note: Element, voiceId: string) => {
  if (voiceId === UNASSIGNED_VOICE_ID || explicitVoiceIdOf(note)) return;
  const voice = doc.createElement('voice'); voice.textContent = voiceId;
  const followingVoice = new Set(['type', 'dot', 'accidental', 'time-modification', 'stem', 'notehead', 'notehead-text', 'staff', 'beam', 'notations', 'lyric', 'play', 'listen']);
  const successor = [...note.children].find(child => followingVoice.has(child.localName));
  note.insertBefore(voice, successor || null);
};

/**
 * Filters note groups without collapsing the source cursor. A fully removed
 * duration-bearing group becomes <forward>; a surviving chord member is
 * promoted to the cursor-advancing head when its original head was removed.
 * Existing backup/forward elements therefore keep their original semantics.
 */
const filterMeasureTimeline = (doc: XMLDocument, measure: Element, selection: PartSelection) => {
  const children = [...measure.children], resolvedVoices = resolvedVoiceIdsForMeasure(measure);
  for (let index = 0; index < children.length; index++) {
    const head = children[index];
    if (head.localName !== 'note') continue;
    if (isChordNote(head)) throw new Error(`마디 ${measure.getAttribute('number') || '?'}에 선행 음표가 없는 <chord>가 있어 Staff/Voice 추출을 중단했습니다.`);
    const group = [head];
    while (index + group.length < children.length) {
      const candidate = children[index + group.length];
      if (candidate.localName !== 'note' || !isChordNote(candidate)) break;
      group.push(candidate);
    }
    index += group.length - 1;
    const kept = group.filter(note => matchesSelection(selection, staffIdOf(note), resolvedVoiceIdOf(note, resolvedVoices)));
    const headDuration = durationOf(head);
    if (!kept.length) {
      if (!isGraceNote(head) && headDuration > 0) {
        const forward = doc.createElement('forward'), duration = doc.createElement('duration');
        duration.textContent = String(headDuration); forward.appendChild(duration); head.parentNode?.replaceChild(forward, head);
      } else head.remove();
      for (const chord of group.slice(1)) chord.remove();
      continue;
    }
    const promoted = kept[0];
    if (promoted !== head) {
      if (durationOf(promoted) !== headDuration || isGraceNote(promoted) !== isGraceNote(head)) {
        throw new Error(`마디 ${measure.getAttribute('number') || '?'}의 cross-staff 화음 음가가 달라 안전하게 추출할 수 없습니다.`);
      }
      materializeInheritedVoice(doc, promoted, resolvedVoiceIdOf(promoted, resolvedVoices));
      removeChordMarker(promoted);
    }
    for (const note of group) if (!kept.includes(note)) note.remove();
  }
};

const remapStaffReferences = (doc: XMLDocument, part: Element, keptStaffIds: readonly string[]) => {
  const ordered = [...new Set(keptStaffIds)].sort(stableIdSort), map = new Map(ordered.map((staffId, index) => [staffId, String(index + 1)]));
  if (!ordered.length) return;
  for (const measure of directChildren(part, 'measure')) {
    for (const child of [...measure.children]) {
      if (!['direction', 'harmony', 'figured-bass'].includes(child.localName)) continue;
      const staff = firstDirect(child, 'staff');
      if (!staff) continue;
      const mapped = map.get(staff.textContent?.trim() || '1');
      if (!mapped) child.remove(); else staff.textContent = mapped;
    }
    for (const forward of directChildren(measure, 'forward')) firstDirect(forward, 'staff')?.remove();
    for (const attributes of directChildren(measure, 'attributes')) {
      const staves = firstDirect(attributes, 'staves');
      if (staves) staves.textContent = String(ordered.length);
      for (const element of [...attributes.children]) {
        if (!['clef', 'key', 'time', 'staff-details', 'measure-style'].includes(element.localName)) continue;
        const sourceNumber = element.getAttribute('number') || '1', mapped = map.get(sourceNumber);
        if (!mapped) { element.remove(); continue; }
        if (mapped === '1') element.removeAttribute('number'); else element.setAttribute('number', mapped);
      }
    }
  }
  for (const note of [...part.getElementsByTagName('note')]) {
    const staff = firstDirect(note, 'staff'), mapped = map.get(staff?.textContent?.trim() || '1');
    if (!mapped) throw new Error('선택되지 않은 Staff 음표가 파생 악보에 남았습니다.');
    if (staff) staff.textContent = mapped;
    else if (mapped !== '1') { const created = doc.createElement('staff'); created.textContent = mapped; note.appendChild(created); }
  }
};

const ancestorNote = (element: Element): Element | undefined => {
  let current: Element | null = element;
  while (current && current.localName !== 'note') current = current.parentElement;
  return current || undefined;
};
const pitchIdentity = (note: Element) => {
  const pitch = firstDirect(note, 'pitch');
  return pitch ? `${textOf(pitch, 'step')}:${textOf(pitch, 'alter') || '0'}:${textOf(pitch, 'octave')}` : `rest:${note.getElementsByTagName('rest').length}`;
};

const removeDanglingPairs = (part: Element, tagName: string, keyFor: (element: Element) => string) => {
  const groups = new Map<string, Element[]>();
  for (const element of [...part.getElementsByTagName(tagName)]) {
    const type = element.getAttribute('type') || '';
    if (!['start', 'continue', 'stop'].includes(type)) continue;
    const key = keyFor(element), group = groups.get(key) || []; group.push(element); groups.set(key, group);
  }
  let removed = 0;
  for (const group of groups.values()) {
    let active: Element[] | undefined;
    for (const element of group) {
      const type = element.getAttribute('type');
      if (type === 'start') {
        if (active) { for (const orphan of active) { orphan.remove(); removed++; } }
        active = [element];
      } else if (type === 'continue') {
        if (active) active.push(element); else { element.remove(); removed++; }
      } else if (active) active = undefined;
      else { element.remove(); removed++; }
    }
    if (active) for (const orphan of active) { orphan.remove(); removed++; }
  }
  return removed;
};

const cleanupConnections = (part: Element) => {
  let removed = 0;
  const resolvedVoices = resolvedVoiceIdsForPart(part);
  const tieKey = (element: Element) => { const note = ancestorNote(element); return note ? `${resolvedVoiceIdOf(note, resolvedVoices)}:${pitchIdentity(note)}:${element.getAttribute('number') || '1'}` : 'orphan'; };
  const numberedKey = (element: Element) => { const note = ancestorNote(element); return `${element.getAttribute('number') || '1'}:${note ? resolvedVoiceIdOf(note, resolvedVoices) : 'orphan'}`; };
  removed += removeDanglingPairs(part, 'tie', tieKey);
  removed += removeDanglingPairs(part, 'tied', tieKey);
  removed += removeDanglingPairs(part, 'slur', numberedKey);
  removed += removeDanglingPairs(part, 'tuplet', numberedKey);
  // A partial selection can leave explicit beam groups without their source
  // begin/end members. Removing only the notation lets the engraver fall back
  // to flags/automatic beaming without changing onset, pitch, or duration.
  for (const beam of [...part.getElementsByTagName('beam')]) { beam.remove(); removed++; }
  // Arpeggiation is chord-wide notation. Once chord members may have been
  // removed, retaining it could assert a relationship that no longer exists.
  for (const tag of ['arpeggiate', 'non-arpeggiate']) for (const element of [...part.getElementsByTagName(tag)]) { element.remove(); removed++; }
  for (const notations of [...part.getElementsByTagName('notations')]) if (!notations.children.length) notations.remove();
  return removed;
};

const selectionRequiredStaffs = (part: Element, selection: PartSelection, resolvedVoices: ReadonlyMap<Element, string>) => selection.scope === 'staves'
  ? [...selection.staffIds]
  : [...new Set([...part.getElementsByTagName('note')].filter(note => matchesSelection(selection, staffIdOf(note), resolvedVoiceIdOf(note, resolvedVoices))).map(staffIdOf))];

const sameInventoryIds = (selected: readonly string[], available: ReadonlySet<string>) =>
  selected.length === available.size && selected.every(id => available.has(id));

const selectionPreservesWholePart = (part: Element, selection: PartSelection, resolvedVoices: ReadonlyMap<Element, string>) => {
  if (selection.scope === 'whole_part') return true;
  if (selection.scope === 'voices') return sameInventoryIds(selection.voiceIds, new Set(resolvedVoices.values()));
  const availableStaffs = new Set([...part.getElementsByTagName('note')].map(staffIdOf));
  const declaredStaves = Math.max(1, ...[...part.getElementsByTagName('staves')].map(node => Number(node.textContent)).filter(Number.isFinite));
  for (let staff = 1; staff <= declaredStaves; staff++) availableStaffs.add(String(staff));
  return sameInventoryIds(selection.staffIds, availableStaffs);
};

const filterPartToSelection = (doc: XMLDocument, part: Element, selection: PartSelection) => {
  if (selection.scope === 'whole_part') return [] as string[];
  const resolvedVoices = resolvedVoiceIdsForPart(part);
  // Scoped UI modes are representationally equivalent to whole_part when no
  // event is excluded. Preserve all engraving in that case, including beams
  // and chord-wide arpeggiation.
  if (selectionPreservesWholePart(part, selection, resolvedVoices)) return [] as string[];
  const warnings: string[] = [], requiredStaffs = selectionRequiredStaffs(part, selection, resolvedVoices);
  if (selection.scope === 'staves') {
    const voiceStaffs = new Map<string, Set<string>>();
    for (const note of [...part.getElementsByTagName('note')]) {
      const voiceId = resolvedVoiceIdOf(note, resolvedVoices), set = voiceStaffs.get(voiceId) || new Set<string>();
      set.add(staffIdOf(note)); voiceStaffs.set(voiceId, set);
    }
    const selected = new Set(selection.staffIds);
    const crossing = [...voiceStaffs.entries()].filter(([, staffs]) => [...staffs].some(staff => selected.has(staff)) && [...staffs].some(staff => !selected.has(staff))).map(([voice]) => voice);
    if (crossing.length) warnings.push(`선택 경계를 넘는 cross-staff Voice의 일부 음이 제외되었습니다: ${crossing.join(', ')}`);
  } else if (requiredStaffs.length > 1) warnings.push(`선택한 Voice가 ${requiredStaffs.length}개 Staff를 사용하므로 필요한 원래 Staff를 함께 유지했습니다.`);
  let ambiguousDirections = 0;
  for (const measure of directChildren(part, 'measure')) {
    filterMeasureTimeline(doc, measure, selection);
    if (selection.scope === 'voices') for (const direction of directChildren(measure, 'direction')) {
      const voice = firstDirect(direction, 'voice');
      if (voice && !selection.voiceIds.includes(voice.textContent?.trim() || UNASSIGNED_VOICE_ID)) direction.remove();
      else if (!voice && firstDirect(direction, 'staff')) ambiguousDirections++;
    }
  }
  if (ambiguousDirections) warnings.push(`Voice가 지정되지 않은 Staff 지시 ${ambiguousDirections}개는 전역/공용 지시일 수 있어 필요한 Staff에 보존했습니다.`);
  remapStaffReferences(doc, part, requiredStaffs);
  const removedConnections = cleanupConnections(part);
  if (removedConnections) warnings.push(`선택 경계에서 불완전해질 수 있는 tie/slur/tuplet/beam/arpeggiation 표기 ${removedConnections}개를 안전하게 정리했습니다.`);
  return warnings;
};

type SemanticEvent = { partId: string; measureOrdinal: number; staffId: string; voiceId: string; onset: string; duration: string; pitch: string; kind: 'note' | 'rest' };
const rationalKey = (numerator: number, denominator: number) => { const value = rational(numerator, denominator); return `${value.numerator}/${value.denominator}`; };
const semanticEventInventory = (doc: XMLDocument): SemanticEvent[] => {
  const events: SemanticEvent[] = [];
  for (const [partIndex, part] of [...doc.documentElement.children].filter(element => element.localName === 'part').entries()) {
    const partId = part.getAttribute('id') || `P${partIndex + 1}`;
    let divisions = 1;
    for (const [measureIndex, measure] of directChildren(part, 'measure').entries()) {
      const declared = Number(textOf(firstDirect(measure, 'attributes'), 'divisions')); if (declared > 0) divisions = declared;
      const resolvedVoices = resolvedVoiceIdsForMeasure(measure);
      let cursor = 0, lastOnset = 0;
      for (const element of [...measure.children]) {
        const duration = Number(textOf(element, 'duration')) || 0;
        if (element.localName === 'backup') { cursor -= duration; continue; }
        if (element.localName === 'forward') { cursor += duration; continue; }
        if (element.localName !== 'note') continue;
        const chord = isChordNote(element), grace = isGraceNote(element), onset = chord ? lastOnset : cursor, kind = element.getElementsByTagName('rest').length ? 'rest' as const : 'note' as const;
        events.push({ partId, measureOrdinal: measureIndex + 1, staffId: staffIdOf(element), voiceId: resolvedVoiceIdOf(element, resolvedVoices), onset: rationalKey(onset, divisions), duration: rationalKey(duration, divisions), pitch: kind === 'rest' ? 'rest' : pitchIdentity(element), kind });
        if (!chord) lastOnset = onset;
        if (!chord && !grace) cursor += duration;
      }
    }
  }
  return events;
};

const semanticKey = (event: SemanticEvent) => `${event.partId}|${event.measureOrdinal}|${event.voiceId}|${event.onset}|${event.duration}|${event.pitch}|${event.kind}`;
const validateDerivedSemantics = (before: readonly SemanticEvent[], after: readonly SemanticEvent[], selections: readonly PartSelection[]) => {
  const byPart = selectionMap(selections);
  const expected = before.filter(event => { const selection = byPart.get(event.partId); return Boolean(selection && matchesSelection(selection, event.staffId, event.voiceId)); }).map(semanticKey);
  const actual = after.map(semanticKey);
  if (expected.length !== actual.length) throw new Error(`Staff/Voice 추출 검증 실패: 선택 이벤트 ${expected.length}개와 파생 이벤트 ${actual.length}개가 다릅니다.`);
  const mismatch = expected.findIndex((key, index) => key !== actual[index]);
  if (mismatch >= 0) throw new Error(`Staff/Voice 추출 검증 실패: ${mismatch + 1}번째 이벤트의 pitch/onset/duration/voice가 원본과 다릅니다.`);
};

export type AppliedScoreSelection = { selections: PartSelection[]; warnings: string[] };

/** Mutates a temporary render/export document; the caller's XML string remains immutable. */
export const applyScoreViewSelections = (doc: XMLDocument, selections: readonly PartSelection[]): AppliedScoreSelection => {
  const parts = partInventory(doc);
  if (!selections.length) return { selections: [], warnings: [] };
  validateSelectionsForParts(parts, selections);
  const selectionByPart = new Map(selections.map(selection => [selection.partId, selection])), keep = new Set(selectionByPart.keys());
  const allWholeParts = keep.size === parts.length && selections.every(selection => selection.scope === 'whole_part');
  if (allWholeParts) return { selections: selections.map(cloneSelection), warnings: [] };
  const before = semanticEventInventory(doc);
  cleanPartList(doc, keep);
  const warnings: string[] = [];
  for (const part of [...doc.documentElement.children].filter(element => element.localName === 'part')) {
    const partId = part.getAttribute('id') || '', selection = selectionByPart.get(partId);
    if (!selection) { part.remove(); continue; }
    warnings.push(...filterPartToSelection(doc, part, selection).map(warning => `${partId}: ${warning}`));
  }
  validateDerivedSemantics(before, semanticEventInventory(doc), selections);
  return { selections: selections.map(cloneSelection), warnings };
};

const presentationCleanup = (doc: XMLDocument, recipe: ExcerptRecipe) => {
  for (const tag of ['defaults', 'credit', 'work', 'movement-title', 'movement-number']) for (const element of [...doc.getElementsByTagName(tag)]) element.remove();
  for (const print of [...doc.getElementsByTagName('print')]) print.remove();
  if (recipe.presentation.removeLyrics) for (const lyric of [...doc.getElementsByTagName('lyric')]) lyric.remove();
  if (recipe.presentation.removeDynamics) for (const dynamics of [...doc.getElementsByTagName('dynamics')]) dynamics.remove();
};

const applyExcerptSystemBreaks = (doc: XMLDocument, recipe: ExcerptRecipe, startOrdinal: number) => {
  const breakOrdinals = new Set(recipe.presentation.systemBreakBeforeMeasureIds.map(ordinalFromMeasureId));
  if (!breakOrdinals.size) return;
  // MusicXML layout directives are read from the first surviving part. Adding
  // identical print elements to every part is redundant and can confuse other
  // consumers of an exported derived score.
  const part = [...doc.documentElement.children].find(element => element.localName === 'part');
  if (!part) return;
  directChildren(part, 'measure').forEach((measure, localIndex) => {
    if (!breakOrdinals.has(startOrdinal + localIndex)) return;
    const print = doc.createElement('print'); print.setAttribute('new-system', 'yes');
    const attributes = firstDirect(measure, 'attributes');
    measure.insertBefore(print, attributes?.nextSibling || measure.firstChild);
  });
};

const validateRecipe = (snapshot: ScoreSnapshot, recipe: ViewRecipe | ExcerptRecipe) => {
  if (snapshot.sourceVersionId !== recipe.sourceVersionId || snapshot.sourceHash !== recipe.sourceHash) throw new Error('원본 악보가 snapshot 이후 변경되었습니다. 악보 도구를 다시 열어 주세요.');
  validateSelectionsForParts(snapshot.parts, recipe.selections);
  const scoped = recipe.selections.some(selection => selection.scope !== 'whole_part');
  if (scoped && snapshot.schemaVersion === '1.0.0') throw new Error('Legacy snapshot의 Voice 의미는 안전하게 판별할 수 없습니다. 원본 MusicXML과 migrateScoreSnapshot을 사용해 주세요.');
  if (scoped && (recipe.schemaVersion === '1.0.0' || recipe.schemaVersion === '1.3.0')) throw new Error('Staff/Voice 선택은 새 recipe schema가 필요합니다. migrateViewRecipe 또는 migrateExcerptRecipe를 적용해 주세요.');
};

const selectionMap = (selections: readonly PartSelection[]) => new Map(selections.map(selection => [selection.partId, selection]));
const selectedSourceEvents = (snapshot: ScoreSnapshot, selections: readonly PartSelection[]) => {
  const byPart = selectionMap(selections);
  return snapshot.events.filter(event => { const selection = byPart.get(event.partId); return Boolean(selection && matchesEventSelection(selection, event)); });
};
const sourceMapForDerivedDocument = (sourceEvents: readonly ScoreEventRef[], doc: XMLDocument): SourceMapEntry[] => {
  const derivedEvents = eventInventory(doc);
  if (sourceEvents.length !== derivedEvents.length) throw new Error(`Source map 생성 실패: 원본 선택 이벤트 ${sourceEvents.length}개와 파생 이벤트 ${derivedEvents.length}개가 다릅니다.`);
  return sourceEvents.map((sourceEvent, index) => {
    const derivedEvent = derivedEvents[index];
    if (!derivedEvent || derivedEvent.partId !== sourceEvent.partId) throw new Error(`Source map 생성 실패: ${sourceEvent.id}에 대응하는 파생 이벤트를 찾을 수 없습니다.`);
    return { sourceEventId: sourceEvent.id, derivedEventId: derivedEvent.id, partId: sourceEvent.partId, measureId: sourceEvent.measureId };
  });
};

export const deriveExcerptScore = async (xml: string, snapshot: ScoreSnapshot, recipe: ExcerptRecipe): Promise<DerivedScore> => {
  validateRecipe(snapshot, recipe);
  const startOrdinal = ordinalFromMeasureId(recipe.range.startMeasureId), endOrdinal = ordinalFromMeasureId(recipe.range.endMeasureId);
  if (!Number.isInteger(startOrdinal) || !Number.isInteger(endOrdinal) || startOrdinal < 1 || endOrdinal < startOrdinal || endOrdinal > snapshot.measures.length) throw new Error('올바른 연속 마디 범위를 선택해 주세요.');
  const selected = new Set(recipe.selections.map(selection => selection.partId)), doc = parseMusicXml(xml), applied = applyScoreViewSelections(doc, recipe.selections);
  for (const part of [...doc.documentElement.children].filter(element => element.localName === 'part')) {
    const partId = part.getAttribute('id') || ''; if (!selected.has(partId)) { part.remove(); continue; }
    const measures = directChildren(part, 'measure'), firstKept = measures[startOrdinal - 1]; if (!firstKept) throw new Error(`${partId}에 선택한 시작 마디가 없습니다.`);
    copyEffectiveAttributes(doc, measures, firstKept);
    measures.forEach((measure, index) => { measure.removeAttribute('width'); if (index + 1 < startOrdinal || index + 1 > endOrdinal) measure.remove(); });
  }
  presentationCleanup(doc, recipe);
  applyExcerptSystemBreaks(doc, recipe, startOrdinal);
  const sourceEvents = selectedSourceEvents(snapshot, recipe.selections).filter(event => event.measureOrdinal >= startOrdinal && event.measureOrdinal <= endOrdinal);
  const sourceMap = sourceMapForDerivedDocument(sourceEvents, doc);
  const derivedXml = new XMLSerializer().serializeToString(doc); parseMusicXml(derivedXml);
  const derivedParts = partInventory(doc);
  return { sourceVersionId: snapshot.sourceVersionId, sourceHash: snapshot.sourceHash, recipeHash: await recipeHash(recipe), xml: derivedXml, sourceMap, warnings: applied.warnings, partCount: derivedParts.length, measureCount: endOrdinal - startOrdinal + 1, staffCount: derivedParts.reduce((sum, part) => sum + Math.max(1, part.staves.length), 0) };
};

export const deriveSelectedPartsScore = async (xml: string, snapshot: ScoreSnapshot, viewRecipe: ViewRecipe): Promise<DerivedScore> => {
  validateRecipe(snapshot, viewRecipe);
  const selected = new Set(viewRecipe.selections.map(selection => selection.partId)), doc = parseMusicXml(xml), applied = applyScoreViewSelections(doc, viewRecipe.selections);
  for (const part of [...doc.documentElement.children].filter(element => element.localName === 'part')) {
    const partId = part.getAttribute('id') || '';
    if (!selected.has(partId)) { part.remove(); continue; }
    for (const measure of directChildren(part, 'measure')) { measure.removeAttribute('width'); for (const print of directChildren(measure, 'print')) print.remove(); }
  }
  const derivedXml = new XMLSerializer().serializeToString(doc); parseMusicXml(derivedXml);
  const derivedParts = partInventory(doc);
  const sourceMap = sourceMapForDerivedDocument(selectedSourceEvents(snapshot, viewRecipe.selections), doc);
  return {
    sourceVersionId: snapshot.sourceVersionId, sourceHash: snapshot.sourceHash, recipeHash: await recipeHash(viewRecipe), xml: derivedXml,
    sourceMap,
    warnings: applied.warnings, partCount: derivedParts.length, measureCount: snapshot.measures.length,
    staffCount: derivedParts.reduce((sum, part) => sum + Math.max(1, part.staves.length), 0),
  };
};

/**
 * Convenience wrapper for hosts that only have a MusicXML string and selected
 * part ids. Snapshot creation and recipe validation deliberately go through the
 * same code path as the full Score Tools engine.
 *
 * Requires DOMParser and XMLSerializer (available in browsers, or through a
 * standards-compatible DOM shim in a headless JavaScript runtime).
 */
export const filterMusicXmlParts = async (xml: string, partIds: readonly string[], sourceId = 'score-tools-inline'): Promise<string> => {
  const snapshot = await createScoreSnapshot(xml, sourceId);
  const availablePartIds = snapshot.parts.map(part => part.id), available = new Set(availablePartIds);
  const unknownPartIds = [...new Set(partIds)].filter(partId => !available.has(partId));
  if (unknownPartIds.length) throw new Error(`원본에 없는 Part입니다: ${unknownPartIds.join(', ')}`);
  // Keep the viewer contract: no selection and an explicit all-parts selection
  // both mean a full-score derived document. Unknown ids never fall through to it.
  const selectedPartIds = partIds.length === 0 ? availablePartIds : [...partIds];
  const recipe: ViewRecipe = {
    ...defaultViewRecipe(snapshot),
    selections: selectedPartIds.map(partId => ({ partId, scope: 'whole_part' })),
  };
  return (await deriveSelectedPartsScore(xml, snapshot, recipe)).xml;
};

/** Staff/Voice-aware convenience wrapper. As in the viewer contract, an empty
 * selection means the unfiltered full score. */
export const filterMusicXmlSelections = async (xml: string, selections: readonly PartSelection[], sourceId = 'score-tools-inline'): Promise<string> => {
  const snapshot = await createScoreSnapshot(xml, sourceId);
  const recipe: ViewRecipe = { ...defaultViewRecipe(snapshot), selections: selections.length ? selections.map(cloneSelection) : snapshot.parts.map(part => ({ partId: part.id, scope: 'whole_part' })) };
  return (await deriveSelectedPartsScore(xml, snapshot, recipe)).xml;
};

export const suggestedDownloadName = (title: string, suffix: string, extension: string) => {
  const safe = title.normalize('NFKC').replace(/[<>:"/\\|?*\u0000-\u001F]+/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 100) || 'score';
  return `${safe} - ${suffix}.${extension}`;
};

export const sourceMapSidecar = (snapshot: ScoreSnapshot, derived: DerivedScore, recipe: ViewRecipe | ExcerptRecipe) => JSON.stringify({ schema: 'musicanote-derived-score-sidecar', schemaVersion: '1.1.0', snapshotSchemaVersion: snapshot.schemaVersion, sourceId: snapshot.sourceId, sourceVersionId: snapshot.sourceVersionId, sourceHash: snapshot.sourceHash, recipeHash: derived.recipeHash, recipe, sourceMap: derived.sourceMap }, null, 2);
