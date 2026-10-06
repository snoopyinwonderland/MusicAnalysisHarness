import { normalizeMusicXmlVoices } from '../music/musicXmlVoiceNormalizer';
import { newVerovioToolkit } from '../music/verovioRuntime';
import { parseMusicXml } from './musicXmlTransform';
import { normalizeImageWidth, verovioPageWidthForImage } from './excerptLayout';
import type { DerivedScore, ExcerptRecipe } from './model';

export type SvgExportResult = { pages: string[]; pageWidth: number; pageHeight: number; imageWidthPx: number; systemCount: number; warnings: string[] };

/**
 * The smallest Verovio contract required by Score Tools. Consumers can adapt
 * another Verovio loader without importing this application's WASM runtime.
 */
export type VerovioToolkitLike = {
  setOptions(options: Record<string, unknown>): void;
  loadData(data: string): boolean | number;
  getPageCount(): number;
  renderToSVG(page: number, xmlDeclaration?: boolean): string;
};

export type VerovioToolkitFactory = () => VerovioToolkitLike | Promise<VerovioToolkitLike>;

export type VerovioRenderDependencies = {
  /** A fresh toolkit must be returned for every invocation. */
  createToolkit: VerovioToolkitFactory;
  /** Optional, non-destructive normalization of the temporary render DOM. */
  normalizeDocument?: (document: XMLDocument) => void | Promise<void>;
};

export type DerivedScoreSvgRenderer = (
  score: DerivedScore,
  transpose?: string,
  presentation?: ExcerptRecipe['presentation'],
) => Promise<SvgExportResult>;

/**
 * Removes executable SVG surface while retaining Verovio's notation markup,
 * inline styles, paths, symbols, ids and ordinary internal fragment links.
 */
export const sanitizeVerovioSvg = (svg: string) => svg
  .replace(/<\s*(script|foreignObject|iframe|object|embed)\b[^>]*>[\s\S]*?<\s*\/\s*\1\s*>/gi, '')
  .replace(/<\s*(script|foreignObject|iframe|object|embed)\b[^>]*\/?\s*>/gi, '')
  .replace(/\s+on[a-z][\w:.-]*\s*=\s*(?:"[^"]*"|'[^']*'|[^\s>]+)/gi, '')
  .replace(/\s+(?:href|xlink:href)\s*=\s*(?:"\s*javascript:[^"]*"|'\s*javascript:[^']*'|javascript:[^\s>]+)/gi, '');

const explicitSvgDimensions = (svg: string, widthPx: number) => {
  const viewBox = svg.match(/\bviewBox="[\d.-]+\s+[\d.-]+\s+([\d.-]+)\s+([\d.-]+)"/);
  if (!viewBox) return svg;
  const viewWidth = Number(viewBox[1]), viewHeight = Number(viewBox[2]), heightPx = Math.max(1, Math.round(widthPx * viewHeight / Math.max(1, viewWidth)));
  return svg.replace('<svg ', `<svg width="${widthPx}" height="${heightPx}" `);
};

export const renderDerivedScoreToSvgWithDependencies = async (
  score: DerivedScore,
  transpose = '',
  presentation: ExcerptRecipe['presentation'] | undefined,
  dependencies: VerovioRenderDependencies,
): Promise<SvgExportResult> => {
  // The factory is intentionally invoked for each render so toolkit state can
  // never leak between independent scores or host viewer instances.
  const toolkit = await dependencies.createToolkit(), doc = parseMusicXml(score.xml);
  // Rendering normalization is temporary. The serialized MusicXML export stays untouched.
  await dependencies.normalizeDocument?.(doc);
  const scale = score.staffCount >= 12 ? 18 : score.staffCount >= 7 ? 20 : 25;
  const layout = presentation?.layout || 'single_system', wrapped = layout !== 'single_system', imageWidthPx = normalizeImageWidth(presentation?.imageWidthPx || 1200);
  const pageWidth = wrapped ? verovioPageWidthForImage(imageWidthPx, scale) : Math.min(16000, Math.max(1800, score.measureCount * 500 + score.staffCount * 90));
  const baseSystemHeight = Math.max(900, 360 + score.staffCount * 360), expectedSystems = Math.max(1, (presentation?.systemBreakBeforeMeasureIds.length || 0) + 1);
  const pageHeight = wrapped ? Math.min(60000, Math.max(4000, baseSystemHeight * Math.max(expectedSystems + 1, Math.ceil(score.measureCount / 2)))) : baseSystemHeight;
  const breaks = layout === 'single_system' ? 'none' : layout === 'auto_wrap' ? 'auto' : 'line';
  toolkit.setOptions({ pageWidth, pageHeight, pageMarginTop: 45, pageMarginBottom: 65, adjustPageHeight: true, scale, breaks, inputFrom: 'musicxml', svgViewBox: true, header: 'none', footer: 'none', mnumInterval: 1, spacingStaff: 12, spacingSystem: 8, transpose: transpose || '' });
  if (!toolkit.loadData(new XMLSerializer().serializeToString(doc))) throw new Error('파생 MusicXML을 Verovio에서 불러오지 못했습니다.');
  const pageCount = Math.max(1, toolkit.getPageCount()), pages: string[] = [];
  for (let page = 1; page <= pageCount; page++) {
    const svg = sanitizeVerovioSvg(toolkit.renderToSVG(page, false));
    pages.push(wrapped ? explicitSvgDimensions(svg, imageWidthPx) : svg);
  }
  const systemCount = pages.reduce((count, svg) => count + (svg.match(/class="system"/g) || []).length, 0), warnings: string[] = [];
  if (pageCount > 1) warnings.push('선택 범위가 길어 여러 SVG 페이지로 분리되었습니다.');
  if (layout === 'custom_breaks' && !presentation?.systemBreakBeforeMeasureIds.length) warnings.push('사용자 지정 줄바꿈 마디가 없어 한 시스템으로 조판될 수 있습니다.');
  return { pages, pageWidth, pageHeight, imageWidthPx: wrapped ? imageWidthPx : 0, systemCount, warnings };
};

export const createVerovioRenderer = (dependencies: VerovioRenderDependencies): DerivedScoreSvgRenderer =>
  (score, transpose = '', presentation) => renderDerivedScoreToSvgWithDependencies(score, transpose, presentation, dependencies);

const defaultVerovioRenderer = createVerovioRenderer({
  createToolkit: newVerovioToolkit,
  normalizeDocument: document => { normalizeMusicXmlVoices(document); },
});

/** Existing application adapter using the bundled Verovio WASM runtime. */
export const renderDerivedScoreToSvg: DerivedScoreSvgRenderer = (score, transpose = '', presentation) =>
  defaultVerovioRenderer(score, transpose, presentation);

export const downloadTextFile = (content: string, filename: string, type: string) => {
  const url = URL.createObjectURL(new Blob([content], { type })), anchor = document.createElement('a');
  anchor.href = url; anchor.download = filename; anchor.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
};
