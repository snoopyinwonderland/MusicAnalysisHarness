import { describe, expect, it } from 'vitest';
import { rational, stableJson, testOpenScoreExportPolicy } from './model';
import { TRANSPOSE_OPTIONS, transposeRecipe } from './transposition';
import { defaultExcerptRecipe, normalizePartViewSelection } from './musicXmlTransform';
import { breakMeasureIdsForLayout, evenlySpacedBreakOrdinals, normalizeImageWidth, normalizeSystemCount, parseBreakMeasureInput, verovioPageWidthForImage } from './excerptLayout';

describe('score tools foundation', () => {
  it('uses canonical object ordering for recipe hashes', () => {
    expect(stableJson({ z: 1, a: { y: 2, b: 3 } })).toBe(stableJson({ a: { b: 3, y: 2 }, z: 1 }));
  });

  it('stores score timing as reduced rational values', () => {
    expect(rational(6, 12)).toEqual({ numerator: 1, denominator: 2 });
    expect(rational(-6, -12)).toEqual({ numerator: 1, denominator: 2 });
    expect(rational(7, 0)).toEqual({ numerator: 0, denominator: 1 });
  });

  it('keeps test access open behind a replaceable policy adapter', () => {
    expect(testOpenScoreExportPolicy.mode).toBe('test-open');
    expect(testOpenScoreExportPolicy.decide({ action: 'musicxml', sourceId: 'fixture', accessPolicy: 'research-preview' })).toEqual({ allowed: true });
  });

  it('uses an absolute -7…+7 semitone recipe and never accumulates a prior value', () => {
    expect(transposeRecipe('2')).toEqual({ enabled: true, interval: '2', semitones: 2 });
    expect(transposeRecipe('-7')).toEqual({ enabled: true, interval: '-7', semitones: -7 });
    expect(transposeRecipe('7')).toEqual({ enabled: true, interval: '7', semitones: 7 });
    expect(transposeRecipe('not-supported')).toEqual({ enabled: false, interval: '', semitones: 0 });
    expect(TRANSPOSE_OPTIONS.map(option => option.semitones)).toEqual([7, 6, 5, 4, 3, 2, 1, 0, -1, -2, -3, -4, -5, -6, -7]);
    expect(new Set(TRANSPOSE_OPTIONS.map(option => option.interval)).size).toBe(TRANSPOSE_OPTIONS.length);
  });

  it('treats zero or all checked parts as the full score view', () => {
    const parts = ['violin', 'cello', 'piano'];
    expect(normalizePartViewSelection(parts, [])).toEqual([]);
    expect(normalizePartViewSelection(parts, parts)).toEqual([]);
    expect(normalizePartViewSelection(parts, ['violin'])).toEqual(['violin']);
    expect(normalizePartViewSelection(parts, ['piano', 'missing', 'violin'])).toEqual(['violin', 'piano']);
  });

  it('creates staff/voice-capable schema 1.4 excerpts with a two-system target by default', () => {
    const snapshot = {
      schemaVersion: '1.0.0' as const,
      sourceId: 'score',
      sourceHash: 'hash',
      sourceVersionId: 'score@hash',
      createdAt: '2026-09-27T00:00:00.000Z',
      parts: [],
      measures: [{ id: 'measure:1', ordinal: 1, displayNumber: '0', implicit: true }],
      events: [],
    };
    const recipe = defaultExcerptRecipe(snapshot);
    expect(recipe.schemaVersion).toBe('1.4.0');
    expect(recipe.presentation.targetSystemCount).toBe(2);
  });

  it('creates deterministic system-count and custom measure breaks', () => {
    const measures = Array.from({ length: 12 }, (_, index) => ({ id: `measure:${index + 1}`, ordinal: index + 1, displayNumber: String(index + 1), implicit: false }));
    expect(evenlySpacedBreakOrdinals(1, 12, 2)).toEqual([7]);
    expect(evenlySpacedBreakOrdinals(1, 12, 3)).toEqual([5, 9]);
    expect(breakMeasureIdsForLayout(measures, 3, 10, 'system_count', 2, [])).toEqual(['measure:7']);
    expect(breakMeasureIdsForLayout(measures, 3, 10, 'system_count', 3, [])).toEqual(['measure:6', 'measure:8']);
    expect(breakMeasureIdsForLayout(measures, 3, 10, 'custom_breaks', 2, [3, 9, 6, 99, 6])).toEqual(['measure:6', 'measure:9']);
    expect(breakMeasureIdsForLayout(measures, 3, 10, 'single_system', 2, [6])).toEqual([]);
    expect(normalizeSystemCount(1)).toBe(2);
    expect(normalizeSystemCount(7.6)).toBe(8);
    expect(normalizeSystemCount(99)).toBe(12);
    expect(normalizeSystemCount(Number.NaN)).toBe(2);
  });

  it('parses displayed measure numbers without exposing internal ordinals', () => {
    const measures = [
      { id: 'measure:1', ordinal: 1, displayNumber: '0', implicit: true },
      { id: 'measure:2', ordinal: 2, displayNumber: '1', implicit: false },
      { id: 'measure:3', ordinal: 3, displayNumber: '2', implicit: false },
      { id: 'measure:4', ordinal: 4, displayNumber: '2', implicit: false },
      { id: 'measure:5', ordinal: 5, displayNumber: '4A', implicit: false },
    ];
    expect(parseBreakMeasureInput(measures, 1, 5, 'm. 0, 1; 4A 99 2 m.1')).toEqual({
      ordinals: [2, 5],
      unmatched: ['99'],
      ambiguous: ['2'],
    });
    expect(parseBreakMeasureInput(measures, 3, 5, '0 1 4A')).toEqual({
      ordinals: [5],
      unmatched: ['0', '1'],
      ambiguous: [],
    });
  });

  it('normalizes exported SVG width and converts it to Verovio page units', () => {
    expect(normalizeImageWidth(583)).toBe(600);
    expect(normalizeImageWidth(1274)).toBe(1250);
    expect(normalizeImageWidth(9999)).toBe(3200);
    expect(verovioPageWidthForImage(1200, 25)).toBe(4800);
    expect(verovioPageWidthForImage(1200, 20)).toBe(6000);
  });
});
