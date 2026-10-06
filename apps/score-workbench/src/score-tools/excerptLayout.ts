import type { ExcerptRecipe, ScoreMeasureRef } from './model';

export type ExcerptLayout = ExcerptRecipe['presentation']['layout'];

export const EXCERPT_LAYOUT_OPTIONS: { value: ExcerptLayout; label: string; description: string }[] = [
  { value: 'single_system', label: '한 줄', description: '선택한 모든 마디를 한 줄로 이어 붙입니다.' },
  { value: 'auto_wrap', label: '가로 폭 지정 자동 줄 바꿈', description: '지정한 이미지 폭에 맞춰 Verovio가 자동으로 줄을 나눕니다.' },
  { value: 'system_count', label: '행 수 지정', description: '선택 마디를 지정한 행 수에 맞춰 균등하게 나눕니다.' },
  { value: 'custom_breaks', label: '줄 바꿈 마디 직접 입력', description: '표시 마디 번호로 새 줄이 시작될 위치를 지정합니다.' },
];

export const normalizeImageWidth = (value: number) => Math.round(Math.max(600, Math.min(3200, Number.isFinite(value) ? value : 1200)) / 50) * 50;
export const normalizeSystemCount = (value: number) => Math.max(2, Math.min(12, Number.isFinite(value) ? Math.round(value) : 2));

export const evenlySpacedBreakOrdinals = (startOrdinal: number, endOrdinal: number, requestedSystems: number) => {
  const count = Math.max(0, endOrdinal - startOrdinal + 1), systems = Math.max(1, Math.min(Math.trunc(requestedSystems), count));
  if (systems <= 1) return [];
  const breaks = new Set<number>();
  for (let system = 1; system < systems; system++) {
    const ordinal = startOrdinal + Math.round(system * count / systems);
    if (ordinal > startOrdinal && ordinal <= endOrdinal) breaks.add(ordinal);
  }
  return [...breaks].sort((a, b) => a - b);
};

export const parseBreakMeasureInput = (measures: readonly ScoreMeasureRef[], startOrdinal: number, endOrdinal: number, input: string) => {
  const tokens = input
    .replace(/\bm\.\s*/gi, 'm.')
    .split(/[,;\s]+/)
    .map(token => token.replace(/^m\./i, '').trim())
    .filter(Boolean);
  const selected = measures.filter(measure => measure.ordinal >= startOrdinal && measure.ordinal <= endOrdinal);
  const ordinalsByDisplayNumber = new Map<string, number[]>();
  for (const measure of selected) {
    const ordinals = ordinalsByDisplayNumber.get(measure.displayNumber) || [];
    ordinals.push(measure.ordinal);
    ordinalsByDisplayNumber.set(measure.displayNumber, ordinals);
  }
  const ordinals = new Set<number>(), unmatched = new Set<string>(), ambiguous = new Set<string>();
  for (const token of tokens) {
    const matches = ordinalsByDisplayNumber.get(token) || [];
    if (!matches.length) unmatched.add(token);
    else if (matches.length > 1) ambiguous.add(token);
    // The first selected measure already begins the first system, so it is not
    // a meaningful line-break target even when the user enters its display number.
    else if (matches[0] > startOrdinal) ordinals.add(matches[0]);
  }
  return {
    ordinals: [...ordinals].sort((a, b) => a - b),
    unmatched: [...unmatched],
    ambiguous: [...ambiguous],
  };
};

export const breakMeasureIdsForLayout = (measures: readonly ScoreMeasureRef[], startOrdinal: number, endOrdinal: number, layout: ExcerptLayout, targetSystemCount: number, customBreakOrdinals: readonly number[]) => {
  const ordinals = layout === 'system_count'
    ? evenlySpacedBreakOrdinals(startOrdinal, endOrdinal, normalizeSystemCount(targetSystemCount))
    : layout === 'custom_breaks'
      ? [...new Set(customBreakOrdinals.filter(ordinal => ordinal > startOrdinal && ordinal <= endOrdinal))].sort((a, b) => a - b)
      : [];
  const measureIdsByOrdinal = new Map(measures.map(measure => [measure.ordinal, measure.id]));
  return ordinals.map(ordinal => measureIdsByOrdinal.get(ordinal)).filter((id): id is string => Boolean(id));
};

export const verovioPageWidthForImage = (imageWidthPx: number, scale: number) => Math.round(normalizeImageWidth(imageWidthPx) * 100 / Math.max(1, scale));
