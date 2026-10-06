// Note-level motif discovery, ported 1:1 from musicomp analysis/motif_discovery.py (v0.2 defaults).
//
// Each note k gets a token (IOI to the next note, diatonic step to the next note); equal token strings are
// repetitions with the same rhythm under exact or tonal transposition, from ANY starting note.  Longest
// common extensions give candidate patterns; a greedy compressed cover (COSIATEC-like, lazy re-scoring)
// keeps non-overlapping occurrences.  Retrograde occurrences are added to the families.
//
// Role in MusicSearch (musicomp DEVELOPMENT_LOG #22-#23): FAMILY LINKS between the score page's motif spans,
// not the spans themselves.  On BPS-motif the page's spans are better (occurrence F1 0.40 vs 0.30) while
// these links are better (family recall 0.63 vs 0.35); linkMotifSpanFamilies() unions both link sources:
// family F1 0.51 -> 0.59 (BPS), 0.81 -> 1.0 (JKU-PDD), spans unchanged.  Melody only, no harmony.
//
// Input notes as for phrase-breath-layer.mjs (onset, durationRatio, pitchMidi, spelling|tpc, measureOrdinal,
// meterCount/meterUnit or meter, mstart|beat, tieStop/isAttack).
import {analyzeBreathLayer} from './phrase-breath-layer.mjs';

const VERSION = 'motif-discovery-v0.2 (musicomp 2026-10-05)';
export const MOTIF_DEFAULTS = Object.freeze({minNotes: 4, maxBars: 4, minGain: 16, wBound: 0.5, maxNotes: 24, variantKinds: ['retrograde']});
const EPS = 1e-6;
const k6 = v => Math.round(v * 1e6) / 1e6;
const sign = x => (x > EPS) - (x < -EPS);
const finite = v => v !== null && v !== undefined && v !== '' && Number.isFinite(Number(v));
const feltBeat = (count, unit) => (unit === 8 && count % 3 === 0 && count > 3 ? 1.5 : 4 / unit);
const STEP_PC = [0, 2, 4, 5, 7, 9, 11];

