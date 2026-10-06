import { describe, expect, it } from 'vitest';
import { playbackInstrumentForWork } from './playbackInstrument';

const xml = `<score-partwise><part-list>
  <score-part id="P1"><part-name>Vln. I</part-name><score-instrument id="I1"><instrument-name>Violin</instrument-name></score-instrument><midi-instrument id="I1"><midi-program>41</midi-program></midi-instrument></score-part>
  <score-part id='P2'><part-name>Inner &amp; lower</part-name><part-abbreviation>Vla.</part-abbreviation><midi-instrument id='I2'><midi-program>42</midi-program></midi-instrument></score-part>
  <score-part id="P3"><part-name>Solo</part-name><midi-instrument id="I3"><midi-program>43</midi-program></midi-instrument></score-part>
</part-list><part id="P1"><measure><note/></measure></part></score-partwise>`;

describe('actual playback stream instrument metadata', () => {
  it('matches the actual stream prefix, not the first, displayed, or structure part', () => {
    const work = { streamId: 'P2:2:1', partName: 'Violin', xml, structureWork: { streamId: 'P1:1:1', partName: 'Violin' } };
    expect(playbackInstrumentForWork(work)).toEqual({ instrument: 'viola', partLabel: 'Inner & lower', pianoFallback: false, source: 'xml' });
  });

  it('uses MusicXML 1-based MIDI program when names are uninformative', () => {
    expect(playbackInstrumentForWork({ streamId: 'P3:1:1', partName: 'Solo', xml }).instrument).toBe('cello');
  });

  it.each([['Vln. II', 'violin'], ['Vla.', 'viola'], ['Vc.', 'cello'], ['Pno.', 'piano']])('recognizes %s without fetching XML', (partName, instrument) => {
    expect(playbackInstrumentForWork({ partName })).toMatchObject({ instrument, pianoFallback: false, source: 'part-name' });
  });

  it('keeps a missing-stream fallback anchored to the actual work part name', () => {
    const work = { streamId: 'missing:1:1', partName: 'Vc.', xml, structureWork: { partName: 'Violin' } };
    expect(playbackInstrumentForWork(work)).toMatchObject({ instrument: 'cello', partLabel: 'Vc.', source: 'part-name' });
  });

  it('clearly marks unknown or missing instruments as piano substitutions', () => {
    expect(playbackInstrumentForWork({ partName: 'Clarinet' })).toMatchObject({ instrument: 'piano', pianoFallback: true });
    expect(playbackInstrumentForWork(null)).toMatchObject({ instrument: 'piano', pianoFallback: true, source: 'default' });
  });

  it('does not read score-body tags or an unbounded malformed header', () => {
    expect(playbackInstrumentForWork({ streamId: 'P3', xml: '<score-partwise><part><instrument-name>Cello</instrument-name></part></score-partwise>' }).instrument).toBe('piano');
    expect(playbackInstrumentForWork({ streamId: 'P3', xml: '<score-partwise>' + ' '.repeat(256 * 1024) + xml }).source).toBe('default');
  });

  it('accepts namespaced metadata and preserves natural names', () => {
    expect(playbackInstrumentForWork({ streamId: 'P4:1:1', xml: '<m:part-list><m:score-part id="P4"><m:part-name>Violoncello</m:part-name></m:score-part></m:part-list>' })).toMatchObject({ instrument: 'cello', partLabel: 'Violoncello', source: 'xml' });
  });
});
