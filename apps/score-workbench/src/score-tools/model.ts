export type Rational = { numerator: number; denominator: number };

export type ScorePartRef = {
  id: string;
  name: string;
  abbreviation?: string;
  sourceIndex: number;
  staves: string[];
  voices: string[];
};

export type ScoreMeasureRef = {
  id: string;
  ordinal: number;
  displayNumber: string;
  implicit: boolean;
};

export type ScoreEventRef = {
  id: string;
  partId: string;
  measureId: string;
  measureOrdinal: number;
  eventOrdinal: number;
  staffId: string;
  voiceId: string;
  onset: Rational;
  duration: Rational;
  kind: 'note' | 'rest';
};

export type ScoreSnapshot = {
  /**
   * 1.0.0 snapshots may have classified every note without an explicit
   * <voice> as Voice 1. Version 1.1.0 resolves only safe chord-continuation
   * inheritance and otherwise uses UNASSIGNED_VOICE_ID.
   */
  schemaVersion: '1.0.0' | '1.1.0';
  sourceId: string;
  sourceHash: string;
  sourceVersionId: string;
  createdAt: string;
  parts: ScorePartRef[];
  measures: ScoreMeasureRef[];
  events: ScoreEventRef[];
};

/** Stable sentinel for MusicXML notes whose source does not encode <voice>. */
export const UNASSIGNED_VOICE_ID = '__unassigned__' as const;

export type WholePartSelection = { partId: string; scope: 'whole_part' };
export type StaffSelection = { partId: string; scope: 'staves'; staffIds: string[] };
export type VoiceSelection = { partId: string; scope: 'voices'; voiceIds: string[] };

/**
 * A part-scoped selection. Staff and voice identifiers are source MusicXML
 * values, not UI ordinals. One recipe may contain at most one selection for a
 * given part.
 */
export type PartSelection = WholePartSelection | StaffSelection | VoiceSelection;

export type TransposeRecipe = {
  enabled: boolean;
  interval: string;
  semitones: number;
};

export type ViewRecipe = {
  /** 1.0.0 is the legacy whole-part-only shape; 1.1.0 adds staff/voice scopes. */
  schemaVersion: '1.0.0' | '1.1.0';
  sourceVersionId: string;
  sourceHash: string;
  transpose: TransposeRecipe;
  selections: PartSelection[];
};

export type ExcerptRecipe = {
  /** 1.3.0 is the legacy whole-part-only shape; 1.4.0 adds staff/voice scopes. */
  schemaVersion: '1.3.0' | '1.4.0';
  sourceVersionId: string;
  sourceHash: string;
  source: 'original' | 'current_view';
  view: { transpose: TransposeRecipe };
  range: { kind: 'measures'; startMeasureId: string; endMeasureId: string };
  selections: PartSelection[];
  presentation: {
    layout: 'single_system' | 'auto_wrap' | 'system_count' | 'custom_breaks';
    imageWidthPx: number;
    targetSystemCount: number;
    systemBreakBeforeMeasureIds: string[];
    showMeasureNumbers: true;
    removeLyrics: boolean;
    removeDynamics: boolean;
  };
};

export type SourceMapEntry = {
  sourceEventId: string;
  derivedEventId: string;
  partId: string;
  measureId: string;
};

export type DerivedScore = {
  sourceVersionId: string;
  sourceHash: string;
  recipeHash: string;
  xml: string;
  sourceMap: SourceMapEntry[];
  warnings: string[];
  partCount: number;
  measureCount: number;
  staffCount: number;
};

export type ScoreExportAction = 'preview' | 'svg' | 'musicxml' | 'png' | 'jpg' | 'pdf';
export type ScoreExportPolicyContext = { action: ScoreExportAction; sourceId: string; accessPolicy?: string };
export type ScoreExportDecision = { allowed: boolean; reason?: string };
export interface ScoreExportPolicy {
  mode: 'test-open' | 'enforced';
  decide(context: ScoreExportPolicyContext): ScoreExportDecision;
}

/** Test-only open policy. Production can replace this adapter without changing transformation code. */
export const testOpenScoreExportPolicy: ScoreExportPolicy = { mode: 'test-open', decide: () => ({ allowed: true }) };

export const stableJson = (value: unknown): string => {
  if (Array.isArray(value)) return `[${value.map(stableJson).join(',')}]`;
  if (value && typeof value === 'object') return `{${Object.entries(value as Record<string, unknown>).sort(([a], [b]) => a.localeCompare(b)).map(([key, item]) => `${JSON.stringify(key)}:${stableJson(item)}`).join(',')}}`;
  return JSON.stringify(value);
};

export const sha256Text = async (value: string): Promise<string> => {
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(value));
  return [...new Uint8Array(digest)].map(byte => byte.toString(16).padStart(2, '0')).join('');
};
export const recipeHash = (recipe: ViewRecipe | ExcerptRecipe) => sha256Text(stableJson(recipe));

export const gcd = (left: number, right: number): number => {
  let a = Math.abs(Math.trunc(left)), b = Math.abs(Math.trunc(right));
  while (b) [a, b] = [b, a % b];
  return a || 1;
};
export const rational = (numerator: number, denominator: number): Rational => {
  if (!Number.isFinite(numerator) || !Number.isFinite(denominator) || denominator === 0) return { numerator: 0, denominator: 1 };
  const divisor = gcd(numerator, denominator), sign = denominator < 0 ? -1 : 1;
  return { numerator: sign * Math.trunc(numerator / divisor), denominator: Math.abs(Math.trunc(denominator / divisor)) };
};
