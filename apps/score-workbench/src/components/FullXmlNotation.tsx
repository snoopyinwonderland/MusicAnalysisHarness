import { memo, useEffect, useLayoutEffect, useRef, useState } from 'react';
import type { VerovioToolkit } from 'verovio/esm';
import type { CorpusNote } from '../types';
import { normalizeMusicXmlVoices } from '../music/musicXmlVoiceNormalizer';
import {scorePageTopInset} from '../music/scorePageInsets';
import {proposalOverlayLayout,overlayLabelOffset} from '../music/scoreOverlayLayout';
import { newVerovioToolkit } from '../music/verovioRuntime';
import { applyPartViewSelection, applyScoreViewSelections } from '../score-tools/musicXmlTransform';
import { UNASSIGNED_VOICE_ID, type PartSelection } from '../score-tools/model';

declare module 'verovio/esm' { interface VerovioToolkit { getPageCount(): number; getPageWithElement(id: string): number } }

const EMPTY_NOTES: CorpusNote[] = [];
const EMPTY_PART_IDS: string[] = [];
const EMPTY_SCORE_SELECTIONS: PartSelection[] = [];
// Preserve the SVG DOM (including overlay anchors) on unrelated state updates.
const RenderedScorePage=memo(function RenderedScorePage({svg}:{svg:string}){
  return <section dangerouslySetInnerHTML={{__html:svg}}/>;
});
const midi = (n: Element) => {
  const s = n.getElementsByTagName('step')[0]?.textContent || 'C';
  const o = +(n.getElementsByTagName('octave')[0]?.textContent || 4);
  const a = +(n.getElementsByTagName('alter')[0]?.textContent || 0);
  const pc: any = { C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 };
  return (o + 1) * 12 + pc[s] + a;
};
const tieTypes = (n: Element) => [...n.getElementsByTagName('tie')].map(x => x.getAttribute('type'));
export type TieChainEvent<T> = {
  value: T;
  partId: string;
  staff: string;
  voice: string;
  measureOrdinal: number;
  beat: number;
  pitchMidi: number;
  isRest: boolean;
  tieTypes: readonly (string | null)[];
};
const sameOnset = <T,>(a: TieChainEvent<T>, b: TieChainEvent<T>) => a.measureOrdinal === b.measureOrdinal && Math.abs(a.beat - b.beat) < 1e-6;
const follows = <T,>(candidate: TieChainEvent<T>, current: TieChainEvent<T>) => candidate.measureOrdinal > current.measureOrdinal || candidate.measureOrdinal === current.measureOrdinal && candidate.beat > current.beat + 1e-6;

// Follow only the next onset in the matched part/staff/voice. DOM order is
// not musical order after MusicXML <backup>s, and a same-pitch note in a
// different voice is not a continuation of this tie.
export const tiedNoteChain = <T,>(seed: TieChainEvent<T>, events: readonly TieChainEvent<T>[]) => {
  const lane = events.filter(event => event.partId === seed.partId && event.staff === seed.staff && event.voice === seed.voice)
    .map((event, index) => ({ event, index }))
    .sort((a, b) => a.event.measureOrdinal - b.event.measureOrdinal || a.event.beat - b.event.beat || a.index - b.index);
  const chain = [seed.value];
  let current = seed;
  while (current.tieTypes.includes('start')) {
    const firstFollowing = lane.find(({ event }) => follows(event, current))?.event;
    if (!firstFollowing) break;
    const onset = lane.filter(({ event }) => sameOnset(event, firstFollowing)).map(({ event }) => event);
    if (onset.some(event => event.isRest)) break;
    const continuation = onset.find(event => !event.isRest && event.pitchMidi === current.pitchMidi && event.tieTypes.includes('stop'));
    if (!continuation) break;
    chain.push(continuation.value);
    current = continuation;
  }
  return chain;
};
const directChild = (element: Element, tagName: string) => [...element.children].find(child => child.localName === tagName);
export const resolvedSourceVoiceIds = (measure: Element) => {
  const voices = new Map<Element, string>();
  let chordHeadExplicitVoice: string | undefined;
  for (const child of [...measure.children]) {
    if (child.localName !== 'note') { chordHeadExplicitVoice = undefined; continue; }
    const explicitVoice = directChild(child, 'voice')?.textContent?.trim() || undefined;
    const chordContinuation = Boolean(directChild(child, 'chord'));
    if (!chordContinuation) chordHeadExplicitVoice = explicitVoice;
    voices.set(child, explicitVoice || (chordContinuation ? chordHeadExplicitVoice : undefined) || UNASSIGNED_VOICE_ID);
  }
  return voices;
};
const positionedNotes = (part: Element | undefined, measureOrdinalOffset = 0) => {
  const positions = new Map<Element, { beat: number; staff: string; voice: string; measureOrdinal: number }>();
  let divisions = 1;
  for (const [measureIndex, measure] of [...(part?.children || [])].filter(child => child.tagName === 'measure').entries()) {
    const declared = +(measure.getElementsByTagName('attributes')[0]?.getElementsByTagName('divisions')[0]?.textContent || 0);
    if (declared > 0) divisions = declared;
    const resolvedVoices = resolvedSourceVoiceIds(measure);
    let cursor = 0, lastOnset = 0;
    for (const element of [...measure.children]) {
      const duration = +(element.getElementsByTagName('duration')[0]?.textContent || 0);
      if (element.tagName === 'backup') { cursor -= duration; continue; }
      if (element.tagName === 'forward') { cursor += duration; continue; }
      if (element.tagName !== 'note') continue;
      const chord = Boolean(element.getElementsByTagName('chord').length), grace = Boolean(element.getElementsByTagName('grace').length), onset = chord ? lastOnset : cursor;
      positions.set(element, { beat: 1 + onset / divisions, staff: element.getElementsByTagName('staff')[0]?.textContent || '1', voice: resolvedVoices.get(element) || UNASSIGNED_VOICE_ID, measureOrdinal: measureIndex + 1 + measureOrdinalOffset });
      if (!chord) lastOnset = onset;
      if (!chord && !grace) cursor += duration;
    }
  }
  return positions;
};
export type SourceNoteIdentity = {
  sourceIndex: number;
  partId: string;
  staff: string;
  voice: string;
  measureOrdinal: number;
  beat: number;
};

/**
 * Capture a note's source lane before Score Tools removes notes or compacts
 * Staff numbers. The surviving DOM node remains the same object, so this map
 * is also a lightweight source map for the temporary derived render document.
 */
export const sourceNoteIdentityMap = (doc: XMLDocument, measureOrdinalOffset = 0) => {
  const identities = new Map<Element, SourceNoteIdentity>();
  let sourceIndex = 0;
  for (const [partIndex, part] of [...doc.getElementsByTagName('part')].entries()) {
    const partId = part.getAttribute('id') || `P${partIndex + 1}`;
    const positions = positionedNotes(part, measureOrdinalOffset);
    for (const note of [...part.getElementsByTagName('note')]) {
      const position = positions.get(note);
      if (position) identities.set(note, { sourceIndex, partId, ...position });
      sourceIndex++;
    }
  }
  return identities;
};

