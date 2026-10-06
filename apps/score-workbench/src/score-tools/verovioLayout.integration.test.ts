import { beforeAll, describe, expect, it } from 'vitest';
import createVerovioModule from 'verovio/wasm';
import { VerovioToolkit } from 'verovio/esm';

const measures = Array.from({ length: 12 }, (_, index) => `<measure number="${index + 1}">${index === 0 ? '<attributes><divisions>1</divisions><key><fifths>0</fifths></key><time><beats>4</beats><beat-type>4</beat-type></time><clef><sign>G</sign><line>2</line></clef></attributes>' : ''}${index === 4 || index === 8 ? '<print new-system="yes"/>' : ''}<note><pitch><step>C</step><octave>4</octave></pitch><duration>4</duration><type>whole</type></note></measure>`).join('');
const SCORE = `<score-partwise version="4.0"><part-list><score-part id="P1"><part-name>Test</part-name></score-part></part-list><part id="P1">${measures}</part></score-partwise>`;

let module: Awaited<ReturnType<typeof createVerovioModule>>;
beforeAll(async () => { module = await createVerovioModule(); });

const render = (breaks: 'none'|'line'|'auto', pageWidth: number) => {
  const toolkit = new VerovioToolkit(module);
  toolkit.setOptions({ inputFrom: 'musicxml', breaks, pageWidth, pageHeight: 30000, adjustPageHeight: true, scale: 25, svgViewBox: true });
  expect(toolkit.loadData(SCORE)).toBe(1);
  return toolkit.renderToSVG(1, false);
};

describe('Verovio excerpt image layout contract', () => {
  it('keeps current one-line mode and honors explicit three-system breaks in line mode', () => {
    expect((render('none', 4800).match(/class="system"/g) || []).length).toBe(1);
    expect((render('line', 4800).match(/class="system"/g) || []).length).toBe(3);
  });

  it('uses page width and scale to produce the requested SVG viewBox width', () => {
    const svg = render('line', 4800), viewBox = svg.match(/viewBox="[\d.-]+\s+[\d.-]+\s+([\d.-]+)\s+([\d.-]+)"/);
    expect(viewBox).not.toBeNull();
    expect(Number(viewBox![1])).toBe(1200);
  });
});
