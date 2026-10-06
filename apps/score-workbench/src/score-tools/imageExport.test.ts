import { describe, expect, it } from 'vitest';
import { buildJpegPdf, svgPixelDimensions } from './imageExport';

describe('score image export', () => {
  it('reads explicit SVG dimensions and falls back to the viewBox', () => {
    expect(svgPixelDimensions('<svg width="1200" height="800" viewBox="0 0 600 400"></svg>')).toMatchObject({ width: 1200, height: 800, limited: false });
    expect(svgPixelDimensions('<svg viewBox="0 0 900 450"></svg>')).toMatchObject({ width: 900, height: 450, limited: false });
  });

  it('limits oversized raster canvases without changing aspect ratio', () => {
    const result = svgPixelDimensions('<svg viewBox="0 0 40000 20000"></svg>');
    expect(result.limited).toBe(true);
    expect(result.width / result.height).toBeCloseTo(2, 3);
    expect(result.width).toBeLessThanOrEqual(16384);
    expect(result.width * result.height).toBeLessThanOrEqual(48_000_000);
  });

  it('builds a multi-page PDF with one JPEG XObject per page', () => {
    const jpeg = new Uint8Array([0xff, 0xd8, 0xff, 0xd9]);
    const pdf = buildJpegPdf([{ bytes: jpeg, width: 1200, height: 800 }, { bytes: jpeg, width: 800, height: 1200 }]);
    const text = new TextDecoder().decode(pdf);
    expect(text.startsWith('%PDF-1.4')).toBe(true);
    expect(text).toContain('/Type /Pages /Count 2');
    expect((text.match(/\/Subtype \/Image/g) || []).length).toBe(2);
    expect((text.match(/\/Filter \/DCTDecode/g) || []).length).toBe(2);
    expect(text).toContain('/MediaBox [0 0 900 600]');
    expect(text).toContain('/MediaBox [0 0 600 900]');
    expect(text.trimEnd().endsWith('%%EOF')).toBe(true);
  });
});
