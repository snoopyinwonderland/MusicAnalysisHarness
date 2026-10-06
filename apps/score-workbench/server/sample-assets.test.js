import { it, expect } from 'vitest';
import { readFileSync, statSync } from 'node:fs';

it('ships all four sample banks with valid MP3 assets and redistribution attribution', () => {
  const manifest = JSON.parse(readFileSync('public/samples/manifest.json', 'utf8'));
  expect(Object.keys(manifest.instruments).sort()).toEqual(['cello', 'piano', 'viola', 'violin']);
  let totalBytes = 0;
  for (const [instrument, midis] of Object.entries(manifest.instruments)) {
    expect(midis.length).toBeGreaterThan(10);
    expect(new Set(midis).size).toBe(midis.length);
    expect([...midis].sort((a, b) => a - b)).toEqual(midis);
    for (const midi of midis) {
      expect(Number.isInteger(midi) && midi >= 0 && midi <= 127).toBe(true);
      const path = `public/samples/${instrument}/${midi}.mp3`;
      const bytes = readFileSync(path);
      expect(bytes.length).toBeGreaterThan(1000);
      const hasId3 = bytes.subarray(0, 3).toString('ascii') === 'ID3';
      const hasMpegFrame = bytes[0] === 0xff && (bytes[1] & 0xe0) === 0xe0;
      expect(hasId3 || hasMpegFrame).toBe(true);
      totalBytes += statSync(path).size;
    }
  }
  expect(totalBytes).toBeLessThan(2_000_000);
  expect(manifest.source).toMatch(/CC BY 3\.0/);
  const attribution = readFileSync('public/samples/README.md', 'utf8');
  expect(attribution).toMatch(/Frank Wen/);
  expect(attribution).toMatch(/gleitz\/midi-js-soundfonts/);
});
