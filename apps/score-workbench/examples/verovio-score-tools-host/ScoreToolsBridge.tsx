import { useMemo, useState, type ComponentType } from 'react';
import type { ScoreExportPolicy } from '@musicanote/verovio-score-tools';
import { ScoreToolsPanel } from '@musicanote/verovio-score-tools/react';
import type { DerivedScoreSvgRenderer } from '@musicanote/verovio-score-tools/verovio';
import '@musicanote/verovio-score-tools/style.css';

export type ExistingVerovioViewerProps = {
  xml: string;
  transpose: string;
  viewPartIds: string[];
  onOpenScoreTools: () => void;
};

export type ScoreToolsBridgeProps = {
  Viewer: ComponentType<ExistingVerovioViewerProps>;
  xml: string;
  sourceId: string;
  revisionKey: string;
  title: string;
  accessPolicy?: string;
  initialStart: number;
  initialEnd: number;
  /** Stable measure id from the host's score snapshot. */
  initialStartMeasureId: string;
  /** Stable measure id from the host's score snapshot. */
  initialEndMeasureId: string;
  exportPolicy?: ScoreExportPolicy;
  /** Optional adapter that reuses the host viewer's own Verovio loader. */
  renderScoreToSvg?: DerivedScoreSvgRenderer;
};

/**
 * Example production boundary. Preview remains available while file downloads
 * can be controlled by the host's authorization layer.
 */
export const createHostExportPolicy = (allowDownloads: boolean): ScoreExportPolicy => ({
  mode: 'enforced',
  decide: ({ action }) => action === 'preview' || allowDownloads
    ? { allowed: true }
    : { allowed: false, reason: '이 계정에는 악보 파일 내보내기 권한이 없습니다.' },
});

/**
 * Minimal host integration. The host owns viewer state; ScoreToolsPanel only
 * receives controlled values and reports changes through callbacks.
 */
export function ScoreToolsBridge({
  Viewer,
  xml,
  sourceId,
  revisionKey,
  title,
  accessPolicy,
  initialStart,
  initialEnd,
  initialStartMeasureId,
  initialEndMeasureId,
  exportPolicy,
  renderScoreToSvg,
}: ScoreToolsBridgeProps) {
  const [open, setOpen] = useState(false);
  const [transpose, setTranspose] = useState('');
  const [viewPartIds, setViewPartIds] = useState<string[]>([]);
  const resolvedExportPolicy = useMemo(
    () => exportPolicy ?? createHostExportPolicy(true),
    [exportPolicy],
  );

  return <>
    <Viewer
      xml={xml}
      transpose={transpose}
      viewPartIds={viewPartIds}
      onOpenScoreTools={() => setOpen(true)}
    />
    <ScoreToolsPanel
      open={open}
      onClose={() => setOpen(false)}
      xml={xml}
      sourceId={sourceId}
      revisionKey={revisionKey}
      title={title}
      accessPolicy={accessPolicy}
      initialStart={initialStart}
      initialEnd={initialEnd}
      initialStartMeasureId={initialStartMeasureId}
      initialEndMeasureId={initialEndMeasureId}
      transpose={transpose}
      onTransposeChange={setTranspose}
      viewPartIds={viewPartIds}
      onViewPartIdsChange={setViewPartIds}
      exportPolicy={resolvedExportPolicy}
      renderScoreToSvg={renderScoreToSvg}
    />
  </>;
}
