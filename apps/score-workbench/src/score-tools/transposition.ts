import type { TransposeRecipe } from './model';

export type TransposeOption = { interval: string; semitones: number; label: string };

const TRANSPOSE_SEMITONE_ORDER = [7, 6, 5, 4, 3, 2, 1, 0, -1, -2, -3, -4, -5, -6, -7] as const;

export const TRANSPOSE_OPTIONS: TransposeOption[] = TRANSPOSE_SEMITONE_ORDER.map(semitones => {
  return {
    // Verovio accepts an integer string as a chromatic semitone offset.
    // Keep the existing `interval` key for sidecar-schema compatibility.
    interval: semitones === 0 ? '' : String(semitones),
    semitones,
    label: semitones === 0 ? '0 · Original · 원조' : `${semitones > 0 ? '+' : '−'}${Math.abs(semitones)} 반음 · ${semitones > 0 ? '위' : '아래'}`,
  };
});

export const transposeRecipe = (interval: string): TransposeRecipe => {
  const option = TRANSPOSE_OPTIONS.find(candidate => candidate.interval === interval) || TRANSPOSE_OPTIONS.find(candidate => candidate.interval === '')!;
  return { enabled: option.semitones !== 0, interval: option.interval, semitones: option.semitones };
};

export const transposeLabel = (interval: string) => TRANSPOSE_OPTIONS.find(option => option.interval === interval)?.label || '0 · Original · 원조';
