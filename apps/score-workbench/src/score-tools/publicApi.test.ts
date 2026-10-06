import { afterEach, describe, expect, it, vi } from 'vitest';
import * as scoreTools from './index';
import { createScoreToolsEngine } from './engine';
import { createVerovioRenderer, sanitizeVerovioSvg } from './verovioExport';
import type { DerivedScore, ExcerptRecipe, ScoreSnapshot } from './model';

const score: DerivedScore = {
  sourceVersionId: 'fixture@hash',
  sourceHash: 'hash',
  recipeHash: 'recipe',
  xml: '<score-partwise version="4.0"/>',
  sourceMap: [],
  warnings: [],
  partCount: 1,
  measureCount: 1,
  staffCount: 1,
};

const originalDomParser = globalThis.DOMParser;
const originalXmlSerializer = globalThis.XMLSerializer;

afterEach(() => {
  if (originalDomParser) globalThis.DOMParser = originalDomParser;
  else Reflect.deleteProperty(globalThis, 'DOMParser');
  if (originalXmlSerializer) globalThis.XMLSerializer = originalXmlSerializer;
  else Reflect.deleteProperty(globalThis, 'XMLSerializer');
});

describe('portable Score Tools public API', () => {
  it('keeps React, download and raster helpers out of the headless entry point', () => {
    expect(typeof scoreTools.createScoreToolsEngine).toBe('function');
    expect(typeof scoreTools.filterMusicXmlParts).toBe('function');
    expect(typeof scoreTools.filterMusicXmlSelections).toBe('function');
    expect('downloadTextFile' in scoreTools).toBe(false);
    expect('exportSvgPages' in scoreTools).toBe(false);
    expect('createVerovioRenderer' in scoreTools).toBe(false);
  });

  it('keeps transforms usable without Verovio and gives a clear render error', async () => {
    const engine = createScoreToolsEngine();
    await expect(engine.renderDerivedScore(score)).rejects.toThrow('renderDerivedScore');
  });

  it('uses an injected renderer through the stateless engine facade', async () => {
    const rendered = { pages: ['<svg/>'], pageWidth: 1, pageHeight: 1, imageWidthPx: 0, systemCount: 1, warnings: [] };
    const renderer = vi.fn(async () => rendered);
    const engine = createScoreToolsEngine({ renderDerivedScore: renderer });
    await expect(engine.renderDerivedScore(score, '3')).resolves.toBe(rendered);
    expect(renderer).toHaveBeenCalledWith(score, '3');
    expect(typeof engine.createSnapshot).toBe('function');
    expect(typeof engine.deriveExcerpt).toBe('function');
    expect(typeof engine.deriveSelectedParts).toBe('function');
    expect(typeof engine.renderExcerpt).toBe('function');
    expect(typeof engine.createSidecar).toBe('function');
    expect(typeof engine.filterSelections).toBe('function');
  });

  it('creates a fresh injected Verovio toolkit for every render', async () => {
    class TestDomParser {
      parseFromString(source: string) {
        return { source, documentElement: { localName: 'score-partwise' }, getElementsByTagName: () => [] };
      }
    }
    class TestXmlSerializer {
      serializeToString(document: { source: string }) { return document.source; }
    }
    globalThis.DOMParser = TestDomParser as unknown as typeof DOMParser;
    globalThis.XMLSerializer = TestXmlSerializer as unknown as typeof XMLSerializer;

    let factoryCalls = 0, normalizationCalls = 0;
    const renderer = createVerovioRenderer({
      createToolkit: () => {
        factoryCalls++;
        return {
          setOptions: () => undefined,
          loadData: () => true,
          getPageCount: () => 1,
          renderToSVG: () => '<svg viewBox="0 0 100 50"><g class="system"/></svg>',
        };
      },
      normalizeDocument: () => { normalizationCalls++; },
    });
    await renderer(score);
    await renderer(score);
    expect(factoryCalls).toBe(2);
    expect(normalizationCalls).toBe(2);
  });

  it('removes executable SVG content but preserves Verovio notation and styles', () => {
    const unsafe = '<svg><style>.note{fill:red}</style><path class="note" d="M0 0" onclick="alert(1)"/><a href="javascript:alert(2)"><use href="#glyph"/></a><foreignObject><iframe src="x"/></foreignObject><script>alert(3)</script></svg>';
    const safe = sanitizeVerovioSvg(unsafe);
    expect(safe).toContain('<style>.note{fill:red}</style>');
    expect(safe).toContain('<path class="note" d="M0 0"/>');
    expect(safe).toContain('<use href="#glyph"/>');
    expect(safe).not.toMatch(/onclick|javascript:|foreignObject|iframe|script/i);
  });

  it('creates a portable sidecar without rendering', () => {
    const snapshot: ScoreSnapshot = {
      schemaVersion: '1.0.0', sourceId: 'fixture', sourceHash: 'hash', sourceVersionId: 'fixture@hash',
      createdAt: '2026-09-27T00:00:00.000Z', parts: [], measures: [], events: [],
    };
    const recipe = {
      schemaVersion: '1.3.0', sourceVersionId: 'fixture@hash', sourceHash: 'hash', source: 'original',
      view: { transpose: { enabled: false, interval: '', semitones: 0 } },
      range: { kind: 'measures', startMeasureId: 'measure:1', endMeasureId: 'measure:1' }, selections: [],
      presentation: { layout: 'single_system', imageWidthPx: 1200, targetSystemCount: 2, systemBreakBeforeMeasureIds: [], showMeasureNumbers: true, removeLyrics: false, removeDynamics: false },
    } satisfies ExcerptRecipe;
    const sidecar = createScoreToolsEngine().createSidecar(snapshot, score, recipe);
    expect(JSON.parse(sidecar)).toMatchObject({ schema: 'musicanote-derived-score-sidecar', sourceId: 'fixture', recipeHash: 'recipe' });
  });
});