function diatonic(note) {
  const m = /^([A-Ga-g])([#b\-x]*)(-?\d+)$/.exec(String(note?.spelling ?? ''));
  if (m) return Number(m[3]) * 7 + 'CDEFGAB'.indexOf(m[1].toUpperCase());
  if (finite(note?.tpc)) {
    const t = Number(note.tpc) + 1, step = 'CDEFGAB'.indexOf('FCGDAEB'[((t % 7) + 7) % 7]), alter = Math.floor(t / 7);
    return Math.floor((Number(note.pitchMidi) - alter - STEP_PC[step]) / 12) * 7 + step;
  }
  return null;
}

function meterOf(note) {
  const m = /^(\d+)\/(\d+)$/.exec(String(note?.meter ?? ''));
  return m ? [Number(m[1]), Number(m[2])] : [Number(note.meterCount), Number(note.meterUnit)];
}

/** Attack notes (tie tails folded into the previous attack when continuous) with metric phase. */
function attacks(notes, warnings) {
  const ev = [];
  notes.forEach((note, index) => {
    const onset = Number(note.onset), dur = Number(note.durationRatio);
    if (!finite(note.onset) || !finite(note.durationRatio) || dur < 0 || !finite(note.pitchMidi)) throw new Error(`note ${index}: invalid onset/duration/pitch`);
    if (note.isAttack === false || note.tieStop) {
      const last = ev.at(-1);
      const sameVoice = last && (note.voice === undefined || last.voice === undefined || String(note.voice) === String(last.voice));
      if (last && Math.abs(onset - last.end) <= EPS && Number(note.pitchMidi) === last.pitch && sameVoice) {
        last.end = Math.max(last.end, onset + dur);
        last.lastIndex = index;
        return;
      }
      warnings.push({index, issue:'tie-tail-not-continuous', reason:!last?'no preceding attack':Number(note.pitchMidi)!==last.pitch?'pitch differs':!sameVoice?'voice differs':`gap ${k6(onset-last.end)} quarters`});
    }
    const [count, unit] = meterOf(note);
    if (!(count > 0 && unit > 0)) throw new Error(`note ${index}: positive meter required`);
    ev.push({index, lastIndex:index, voice:note.voice, onset, end: onset + dur, pitch: Number(note.pitchMidi), dia: diatonic(note), measure: Number(note.measureOrdinal ?? note.measure),
      count, unit, beat: feltBeat(count, unit),
      mstart: finite(note.mstart) ? Number(note.mstart) : finite(note.beat) ? onset - (Number(note.beat) - 1) * 4 / unit : null});
  });
  const starts = new Map();
  for (const e of ev) if (e.mstart !== null && !starts.has(e.measure)) starts.set(e.measure, Math.min(starts.get(e.measure) ?? Infinity, e.mstart));
  for (const e of ev) {
    const s = starts.get(e.measure) ?? e.onset;
    const r = ((e.onset - s) % e.beat + e.beat) % e.beat;  // phase within the beat (raw bar start, as in musicomp)
    e.phase = k6(Math.abs(r - e.beat) < EPS ? 0 : r);
  }
  return ev;
}

class Heap {  // min-heap on [negGain, i, toks] (lexicographic, like Python heapq on tuples)
  constructor() { this.a = []; }
  static less(x, y) { return x[0] !== y[0] ? x[0] < y[0] : x[1] !== y[1] ? x[1] < y[1] : x[2] < y[2]; }
  push(v) { const a = this.a; a.push(v); let i = a.length - 1; while (i > 0) { const p = (i - 1) >> 1; if (!Heap.less(a[i], a[p])) break; [a[i], a[p]] = [a[p], a[i]]; i = p; } }
  pop() {
    const a = this.a, top = a[0], last = a.pop();
    if (a.length) { a[0] = last; let i = 0; for (;;) { const l = 2 * i + 1, r = l + 1; let m = i;
      if (l < a.length && Heap.less(a[l], a[m])) m = l; if (r < a.length && Heap.less(a[r], a[m])) m = r; if (m === i) break; [a[i], a[m]] = [a[m], a[i]]; i = m; } }
    return top;
  }
  get size() { return this.a.length; }
  peek() { return this.a[0]; }
}

export function transformTokens(proto, kind) {
  if (kind === 'inversion') return proto.map(([r, d]) => [r, -d]);
  const rev = [...proto].reverse();
  if (kind === 'retrograde') return rev.map(([r, d]) => [r, -d]);
  if (kind === 'retrograde_inversion') return rev.map(([r, d]) => [r, d]);
  if (kind === 'augmentation') return proto.map(([r, d]) => [k6(r * 2), d]);
  if (kind === 'diminution') return proto.map(([r, d]) => [k6(r / 2), d]);
  return null;
}

/**
 * Motif families: [{id, notes, gain, occurrences:[{first, last, startIndex, endIndex, start, end, variant}]}]
 * first/last index the attack list; startIndex/endIndex index the INPUT notes.
 */
export function discoverMotifs(notes, options = {}) {
  const p = {...MOTIF_DEFAULTS, ...options};
  const inputWarnings = [];
  const ev = attacks(Array.isArray(notes) ? notes : [], inputWarnings);
  const n = ev.length;
  const result = {version: VERSION, params: p, families: [], inputWarnings};
  if (n < 2 * p.minNotes || ev.some(e => e.dia === null)) return {...result, skipped: n < 2 * p.minNotes ? 'too few notes' : 'spelling/tpc missing'};
  let breath = options.breathStarts;
  if (!breath) {
    try {
      const byIndex = new Map(ev.map((e, k) => [e.index, k]));
      breath = new Set(analyzeBreathLayer(notes).starts.map(i => byIndex.get(i)).filter(k => k !== undefined));
    } catch { breath = new Set(); }
  }
  const tok = ev.slice(0, -1).map((e, k) => [k6(ev[k + 1].onset - e.onset), ev[k + 1].dia - e.dia]);
  const rhy = tok.map(t => t[0]);
  const ids = new Map(), T = new Int32Array(tok.length);
  tok.forEach((t, k) => { const key = `${t[0]}|${t[1]}`; if (!ids.has(key)) ids.set(key, ids.size); T[k] = ids.get(key); });
  const m = tok.length, cap = p.maxNotes, W = m + 1;
  const L = new Int16Array((m + 1) * W);  // L[i*W + j]
  for (let i = m - 1; i >= 0; i--) {
    for (let j = 0; j < m; j++) L[i * W + j] = T[i] === T[j] ? Math.min(L[(i + 1) * W + j + 1] + 1, cap) : 0;
  }
  for (let i = 0; i < m; i++) L[i * W + i] = 0;
  const bar = ev[0].count * 4 / ev[0].unit, maxSpan = p.maxBars * bar;
  const gaps = ev.map((e, k) => (k === n - 1 ? true : ev[k + 1].onset - e.end > EPS || e.end - e.onset >= e.beat - EPS));
  const covered = new Uint8Array(n);
  const anyCovered = (a, b) => { for (let k = a; k <= b; k++) if (covered[k]) return true; return false; };
  const occurrences = (i, toks) => {
    const js = [];
    for (let j = 0; j < m; j++) if (L[i * W + j] >= toks || j === i) js.push(j);
    const out = []; let lastEnd = -1;
    for (const j of js) {
      if (j <= lastEnd || ev[j].phase !== ev[i].phase || anyCovered(j, j + toks)) continue;
      out.push(j); lastEnd = j + toks;
    }
    return out;
  };
  const score = (toks, occ) => {
    let fit = 0;
    for (const j of occ) fit += ((breath.has(j) || ev[j].phase === 0) ? 1 : 0) + (gaps[j + toks] ? 1 : 0);
    fit /= 2 * occ.length;
    return (occ.length - 1) * (toks + 1) * (1 + p.wBound * fit);
  };
  const cands = [];
  for (let i = 0; i < m; i++) {
    let rowMax = 0, before = 0;
    for (let j = 0; j < m; j++) { const v = L[i * W + j]; if (v > rowMax) rowMax = v; }
    for (let j = 0; j < i; j++) { const v = L[j * W + i]; if (v > before) before = v; }
    if (rowMax < p.minNotes - 1) continue;
    const top = Math.min(rowMax, cap);
    for (let toks = p.minNotes - 1; toks <= top; toks++) {
      if (i + toks >= n || ev[i + toks].onset - ev[i].onset > maxSpan + EPS) break;
      if (before >= toks) continue;
      let cnt = 0, nxt = 0;
      for (let j = 0; j < m; j++) { const v = L[i * W + j]; if (v >= toks) cnt++; if (v >= toks + 1) nxt++; }
      if (toks === top || nxt < cnt || gaps[i + toks]) cands.push([i, toks]);
    }
  }
  const heap = new Heap();
  for (const [i, toks] of cands) { const occ = occurrences(i, toks); if (occ.length >= 2) heap.push([-score(toks, occ), i, toks]); }
  const fams = [];
  while (heap.size) {
    const [neg, i, toks] = heap.pop();
    if (-neg < p.minGain) break;
    const occ = occurrences(i, toks);
    if (occ.length < 2) continue;
    const g = score(toks, occ);
    if (heap.size && g < -heap.peek()[0] - 1e-9) { heap.push([-g, i, toks]); continue; }
    if (g < p.minGain) continue;
    const fam = {id: `M${fams.length + 1}`, notes: toks + 1, gain: Math.round(g * 100) / 100, occurrences: []};
    for (const j of occ) { fam.occurrences.push({first: j, last: j + toks, variant: null}); for (let k = j; k <= j + toks; k++) covered[k] = 1; }
    fams.push(fam);
  }
  for (const fam of fams) {
    const j0 = fam.occurrences[0].first, toks = fam.notes - 1, proto = tok.slice(j0, j0 + toks);
    for (const kind of p.variantKinds || []) {
      const want = transformTokens(proto, kind);
      if (!want || (kind === 'inversion' && want.every(([, d]) => d === 0))) continue;
      for (let j = 0; j <= m - toks; j++) {
        if (anyCovered(j, j + toks)) continue;
        let ok = true;
        for (let k = 0; k < toks && ok; k++) ok = tok[j + k][0] === want[k][0] && tok[j + k][1] === want[k][1];
        if (ok) { fam.occurrences.push({first: j, last: j + toks, variant: kind}); for (let k = j; k <= j + toks; k++) covered[k] = 1; }
      }
    }
    fam.occurrences.sort((a, b) => a.first - b.first);
  }
  for (const fam of fams) for (const o of fam.occurrences) Object.assign(o, {startIndex: ev[o.first].index, endIndex: ev[o.last].lastIndex, start: ev[o.first].onset, end: ev[o.last].end});
  return {...result, families: fams};
}

/**
 * Union the page's motif family links with discovery links.  spans: [{startIndex, endIndex, familyNumber, ...}]
 * (input-note indices, inclusive).  A span joins a discovery family when one occurrence covers >= half of the
 * span's time; two spans end in one family when either source links them.  Returns spans with
 * linkedFamily (a new consecutive number) and linkSources.
 */
export function linkMotifSpanFamilies(notes, spans, discovery) {
  const t0 = i => Number(notes[i].onset), t1 = i => Number(notes[i].onset) + Number(notes[i].durationRatio);
  const occs = (discovery?.families || []).flatMap(f => f.occurrences.map(o => ({fam: f.id, start: o.start, end: o.end})));
  const parent = spans.map((_, i) => i);
  const find = x => { while (parent[x] !== x) { parent[x] = parent[parent[x]]; x = parent[x]; } return x; };
  const groups = new Map(), sources = spans.map(() => new Set());
  spans.forEach((s, i) => {
    const a = t0(s.startIndex), b = t1(s.endIndex);
    const key = Number.isInteger(s.familyNumber) && s.familyNumber > 0 ? `page:${s.familyNumber}` : `unassigned:${i}`;
    groups.set(key, [...(groups.get(key) || []), i]);
    let best = null, bestCover = 0;
    for (const o of occs) {
      const inter = Math.min(b, o.end) - Math.max(a, o.start);
      const cover = b > a && inter > 0 ? inter / (b - a) : 0;
      if (cover > bestCover) { bestCover = cover; best = o; }
    }
    if (best && bestCover >= 0.5) { const k = `discovery:${best.fam}`; groups.set(k, [...(groups.get(k) || []), i]); sources[i].add('discovery'); }
  });
  for (const members of groups.values()) for (const i of members.slice(1)) parent[find(i)] = find(members[0]);
  const renumber = new Map();
  return spans.map((s, i) => {
    const root = find(i);
    if (!renumber.has(root)) renumber.set(root, renumber.size + 1);
    return {...s, linkedFamily: renumber.get(root), linkSources: ['page', ...sources[i]]};
  });
}
