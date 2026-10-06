import { useEffect, useMemo, useState } from 'react';
import { Check, Download, FileCode2, Scissors, X } from 'lucide-react';
import { defaultExcerptRecipe, defaultViewRecipe, deriveExcerptScore, deriveSelectedPartsScore, createScoreSnapshot, sourceMapSidecar, suggestedDownloadName } from '../score-tools/musicXmlTransform';
import { testOpenScoreExportPolicy, UNASSIGNED_VOICE_ID, type DerivedScore, type ExcerptRecipe, type PartSelection, type ScoreExportAction, type ScoreExportPolicy, type ScoreSnapshot } from '../score-tools/model';
import { downloadTextFile, renderDerivedScoreToSvg, type SvgExportResult } from '../score-tools/verovioExport';
import { TRANSPOSE_OPTIONS, transposeLabel, transposeRecipe } from '../score-tools/transposition';
import { breakMeasureIdsForLayout, EXCERPT_LAYOUT_OPTIONS, normalizeImageWidth, normalizeSystemCount, parseBreakMeasureInput, type ExcerptLayout } from '../score-tools/excerptLayout';
import { downloadBlobFile, pdfFromSvgPages, rasterizeSvg } from '../score-tools/imageExport';

type Preview = { derived: DerivedScore; recipe: ExcerptRecipe; render: SvgExportResult; key: string };
type ExportFormat = 'svg'|'png'|'jpg'|'pdf';
type ActiveTab = 'transpose'|'parts'|'image';

const wholePartSelections = (snapshot: ScoreSnapshot): PartSelection[] => snapshot.parts.map(part => ({ partId: part.id, scope: 'whole_part' }));
const normalizeSelections = (snapshot: ScoreSnapshot, selections: PartSelection[]): PartSelection[] => {
  const byPart = new Map(snapshot.parts.map(part => [part.id, part] as const)), seen = new Set<string>();
  return selections.flatMap<PartSelection>(selection => {
    const part = byPart.get(selection.partId);
    if (!part || seen.has(selection.partId)) return [];
    seen.add(selection.partId);
    if (selection.scope === 'staves') return [{ ...selection, staffIds: selection.staffIds.filter(id => part.staves.includes(id)) }];
    if (selection.scope === 'voices') return [{ ...selection, voiceIds: selection.voiceIds.filter(id => part.voices.includes(id)) }];
    return [selection];
  });
};
const selectionProblem = (snapshot: ScoreSnapshot, selections: PartSelection[]): string => {
  if (!selections.length) return '';
  const byPart = new Map(snapshot.parts.map(part => [part.id, part] as const)), seen = new Set<string>();
  for (const selection of selections) {
    const part = byPart.get(selection.partId);
    if (!part) return `원본에 없는 Part 선택입니다: ${selection.partId}`;
    if (seen.has(selection.partId)) return `같은 Part의 선택 범위가 중복되었습니다: ${selection.partId}`;
    seen.add(selection.partId);
    if (selection.scope === 'whole_part') continue;
    const values = selection.scope === 'staves' ? selection.staffIds : selection.voiceIds;
    const label = selection.scope === 'staves' ? 'Staff' : 'Voice';
    if (!values.length) return `${part.name}에서 ${label}를 하나 이상 선택해 주세요.`;
    if (new Set(values).size !== values.length) return `${part.name}의 ${label} 선택에 중복 ID가 있습니다.`;
    const available = new Set(selection.scope === 'staves' ? part.staves : part.voices);
    const unknown = values.filter(value => !available.has(value));
    if (unknown.length) return `${part.name}에 없는 ${label} 선택입니다: ${unknown.join(', ')}`;
  }
  return '';
};
const selectionKeyOf = (selections: PartSelection[]) => JSON.stringify(selections.map(selection => selection.scope === 'staves'
  ? { ...selection, staffIds: [...selection.staffIds].sort() }
  : selection.scope === 'voices'
    ? { ...selection, voiceIds: [...selection.voiceIds].sort() }
    : selection).sort((left, right) => left.partId.localeCompare(right.partId)));
