import { DOMParser as XmlDomParser } from '@xmldom/xmldom';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { UNASSIGNED_VOICE_ID } from '../score-tools/model';
import { applyScoreViewSelections, createScoreSnapshot } from '../score-tools/musicXmlTransform';
import { denseTempoDisplayIndexes, excerptMeasureIndexes, excerptOrdinalOffset, findSourceStreamNote, fullScoreBreakMode, fullScoreLayout, normalizeMusicXmlInput, phraseBoundaryLabel, phraseColorIndex, phraseSegmentKey, scoreStaffCount, sourceNoteIdentityMap, tiedNoteChain, type TieChainEvent } from './FullXmlNotation';

const previousParser = globalThis.DOMParser;

beforeAll(() => {
  globalThis.DOMParser = XmlDomParser as unknown as typeof DOMParser;
  const document = new XmlDomParser().parseFromString('<root><child/></root>', 'application/xml');
  const prototype = Object.getPrototypeOf(document.documentElement!.firstChild!);
  if (typeof prototype.remove !== 'function') prototype.remove = function remove(this: Element) { this.parentNode?.removeChild(this); };
});

afterAll(() => {
  if (previousParser) globalThis.DOMParser = previousParser;
  else Reflect.deleteProperty(globalThis, 'DOMParser');
});

const event = (value: string, overrides: Partial<Omit<TieChainEvent<string>, 'value'>> = {}): TieChainEvent<string> => ({
  value, partId: 'P3', staff: '1', voice: '1', measureOrdinal: 25, beat: 4, pitchMidi: 65, isRest: false, tieTypes: [], ...overrides,
});

describe('full score layout',()=>{
  it('expands tall pages for large ensembles without changing small scores',()=>{
    expect(fullScoreLayout(4)).toEqual({pageWidth:1900,pageHeight:2700,scale:24});
    expect(fullScoreLayout(5)).toEqual({pageWidth:2100,pageHeight:3100,scale:21});
    expect(fullScoreLayout(20)).toEqual({pageWidth:2100,pageHeight:6220,scale:18});
  });
  it('counts the declared staves of a multi-staff part',()=>{
    const part=(staves:number[])=>({getElementsByTagName:()=>staves.map(value=>({textContent:String(value)}))});
    const doc={getElementsByTagName:()=>[part([2]),part([])]} as unknown as XMLDocument;
    expect(scoreStaffCount(doc)).toBe(3);
  });  it('reflows for the viewer page instead of forcing source paper breaks',()=>{
    expect(fullScoreBreakMode).toBe('auto');
  });
});

describe('phrase boundary labels',()=>{
  it('labels a non-overlapping boundary by the phrase that starts there',()=>{
    expect(phraseBoundaryLabel({afterPhrase:2})).toBe('P2 시작');
    expect(phraseBoundaryLabel({})).toBe('경계');
  });
  it('uses the same palette slot for a phrase band and its start marker',()=>{
    expect(phraseColorIndex(1)).toBe(0);
    expect(phraseColorIndex(5)).toBe(0);
    expect(phraseColorIndex(2)).toBe(1);
  });
  it('changes only the selected phrase key when a new flash token is issued',()=>{
    expect(phraseSegmentKey('5-2',5,5,3)).toBe('5-2-3');
    expect(phraseSegmentKey('4-2',4,5,3)).toBe('4-2-0');
  });
});

describe('MusicXML input normalization',()=>{
  it('removes a UTF-8 BOM before Verovio format detection',()=>{
    expect(normalizeMusicXmlInput('\uFEFF<?xml version="1.0"?><score-partwise/>')).toBe('<?xml version="1.0"?><score-partwise/>');
  });
  it('does not alter MusicXML that has no BOM',()=>{
    const xml='<?xml version="1.0"?><score-partwise/>';
    expect(normalizeMusicXmlInput(xml)).toBe(xml);
  });
});

