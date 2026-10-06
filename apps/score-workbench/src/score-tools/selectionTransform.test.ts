import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { DOMParser as XmlDomParser, XMLSerializer as XmlSerializer } from '@xmldom/xmldom';
import { UNASSIGNED_VOICE_ID, type ViewRecipe } from './model';
import { createScoreSnapshot, defaultExcerptRecipe, defaultViewRecipe, deriveExcerptScore, deriveSelectedPartsScore, filterMusicXmlSelections, migrateScoreSnapshot, migrateViewRecipe, parseMusicXml, sourceMapSidecar } from './musicXmlTransform';

const previousParser = globalThis.DOMParser;
const previousSerializer = globalThis.XMLSerializer;

beforeAll(() => {
  globalThis.DOMParser = XmlDomParser as unknown as typeof DOMParser;
  globalThis.XMLSerializer = XmlSerializer as unknown as typeof XMLSerializer;
  const document = new XmlDomParser().parseFromString('<root><child/></root>', 'application/xml');
  const prototype = Object.getPrototypeOf(document.documentElement!.firstChild!);
  if (typeof prototype.remove !== 'function') prototype.remove = function remove(this: Element) { this.parentNode?.removeChild(this); };
});

afterAll(() => {
  if (previousParser) globalThis.DOMParser = previousParser; else Reflect.deleteProperty(globalThis, 'DOMParser');
  if (previousSerializer) globalThis.XMLSerializer = previousSerializer; else Reflect.deleteProperty(globalThis, 'XMLSerializer');
});

const fixture = `<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <part-list><score-part id="P1"><part-name>Piano</part-name></score-part></part-list>
  <part id="P1">
    <measure number="1">
      <attributes><divisions>2</divisions><staves>2</staves><clef number="1"><sign>G</sign><line>2</line></clef><clef number="2"><sign>F</sign><line>4</line></clef></attributes>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>2</duration><tie type="start"/><voice>1</voice><staff>1</staff><beam number="1">begin</beam><notations><tied type="start"/></notations></note>
      <note><pitch><step>D</step><octave>4</octave></pitch><duration>2</duration><voice>1</voice><staff>1</staff><beam number="1">end</beam></note>
      <backup><duration>4</duration></backup>
      <note><pitch><step>E</step><octave>3</octave></pitch><duration>2</duration><voice>2</voice><staff>2</staff><notations><arpeggiate/></notations></note>
      <note><chord/><pitch><step>G</step><octave>3</octave></pitch><duration>2</duration><voice>2</voice><staff>2</staff></note>
      <note><pitch><step>F</step><octave>3</octave></pitch><duration>2</duration><voice>2</voice><staff>2</staff></note>
    </measure>
    <measure number="2">
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>4</duration><tie type="stop"/><voice>1</voice><staff>1</staff><notations><tied type="stop"/></notations></note>
      <backup><duration>4</duration></backup>
      <direction><direction-type><words>shared staff direction</words></direction-type><staff>2</staff></direction>
      <note><pitch><step>A</step><octave>3</octave></pitch><duration>2</duration><voice>2</voice><staff>1</staff></note>
      <note><pitch><step>B</step><octave>3</octave></pitch><duration>2</duration><voice>2</voice><staff>2</staff></note>
    </measure>
  </part>
</score-partwise>`;

const text = (element: Element, tag: string) => element.getElementsByTagName(tag)[0]?.textContent?.trim() || '';
const pitches = (xml: string) => [...parseMusicXml(xml).getElementsByTagName('note')].map(note => text(note, 'step'));

