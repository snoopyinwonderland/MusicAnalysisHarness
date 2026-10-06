import type { DerivedScore, ExcerptRecipe, PartSelection, ScoreSnapshot, ViewRecipe } from './model';
import {
  createScoreSnapshot,
  defaultExcerptRecipe,
  defaultViewRecipe,
  deriveExcerptScore,
  deriveSelectedPartsScore,
  filterMusicXmlParts,
  filterMusicXmlSelections,
  sourceMapSidecar,
} from './musicXmlTransform';
import type { DerivedScoreSvgRenderer, SvgExportResult } from './verovioExport';

export type RenderedExcerpt = {
  derived: DerivedScore;
  render: SvgExportResult;
};

export type ScoreToolsEngineDependencies = {
  /** Replace this to connect a host viewer's own Verovio runtime. */
  renderDerivedScore?: DerivedScoreSvgRenderer;
};

export type ScoreToolsEngine = {
  createSnapshot(xml: string, sourceId: string): Promise<ScoreSnapshot>;
  createDefaultViewRecipe(snapshot: ScoreSnapshot): ViewRecipe;
  createDefaultExcerptRecipe(snapshot: ScoreSnapshot, startOrdinal?: number, endOrdinal?: number): ExcerptRecipe;
  deriveExcerpt(xml: string, snapshot: ScoreSnapshot, recipe: ExcerptRecipe): Promise<DerivedScore>;
  deriveSelectedParts(xml: string, snapshot: ScoreSnapshot, recipe: ViewRecipe): Promise<DerivedScore>;
  filterParts(xml: string, partIds: readonly string[], sourceId?: string): Promise<string>;
  filterSelections(xml: string, selections: readonly PartSelection[], sourceId?: string): Promise<string>;
  renderDerivedScore(score: DerivedScore, transpose?: string, presentation?: ExcerptRecipe['presentation']): Promise<SvgExportResult>;
  renderExcerpt(xml: string, snapshot: ScoreSnapshot, recipe: ExcerptRecipe): Promise<RenderedExcerpt>;
  createSidecar(snapshot: ScoreSnapshot, derived: DerivedScore, recipe: ViewRecipe | ExcerptRecipe): string;
};

/**
 * Creates a stateless, headless Score Tools facade.
 *
 * MusicXML operations require DOMParser, XMLSerializer, XMLDocument and Element.
 * Browsers provide these globals. Node/Deno/Bun hosts must install a compatible
 * DOM shim before calling XML-transforming methods. Rendering additionally
 * requires either the bundled adapter or an injected `renderDerivedScore`.
 */
export const createScoreToolsEngine = (dependencies: ScoreToolsEngineDependencies = {}): ScoreToolsEngine => {
  const renderer: DerivedScoreSvgRenderer = dependencies.renderDerivedScore ?? (async () => {
    throw new Error('Score Tools 렌더러가 설정되지 않았습니다. createScoreToolsEngine({ renderDerivedScore })로 Verovio 어댑터를 주입해 주세요.');
  });
  return {
    createSnapshot: createScoreSnapshot,
    createDefaultViewRecipe: defaultViewRecipe,
    createDefaultExcerptRecipe: defaultExcerptRecipe,
    deriveExcerpt: deriveExcerptScore,
    deriveSelectedParts: deriveSelectedPartsScore,
    filterParts: filterMusicXmlParts,
    filterSelections: filterMusicXmlSelections,
    renderDerivedScore: renderer,
    renderExcerpt: async (xml, snapshot, recipe) => {
      const derived = await deriveExcerptScore(xml, snapshot, recipe);
      const render = await renderer(derived, recipe.view.transpose.interval, recipe.presentation);
      return { derived, render };
    },
    createSidecar: sourceMapSidecar,
  };
};