describe('MusicXML excerpt measure selection', () => {
  it('uses absolute XML ordinals when printed measure numbers repeat', () => {
    const labels = [...Array(3)].flatMap(() => Array.from({ length: 20 }, (_, index) => String(index + 1)));
    expect(excerptMeasureIndexes(labels, 13, 15)).toHaveLength(9);
    expect(excerptMeasureIndexes(labels, 13, 15, 13, 15)).toEqual([12, 13, 14]);
  });
  it('retains the absolute ordinal origin after trimming a public excerpt', () => {
    expect(excerptOrdinalOffset([{ measureOrdinal: 8 }, { measureOrdinal: 9 }] as never)).toBe(7);
    expect(excerptOrdinalOffset([])).toBe(0);
  });
});

describe('source-lane identity after Staff/Voice view selection', () => {
  const xml = `<score-partwise version="4.0">
    <part-list><score-part id="P1"><part-name>Piano</part-name></score-part></part-list>
    <part id="P1"><measure number="1">
      <attributes><divisions>1</divisions><staves>2</staves><clef number="1"><sign>G</sign><line>2</line></clef><clef number="2"><sign>F</sign><line>4</line></clef></attributes>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice><staff>1</staff></note>
      <backup><duration>1</duration></backup>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><voice>5</voice><staff>2</staff></note>
    </measure></part>
  </score-partwise>`;
  const target = { measureOrdinal: 1, measure: 1, beat: 1, pitchMidi: 60 };
  const parse = () => new XmlDomParser().parseFromString(xml, 'application/xml') as unknown as XMLDocument;

  it('keeps the existing full-score mapping unchanged', () => {
    const doc = parse(), identities = sourceNoteIdentityMap(doc), notes = [...doc.getElementsByTagName('note')];
    expect(findSourceStreamNote(notes, identities, 'P1:1:1', target)).toBe(notes[0]);
    expect(findSourceStreamNote(notes, identities, 'P1:2:5', target)).toBe(notes[1]);
    expect(identities.get(notes[1])).toMatchObject({ sourceIndex: 1, partId: 'P1', staff: '2', voice: '5', measureOrdinal: 1, beat: 1 });
  });

  it('matches the original Staff after a selected Staff is compacted to Staff 1', () => {
    const doc = parse(), identities = sourceNoteIdentityMap(doc), sourceStaff2 = doc.getElementsByTagName('note')[1];
    applyScoreViewSelections(doc, [{ partId: 'P1', scope: 'staves', staffIds: ['2'] }]);
    const notes = [...doc.getElementsByTagName('note')];
    expect(notes).toEqual([sourceStaff2]);
    expect(notes[0].getElementsByTagName('staff')[0]?.textContent).toBe('1');
    expect(findSourceStreamNote(notes, identities, 'P1:2:5', target)).toBe(sourceStaff2);
    expect(findSourceStreamNote(notes, identities, 'P1:1:1', target)).toBeUndefined();
  });

  it('keeps the original Staff and Voice identity for a Voice-scoped view', () => {
    const doc = parse(), identities = sourceNoteIdentityMap(doc), sourceVoice5 = doc.getElementsByTagName('note')[1];
    applyScoreViewSelections(doc, [{ partId: 'P1', scope: 'voices', voiceIds: ['5'] }]);
    const notes = [...doc.getElementsByTagName('note')];
    expect(notes[0].getElementsByTagName('staff')[0]?.textContent).toBe('1');
    expect(findSourceStreamNote(notes, identities, 'P1:2:5', target)).toBe(sourceVoice5);
    expect(findSourceStreamNote(notes, identities, 'P1:1:5', target)).toBeUndefined();
  });

  it('inherits only an explicit contiguous chord-head Voice and otherwise stays unassigned', async () => {
    const chordXml = `<score-partwise version="4.0">
      <part-list><score-part id="P1"><part-name>Chords</part-name></score-part></part-list>
      <part id="P1"><measure number="1"><attributes><divisions>1</divisions></attributes>
        <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><voice>2</voice></note>
        <note><chord/><pitch><step>E</step><octave>4</octave></pitch><duration>1</duration></note>
        <note><pitch><step>F</step><octave>4</octave></pitch><duration>1</duration></note>
        <note><pitch><step>G</step><octave>4</octave></pitch><duration>1</duration></note>
        <note><chord/><pitch><step>B</step><octave>4</octave></pitch><duration>1</duration><voice>3</voice></note>
        <note><chord/><pitch><step>D</step><octave>5</octave></pitch><duration>1</duration></note>
      </measure></part>
    </score-partwise>`;
    const doc = new XmlDomParser().parseFromString(chordXml, 'application/xml') as unknown as XMLDocument;
    const notes = [...doc.getElementsByTagName('note')], identities = sourceNoteIdentityMap(doc);
    const voices = notes.map(note => identities.get(note)?.voice);
    expect(voices).toEqual(['2', '2', UNASSIGNED_VOICE_ID, UNASSIGNED_VOICE_ID, '3', UNASSIGNED_VOICE_ID]);
    expect(voices).toEqual((await createScoreSnapshot(chordXml, 'full-xml-voice-contract')).events.map(event => event.voiceId));
    expect(findSourceStreamNote(notes, identities, 'P1:1:2', { measureOrdinal: 1, measure: 1, beat: 1, pitchMidi: 64 })).toBe(notes[1]);
    expect(findSourceStreamNote(notes, identities, `P1:1:${UNASSIGNED_VOICE_ID}`, { measureOrdinal: 1, measure: 1, beat: 2, pitchMidi: 65 })).toBe(notes[2]);
    expect(findSourceStreamNote(notes, identities, 'P1:1:1', { measureOrdinal: 1, measure: 1, beat: 2, pitchMidi: 65 })).toBeUndefined();
  });
});