const containingMeasureNumber = (note: Element) => {
  let current: Element | null = note.parentElement;
  while (current && current.tagName !== 'measure') current = current.parentElement;
  return current?.getAttribute('number');
};

/** Match CorpusNote coordinates against the unmodified source lane. */
export const findSourceStreamNote = (
  notes: readonly Element[],
  identities: ReadonlyMap<Element, SourceNoteIdentity>,
  streamId: string,
  target: Pick<CorpusNote, 'measureOrdinal' | 'measure' | 'beat' | 'pitchMidi'>,
  used: ReadonlySet<Element> = new Set<Element>(),
) => {
  const [partId, staff = '1', voice = '1'] = streamId.split(':');
  return notes.find(note => {
    const identity = identities.get(note);
    if (!identity || used.has(note) || identity.partId !== partId || identity.staff !== staff || identity.voice !== voice) return false;
    const measureMatches = target.measureOrdinal
      ? identity.measureOrdinal === target.measureOrdinal
      : containingMeasureNumber(note) === String(target.measure);
    return measureMatches
      && !note.getElementsByTagName('rest').length
      && Math.abs(identity.beat - Number(target.beat)) < 1e-6
      && midi(note) === target.pitchMidi;
  });
};
const isShortFirstMeasure = (measure: Element) => {
  const attributes = measure.getElementsByTagName('attributes')[0];
  const divisions = +(attributes?.getElementsByTagName('divisions')[0]?.textContent || 1);
  const beatsText = attributes?.getElementsByTagName('beats')[0]?.textContent || '4';
  const beats = beatsText.split('+').reduce((sum, value) => sum + (+value || 0), 0);
  const beatType = +(attributes?.getElementsByTagName('beat-type')[0]?.textContent || 4);
  const nominal = divisions * beats * 4 / beatType;
  let cursor = 0, maximum = 0;
  for (const element of [...measure.children]) {
    const duration = +(element.getElementsByTagName('duration')[0]?.textContent || 0);
    if (element.tagName === 'backup') cursor -= duration;
    else if (element.tagName === 'forward') { cursor += duration; maximum = Math.max(maximum, cursor); }
    else if (element.tagName === 'note' && !element.getElementsByTagName('chord').length && !element.getElementsByTagName('grace').length) {
      cursor += duration; maximum = Math.max(maximum, cursor);
    }
  }
  return nominal > 0 && maximum > 0 && maximum < nominal - .001;
};
const normalizePickupMeasures = (doc: XMLDocument) => {
  for (const part of [...doc.getElementsByTagName('part')]) {
    const measures = [...part.children].filter(child => child.tagName === 'measure');
    const first = measures[0];
    if (!first) continue;
    const pickup = first.getAttribute('implicit')?.toLowerCase() === 'yes' || isShortFirstMeasure(first);
    if (!pickup) continue;
    const firstNumber = Number(first.getAttribute('number'));
    const shift = Number.isFinite(firstNumber) && firstNumber > 0 ? firstNumber : 0;
    for (const [index, measure] of measures.entries()) {
      const declared = Number(measure.getAttribute('number'));
      if (Number.isFinite(declared)) measure.setAttribute('number', String(declared - shift));
      else if (index === 0) measure.setAttribute('number', '0');
    }
  }
};
const effectiveAttributes = (doc: XMLDocument, measures: Element[], first: Element) => {
  let attrs = first.getElementsByTagName('attributes')[0];
  if (!attrs) { attrs = doc.createElement('attributes'); first.insertBefore(attrs, first.firstChild); }
  const prior = measures.slice(0, measures.indexOf(first) + 1);
  for (const tag of ['divisions', 'key', 'time', 'staves', 'clef', 'transpose']) {
    if (attrs.getElementsByTagName(tag).length) continue;
    const source = prior.slice().reverse().map(m => m.getElementsByTagName('attributes')[0]).find(a => a?.getElementsByTagName(tag).length);
    if (source) for (const node of [...source.getElementsByTagName(tag)]) attrs.appendChild(node.cloneNode(true));
  }
};
const tempoSignature = (direction: Element) => {
  const metronome = direction.getElementsByTagName('metronome')[0];
  const soundTempo = direction.getElementsByTagName('sound')[0]?.getAttribute('tempo')?.trim();
  if (!metronome && !soundTempo) return '';
  const beatUnit = metronome?.getElementsByTagName('beat-unit')[0]?.textContent?.trim() || '';
  const dots = metronome?.getElementsByTagName('beat-unit-dot').length || 0;
  const perMinute = metronome?.getElementsByTagName('per-minute')[0]?.textContent?.trim() || '';
  return [beatUnit, dots, perMinute, soundTempo || ''].join('|');
};
export type TempoDisplayPoint = { measureIndex: number; bpm: number; pure: boolean };
export const denseTempoDisplayIndexes = (points: readonly TempoDisplayPoint[]) => {
  const keep = new Set(points.map((_, index) => index));
  const pure = points.map((point, index) => ({ ...point, index })).filter(point => point.pure && Number.isFinite(point.bpm));
  const dense = new Set<number>();
  for (let left = 0; left < pure.length; left++) {
    const window = pure.slice(left).filter(point => point.measureIndex <= pure[left].measureIndex + 3);
    if (window.length >= 4) for (const point of window) dense.add(point.index);
  }
  let priorKept: (TempoDisplayPoint & { index: number }) | null = null;
  for (const point of pure) {
    if (!dense.has(point.index)) { priorKept = null; continue; }
    if (!priorKept) { priorKept = point; continue; }
    const gap = point.measureIndex - priorKept.measureIndex;
    const ratio = Math.max(point.bpm, priorKept.bpm) / Math.max(1, Math.min(point.bpm, priorKept.bpm));
    if (gap >= 4 || ratio >= 1.25) priorKept = point;
    else keep.delete(point.index);
  }
  return keep;
};
const isPureMetronomeDirection = (direction: Element) => {
  const types = [...direction.children].filter(child => child.tagName === 'direction-type');
  return types.length > 0 && types.every(type => type.children.length > 0 && [...type.children].every(child => child.tagName === 'metronome'));
};
const tempoBpm = (direction: Element) => Number(direction.getElementsByTagName('per-minute')[0]?.textContent?.trim() || direction.getElementsByTagName('sound')[0]?.getAttribute('tempo') || NaN);
const dedupeTempoDirections = (part: Element) => {
  const measures = [...part.children].filter(child => child.tagName === 'measure');
  const entries: { direction: Element; signature: string; measureIndex: number; bpm: number; pure: boolean }[] = [];
  let previousTempo = '';
  for (const [measureIndex, measure] of measures.entries()) {
    const seenHere = new Set<string>();
    for (const direction of [...measure.children].filter(child => child.tagName === 'direction')) {
      const signature = tempoSignature(direction);
      if (!signature) continue;
      if (signature === previousTempo || seenHere.has(signature)) { direction.remove(); continue; }
      seenHere.add(signature); previousTempo = signature;
      entries.push({ direction, signature, measureIndex, bpm: tempoBpm(direction), pure: isPureMetronomeDirection(direction) });
    }
  }
  const keep = denseTempoDisplayIndexes(entries);
  entries.forEach((entry, index) => { if (!keep.has(index)) entry.direction.remove(); });
};
const dedupeChordLyrics = (part: Element) => {
  for (const measure of [...part.children].filter(child => child.tagName === 'measure')) {
    let root: Element | null = null;
    for (const note of [...measure.children].filter(child => child.tagName === 'note')) {
      if (!note.getElementsByTagName('chord').length) { root = note; continue; }
      const rootLyrics = new Set([...(root?.getElementsByTagName('lyric') || [])].map(lyric => `${lyric.getAttribute('number') || '1'}:${lyric.textContent?.trim() || ''}`));
      for (const lyric of [...note.getElementsByTagName('lyric')]) {
        const signature = `${lyric.getAttribute('number') || '1'}:${lyric.textContent?.trim() || ''}`;
        if (rootLyrics.has(signature)) lyric.remove();
      }
    }
  }
};
export const excerptMeasureIndexes = (labels: string[], start: number, end: number, ordinalStart?: number, ordinalEnd?: number) => labels.map((label,index)=>({label,index})).filter(({label,index})=>ordinalStart&&ordinalEnd?index+1>=ordinalStart&&index+1<=ordinalEnd:Number(label)>=start&&Number(label)<=end).map(({index})=>index);
export const excerptOrdinalOffset = (targets: CorpusNote[]) => { const ordinals=targets.map(note=>note.measureOrdinal).filter((value):value is number=>Number.isFinite(value));return Math.max(0,(ordinals.length?Math.min(...ordinals):1)-1) };
export const scoreStaffCount = (doc: XMLDocument) => [...doc.getElementsByTagName('part')].reduce((total,part) => {
  const declared=[...part.getElementsByTagName('staves')].map(node=>Number(node.textContent));
  return total+Math.max(1,...declared.filter(Number.isFinite));
},0);
export const fullScoreLayout = (staffCount: number) => {
  if(staffCount < 5)return { pageWidth: 1900, pageHeight: 2700, scale: 24 };
  if(staffCount < 9)return { pageWidth: 2100, pageHeight: 3100, scale: 21 };
  return { pageWidth: 2100, pageHeight: 3100 + 260 * (staffCount - 8), scale: staffCount >= 16 ? 18 : 20 };
};
export const fullScoreBreakMode = 'auto' as const;
export const normalizeMusicXmlInput = (xml: string) => xml.replace(/^\uFEFF/, '');
export type PhraseBoundaryMarker = { note: CorpusNote; boundaryIndex: number; strength: number; beforePhrase?:number; afterPhrase?:number };
export type PhraseSpanMarker = { phraseNumber: number; startIndex: number; endIndex: number; startNote: CorpusNote; endNote: CorpusNote; sharedStart: boolean; sharedEnd: boolean; startMeasure?:number; endMeasure?:number; startPitch?:string; endPitch?:string; startDisplay?:string; endDisplay?:string };
export type MotifSimilarityEvidence={similarity:number;melodic:number;interval:number;contour:number;shape:number;rhythm:number;coverage:number;matchedNotes:number;transformations:string[];alignment:Array<{leftIndex:number|null;rightIndex:number|null;type:string}>};
export type MotifSpanMarker = { reviewOnly?:boolean; reviewLane?:'phrase'; motifNumber:number; familyNumber:number; variantIndex:number; label:string; startIndex:number; endIndex:number; startNote:CorpusNote; endNote:CorpusNote; similarity:MotifSimilarityEvidence };
export type HarmonyHighlightMarker = { analysisId:string; label:string; kind?:'harmony'|'cadence'; startIndex:number; endIndex:number; startNote:CorpusNote; endNote:CorpusNote; flashToken:number };
export const phraseBoundaryLabel = (marker: Pick<PhraseBoundaryMarker, 'afterPhrase'>) => marker.afterPhrase ? `P${marker.afterPhrase} 시작` : '경계';
export const phraseColorIndex = (phraseNumber:number) => Math.max(0, phraseNumber - 1) % 4;
export const phraseSegmentKey = (segmentKey:string, phraseNumber:number, flashingPhraseNumber:number|null, flashToken:number) => `${segmentKey}-${phraseNumber===flashingPhraseNumber?flashToken:0}`;
const EMPTY_PHRASE_MARKERS: PhraseBoundaryMarker[] = [];
const EMPTY_PHRASE_SPANS: PhraseSpanMarker[] = [];
const EMPTY_MOTIF_SPANS: MotifSpanMarker[] = [];
const trimToExcerpt = (doc: XMLDocument, partId: string, start: number, end: number, ordinalStart?: number, ordinalEnd?: number) => {
  for (const p of [...doc.getElementsByTagName('part')]) if (p.getAttribute('id') !== partId) p.remove();
  for (const p of [...doc.getElementsByTagName('score-part')]) if (p.getAttribute('id') !== partId) p.remove();
  for (const g of [...doc.getElementsByTagName('part-group')]) g.remove();
  for (const d of [...doc.getElementsByTagName('defaults')]) d.remove();
  for (const part of [...doc.getElementsByTagName('part')]) {
    const all = [...part.getElementsByTagName('measure')];
    const indexes=new Set(excerptMeasureIndexes(all.map(m=>m.getAttribute('number')||''),start,end,ordinalStart,ordinalEnd)),keep=all.filter((_,index)=>indexes.has(index));
    const first = keep[0];
    if (first) effectiveAttributes(doc, all, first);
    for (const m of all) {
      m.removeAttribute('width');
      for (const p of [...m.getElementsByTagName('print')]) p.remove();
      if (!keep.includes(m)) m.remove();
    }
    dedupeTempoDirections(part);
  }
};