const voiceLabel = (voiceId: string) => voiceId === UNASSIGNED_VOICE_ID ? 'Unassigned · Voice not encoded' : `Voice ${voiceId}`;

const initialOrdinal = (snapshot: ScoreSnapshot, display: number, fallback: number) => {
  const match = snapshot.measures.find(measure => Number(measure.displayNumber) === display);
  return match?.ordinal || Math.max(1, Math.min(snapshot.measures.length, fallback));
};

const initialMeasureOrdinal = (snapshot: ScoreSnapshot, measureId: string | undefined, display: number, fallback: number) => {
  const stableMatch = measureId ? snapshot.measures.find(measure => measure.id === measureId) : undefined;
  return stableMatch?.ordinal || initialOrdinal(snapshot, display, fallback);
};

export type ScoreToolsPanelProps = {
  open: boolean;
  onClose: () => void;
  xml: string;
  sourceId: string;
  title: string;
  accessPolicy?: string;
  /** Host revision key. Changing it rebuilds the immutable score snapshot. */
  revisionKey?: string;
  /** @deprecated Use revisionKey. Kept for the MusicSearch host bridge. */
  streamId?: string;
  initialStart: number;
  initialEnd: number;
  initialStartMeasureId?: string;
  initialEndMeasureId?: string;
  transpose: string;
  onTransposeChange: (interval: string) => void;
  viewPartIds: string[];
  onViewPartIdsChange: (partIds: string[]) => void;
  /** Detailed score-content selection. When supplied, pair it with onViewSelectionsChange. */
  viewSelections?: PartSelection[];
  onViewSelectionsChange?: (selections: PartSelection[]) => void;
  exportPolicy?: ScoreExportPolicy;
  renderScoreToSvg?: typeof renderDerivedScoreToSvg;
};