describe('MusicXML tie highlighting', () => {
  it('follows the source tie in its staff and voice, not an earlier competing-voice F4', () => {
    // 57982.xml: P3/staff 1/voice 1 m25 beat 4 ties into m26 beat 1.
    // The staff 2/voice 5 F4 at m25 beat 3 is later in DOM order after a backup.
    const sourceStart = event('m25-staff1-voice1', { tieTypes: ['start'] });
    const wrongVoice = event('m25-staff2-voice5', { staff: '2', voice: '5', beat: 3, tieTypes: ['stop'] });
    const sourceStop = event('m26-staff1-voice1', { measureOrdinal: 26, beat: 1, tieTypes: ['stop'] });
    expect(tiedNoteChain(sourceStart, [sourceStart, wrongVoice, sourceStop])).toEqual(['m25-staff1-voice1', 'm26-staff1-voice1']);
  });

  it('continues a stop-and-start tie chain at each next onset', () => {
    const start = event('start', { tieTypes: ['start'] });
    const middle = event('middle', { measureOrdinal: 26, beat: 1, tieTypes: ['stop', 'start'] });
    const end = event('end', { measureOrdinal: 27, beat: 1, tieTypes: ['stop'] });
    expect(tiedNoteChain(start, [start, middle, end])).toEqual(['start', 'middle', 'end']);
  });

  it('does not jump across a new attack, rest, or malformed continuation to a later stop', () => {
    const start = event('start', { tieTypes: ['start'] });
    const attack = event('attack', { measureOrdinal: 26, beat: 1 });
    const laterStop = event('later-stop', { measureOrdinal: 27, beat: 1, tieTypes: ['stop'] });
    const rest = event('rest', { measureOrdinal: 26, beat: 1, pitchMidi: 0, isRest: true });
    const malformed = event('malformed', { measureOrdinal: 26, beat: 1, tieTypes: ['continue'] });
    expect(tiedNoteChain(start, [start, attack, laterStop])).toEqual(['start']);
    expect(tiedNoteChain(start, [start, rest, laterStop])).toEqual(['start']);
    expect(tiedNoteChain(start, [start, malformed, laterStop])).toEqual(['start']);
  });

  it('collapses dense micro-tempo automation but preserves a large tempo change', () => {
    const keep = denseTempoDisplayIndexes([
      { measureIndex: 0, bpm: 63, pure: true },
      { measureIndex: 0, bpm: 68, pure: true },
      { measureIndex: 1, bpm: 65, pure: true },
      { measureIndex: 2, bpm: 70, pure: true },
      { measureIndex: 3, bpm: 112, pure: true },
      { measureIndex: 4, bpm: 109, pure: true },
    ]);
    expect([...keep]).toEqual([0, 4]);
  });});