export function FullXmlNotation({ xml, start, end, targets, playbackNotes = EMPTY_NOTES, activePlaybackIndex = null, onPlaybackRangeChange, streamId, analysisStreamId = streamId, excerpt = false, autoScroll = true, pretrimmed = false, measureOrdinalOffset = 0, transpose = '', partIds = EMPTY_PART_IDS, selections = EMPTY_SCORE_SELECTIONS, phraseMarkers = EMPTY_PHRASE_MARKERS, phraseSpans = EMPTY_PHRASE_SPANS, motifSpans = EMPTY_MOTIF_SPANS, phraseVisible = true, motifVisible = true, selectedPhraseBoundary = null, selectedMotifNumber = null, onPhraseBoundarySelect, onMotifSelect, flashingPhraseNumber = null, phraseFlashToken = 0, onPhraseSelect, harmonyHighlight = null }: { xml: string; start: number; end: number; targets: CorpusNote[]; playbackNotes?: CorpusNote[]; activePlaybackIndex?: number|null; onPlaybackRangeChange?:(range:{first:number|null;last:number|null;complete:boolean})=>void; streamId: string; analysisStreamId?: string; excerpt?: boolean; autoScroll?: boolean; pretrimmed?: boolean; measureOrdinalOffset?: number; transpose?:string; partIds?:string[]; selections?:PartSelection[]; phraseMarkers?: PhraseBoundaryMarker[]; phraseSpans?: PhraseSpanMarker[]; motifSpans?:MotifSpanMarker[]; phraseVisible?: boolean; motifVisible?:boolean; selectedPhraseBoundary?: number|null; selectedMotifNumber?:number|null; onPhraseBoundarySelect?:(boundaryIndex:number)=>void; onMotifSelect?:(motifNumber:number)=>void; flashingPhraseNumber?:number|null; phraseFlashToken?:number; onPhraseSelect?:(phraseNumber:number)=>void; harmonyHighlight?:HarmonyHighlightMarker|null }) {
  const [pages, setPages] = useState<(string | null)[]>([]);
  const [renderProgress, setRenderProgress] = useState({ done: 0, total: 0 });
  const [renderError, setRenderError] = useState('');
  const [selectionWarnings, setSelectionWarnings] = useState<string[]>([]);
  const [excerptWidth, setExcerptWidth] = useState(620);
  const [playhead, setPlayhead] = useState<{left:number;top:number;height:number}|null>(null);
  const [phraseMarkerPositions, setPhraseMarkerPositions] = useState<Array<{boundaryIndex:number;strength:number;beforePhrase?:number;afterPhrase?:number;left:number;top:number;height:number}>>([]);
  const [phraseRangeSegments,setPhraseRangeSegments]=useState<Array<{key:string;phraseNumber:number;colorIndex:number;left:number;top:number;width:number;label:boolean;endLabel:boolean;labelText:string}>>([]);
  const [phraseSharedAnchors,setPhraseSharedAnchors]=useState<Array<{key:string;left:number;top:number;leftColor:number;rightColor:number}>>([]);
  const [harmonyRangeSegments,setHarmonyRangeSegments]=useState<Array<{key:string;left:number;top:number;width:number;height:number;label:boolean}>>([]);
  const host = useRef<HTMLDivElement>(null);
  const autoScrolledKey = useRef('');
  const renderMore = useRef<(() => void) | null>(null);
  const revealPhrase = useRef<((phraseNumber:number)=>void) | null>(null);
  const latestSpans = useRef(phraseSpans);latestSpans.current=phraseSpans;
  const resolveAnchor = useRef<(note:CorpusNote)=>string[]>(()=>[]);
  const [renderBusy,setRenderBusy]=useState(false);
  const instance = useRef<Promise<VerovioToolkit> | null>(null);
  if (!instance.current) instance.current = newVerovioToolkit();
  useEffect(() => {
    let live = true;
    resolveAnchor.current=()=>[];
    setRenderBusy(true);setPages([]);setRenderError('');setSelectionWarnings([]);setRenderProgress({done:0,total:excerpt?0:-1});
    instance.current!.then(async tk => {
      if(!live)return;
      if(!excerpt){await new Promise<void>(resolve=>window.setTimeout(resolve,40));if(!live)return}
      const doc = new DOMParser().parseFromString(normalizeMusicXmlInput(xml), 'application/xml');
      const sourceNoteIndices=new Map([...doc.getElementsByTagName('note')].map((note,index)=>[note,index]));
      const sourceNoteIdentities=sourceNoteIdentityMap(doc,measureOrdinalOffset);
      if(selections.length)setSelectionWarnings(applyScoreViewSelections(doc,selections).warnings);
      else applyPartViewSelection(doc,partIds);
      const [partId] = streamId.split(':');
      for (const tag of ['credit', 'work', 'movement-title']) for (const n of [...doc.getElementsByTagName(tag)]) n.remove();
      normalizePickupMeasures(doc);
      let positionedOrdinalOffset=measureOrdinalOffset;
      if (excerpt && !pretrimmed) { const ordinals=targets.map(note=>note.measureOrdinal).filter((value):value is number=>Number.isFinite(value)),firstOrdinal=ordinals.length?Math.min(...ordinals):undefined;trimToExcerpt(doc,partId,start,end,firstOrdinal,ordinals.length?Math.max(...ordinals):undefined);positionedOrdinalOffset=excerptOrdinalOffset(targets); }
      const part = [...doc.getElementsByTagName('part')].find(x => x.getAttribute('id') === partId);
      for (const scorePart of [...doc.getElementsByTagName('part')]) dedupeTempoDirections(scorePart);
      if(part)dedupeChordLyrics(part);
      const excerptMeasures=excerpt?[...(part?.children||[])].filter(child=>child.tagName==='measure').length:0,staffCount=scoreStaffCount(doc),fullLayout=fullScoreLayout(staffCount),pageWidth=excerpt?Math.max(1800,excerptMeasures*450):fullLayout.pageWidth,pageHeight=excerpt?720:fullLayout.pageHeight;
      if(excerpt)setExcerptWidth(Math.max(620,Math.round(620*pageWidth/1800)));
      if(!excerpt)host.current?.style.setProperty('--score-page-ratio',`${pageWidth} / ${pageHeight}`);
      tk.setOptions({ pageWidth, pageHeight, pageMarginTop: excerpt ? 24 : 75, pageMarginBottom: excerpt ? 38 : 210, adjustPageHeight: excerpt, scale: excerpt ? 25 : fullLayout.scale, breaks: excerpt ? 'none' : fullScoreBreakMode, inputFrom: 'musicxml', svgViewBox: true, header: 'none', footer: 'none', mnumInterval: 1, spacingStaff: 12, spacingSystem: 6, transpose: transpose || '' });
      const ordered = [...(part?.getElementsByTagName('note') || [])];
      const positions = positionedNotes(part, positionedOrdinalOffset);
      const tieEvents = ordered.flatMap(note => {
        const identity = sourceNoteIdentities.get(note);
        return identity ? [{ value: note, partId: identity.partId, staff: identity.staff, voice: identity.voice, measureOrdinal: identity.measureOrdinal, beat: identity.beat, pitchMidi: midi(note), isRest: Boolean(note.getElementsByTagName('rest').length), tieTypes: tieTypes(note) }] : [];
      });
      const lyricPositions=new Set<string>();
      for(const note of ordered){const position=positions.get(note);if(!position)continue;for(const lyric of [...note.getElementsByTagName('lyric')]){const signature=`${position.measureOrdinal}:${position.staff}:${position.beat}:${lyric.getAttribute('number')||'1'}:${lyric.textContent?.trim()||''}`;if(lyricPositions.has(signature))lyric.remove();else lyricPositions.add(signature)}}
      const used = new Set<Element>();
      const marked = new Set<Element>();
      const mark = (n: Element) => { if (!marked.has(n)) { n.setAttribute('id', `search-match-${marked.size}`); n.setAttribute('color', '#c9473f'); marked.add(n); } };
      // MusicXML stores a chord as one root note followed by adjacent <note><chord/> siblings.
      const markChord = (n: Element) => {
        let i = ordered.indexOf(n);
        while (i > 0 && ordered[i].getElementsByTagName('chord').length) i--;
        mark(ordered[i]);
        for (let j = i + 1; j < ordered.length && ordered[j].getElementsByTagName('chord').length; j++) mark(ordered[j]);
      };
      for (const target of targets) {
        const note = findSourceStreamNote(ordered,sourceNoteIdentities,streamId,target,used);
        if (!note) continue;
        used.add(note);
        markChord(note);
        const seed = tieEvents.find(event => event.value === note);
        if (seed) for (const continuation of tiedNoteChain(seed, tieEvents).slice(1)) markChord(continuation);
      }
      const playbackIds = new Map<string, number>(), playbackUsed = new Set<Element>();
      playbackNotes.filter(note => note.kind === 'note').forEach((target, playbackIndex) => {
        const note = findSourceStreamNote(ordered,sourceNoteIdentities,streamId,target,playbackUsed);
        if (!note) return;playbackUsed.add(note);const id=note.getAttribute('id')||`playback-note-${playbackIndex}`;note.setAttribute('id',id);playbackIds.set(id,playbackIndex);
      });
      // Anchor every source note once, independently of the currently visible analysis.
      const occupiedIds=new Set([...doc.querySelectorAll('[id]')].map(n=>n.getAttribute('id')));
      for(const [index,note] of ordered.entries())if(!note.getAttribute('id')){
        let id=`viewer-anchor-${index}`;while(occupiedIds.has(id))id+='-';
        occupiedIds.add(id);note.setAttribute('id',id);
      }
      const [analysisPartId]=analysisStreamId.split(':');
      const analysisPart=[...doc.getElementsByTagName('part')].find(p=>p.getAttribute('id')===analysisPartId);
      const analysisOrdered=[...(analysisPart?.getElementsByTagName('note')||[])];
      for(const [index,note] of analysisOrdered.entries())if(!note.getAttribute('id')){
        let id=`analysis-anchor-${index}`;while(occupiedIds.has(id))id+='-';occupiedIds.add(id);note.setAttribute('id',id);
      }
      const analysisTieEvents=analysisOrdered.flatMap(note=>{const identity=sourceNoteIdentities.get(note);return identity?[{value:note,partId:identity.partId,staff:identity.staff,voice:identity.voice,measureOrdinal:identity.measureOrdinal,beat:identity.beat,pitchMidi:midi(note),isRest:Boolean(note.getElementsByTagName('rest').length),tieTypes:tieTypes(note)}]:[]});
      const anchorCache=new Map<string,string[]>();
      resolveAnchor.current=(target)=>{
        const key=JSON.stringify([target.measureOrdinal,target.measure,target.beat,target.pitchMidi]);
        const cached=anchorCache.get(key);if(cached)return cached;
        const note=findSourceStreamNote(analysisOrdered,sourceNoteIdentities,analysisStreamId,target);
        const seed=note&&analysisTieEvents.find(event=>event.value===note);
        const ids=(seed?tiedNoteChain(seed,analysisTieEvents):note?[note]:[]).map(n=>n.getAttribute('id')!);
        anchorCache.set(key,ids);return ids;
      };
      if(!live)return;
      // Normalize only the temporary render document; source XML and analysis stay unchanged.
      normalizeMusicXmlVoices(doc);
      const loaded = tk.loadData(new XMLSerializer().serializeToString(doc));
      if (!loaded || tk.getPageCount() < 1) throw new Error('MusicXML을 Verovio에서 불러오지 못했습니다.');
      const renderedPlaybackIndices=new Set<number>();
      const notifyPlaybackRange=(complete:boolean)=>{const values=[...renderedPlaybackIndices].sort((a,b)=>a-b);onPlaybackRangeChange?.({first:values[0]??null,last:values.at(-1)??null,complete})};
      const renderPage = (page: number) => {
        const svg = new DOMParser().parseFromString(tk.renderToSVG(page, false), 'image/svg+xml');
        for(const [note,index] of sourceNoteIndices){const id=note.getAttribute('id');if(id)svg.getElementById(id)?.setAttribute('data-source-note-index',String(index));}
        for (let i = 0; i < marked.size; i++) {
          const n = svg.getElementById(`search-match-${i}`);
          if (n) { n.setAttribute('data-target-note', 'true'); if (i === 0) n.setAttribute('data-target-start', 'true'); }
        }
        for(const [id,index] of playbackIds){const n=svg.getElementById(id);if(n){n.setAttribute('data-playback-index',String(index));renderedPlaybackIndices.add(index)}}
        return new XMLSerializer().serializeToString(svg.documentElement);
      };
      const pageCount = tk.getPageCount();
      if (excerpt) { const output: string[]=[];for(let page=1;page<=pageCount;page++)output.push(renderPage(page));if(live){setPages(output);setRenderProgress({done:pageCount,total:pageCount});setRenderBusy(false);notifyPlaybackRange(true)}return }
      // Reserve all page positions and engrave the matched page first. Large
      // scores stay in score order while the useful page appears immediately.
      const output:(string|null)[]=Array(pageCount).fill(null),matchedPages=[...new Set(Array.from({length:marked.size},(_,index)=>Math.max(1,Math.min(pageCount,tk.getPageWithElement(`search-match-${index}`)||1))))],priority=matchedPages.length?matchedPages:[1],prioritySet=new Set(priority),distanceToMatch=(page:number)=>Math.min(...priority.map(target=>Math.abs(target-page))),remaining=Array.from({length:pageCount},(_,index)=>index+1).filter(page=>!prioritySet.has(page)).sort((a,b)=>distanceToMatch(a)-distanceToMatch(b)||a-b),order=[...priority,...remaining];
      setPages([...output]);setRenderProgress({done:0,total:pageCount});
      await new Promise<void>(resolve=>window.setTimeout(resolve,40));
      if(!live)return;
      const yieldToBrowser=()=>new Promise<void>(resolve=>window.requestIdleCallback?window.requestIdleCallback(()=>resolve(),{timeout:500}):window.setTimeout(resolve,120));
      let done=0,rendering=false;
      const renderBatch=async(count=3)=>{if(rendering||!live)return;rendering=true;setRenderBusy(true);try{for(let index=0;index<count&&order.length;index++){if(!live)return;const page=order.shift()!;output[page-1]=renderPage(page);done++;setPages([...output]);setRenderProgress({done,total:pageCount});notifyPlaybackRange(done>=pageCount);await yieldToBrowser()}}finally{rendering=false;if(live)setRenderBusy(false)}};
      renderMore.current=()=>void renderBatch(3);
      revealPhrase.current=(phraseNumber:number)=>{if(!live)return;const span=latestSpans.current.find(s=>s.phraseNumber===phraseNumber),id=span?resolveAnchor.current(span.startNote)[0]:null,page=id?tk.getPageWithElement(id):0;if(!page)return;const scrollToPhrase=()=>window.setTimeout(()=>{if(live)host.current?.querySelector(`[aria-label="Phrase ${phraseNumber} 구간 강조"]`)?.scrollIntoView({behavior:'smooth',block:'center'})},40);if(output[page-1]){scrollToPhrase();return}if(rendering){window.setTimeout(()=>{if(live)revealPhrase.current?.(phraseNumber)},120);return}rendering=true;setRenderBusy(true);void(async()=>{try{const orderIndex=order.indexOf(page);if(orderIndex>=0)order.splice(orderIndex,1);output[page-1]=renderPage(page);done++;setPages([...output]);setRenderProgress({done,total:pageCount});notifyPlaybackRange(done>=pageCount);await yieldToBrowser();if(live)scrollToPhrase()}finally{rendering=false;if(live)setRenderBusy(false)}})()};
      await renderBatch(Math.max(3,priority.length));
    }).catch(error => {
      if (!live) return;
      console.error(`Verovio ${excerpt ? 'excerpt' : 'full score'} rendering failed`, error);
      setRenderBusy(false);setPages([]);setRenderProgress({done:0,total:0});
      setRenderError(error instanceof Error ? error.message : String(error));
    });
    return () => { live = false;renderMore.current=null;revealPhrase.current=null };
  }, [xml, start, end, targets, playbackNotes, streamId, analysisStreamId, excerpt, pretrimmed, measureOrdinalOffset, transpose, partIds, selections, onPlaybackRangeChange]);
  useLayoutEffect(()=>{
    const container=host.current;if(!container||excerpt)return;
    const attrs=['data-phrase-note-index','data-phrase-boundary-index','data-phrase-strength','data-phrase-before','data-phrase-after'];
    for(const node of container.querySelectorAll('[data-phrase-note-index]'))for(const attr of attrs)node.removeAttribute(attr);
    const byId=new Map([...container.querySelectorAll('[id]')].map(n=>[n.id,n]));
    const anchors=new Map<number,{note:CorpusNote;end:boolean}>();
    for(const span of [...phraseSpans,...motifSpans]){
      if(!anchors.has(span.startIndex))anchors.set(span.startIndex,{note:span.startNote,end:false});
      anchors.set(span.endIndex,{note:span.endNote,end:true});
    }
    if(harmonyHighlight){if(!anchors.has(harmonyHighlight.startIndex))anchors.set(harmonyHighlight.startIndex,{note:harmonyHighlight.startNote,end:false});anchors.set(harmonyHighlight.endIndex,{note:harmonyHighlight.endNote,end:true})}
    for(const marker of phraseMarkers)if(!anchors.has(marker.boundaryIndex))anchors.set(marker.boundaryIndex,{note:marker.note,end:false});
    for(const [index,anchor] of anchors){
      const ids=resolveAnchor.current(anchor.note);
      for(const id of anchor.end?ids:ids.slice(0,1))byId.get(id)?.setAttribute('data-phrase-note-index',String(index));
    }
    for(const marker of phraseMarkers){
      const node=byId.get(resolveAnchor.current(marker.note)[0]);if(!node)continue;
      node.setAttribute('data-phrase-boundary-index',String(marker.boundaryIndex));node.setAttribute('data-phrase-strength',String(marker.strength));
      if(marker.beforePhrase)node.setAttribute('data-phrase-before',String(marker.beforePhrase));
      if(marker.afterPhrase)node.setAttribute('data-phrase-after',String(marker.afterPhrase));
    }
  },[pages,excerpt,phraseMarkers,phraseSpans,motifSpans,harmonyHighlight]);
  useEffect(()=>{
    const container=host.current;if(!container||excerpt)return;
    let frame=0;
    const measure=()=>{cancelAnimationFrame(frame);frame=requestAnimationFrame(()=>{
      for(const page of container.querySelectorAll<HTMLElement>('section')){
        const svg=page.querySelector('svg'),systems=[...page.querySelectorAll('g.system')];
        if(!svg||!systems.length)continue;
        const inkTop=Math.min(...systems.map(s=>s.getBoundingClientRect().top));
        const inset=scorePageTopInset(inkTop-svg.getBoundingClientRect().top,motifSpans.some(span=>span.reviewOnly&&span.reviewLane==='phrase')?52:40);
        if(page.style.paddingTop!==`${inset}px`)page.style.paddingTop=`${inset}px`;
      }
    })};
    measure();const observer=new ResizeObserver(measure);observer.observe(container);
    window.addEventListener('resize',measure);
    return()=>{cancelAnimationFrame(frame);observer.disconnect();window.removeEventListener('resize',measure)};
  },[pages,excerpt,motifSpans]);
  useEffect(()=>{
    if(excerpt||!host.current||renderProgress.done>=renderProgress.total)return;
    const observer=new IntersectionObserver(entries=>{if(entries.some(entry=>entry.isIntersecting))renderMore.current?.()},{rootMargin:'1000px 0px'});
    for(const placeholder of host.current.querySelectorAll('.xml-page-loading'))observer.observe(placeholder);
    return()=>observer.disconnect();
  },[pages,excerpt,renderProgress.done,renderProgress.total]);
  useEffect(() => {
    if (!autoScroll || !pages.length) return;
    const key=`${streamId}:${start}:${end}`;if(autoScrolledKey.current===key)return;
    requestAnimationFrame(() => { const target=host.current?.querySelector('[data-target-start="true"]');if(!target)return;autoScrolledKey.current=key;const rect=target.getBoundingClientRect(),offset=Math.max(110,window.innerHeight*.2);window.scrollTo({top:Math.max(0,window.scrollY+rect.top-offset),behavior:'auto'}); });
  }, [pages, autoScroll, streamId, start, end]);
  useEffect(()=>{if(excerpt)host.current?.style.setProperty('--excerpt-width',`${excerptWidth}px`)},[excerpt,excerptWidth]);
  useEffect(()=>{if(activePlaybackIndex===null){setPlayhead(null);return}requestAnimationFrame(()=>{const container=host.current,target=container?.querySelector(`[data-playback-index="${activePlaybackIndex}"]`);if(!container||!target){setPlayhead(null);return}const rootRect=container.getBoundingClientRect(),rect=target.getBoundingClientRect();setPlayhead({left:rect.left-rootRect.left-4,top:rect.top-rootRect.top-24,height:Math.max(80,rect.height+48)});if(rect.top<100||rect.bottom>window.innerHeight-60)target.scrollIntoView({behavior:'smooth',block:'center'})})},[activePlaybackIndex,pages]);
  useEffect(()=>{if(flashingPhraseNumber!==null&&phraseFlashToken>0)revealPhrase.current?.(flashingPhraseNumber)},[flashingPhraseNumber,phraseFlashToken]);
  useEffect(()=>{
    if(excerpt||!host.current){setPhraseMarkerPositions([]);setPhraseRangeSegments([]);setPhraseSharedAnchors([]);return}
    let frame=0;
    const measure=()=>{cancelAnimationFrame(frame);frame=requestAnimationFrame(()=>{const container=host.current;if(!container)return;const rootRect=container.getBoundingClientRect(),noteElements=new Map<number,Element>();for(const target of container.querySelectorAll('[data-phrase-note-index]'))noteElements.set(Number(target.getAttribute('data-phrase-note-index')),target);const positions=[...container.querySelectorAll('[data-phrase-boundary-index]')].map(target=>{const rect=target.getBoundingClientRect();return{boundaryIndex:Number(target.getAttribute('data-phrase-boundary-index')),strength:Number(target.getAttribute('data-phrase-strength')),beforePhrase:Number(target.getAttribute('data-phrase-before'))||undefined,afterPhrase:Number(target.getAttribute('data-phrase-after'))||undefined,left:rect.left-rootRect.left+rect.width/2,top:rect.top-rootRect.top-34,height:Math.max(92,rect.height+68)}}).filter(position=>Number.isFinite(position.boundaryIndex));setPhraseMarkerPositions(positions);
      const systems=[...container.querySelectorAll('g.system')],systemIndex=new Map(systems.map((system,index)=>[system,index])),ranges:Array<{key:string;phraseNumber:number;colorIndex:number;left:number;top:number;width:number;label:boolean;endLabel:boolean;labelText:string}>=[];
      for(const span of phraseSpans){const startNode=noteElements.get(span.startIndex),endNode=noteElements.get(span.endIndex);if(!startNode||!endNode)continue;const startSystem=startNode.closest('g.system'),endSystem=endNode.closest('g.system');if(!startSystem||!endSystem)continue;const first=systemIndex.get(startSystem),last=systemIndex.get(endSystem);if(first===undefined||last===undefined)continue;const measures=span.startMeasure===span.endMeasure?`${span.startMeasure}마디`:`${span.startMeasure}–${span.endMeasure}마디`,labelText=`Phrase ${span.phraseNumber} · ${measures} · ${span.startDisplay||span.startPitch}→${span.endDisplay||span.endPitch}`;for(let index=first;index<=last;index++){const system=systems[index],systemRect=system.getBoundingClientRect(),startRect=startNode.getBoundingClientRect(),endRect=endNode.getBoundingClientRect(),left=index===first?startRect.left+startRect.width/2:systemRect.left+4,right=index===last?endRect.left+endRect.width/2:systemRect.right-4;ranges.push({key:`${span.phraseNumber}-${index}`,phraseNumber:span.phraseNumber,colorIndex:phraseColorIndex(span.phraseNumber),left:left-rootRect.left,top:systemRect.top-rootRect.top+3,width:Math.max(8,right-left),label:index===first,endLabel:index===last,labelText})}}setPhraseRangeSegments(ranges);
      const shared:Array<{key:string;left:number;top:number;leftColor:number;rightColor:number}>=[];for(let index=0;index<phraseSpans.length-1;index++){const left=phraseSpans[index],right=phraseSpans[index+1];if(left.endIndex!==right.startIndex)continue;const target=noteElements.get(left.endIndex);if(!target)continue;const rect=target.getBoundingClientRect();shared.push({key:String(left.endIndex),left:rect.left-rootRect.left+rect.width/2,top:rect.top-rootRect.top+rect.height/2,leftColor:(left.phraseNumber-1)%4,rightColor:(right.phraseNumber-1)%4})}setPhraseSharedAnchors(shared);
      const harmonyRanges:Array<{key:string;left:number;top:number;width:number;height:number;label:boolean}>=[];if(harmonyHighlight){const startNode=noteElements.get(harmonyHighlight.startIndex),endNode=noteElements.get(harmonyHighlight.endIndex),startSystem=startNode?.closest('g.system'),endSystem=endNode?.closest('g.system'),first=startSystem?systemIndex.get(startSystem):undefined,last=endSystem?systemIndex.get(endSystem):undefined;if(startNode&&endNode&&first!==undefined&&last!==undefined){for(let index=first;index<=last;index++){const system=systems[index],systemRect=system.getBoundingClientRect(),startRect=startNode.getBoundingClientRect(),endRect=endNode.getBoundingClientRect(),left=index===first?startRect.left+startRect.width/2:systemRect.left+3,right=index===last?endRect.right:systemRect.right-3;harmonyRanges.push({key:`${harmonyHighlight.analysisId}-${index}-${harmonyHighlight.flashToken}`,left:left-rootRect.left,top:systemRect.top-rootRect.top,width:Math.max(8,right-left),height:Math.max(28,systemRect.height),label:index===first})}}}setHarmonyRangeSegments(harmonyRanges)})};
    measure();const observer=new ResizeObserver(measure);observer.observe(host.current);window.addEventListener('resize',measure);return()=>{cancelAnimationFrame(frame);observer.disconnect();window.removeEventListener('resize',measure)};
  },[pages,excerpt,phraseMarkers,phraseSpans,harmonyHighlight]);
  useEffect(()=>{if(!harmonyHighlight||!harmonyRangeSegments.length)return;requestAnimationFrame(()=>host.current?.querySelector(`[data-harmony-highlight="${harmonyHighlight.analysisId}"]`)?.scrollIntoView({behavior:'smooth',block:'center'}))},[harmonyHighlight?.flashToken,harmonyRangeSegments.length]);
  useEffect(()=>{
    const container=host.current;
    if(excerpt||!container)return;
    let frame=0;
    const measure=()=>{cancelAnimationFrame(frame);frame=requestAnimationFrame(()=>{
      for(const old of container.querySelectorAll('.motif-range-segment'))old.remove();
      const rootRect=container.getBoundingClientRect(),noteElements=new Map<number,Element>();
      for(const target of container.querySelectorAll('[data-phrase-note-index]'))noteElements.set(Number(target.getAttribute('data-phrase-note-index')),target);
      const systems=[...container.querySelectorAll('g.system')],systemIndex=new Map(systems.map((system,index)=>[system,index]));
      for(const span of motifSpans){
        if(!motifVisible&&!span.reviewOnly)continue;
        const startNode=noteElements.get(span.startIndex),endNode=noteElements.get(span.endIndex);if(!startNode||!endNode)continue;
        const startSystem=startNode.closest('g.system'),endSystem=endNode.closest('g.system');if(!startSystem||!endSystem)continue;
        const first=systemIndex.get(startSystem),last=systemIndex.get(endSystem);if(first===undefined||last===undefined)continue;
        for(let index=first;index<=last;index++){
          const system=systems[index],systemRect=system.getBoundingClientRect(),startRect=startNode.getBoundingClientRect(),endRect=endNode.getBoundingClientRect(),left=index===first?startRect.left+startRect.width/2:systemRect.left+4,right=index===last?endRect.left+endRect.width/2:systemRect.right-4;
          const marker=document.createElement('button');marker.type='button';marker.className=`motif-range-segment${span.motifNumber===selectedMotifNumber?' selected':''}`;marker.style.left=`${left-rootRect.left}px`;marker.style.top=`${systemRect.top-rootRect.top+22}px`;marker.style.width=`${Math.max(8,right-left)}px`;marker.setAttribute('aria-label',`${span.label} 후보 구간 · 상세 보기`);marker.addEventListener('click',()=>onMotifSelect?.(span.motifNumber));
          marker.dataset.motifNumber=String(span.motifNumber);marker.dataset.motifStart=String(span.startIndex);marker.dataset.motifEnd=String(span.endIndex);marker.dataset.motifSegment=String(index-first);
          const pageRect=system.closest('section')?.getBoundingClientRect();
          if(span.reviewOnly){
            marker.disabled=true;marker.classList.add('structure-proposal-range');
            if(pageRect&&span.reviewLane==='phrase'){
              const originLeft=rootRect.left+container.clientLeft,originTop=rootRect.top+container.clientTop;
              const layout=proposalOverlayLayout({left:pageRect.left-originLeft,right:pageRect.right-originLeft,top:pageRect.top-originTop},systemRect.top-originTop,left-originLeft,right-originLeft);
              marker.style.left=`${layout.left}px`;marker.style.top=`${layout.top}px`;marker.style.width=`${layout.width}px`;
            }else marker.style.top=`${systemRect.top-rootRect.top+44}px`;
            marker.setAttribute('aria-label',span.label);marker.dataset.reviewOnly='true';
          }
          if(index===first){const label=document.createElement('span');label.textContent=span.label;marker.append(label)}
          if(span.reviewOnly&&index===last){const label=document.createElement('span');label.textContent='끝';label.style.left='auto';label.style.right='0';marker.append(label);}
          container.append(marker);
          if(span.reviewOnly&&pageRect){
            const label=index===first?marker.querySelector('span'):null;
            if(label){
              const fit=overlayLabelOffset(marker.getBoundingClientRect().left,label.getBoundingClientRect().width,pageRect.left,pageRect.right);
              label.style.left=`${fit.left}px`;label.style.maxWidth=`${fit.maxWidth}px`;
              label.title=span.label;
            }
          }
        }
      }
    })};
    measure();const observer=new ResizeObserver(measure);observer.observe(container);window.addEventListener('resize',measure);return()=>{cancelAnimationFrame(frame);observer.disconnect();window.removeEventListener('resize',measure);for(const old of container.querySelectorAll('.motif-range-segment'))old.remove()};
  },[pages,excerpt,motifSpans,motifVisible,selectedMotifNumber,onMotifSelect]);
  const colors=['#2d9485','#d9842b','#7658b7','#2f6eb5'];
  return <div ref={host} className={`xml-score ${excerpt ? 'xml-excerpt' : ''}`} data-target-count={targets.length}>{playhead&&<i className="full-score-playhead" style={{left:playhead.left,top:playhead.top,height:playhead.height}}/>}{harmonyHighlight&&harmonyRangeSegments.map(segment=><div key={segment.key} data-harmony-highlight={harmonyHighlight.analysisId} className={`harmony-range-highlight ${harmonyHighlight.kind==='cadence'?'cadence':''}`} style={{left:segment.left,top:segment.top,width:segment.width,height:segment.height}} title={harmonyHighlight.kind==='cadence'?'선택한 Cadence 후보의 준비화음부터 종결화음까지입니다. 미보정 분석 가설입니다.':'선택한 자동 화성의 시간 범위입니다. 범위 안의 모든 음이 화음 구성음이라는 뜻은 아닙니다.'}>{segment.label&&<span>{harmonyHighlight.label}</span>}</div>)}{phraseVisible&&phraseRangeSegments.map(segment=><button key={phraseSegmentKey(segment.key,segment.phraseNumber,flashingPhraseNumber,phraseFlashToken)} type="button" aria-label={`Phrase ${segment.phraseNumber} 구간 강조`} className={`phrase-range-segment ${segment.phraseNumber===flashingPhraseNumber?'flashing':''}`} onClick={()=>onPhraseSelect?.(segment.phraseNumber)} style={{left:segment.left,top:segment.top,width:segment.width,color:colors[segment.colorIndex],borderColor:colors[segment.colorIndex]}}>{segment.label&&<span style={{background:colors[segment.colorIndex]}}>{segment.labelText}</span>}{segment.endLabel&&<b>끝</b>}</button>)}{phraseVisible&&phraseSharedAnchors.map(anchor=><i key={anchor.key} className="phrase-shared-anchor" style={{left:anchor.left,top:anchor.top,background:`linear-gradient(90deg,${colors[anchor.leftColor]} 0 50%,${colors[anchor.rightColor]} 50% 100%)`}} title="명시적 overlap 가설에서 앞·뒤 Phrase가 공유하는 음"/>)}{phraseVisible&&phraseMarkerPositions.map((marker,index)=>{const boundaryLabel=phraseBoundaryLabel(marker),color=colors[phraseColorIndex(marker.afterPhrase||1)];return <button key={`${marker.boundaryIndex}-${index}`} type="button" className={`phrase-boundary-marker ${selectedPhraseBoundary===marker.boundaryIndex?'selected':''}`} style={{left:marker.left,top:marker.top,height:marker.height,color}} onClick={()=>onPhraseBoundarySelect?.(marker.boundaryIndex)} title={`${boundaryLabel} 경계 후보 · 증거 강도 ${Math.round(marker.strength*100)}%`} aria-label={`Phrase ${marker.afterPhrase||''} 시작 경계`}><span>{boundaryLabel}</span></button>})}{selectionWarnings.length>0&&<div className="xml-selection-warning" role="status">{selectionWarnings.map(warning=><span key={warning}>{warning}</span>)}</div>}{renderError&&<div className="xml-render-error">악보 렌더링에 실패했습니다. {renderError}</div>}{!excerpt&&renderProgress.total!==0&&<div className="xml-render-progress"><span>{renderProgress.total<0?'전체 악보 구조를 분석하는 중':renderProgress.done<renderProgress.total?(renderBusy?'악보 렌더링 진행 중':'표시 준비 완료 · 나머지 페이지는 스크롤하면 불러옵니다'):'악보 렌더링 완료'}</span><b>{renderProgress.total<0?'Verovio 조판 준비':`${renderProgress.done} / ${renderProgress.total} pages`}</b>{renderProgress.total>0&&<i><em style={{width:`${100*renderProgress.done/renderProgress.total}%`}}/></i>}{renderProgress.total>0&&renderProgress.done<renderProgress.total&&<button type="button" disabled={renderBusy} onClick={()=>renderMore.current?.()}>{renderBusy?'페이지를 그리는 중…':'다음 3쪽 불러오기'}</button>}</div>}{pages.map((svg, i) => svg?<RenderedScorePage key={i} svg={svg} />:<section key={i} className="xml-page-loading"><span>스크롤하면 불러옵니다 · page {i+1}/{pages.length}</span></section>)}</div>;
}