export function ScoreToolsPanel({ open, onClose, xml, sourceId, title, accessPolicy, revisionKey, streamId, initialStart, initialEnd, initialStartMeasureId, initialEndMeasureId, transpose, onTransposeChange, viewPartIds, onViewPartIdsChange, viewSelections, onViewSelectionsChange, exportPolicy = testOpenScoreExportPolicy, renderScoreToSvg = renderDerivedScoreToSvg }: ScoreToolsPanelProps) {
  const [snapshot, setSnapshot] = useState<ScoreSnapshot | null>(null), [selectedSelections, setSelectedSelections] = useState<PartSelection[]>([]);
  const [startOrdinal, setStartOrdinal] = useState(1), [endOrdinal, setEndOrdinal] = useState(1);
  const [removeLyrics, setRemoveLyrics] = useState(false), [removeDynamics, setRemoveDynamics] = useState(false);
  const [activeTab,setActiveTab]=useState<ActiveTab>('transpose');
  const [layout,setLayout]=useState<ExcerptLayout>('single_system'),[imageWidthPx,setImageWidthPx]=useState(1200),[targetSystemCount,setTargetSystemCount]=useState(2),[customBreakInput,setCustomBreakInput]=useState('');
  const [applyCurrentTranspose,setApplyCurrentTranspose]=useState(true);
  const [exportFormat,setExportFormat]=useState<ExportFormat>('svg');
  const [preview, setPreview] = useState<Preview | null>(null), [busy, setBusy] = useState(false), [error, setError] = useState('');
  const [selectionInputError,setSelectionInputError]=useState(''),[exportNotice,setExportNotice]=useState('');

  useEffect(() => {
    if (!open) return;
    let active = true;
    setSnapshot(null); setPreview(null); setError(''); setSelectionInputError(''); setExportNotice('');
    createScoreSnapshot(xml, sourceId).then(value => {
      if (!active) return;
      setSnapshot(value);
      const available = value.parts.map(part => part.id), retained = viewPartIds.filter(partId => available.includes(partId));
      const detailed = viewSelections !== undefined ? normalizeSelections(value, viewSelections) : undefined;
      const incomingProblem = viewSelections !== undefined ? selectionProblem(value, viewSelections) : '';
      setSelectionInputError(incomingProblem);
      setSelectedSelections(detailed ? (viewSelections?.length === 0 ? wholePartSelections(value) : detailed) : (retained.length ? retained.map(partId => ({ partId, scope: 'whole_part' as const })) : wholePartSelections(value)));
      const start = initialMeasureOrdinal(value, initialStartMeasureId, initialStart, 1), end = initialMeasureOrdinal(value, initialEndMeasureId, initialEnd, Math.min(value.measures.length, start + 3));
      setStartOrdinal(Math.min(start, end)); setEndOrdinal(Math.max(start, end));
    }).catch(reason => active && setError(reason instanceof Error ? reason.message : String(reason)));
    return () => { active = false; };
  }, [open, xml, sourceId, revisionKey, streamId, initialStart, initialEnd, initialStartMeasureId, initialEndMeasureId]);

  useEffect(() => {
    if (!open || !snapshot || viewSelections === undefined) return;
    const normalized = normalizeSelections(snapshot, viewSelections);
    const incomingProblem = selectionProblem(snapshot, viewSelections);
    const displayed = viewSelections.length === 0 ? wholePartSelections(snapshot) : normalized;
    setSelectionInputError(incomingProblem);
    setSelectedSelections(current => selectionKeyOf(current) === selectionKeyOf(displayed) ? current : displayed);
  }, [open, snapshot, viewSelections]);

  const breakInputResult = useMemo(() => snapshot ? parseBreakMeasureInput(snapshot.measures,startOrdinal,endOrdinal,customBreakInput) : { ordinals: [], unmatched: [], ambiguous: [] }, [snapshot,startOrdinal,endOrdinal,customBreakInput]);
  const appliedTranspose = applyCurrentTranspose ? transpose : '';
  const selectionKey = useMemo(() => JSON.stringify([
    selectionKeyOf(selectedSelections), startOrdinal, endOrdinal, removeLyrics, removeDynamics, appliedTranspose, layout,
    layout === 'single_system' ? null : normalizeImageWidth(imageWidthPx),
    layout === 'system_count' ? normalizeSystemCount(targetSystemCount) : null,
    layout === 'custom_breaks' ? breakInputResult.ordinals : null,
    snapshot?.sourceVersionId,
  ]), [selectedSelections,startOrdinal,endOrdinal,removeLyrics,removeDynamics,appliedTranspose,layout,imageWidthPx,targetSystemCount,breakInputResult.ordinals,snapshot]);
  const stalePreview = Boolean(preview && preview.key !== selectionKey);
  if (!open) return null;

  const commitSelections = (next: PartSelection[]) => {
    const normalized = snapshot ? normalizeSelections(snapshot, next) : next;
    const displayed = snapshot && normalized.length === 0 ? wholePartSelections(snapshot) : normalized;
    const localProblem = snapshot ? selectionProblem(snapshot, displayed) : '';
    setSelectionInputError(localProblem);
    const allWhole = Boolean(snapshot && displayed.length === snapshot.parts.length && displayed.every(selection => selection.scope === 'whole_part'));
    const outbound = allWhole ? [] : displayed;
    setSelectedSelections(displayed);
    setExportNotice('');
    if (localProblem) return;
    onViewSelectionsChange?.(outbound);
    onViewPartIdsChange(allWhole ? [] : displayed.map(selection => selection.partId));
  };
  const selectionForPart = (partId: string) => selectedSelections.find(selection => selection.partId === partId);
  const togglePart = (partId: string) => commitSelections(selectionForPart(partId) ? selectedSelections.filter(selection => selection.partId !== partId) : [...selectedSelections, { partId, scope: 'whole_part' }]);
  const setPartScope = (partId: string, scope: PartSelection['scope']) => {
    if (!snapshot) return;
    const part = snapshot.parts.find(candidate => candidate.id === partId);
    if (!part) return;
    const replacement: PartSelection = scope === 'staves' ? { partId, scope, staffIds: [...part.staves] } : scope === 'voices' ? { partId, scope, voiceIds: [...part.voices] } : { partId, scope };
    commitSelections([...selectedSelections.filter(selection => selection.partId !== partId), replacement]);
  };
  const toggleStaff = (partId: string, staffId: string) => {
    const selection = selectionForPart(partId);
    if (!selection || selection.scope !== 'staves') return;
    commitSelections(selectedSelections.map(item => item.partId !== partId ? item : { ...selection, staffIds: selection.staffIds.includes(staffId) ? selection.staffIds.filter(id => id !== staffId) : [...selection.staffIds, staffId] }));
  };
  const toggleVoice = (partId: string, voiceId: string) => {
    const selection = selectionForPart(partId);
    if (!selection || selection.scope !== 'voices') return;
    commitSelections(selectedSelections.map(item => item.partId !== partId ? item : { ...selection, voiceIds: selection.voiceIds.includes(voiceId) ? selection.voiceIds.filter(id => id !== voiceId) : [...selection.voiceIds, voiceId] }));
  };
  const effectiveSelections = () => {
    if (selectionInputError) throw new Error(selectionInputError);
    return selectedSelections.length ? selectedSelections : (snapshot ? wholePartSelections(snapshot) : []);
  };
  const invalidChildSelection = selectedSelections.some(selection => selection.scope === 'staves' ? selection.staffIds.length === 0 : selection.scope === 'voices' && selection.voiceIds.length === 0);
  const allWholeSelected = Boolean(snapshot && selectedSelections.length === snapshot.parts.length && selectedSelections.every(selection => selection.scope === 'whole_part'));
  const fullScoreSelection = !selectionInputError && (selectedSelections.length === 0 || allWholeSelected);
  const selectionSummary = !snapshot || fullScoreSelection ? 'Full score · all Parts, Staffs, and Voices' : selectedSelections.map(selection => {
    const part = snapshot.parts.find(candidate => candidate.id === selection.partId), name = part?.name || selection.partId;
    if (selection.scope === 'staves') return `${name}: Staff ${selection.staffIds.join(', ') || 'none'}`;
    if (selection.scope === 'voices') return `${name}: ${selection.voiceIds.map(voiceLabel).join(', ') || 'none'}`;
    return `${name}: whole Part`;
  }).join(' · ');
  const permission = (action: ScoreExportAction) => exportPolicy.decide({ action, sourceId, accessPolicy });
  const makeRecipe = (): ExcerptRecipe => {
    if (!snapshot) throw new Error('악보 snapshot을 준비하는 중입니다.');
    if(layout==='custom_breaks'&&(breakInputResult.unmatched.length||breakInputResult.ambiguous.length)) throw new Error('줄 바꿈 마디 입력을 확인해 주세요.');
    const base = defaultExcerptRecipe(snapshot, startOrdinal, endOrdinal), systemBreakBeforeMeasureIds = breakMeasureIdsForLayout(snapshot.measures,startOrdinal,endOrdinal,layout,targetSystemCount,breakInputResult.ordinals);
    return { ...base, source: applyCurrentTranspose ? 'current_view' : 'original', view: { transpose: transposeRecipe(appliedTranspose) }, selections: effectiveSelections(), presentation: { ...base.presentation, layout, imageWidthPx:normalizeImageWidth(imageWidthPx), targetSystemCount:normalizeSystemCount(targetSystemCount), systemBreakBeforeMeasureIds, removeLyrics, removeDynamics } };
  };
  const runPreview = async () => {
    const decision = permission('preview'); if (!decision.allowed) { setError(decision.reason || '미리보기 권한이 없습니다.'); return; }
    setBusy(true); setError(''); setExportNotice('');
    try { const recipe = makeRecipe(), derived = await deriveExcerptScore(xml, snapshot!, recipe), render = await renderScoreToSvg(derived, recipe.view.transpose.interval,recipe.presentation); setPreview({ derived, recipe, render, key: selectionKey }); }
    catch (reason) { setError(reason instanceof Error ? reason.message : String(reason)); }
    finally { setBusy(false); }
  };
  const exportPreview = async () => {
    if (!preview || stalePreview) { setError('현재 선택으로 미리보기를 다시 만들어 주세요.'); return; }
    const decision = permission(exportFormat); if (!decision.allowed) { setError(decision.reason || `${exportFormat.toUpperCase()} 내보내기 권한이 없습니다.`); return; }
    setBusy(true);setError('');setExportNotice('');
    try {
      if(exportFormat==='svg'){preview.render.pages.forEach((svg,index)=>window.setTimeout(()=>downloadTextFile(svg,suggestedDownloadName(title,`excerpt${preview.render.pages.length>1?`-${index+1}`:''}`,'svg'),'image/svg+xml;charset=utf-8'),index*150));return}
      if(exportFormat==='pdf'){downloadBlobFile(await pdfFromSvgPages(preview.render.pages),suggestedDownloadName(title,'excerpt','pdf'));return}
      for(const [index,svg] of preview.render.pages.entries()){
        const raster=await rasterizeSvg(svg,exportFormat),suffix=`excerpt${preview.render.pages.length>1?`-${index+1}`:''}`;
        downloadBlobFile(raster.blob,suggestedDownloadName(title,suffix,exportFormat));
        if(index+1<preview.render.pages.length)await new Promise(resolve=>window.setTimeout(resolve,150));
      }
    }catch(reason){setError(reason instanceof Error?reason.message:String(reason))}finally{setBusy(false)}
  };
  const exportPartsXml = async () => {
    if (!snapshot) return;
    const decision = permission('musicxml'); if (!decision.allowed) { setError(decision.reason || 'MusicXML 내보내기 권한이 없습니다.'); return; }
    setBusy(true); setError(''); setExportNotice('');
    try {
      const base = defaultViewRecipe(snapshot), recipe = { ...base, selections: effectiveSelections() }, derived = await deriveSelectedPartsScore(xml, snapshot, recipe);
      downloadTextFile(derived.xml, suggestedDownloadName(title, 'selected parts', 'musicxml'), 'application/vnd.recordare.musicxml+xml;charset=utf-8');
      downloadTextFile(sourceMapSidecar(snapshot, derived, recipe), suggestedDownloadName(title, 'selected parts sidecar', 'json'), 'application/json;charset=utf-8');
      setExportNotice(derived.warnings.length ? 'MusicXML 저장 완료 · ' + derived.warnings.join(' ') : 'MusicXML과 sidecar 저장을 시작했습니다.');
    } catch (reason) { setError(reason instanceof Error ? reason.message : String(reason)); }
    finally { setBusy(false); }
  };
  const exportSidecar = () => {
    if (!snapshot || !preview || stalePreview) return;
    downloadTextFile(sourceMapSidecar(snapshot, preview.derived, preview.recipe), suggestedDownloadName(title, 'excerpt sidecar', 'json'), 'application/json;charset=utf-8');
  };
  const partValid = Boolean(snapshot?.parts.length && !invalidChildSelection && !selectionInputError);
  const imageValid = Boolean(partValid && startOrdinal <= endOrdinal && (layout!=='custom_breaks'||(!breakInputResult.unmatched.length&&!breakInputResult.ambiguous.length)));
  const layoutOption=EXCERPT_LAYOUT_OPTIONS.find(option=>option.value===layout)!;

  return <div className="score-tools-backdrop" role="presentation" onMouseDown={event => { if (event.target === event.currentTarget) onClose(); }}>
    <section className="score-tools-panel" role="dialog" aria-modal="true" aria-labelledby="score-tools-title">
      <header><div><small>DERIVED SCORE TOOLS · TEST</small><h2 id="score-tools-title">Score Tools</h2><p>원본을 바꾸지 않고 조옮김 뷰와 파생 악보를 만듭니다.</p></div><button type="button" onClick={onClose} aria-label="악보 도구 닫기"><X/></button></header>
      <div className="score-tools-policy"><Check/> {exportPolicy.mode==='test-open'?'테스트 개발 중에는 모든 자료의 미리보기와 내보내기를 허용합니다.':'미리보기와 내보내기는 호스트의 권한 정책을 따릅니다.'} <b>{exportPolicy.mode==='test-open'?'TEST OPEN':'HOST POLICY'}</b></div>
      <nav className="score-tools-tabs" role="tablist" aria-label="Score Tools 기능">
        {([
          ['transpose','1. Transpose'],
          ['parts','2. Part / Staff / Voice'],
          ['image','3. Measure Image Export'],
        ] as const).map(([value,label])=><button key={value} id={`score-tools-tab-${value}`} type="button" role="tab" aria-selected={activeTab===value} aria-controls={`score-tools-panel-${value}`} tabIndex={activeTab===value?0:-1} className={activeTab===value?'active':''} onClick={()=>{setActiveTab(value);setError('')}}>{label}</button>)}
      </nav>

      {activeTab==='transpose'&&<section id="score-tools-panel-transpose" className="score-tools-tab-panel" role="tabpanel" aria-labelledby="score-tools-tab-transpose">
        <div className="score-tools-transpose"><div><small>TRANSPOSE PREVIEW</small><b>{transposeLabel(transpose)}</b><span>원조 기준 −7~+7 반음입니다. 조표와 모든 음표를 함께 이동하며 누적되지 않습니다.</span></div><label>Semitones<select value={transpose} onChange={event=>onTransposeChange(event.target.value)}>{TRANSPOSE_OPTIONS.map(option=><option key={option.interval||'original'} value={option.interval}>{option.label}</option>)}</select></label><button type="button" onClick={()=>onTransposeChange('')} disabled={!transpose}>Reset View</button><p>Choose how many semitones to raise or lower every note.</p></div>
      </section>}

      {!snapshot&&!error&&activeTab!=='transpose'&&<p className="score-tools-loading">원본 hash와 악보 구조를 확인하는 중…</p>}

      {activeTab==='parts'&&snapshot&&<section id="score-tools-panel-parts" className="score-tools-tab-panel" role="tabpanel" aria-labelledby="score-tools-tab-parts">
        <div className="score-tools-card">
          <div className="score-tools-section-title"><div><b>Part / Staff / Voice Selection</b><span>Part별로 전체 Part, Staff 또는 Voice 중 한 가지 방식을 선택합니다.</span><em className="score-tools-view-state">{fullScoreSelection?'Content filter off · Full score':`${selectedSelections.length} Part 범위 선택`}</em></div><button type="button" disabled={allWholeSelected} onClick={() => commitSelections(wholePartSelections(snapshot))}>{allWholeSelected ? '전체 악보 표시 중' : '전체 악보로 돌아가기'}</button></div>
          <p className="score-tools-instruction">Staff and Voice are parallel selection modes. Voice is never nested under a Staff. The same selection is used for the score view, image excerpt, and MusicXML export.</p>
          <div className="score-tools-parts">{snapshot.parts.map(part => {
            const selection = selectionForPart(part.id), included = Boolean(selection);
            return <div className={`score-tools-part-row${included?' selected':''}`} key={part.id}>
              <div className="score-tools-part-heading">
                <label><input type="checkbox" checked={included} onChange={() => togglePart(part.id)}/><span><b>{part.name}</b><small>{part.id} · {part.staves.length} Staff · {part.voices.length} Voice</small></span></label>
                <label className="score-tools-scope"><span>Content</span><select aria-label={`${part.name} selection mode`} disabled={!included} value={selection?.scope || 'whole_part'} onChange={event => setPartScope(part.id, event.target.value as PartSelection['scope'])}><option value="whole_part">Whole Part</option><option value="staves">Staff</option><option value="voices">Voice</option></select></label>
              </div>
              {selection?.scope==='staves'&&<fieldset className="score-tools-child-options"><legend>Staff</legend>{part.staves.map(staffId=><label key={`${part.id}:staff:${staffId}`}><input type="checkbox" checked={selection.staffIds.includes(staffId)} onChange={()=>toggleStaff(part.id,staffId)}/><span>Staff {staffId}</span></label>)}</fieldset>}
              {selection?.scope==='voices'&&<><fieldset className="score-tools-child-options"><legend>Voice</legend>{part.voices.map(voiceId=><label key={`${part.id}:voice:${voiceId}`}><input type="checkbox" checked={selection.voiceIds.includes(voiceId)} onChange={()=>toggleVoice(part.id,voiceId)}/><span>{voiceLabel(voiceId)}</span></label>)}</fieldset><p className="score-tools-selection-note">Voice는 Staff 아래에 종속되지 않습니다. Cross-staff Voice를 온전히 보존하기 위해 필요한 Staff가 함께 남을 수 있습니다.</p></>}
              {selection?.scope==='staves'&&selection.staffIds.length===0&&<p className="score-tools-selection-warning" role="alert">Staff를 하나 이상 선택하세요. 현재 선택으로는 미리보기와 내보내기를 실행할 수 없습니다.</p>}
              {selection?.scope==='voices'&&selection.voiceIds.length===0&&<p className="score-tools-selection-warning" role="alert">Voice를 하나 이상 선택하세요. 현재 선택으로는 미리보기와 내보내기를 실행할 수 없습니다.</p>}
            </div>;
          })}</div>
          {selectionInputError&&<p className="score-tools-selection-warning" role="alert">{selectionInputError} 유효한 선택을 복구하기 전까지 상세 악보와 내보내기에는 마지막 정상 선택이 유지됩니다.</p>}
        </div>
      </section>}

      {activeTab==='image'&&snapshot&&<section id="score-tools-panel-image" className="score-tools-tab-panel" role="tabpanel" aria-labelledby="score-tools-tab-image">
        <div className="score-tools-selection-summary"><div><b>Included Score Content</b><span>{selectionSummary}</span>{invalidChildSelection&&<em>Part / Staff / Voice 탭에서 빈 선택을 확인해 주세요.</em>}</div><button type="button" onClick={()=>setActiveTab('parts')}>Edit Selection</button></div>
        <div className="score-tools-card"><div className="score-tools-section-title"><div><b>Measure Range</b><span>이미지로 추출할 시작·끝 마디를 선택하세요.</span></div></div><div className="score-tools-range"><label>From<select value={startOrdinal} onChange={event => { const value = Number(event.target.value); setStartOrdinal(value); if (value > endOrdinal) setEndOrdinal(value); }}>{snapshot.measures.map(measure => <option value={measure.ordinal} key={measure.id}>m.{measure.displayNumber}{measure.implicit ? ' · pickup' : ''}</option>)}</select></label><span>→</span><label>To<select value={endOrdinal} onChange={event => { const value = Number(event.target.value); setEndOrdinal(value); if (value < startOrdinal) setStartOrdinal(value); }}>{snapshot.measures.map(measure => <option value={measure.ordinal} key={measure.id}>m.{measure.displayNumber}{measure.implicit ? ' · pickup' : ''}</option>)}</select></label></div></div>
        <div className="score-tools-card"><div className="score-tools-section-title"><div><b>이미지 추출 옵션</b><span>이미지 폭과 줄 배치를 지정합니다.</span></div></div><div className="score-tools-options"><label className="score-tools-transpose-export"><input type="checkbox" checked={Boolean(transpose)&&applyCurrentTranspose} disabled={!transpose} onChange={event=>setApplyCurrentTranspose(event.target.checked)}/> 현재 조옮김 적용{transpose?` · ${transposeLabel(transpose)}`:' · 현재 원조'}</label><span>켜면 Transpose 탭의 현재 반음 이동을 적용하고, 끄면 원조로 추출합니다. Part / Staff / Voice 선택은 항상 반영됩니다.</span><div className="score-tools-layout"><label>Layout<select value={layout} onChange={event=>setLayout(event.target.value as ExcerptLayout)}>{EXCERPT_LAYOUT_OPTIONS.map(option=><option key={option.value} value={option.value}>{option.label}</option>)}</select></label>{layout!=='single_system'&&<label>Image width (px)<input type="number" min="600" max="3200" step="50" value={imageWidthPx} onChange={event=>setImageWidthPx(Number(event.target.value))} onBlur={()=>setImageWidthPx(normalizeImageWidth(imageWidthPx))}/></label>}{layout==='system_count'&&<label className="score-tools-system-count">행 수<span><input type="number" min="2" max="12" step="1" value={targetSystemCount} onChange={event=>setTargetSystemCount(Number(event.target.value))} onBlur={()=>setTargetSystemCount(normalizeSystemCount(targetSystemCount))}/> 행</span></label>}<p>{layoutOption.description}{layout==='single_system'?' 가로 폭은 내용 길이에 따라 자동 확장됩니다.':` 출력 폭 ${normalizeImageWidth(imageWidthPx)}px.`}</p></div>{layout==='custom_breaks'&&<label className="score-tools-break-input"><span>줄 바꿈 마디 직접 입력</span><input type="text" value={customBreakInput} onChange={event=>setCustomBreakInput(event.target.value)} placeholder="예: 5, 9, 13"/><small>새 줄에서 시작할 표시 마디 번호를 쉼표 또는 공백으로 입력하세요. 선택 범위의 첫 마디는 이미 첫 줄에서 시작하므로 입력하지 않아도 됩니다.</small>{breakInputResult.unmatched.length>0&&<em>선택 구간에서 찾을 수 없음: {breakInputResult.unmatched.join(', ')}</em>}{breakInputResult.ambiguous.length>0&&<em>같은 표시 번호가 여러 번 있어 모호함: {breakInputResult.ambiguous.join(', ')}</em>}{customBreakInput.trim()&&!breakInputResult.unmatched.length&&!breakInputResult.ambiguous.length&&<strong>{breakInputResult.ordinals.length}개 줄 바꿈 위치</strong>}</label>}<label><input type="checkbox" checked={removeLyrics} onChange={event => setRemoveLyrics(event.target.checked)}/> Remove Lyrics</label><label><input type="checkbox" checked={removeDynamics} onChange={event => setRemoveDynamics(event.target.checked)}/> Remove Dynamics</label><span>Measure Numbers On · SVG</span></div></div>
      </section>}

       {selectionInputError&&activeTab==='image'&&<p className="score-tools-selection-warning" role="alert">{selectionInputError}</p>}
       {exportNotice&&<p className="score-tools-selection-warning" role="status">{exportNotice}</p>}
       {error&&<p className="score-tools-error" role="alert">{error}</p>}
       {activeTab==='image'&&preview&&<section className={`score-tools-preview ${stalePreview ? 'stale' : ''}`}><div><b>{preview.derived.partCount} Part · {preview.derived.staffCount} Staff · {preview.derived.measureCount} Measure · {preview.render.systemCount} System</b><span>{preview.recipe.presentation.layout==='single_system'?'내용 너비':`${preview.render.imageWidthPx}px`} · source {preview.derived.sourceHash.slice(0, 10)} · recipe {preview.derived.recipeHash.slice(0, 10)}</span>{stalePreview&&<em>선택이 바뀌었습니다. Preview를 다시 실행하세요.</em>}</div><div className="score-tools-preview-scroll">{preview.render.pages.map((svg,index)=><div key={index} dangerouslySetInnerHTML={{__html:svg}}/>)}</div>{[...new Set([...preview.derived.warnings,...preview.render.warnings])].map(warning=><p key={warning}>{warning}</p>)}</section>}
      {activeTab==='parts'&&<footer><button type="button" className="secondary" onClick={exportPartsXml} disabled={!partValid||busy}><FileCode2/> 선택 악보 MusicXML · 원조</button></footer>}
      {activeTab==='image'&&<footer><button type="button" className="secondary" onClick={exportSidecar} disabled={!preview||stalePreview}><Download/> Sidecar JSON</button><button type="button" onClick={runPreview} disabled={!imageValid||busy}><Scissors/> {busy?'생성 중…':'Preview'}</button><label className="score-tools-export-format"><span>Format</span><select value={exportFormat} onChange={event=>setExportFormat(event.target.value as ExportFormat)}><option value="svg">SVG</option><option value="png">PNG</option><option value="jpg">JPG</option><option value="pdf">PDF</option></select></label><button type="button" onClick={exportPreview} disabled={!preview||stalePreview||busy}><Download/> Export {exportFormat.toUpperCase()}</button></footer>}
    </section>
  </div>;
}
