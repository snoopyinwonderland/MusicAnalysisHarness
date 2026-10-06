/**
 * Optional Verovio rendering entry point. Import this module only when the host
 * needs SVG rendering; the core `score-tools` entry remains runtime-agnostic.
 */
export {
  createVerovioRenderer,
  renderDerivedScoreToSvg,
  renderDerivedScoreToSvgWithDependencies,
  sanitizeVerovioSvg,
  type DerivedScoreSvgRenderer,
  type SvgExportResult,
  type VerovioRenderDependencies,
  type VerovioToolkitFactory,
  type VerovioToolkitLike,
} from './verovioExport';
