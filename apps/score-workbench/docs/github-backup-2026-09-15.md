# GitHub backup — 2026-09-15

Source, documentation, evaluation records, generated comparison reports and collected metadata are backed up to the existing private MusicSearch repository. Production SQLite databases, index backups, runtime caches and the new full XML copies used by local pair experiments are excluded. Existing versioned case-context excerpts are preserved.

TypeScript compilation and 26 tests covering segment comparison, contour seeds, search windows and preclearance selection passed before this backup. This is not a claim that the entire test suite or browser/audio checks passed.

The system-only pair comparison uses the existing search engine on an isolated two-source index. See system-only-pair-comparison.md for selection limits and reproducibility. External MusicXML libraries and original supplied files remain necessary to rerun source-dependent jobs; this Git backup is not a full data-library backup.