describe('Score Tools Staff/Voice MusicXML derivation', () => {
  it('keeps a selected staff timeline, compacts its number, and reports cross-staff cleanup', async () => {
    const snapshot = await createScoreSnapshot(fixture, 'staff-fixture');
    const recipe: ViewRecipe = { ...defaultViewRecipe(snapshot), selections: [{ partId: 'P1', scope: 'staves', staffIds: ['2'] }] };
    const derived = await deriveSelectedPartsScore(fixture, snapshot, recipe);
    const document = parseMusicXml(derived.xml);

    expect(pitches(derived.xml)).toEqual(['E', 'G', 'F', 'B']);
    expect([...document.getElementsByTagName('note')].map(note => text(note, 'staff'))).toEqual(['1', '1', '1', '1']);
    expect(text(document.getElementsByTagName('attributes')[0], 'staves')).toBe('1');
    expect([...document.getElementsByTagName('clef')]).toHaveLength(1);
    expect(document.getElementsByTagName('arpeggiate')).toHaveLength(0);
    expect(document.getElementsByTagName('forward').length).toBeGreaterThanOrEqual(3);
    expect(derived.sourceMap).toHaveLength(4);
    expect(derived.sourceMap.map(entry => [entry.sourceEventId, entry.derivedEventId])).toEqual([
      ['event:P1:1:3', 'event:P1:1:1'],
      ['event:P1:1:4', 'event:P1:1:2'],
      ['event:P1:1:5', 'event:P1:1:3'],
      ['event:P1:2:3', 'event:P1:2:1'],
    ]);
    expect(derived.staffCount).toBe(1);
    expect(derived.warnings.join(' ')).toMatch(/cross-staff/);
    expect(derived.warnings.join(' ')).toMatch(/arpeggiation/);
    expect(fixture).toContain('<staff>2</staff>');
  });

  it('keeps all required staves for a cross-staff voice and removes other voices without changing events', async () => {
    const snapshot = await createScoreSnapshot(fixture, 'voice-fixture');
    const recipe: ViewRecipe = { ...defaultViewRecipe(snapshot), selections: [{ partId: 'P1', scope: 'voices', voiceIds: ['2'] }] };
    const derived = await deriveSelectedPartsScore(fixture, snapshot, recipe);
    const document = parseMusicXml(derived.xml);

    expect(pitches(derived.xml)).toEqual(['E', 'G', 'F', 'A', 'B']);
    expect([...document.getElementsByTagName('voice')].filter(node => node.parentElement?.localName === 'note').map(node => node.textContent)).toEqual(['2', '2', '2', '2', '2']);
    expect(derived.sourceMap).toHaveLength(5);
    expect(derived.staffCount).toBe(2);
    expect(derived.warnings.join(' ')).toMatch(/2개 Staff/);
    expect(derived.warnings.join(' ')).toMatch(/Voice가 지정되지 않은 Staff 지시/);
  });

  it('preserves whole-part engraving when a Staff or Voice scope retains every event', async () => {
    const snapshot = await createScoreSnapshot(fixture, 'complete-scope');
    const selections: ViewRecipe['selections'][] = [
      [{ partId: 'P1', scope: 'staves', staffIds: ['1', '2'] }],
      [{ partId: 'P1', scope: 'voices', voiceIds: ['1', '2'] }],
    ];
    for (const scoped of selections) {
      const recipe: ViewRecipe = { ...defaultViewRecipe(snapshot), selections: scoped };
      const derived = await deriveSelectedPartsScore(fixture, snapshot, recipe);
      const document = parseMusicXml(derived.xml);
      expect(document.getElementsByTagName('beam')).toHaveLength(2);
      expect(document.getElementsByTagName('arpeggiate')).toHaveLength(1);
      expect(document.getElementsByTagName('note')).toHaveLength(8);
      expect(derived.warnings).toEqual([]);
    }
  });

  it('does not treat an omitted declared-but-empty Staff as whole-part equivalent', async () => {
    const xml = `<score-partwise version="4.0"><part-list><score-part id="P1"><part-name>Piano</part-name></score-part></part-list><part id="P1"><measure number="1"><attributes><divisions>1</divisions><staves>2</staves><clef number="1"><sign>G</sign><line>2</line></clef><clef number="2"><sign>F</sign><line>4</line></clef></attributes><note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice><staff>1</staff></note></measure></part></score-partwise>`;
    const snapshot = await createScoreSnapshot(xml, 'empty-declared-staff');
    expect(snapshot.parts[0].staves).toEqual(['1', '2']);
    const recipe: ViewRecipe = { ...defaultViewRecipe(snapshot), selections: [{ partId: 'P1', scope: 'staves', staffIds: ['1'] }] };
    const derived = await deriveSelectedPartsScore(xml, snapshot, recipe);
    const document = parseMusicXml(derived.xml);
    expect(text(document.getElementsByTagName('attributes')[0], 'staves')).toBe('1');
    expect(document.getElementsByTagName('clef')).toHaveLength(1);
    expect(document.getElementsByTagName('clef')[0].getAttribute('number')).toBeNull();
    expect(derived.staffCount).toBe(1);
    expect(derived.sourceMap).toHaveLength(1);
  });

  it('promotes a retained cross-staff chord member to the duration-bearing head', async () => {
    const xml = `<score-partwise version="4.0"><part-list><score-part id="P1"><part-name>Piano</part-name></score-part></part-list><part id="P1"><measure number="1"><attributes><divisions>1</divisions><staves>2</staves></attributes><note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice><staff>1</staff></note><note><chord/><pitch><step>E</step><octave>4</octave></pitch><duration>1</duration><staff>2</staff></note></measure></part></score-partwise>`;
    const snapshot = await createScoreSnapshot(xml, 'cross-staff-chord');
    const recipe: ViewRecipe = { ...defaultViewRecipe(snapshot), selections: [{ partId: 'P1', scope: 'staves', staffIds: ['2'] }] };
    const derived = await deriveSelectedPartsScore(xml, snapshot, recipe);
    const note = parseMusicXml(derived.xml).getElementsByTagName('note')[0];
    expect(text(note, 'step')).toBe('E');
    expect(note.getElementsByTagName('chord')).toHaveLength(0);
    expect(text(note, 'duration')).toBe('1');
    expect(text(note, 'voice')).toBe('1');
    expect(derived.sourceMap).toHaveLength(1);
  });

  it('does not invent Voice 1 when source voice encoding is absent', async () => {
    const xml = `<score-partwise version="4.0"><part-list><score-part id="P1"><part-name>Solo</part-name></score-part></part-list><part id="P1"><measure number="1"><note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration></note></measure></part></score-partwise>`;
    const snapshot = await createScoreSnapshot(xml, 'unassigned');
    expect(snapshot.parts[0].voices).toEqual([UNASSIGNED_VOICE_ID]);
    expect(snapshot.events[0].voiceId).toBe(UNASSIGNED_VOICE_ID);
  });

  it('inherits only an explicitly encoded chord-head Voice and leaves other missing Voices unassigned', async () => {
    const xml = `<score-partwise version="4.0"><part-list><score-part id="P1"><part-name>Chords</part-name></score-part></part-list><part id="P1"><measure number="1"><attributes><divisions>1</divisions></attributes><note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><voice>2</voice></note><note><chord/><pitch><step>E</step><octave>4</octave></pitch><duration>1</duration></note><note><pitch><step>F</step><octave>4</octave></pitch><duration>1</duration></note><note><pitch><step>G</step><octave>4</octave></pitch><duration>1</duration></note><note><chord/><pitch><step>B</step><octave>4</octave></pitch><duration>1</duration><voice>3</voice></note><note><chord/><pitch><step>D</step><octave>5</octave></pitch><duration>1</duration></note></measure></part></score-partwise>`;
    const snapshot = await createScoreSnapshot(xml, 'voice-inheritance');
    expect(snapshot.schemaVersion).toBe('1.1.0');
    expect(snapshot.events.map(event => event.voiceId)).toEqual(['2', '2', UNASSIGNED_VOICE_ID, UNASSIGNED_VOICE_ID, '3', UNASSIGNED_VOICE_ID]);

    const recipe: ViewRecipe = { ...defaultViewRecipe(snapshot), selections: [{ partId: 'P1', scope: 'voices', voiceIds: ['2'] }] };
    const derived = await deriveSelectedPartsScore(xml, snapshot, recipe);
    expect(pitches(derived.xml)).toEqual(['C', 'E']);
  });

  it('rebuilds legacy Voice semantics from hash-matched source XML before scoped selection', async () => {
    const xml = `<score-partwise version="4.0"><part-list><score-part id="P1"><part-name>Legacy</part-name></score-part></part-list><part id="P1"><measure number="1"><note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><voice>2</voice></note><note><chord/><pitch><step>E</step><octave>4</octave></pitch><duration>1</duration></note><note><pitch><step>G</step><octave>4</octave></pitch><duration>1</duration></note></measure></part></score-partwise>`;
    const current = await createScoreSnapshot(xml, 'legacy');
    const legacy = {
      ...current,
      schemaVersion: '1.0.0' as const,
      parts: current.parts.map(part => ({ ...part, voices: ['1', '2'] })),
      events: current.events.map(event => event.voiceId === UNASSIGNED_VOICE_ID ? { ...event, voiceId: '1' } : event),
    };
    const unsafeRecipe: ViewRecipe = { ...defaultViewRecipe(legacy), selections: [{ partId: 'P1', scope: 'voices', voiceIds: ['1'] }] };
    await expect(deriveSelectedPartsScore(xml, legacy, unsafeRecipe)).rejects.toThrow('migrateScoreSnapshot');
    await expect(migrateScoreSnapshot(legacy, xml.replace('Legacy', 'Changed'))).rejects.toThrow('변경되어');

    const migrated = await migrateScoreSnapshot(legacy, xml);
    expect(migrated.schemaVersion).toBe('1.1.0');
    expect(migrated.events.map(event => event.voiceId)).toEqual(['2', '2', UNASSIGNED_VOICE_ID]);
    const recipe: ViewRecipe = { ...defaultViewRecipe(migrated), selections: [{ partId: 'P1', scope: 'voices', voiceIds: ['2'] }] };
    await expect(deriveSelectedPartsScore(xml, migrated, recipe)).resolves.toMatchObject({ partCount: 1 });
  });

  it('merges effective excerpt attributes by tag and staff identity', async () => {
    const xml = `<score-partwise version="4.0"><part-list><score-part id="P1"><part-name>Piano</part-name></score-part></part-list><part id="P1"><measure number="1"><attributes><divisions>2</divisions><key number="1"><fifths>0</fifths></key><key number="2"><fifths>-2</fifths></key><time number="1"><beats>4</beats><beat-type>4</beat-type></time><time number="2"><beats>3</beats><beat-type>4</beat-type></time><staves>2</staves><clef number="1"><sign>G</sign><line>2</line></clef><clef number="2"><sign>F</sign><line>4</line></clef><staff-details number="1"><staff-lines>5</staff-lines></staff-details><staff-details number="2"><staff-lines>4</staff-lines></staff-details></attributes><note><pitch><step>C</step><octave>4</octave></pitch><duration>2</duration><voice>1</voice><staff>1</staff></note></measure><measure number="2"><attributes><clef number="2"><sign>C</sign><line>4</line></clef></attributes><note><pitch><step>D</step><octave>4</octave></pitch><duration>2</duration><voice>1</voice><staff>1</staff></note></measure><measure number="3"><attributes><clef number="1"><sign>C</sign><line>3</line></clef></attributes><note><pitch><step>E</step><octave>4</octave></pitch><duration>2</duration><voice>1</voice><staff>1</staff></note></measure></part></score-partwise>`;
    const snapshot = await createScoreSnapshot(xml, 'effective-attributes');
    const recipe = defaultExcerptRecipe(snapshot, 3, 3);
    const derived = await deriveExcerptScore(xml, snapshot, recipe);
    const attributes = parseMusicXml(derived.xml).getElementsByTagName('attributes')[0];
    const numbers = (tag: string) => [...attributes.getElementsByTagName(tag)].map(node => node.getAttribute('number') || 'default');
    expect(text(attributes, 'divisions')).toBe('2');
    expect(text(attributes, 'staves')).toBe('2');
    expect(numbers('key')).toEqual(['1', '2']);
    expect(numbers('time')).toEqual(['1', '2']);
    expect(numbers('clef')).toEqual(['1', '2']);
    expect(numbers('staff-details')).toEqual(['1', '2']);
    expect([...attributes.getElementsByTagName('clef')].map(clef => text(clef, 'sign'))).toEqual(['C', 'C']);
  });

  it('renumbers excerpt source-map targets to the actual derived measure and event ordinals', async () => {
    const snapshot = await createScoreSnapshot(fixture, 'excerpt-map');
    const recipe = {
      ...defaultExcerptRecipe(snapshot, 2, 2),
      selections: [{ partId: 'P1', scope: 'staves' as const, staffIds: ['2'] }],
    };
    const derived = await deriveExcerptScore(fixture, snapshot, recipe);
    expect(derived.sourceMap).toEqual([{ sourceEventId: 'event:P1:2:3', derivedEventId: 'event:P1:1:1', partId: 'P1', measureId: 'measure:2' }]);
    expect(JSON.parse(sourceMapSidecar(snapshot, derived, recipe))).toMatchObject({ schemaVersion: '1.1.0', snapshotSchemaVersion: '1.1.0' });
  });

  it('treats an empty public selection as the unfiltered full score', async () => {
    const filtered = await filterMusicXmlSelections(fixture, [], 'full-score');
    expect(pitches(filtered)).toEqual(['C', 'D', 'E', 'G', 'F', 'C', 'A', 'B']);
    expect(parseMusicXml(filtered).getElementsByTagName('part')).toHaveLength(1);
  });

  it('rejects unknown/empty scoped IDs and requires explicit migration for a legacy recipe', async () => {
    const snapshot = await createScoreSnapshot(fixture, 'validation');
    const empty: ViewRecipe = { ...defaultViewRecipe(snapshot), selections: [{ partId: 'P1', scope: 'staves', staffIds: [] }] };
    await expect(deriveSelectedPartsScore(fixture, snapshot, empty)).rejects.toThrow('한 개 이상의 Staff');

    const unknown: ViewRecipe = { ...defaultViewRecipe(snapshot), selections: [{ partId: 'P1', scope: 'voices', voiceIds: ['99'] }] };
    await expect(deriveSelectedPartsScore(fixture, snapshot, unknown)).rejects.toThrow('없는 Voice');

    const legacy: ViewRecipe = { ...defaultViewRecipe(snapshot), schemaVersion: '1.0.0', selections: [{ partId: 'P1', scope: 'voices', voiceIds: ['1'] }] };
    await expect(deriveSelectedPartsScore(fixture, snapshot, legacy)).rejects.toThrow('migrateViewRecipe');
    await expect(deriveSelectedPartsScore(fixture, snapshot, migrateViewRecipe(legacy))).resolves.toMatchObject({ partCount: 1, staffCount: 1 });
  });
});
