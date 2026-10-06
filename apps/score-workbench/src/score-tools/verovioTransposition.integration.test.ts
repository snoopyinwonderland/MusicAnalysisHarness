import { beforeAll, describe, expect, it } from 'vitest';
import createVerovioModule from 'verovio/wasm';
import { VerovioToolkit } from 'verovio/esm';

const SCORE = `<?xml version="1.0"?>
<score-partwise version="4.0">
  <part-list><score-part id="P1"><part-name>Test</part-name></score-part></part-list>
  <part id="P1"><measure number="1">
    <attributes><divisions>1</divisions><key><fifths>0</fifths></key><time><beats>4</beats><beat-type>4</beat-type></time><clef><sign>G</sign><line>2</line></clef></attributes>
    <note id="n1"><pitch><step>C</step><octave>4</octave></pitch><duration>4</duration><type>whole</type></note>
  </measure></part>
</score-partwise>`;

let module: Awaited<ReturnType<typeof createVerovioModule>>;

beforeAll(async () => { module = await createVerovioModule(); });

const transposedMei = (semitones: number) => {
  const toolkit = new VerovioToolkit(module);
  toolkit.setOptions({ inputFrom: 'musicxml', transpose: semitones === 0 ? '' : String(semitones) });
  expect(toolkit.loadData(SCORE)).toBe(1);
  // Verovio 6.3 exposes getMEI at runtime, but its distributed TypeScript
  // declaration omits it. Keep the compatibility cast local to this test.
  return (toolkit as unknown as { getMEI(options: { pageNo: number; scoreBased: boolean }): string }).getMEI({ pageNo: 0, scoreBased: true });
};

const noteTag = (mei: string) => mei.match(/<note\b[^>]*xml:id="n1"[^>]*>/)?.[0] || '';
const keyTag = (mei: string) => mei.match(/<keySig\b[^>]*>/)?.[0] || '';

describe('Verovio chromatic transposition contract', () => {
  it('moves the actual note pitch and key signature for positive and negative semitones', () => {
    const original = transposedMei(0), upOne = transposedMei(1), upTwo = transposedMei(2), downOne = transposedMei(-1);

    expect(noteTag(original)).toContain('pname="c"');
    expect(noteTag(upOne)).toContain('pname="d"');
    expect(noteTag(upTwo)).toContain('pname="d"');
    expect(noteTag(downOne)).toContain('pname="b"');
    expect(keyTag(original)).toContain('sig="0"');
    expect(keyTag(upOne)).toContain('sig="5f"');
    expect(keyTag(upTwo)).toContain('sig="2s"');
    expect(keyTag(downOne)).toContain('sig="5s"');
  });

  it('supports every requested absolute offset from -7 through +7', () => {
    for (let semitones = -7; semitones <= 7; semitones++) {
      const mei = transposedMei(semitones);
      expect(noteTag(mei), `note at ${semitones} semitones`).not.toBe('');
      expect(keyTag(mei), `key at ${semitones} semitones`).not.toBe('');
    }
  });
});
