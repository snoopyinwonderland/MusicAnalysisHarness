// Two-layer phrase segmentation, ported from musicomp analysis/phrase.py (segment_layers).
//
//   lower layer  breath units: rest, lengthening, start alignment + 2-bar length prior (LOW_DEFAULT)
//   upper layer  phrases: ends chosen ONLY among lower-layer ends and cadence points, with rest,
//                lengthening, leap, metric arrival, closural degree, repetition start and cadence
//                cues + 4/8-bar length prior (HIGH_DEFAULT)
//
// Validation (musicomp DEVELOPMENT_LOG #15-#17), boundary F1 within one beat:
//   lower: Bach chorales 0.30 -> 0.77 (2-fold CV), Essen/MTC folk songs 0.33 -> 0.73 (no retuning)
//   upper: DCML expert phrases, cross-validated +0.016..+0.04 over the single-layer model when chords
//          are available.  Cadences come from the caller (here: boundary-harmony.mjs on the other
//          voices), never from this segmentation (no circular evidence).
//
// Additive module: analyzePhraseBoundaries() is unchanged.
// Input notes: {pitchMidi, onset, durationRatio (quarters), measureOrdinal|measure, meterCount, meterUnit,
//               mstart? (measure start, quarters) | beat? (1 = downbeat, metre units), spelling?|tpc?,
//               isAttack?, tieStop?}
const VERSION = 'phrase-layers-v1.1 (musicomp LOW/HIGH_DEFAULT 2026-10-04)';
export const BREATH_WEIGHTS = Object.freeze({rest: 2.0, lengthening: 1.5, startAlignment: 0.6, strength: 1.6,
  segPenalty: 0.0, priorScale: 1.0, candMin: 0.6});
export const PHRASE_WEIGHTS = Object.freeze({rest: 1.4, lengthening: 1.0, leap: 0.3, metricArrival: 0.4, closure: 0.6,
  repetitionStart: 0.8, cadence: 0.75, strength: 1.6, segPenalty: 3.0, priorScale: 0.5});
// log-scale length priors in bars
export const BREATH_PRIOR = Object.freeze({1: -2.5, 2: 0.0, 3: -1.0, 4: -0.6, 5: -2.2, 6: -2.2, 7: -3.0, 8: -2.8});
export const PHRASE_PRIOR = Object.freeze({1: -6.0, 2: -3.0, 3: -3.2, 4: 0.0, 5: -2.0, 6: -1.8, 7: -2.2, 8: -0.6});
export const CADENCE_VALUE = Object.freeze({PAC: 1.0, IAC: 1.0, HC: 0.5});  // Caplin: authentic / half
const PIECE_END = 2.5, MAX_BARS = 16, EPS = 1e-6;
const finite = v => v !== null && v !== undefined && v !== '' && Number.isFinite(Number(v));
const r3 = v => Math.round(v * 1000) / 1000;
const key6 = v => Math.round(v * 1e6) / 1e6;
const round6 = key6;
const priorOf = (table, bars) => table[bars] ?? (-3.0 - 0.25 * Math.abs(bars - 8));
const median = xs => {
  const s = [...xs].sort((a, b) => a - b), n = s.length;
  return n ? (n % 2 ? s[(n - 1) / 2] : (s[n / 2 - 1] + s[n / 2]) / 2) : null;
};
const feltBeat = (count, unit) => (unit === 8 && count % 3 === 0 && count > 3 ? 1.5 : 4 / unit);
const STEP_PC = [0, 2, 4, 5, 7, 9, 11];

/** Diatonic step number (octave*7 + letter) from a spelling ('Eb4') or a line-of-fifths tpc + MIDI. */
function diatonicNumber(note, midi) {
  const m = /^([A-Ga-g])([#b\-x]*)(-?\d+)$/.exec(String(note?.spelling ?? ''));
  if (m) return Number(m[3]) * 7 + 'CDEFGAB'.indexOf(m[1].toUpperCase());
  if (finite(note?.tpc)) {
    const t = Number(note.tpc) + 1, step = 'CDEFGAB'.indexOf('FCGDAEB'[((t % 7) + 7) % 7]), alter = Math.floor(t / 7);
    return Math.floor((midi - alter - STEP_PC[step]) / 12) * 7 + step;
  }
  return null;
}

/** Attack events (ties merged), metric positions and the bar grid. */
function meterOf(note) {
  // per-measure metre string ('3/4', as indexed per measure) wins over a work-level meterCount/meterUnit
  const m = /^(\d+)\/(\d+)$/.exec(String(note?.meter ?? ''));
  return m ? [Number(m[1]), Number(m[2])] : [Number(note.meterCount), Number(note.meterUnit)];
}

function prepare(notes, warnings) {
  const events = [];
  notes.forEach((note, index) => {
    const onset = Number(note?.onset), dur = Number(note?.durationRatio);
    if (!finite(note?.onset) || !finite(note?.durationRatio)) throw new Error(`note ${index}: onset/durationRatio required`);
    if (dur < 0) throw new Error(`note ${index}: negative duration`);
    if (note.isAttack === false || note.tieStop) {
      // a tie tail extends the previous attack ONLY if it is the same pitch (and voice, when given) and
      // starts where that attack ends; anything else is read as a new attack and reported
      const last = events.at(-1), pitch = Number(note.pitchMidi);
      const samePitch = last && (!finite(note.pitchMidi) || pitch === last.pitch);
      const sameVoice = last && (note.voice === undefined || last.voice === undefined || String(note.voice) === String(last.voice));
      const contiguous = last && Math.abs(onset - last.end) <= 1e-6;
      if (samePitch && sameVoice && contiguous) { last.end = Math.max(last.end, onset + dur); return; }
      warnings.push({index, issue: 'tie-tail-not-continuous', reason: !last ? 'no preceding attack' : !samePitch ? 'pitch differs'
        : !sameVoice ? 'voice differs' : `gap ${round6(onset - last.end)} quarters`});
    }
    const [count, unit] = meterOf(note);
    const pitch = Number(note.pitchMidi);
    events.push({index, onset, end: onset + dur, pitch, voice: note.voice, dia: diatonicNumber(note, pitch),
      measure: Number(note.measureOrdinal ?? note.measure), count, unit, nominal: count * 4 / unit, beat: feltBeat(count, unit),
      mstart: finite(note.mstart) ? Number(note.mstart)
        : finite(note.beat) ? onset - (Number(note.beat) - 1) * 4 / unit : null});  // MusicXML beat in metre units
  });
  if (events.some(e => !Number.isFinite(e.count) || !Number.isFinite(e.unit) || !Number.isFinite(e.measure))) {
    throw new Error('meterCount, meterUnit and measureOrdinal are required');
  }
  const starts = new Map();
  for (const e of events) if (e.mstart !== null && !starts.has(e.measure)) starts.set(e.measure, e.mstart);
  const first = Math.min(...events.map(e => e.measure)), last = Math.max(...events.map(e => e.measure));
  const nominal = events[0].nominal;
  // bar grid over every ordinal (empty rest bars included); a short first bar is an anacrusis
  const bars = [];
  for (let m = first; m <= last; m++) {
    const start = starts.has(m) ? starts.get(m) : bars.length ? bars.at(-1).start + bars.at(-1).nominal
      : Math.min(...events.filter(e => e.measure === m).map(e => e.onset));
    bars.push({start, nominal: events.find(e => e.measure === m)?.nominal ?? nominal});
  }
  const total = Math.max(...events.map(e => e.end));
  bars.forEach((b, k) => { b.end = k + 1 < bars.length ? bars[k + 1].start : Math.max(total, b.start + b.nominal); });
  const pickupShift = bars.length > 1 && bars[0].end - bars[0].start < bars[0].nominal - EPS ? bars[0].nominal - (bars[0].end - bars[0].start) : 0;
  for (const e of events) {
    e.bar = e.measure - first;
    const b = bars[e.bar];
    e.pos = e.mstart !== null || starts.has(e.measure) ? e.onset - b.start + (e.bar === 0 ? pickupShift : 0) : null;
    e.downbeat = e.pos !== null && Math.abs(e.pos) < EPS;
  }
  return {events, bars};
}

function metricWeight(e) {
  if (e.pos === null) return 0;
  if (e.downbeat) return 1.0;
  const unit = e.beat, n = Math.round(e.nominal / unit), q = e.pos / unit;
  if (Math.abs(q - Math.round(q)) < EPS) {
    const b = Math.round(q);
    if ((n === 4 && b === 2) || ((n === 6 || n === 4) && b === n / 2)) return 0.75;
    return 0.5;
  }
  const h = e.pos / (unit / 2);
  if (Math.abs(h - Math.round(h)) < EPS || (unit === 1.5 && Math.abs(e.pos * 2 - Math.round(e.pos * 2)) < EPS)) return 0.25;
  return 0.1;
}

function startAlignment(e) {
  if (e.pos === null) return 0;
  if (e.downbeat) return 1;
  const toNext = e.nominal - e.pos;
  return toNext > EPS && toNext < e.nominal && toNext <= e.beat + EPS ? 0.6 : 0;
}

function closure(key, prevPitch, pitch) {
  if (!key || !finite(key.tonicPc)) return 0;
  const deg = (((pitch - key.tonicPc) % 12) + 12) % 12, step = Math.abs(pitch - prevPitch) <= 2;
  if (deg === 0) return step ? 1.0 : 0.7;
  if ((key.minor ? [3, 7] : [4, 7]).includes(deg)) return step ? 0.6 : 0.4;
  if ([2, 11, 10].includes(deg)) return 0.35;
  return 0;
}

// ---- repetition starts: 2-bar units that restate an earlier 2-bar unit (musicomp motif.py) -------------
function units(events, bars) {
  const out = [];
  for (let i = 0; i + 1 < bars.length; i++) {
    const start = bars[i].start, end = bars[i + 1].end;
    const notes = events.filter(e => start <= e.onset + EPS && e.onset < end - EPS);
    out.push({bar: i, start, end, notes,
      onsets: new Set(notes.map(n => key6(n.onset - start))),
      rhythm: notes.map(n => `${key6(n.onset - start)}:${key6(Math.min(n.end, end) - n.onset)}`).join('|')});
  }
  return out;
}

function compare(a, b) {
  if (!a.notes.length || !b.notes.length) return 0;
  const inter = [...a.onsets].filter(x => b.onsets.has(x)).length, union = new Set([...a.onsets, ...b.onsets]).size;
  const rj = inter / union;
  if (a.rhythm === b.rhythm || (rj === 1 && a.notes.length === b.notes.length)) {
    const n = Math.min(a.notes.length, b.notes.length), pairs = [...Array(n).keys()];
    const semis = new Set(pairs.map(k => b.notes[k].pitch - a.notes[k].pitch));
    if (semis.size === 1) return semis.has(0) ? 1.0 : 0.95;
    if (pairs.every(k => a.notes[k].dia !== null && b.notes[k].dia !== null)
        && new Set(pairs.map(k => b.notes[k].dia - a.notes[k].dia)).size === 1) return 0.92;
    const sign = x => (x > 0) - (x < 0);
    const ca = a.notes.slice(1).map((x, k) => sign(x.pitch - a.notes[k].pitch));
    const cb = b.notes.slice(1).map((x, k) => sign(x.pitch - b.notes[k].pitch));
    if (ca.length === cb.length && ca.every((x, k) => x === cb[k])) return 0.8;
    const m = Math.min(ca.length, cb.length);
    let agree = 0;
    for (let k = 0; k < m; k++) agree += ca[k] === cb[k];
    return 0.55 + 0.2 * agree / Math.max(1, ca.length);
  }
  const pa = new Set(a.notes.map(n => ((n.pitch % 12) + 12) % 12)), pb = new Set(b.notes.map(n => ((n.pitch % 12) + 12) % 12));
  const pj = [...pa].filter(x => pb.has(x)).length / new Set([...pa, ...pb]).size;
  return 0.55 * rj + 0.3 * pj + 0.15 * (1 - Math.abs(a.notes.length - b.notes.length) / Math.max(a.notes.length, b.notes.length));
}

export function repetitionStarts(events, bars) {
  const us = units(events, bars), rel = [];
  us.forEach((u, k) => {
    let best = {model: null, score: 0};
    if (u.notes.length) {
      for (let j = 0; j < k; j++) {
        if (us[j].bar + 2 > u.bar) continue;  // overlapping pair units are not independent statements
        const s = compare(us[j], u);
        if (s > best.score) best = {model: us[j].bar, score: s};
      }
    }
    if (best.score < 0.7) best = {model: null, score: best.score};
    rel.push(best);
  });
  const out = new Set();
  rel.forEach((r, k) => {
    if (r.model !== null && r.score >= 0.8 && k - r.model >= 2) {
      const prev = k > 0 ? rel[k - 1] : null;
      if (!(prev && prev.model !== null && prev.score >= 0.8 && prev.model === r.model - 1)) out.add(k);
    }
  });
  return out;
}

// ---- cues --------------------------------------------------------------------------------------------
function gapCues(events, bars, key) {
  const iois = events.slice(1).map((e, i) => e.onset - events[i].onset);
  const reps = repetitionStarts(events, bars);
  return events.slice(0, -1).map((a, i) => {
    const b = events[i + 1], beat = a.beat;
    const med = median(iois.slice(Math.max(0, i - 6), i + 7));
    const ioi = iois[i], rest = b.onset - a.end;
    const nextDown = events.slice(i + 1, i + 6).find(e => e.downbeat);
    return {
      rest: rest > EPS ? r3(Math.min(1, rest / beat)) : 0,
      lengthening: med > 0 && ioi > 0 ? r3(Math.max(0, Math.min(1, Math.log2(ioi / med) / 2))) : 0,
      leap: r3(Math.min(1, Math.max(0, Math.abs(b.pitch - a.pitch) - 4) / 8)),
      metricArrival: ioi >= beat - EPS ? metricWeight(a) : 0,
      closure: ioi >= beat - EPS ? closure(key, i ? events[i - 1].pitch : a.pitch, a.pitch) : 0,
      repetitionStart: nextDown && reps.has(nextDown.bar) && (nextDown.bar === b.bar || nextDown.bar === b.bar + 1) ? 1 : 0,
      startAlignment: startAlignment(b),
    };
  });
}

/** DP over allowed unit ends (same recurrence and tie-breaking as musicomp _segment). */
function segment(events, strength, ends, w, prior) {
  const n = events.length;
  const nextDown = new Array(n + 1).fill(n);
  for (let i = n - 1; i >= 0; i--) nextDown[i] = events[i].downbeat ? i : nextDown[i + 1];
  const span = (first, last) => {
    let fb = events[first].bar;
    if (nextDown[first] !== first && nextDown[first] <= last && events[nextDown[first]].bar === fb + 1) fb += 1;
    return Math.max(fb, events[last].bar) - fb + 1;
  };
  const s = new Map(strength);
  s.set(n - 1, PIECE_END);
  const all = [...ends.filter(j => j < n - 1).sort((a, b) => a - b), n - 1];
  const best = new Map([[-1, [0, null]]]);
  const order = [-1, ...all];
  all.forEach((j, jj) => {
    let top = null;
    const consider = (score, i) => { if (!top || score > top[0] || (score === top[0] && i > top[1])) top = [score, i]; };
    for (let k = jj; k >= 0; k--) {
      const i = order[k], bars = span(i + 1, j);
      if (bars > MAX_BARS) break;
      consider(best.get(i)[0] + w.strength * s.get(j) + w.priorScale * priorOf(prior, bars) - w.segPenalty, i);
    }
    if (!top) {
      const i = order[jj];
      consider(best.get(i)[0] + w.strength * s.get(j) + w.priorScale * priorOf(prior, span(i + 1, j)) - w.segPenalty - 5, i);
    }
    best.set(j, top);
  });
  const bounds = [];
  for (let j = n - 1; j !== -1; j = best.get(j)[1]) bounds.push(j);
  return bounds.reverse();
}

const weigh = (c, w, cad = 0) => (w.rest ?? 0) * c.rest + (w.lengthening ?? 0) * c.lengthening + (w.leap ?? 0) * c.leap
  + (w.metricArrival ?? 0) * c.metricArrival + (w.closure ?? 0) * c.closure + (w.repetitionStart ?? 0) * c.repetitionStart
  + (w.startAlignment ?? 0) * c.startAlignment + (w.cadence ?? 0) * cad;

/** Lower layer only (melody-only). */
export function analyzeBreathLayer(notes) {
  const res = analyzePhraseLayers(notes, {upper: false});
  return {version: res.version, layer: 'breath', label: 'melodic breath units (lower phrase layer); not cadence-defined phrases',
    starts: res.breath.starts, boundaries: res.breath.boundaries};
}

/**
 * Both layers.
 * options.key      {tonicPc, minor} for the closural-degree cue (upper layer)
 * options.cadenceAt(noteIndices) -> Map(noteIndex -> {type, strength}) : cadence evidence at candidate
 *                  phrase starts (the cadence closes the note before).  Supplied by the caller from the
 *                  harmony of the OTHER voices; omitted -> melody-only upper layer.
 * options.cadenceMinStrength  contract for the (uncalibrated) strength: a cadence counts only when
 *                  strength >= this value (default 0.58 = boundary-harmony's own selection gate); weaker or
 *                  strength-less hypotheses stay unresolved and never act as closure evidence.  Strength is
 *                  a gate, not a probability: accepted cadences contribute by type (authentic 1.0, half 0.5).
 *
 * Result: upper-layer ends are chosen among breath-unit ends AND accepted cadence points, so a phrase end
 * is not necessarily a breath end (breathEnd flag).  inputWarnings lists tie tails that were not
 * continuous (read as new attacks).
 */
export function analyzePhraseLayers(notes, {key = null, cadenceAt = null, upper = true, cadenceMinStrength = 0.58} = {}) {
  const empty = {version: VERSION, breath: {starts: [], boundaries: []}, phrases: {starts: [], boundaries: []}, inputWarnings: []};
  if (!Array.isArray(notes) || notes.length < 2) return empty;
  const inputWarnings = [];
  const {events, bars} = prepare(notes, inputWarnings);
  if (events.length < 2) return empty;
  const cues = gapCues(events, bars, key);
  // lower layer
  const lowStrength = cues.map(c => weigh(c, BREATH_WEIGHTS));
  const lowEnds = segment(events, lowStrength.map((s, i) => [i, s]), lowStrength.flatMap((s, i) => (s >= BREATH_WEIGHTS.candMin ? [i] : [])),
    BREATH_WEIGHTS, BREATH_PRIOR).slice(0, -1);
  const mk = (k, strength, extra = {}) => ({index: events[k + 1].index, strength: r3(strength), cues: cues[k], ...extra});
  const breath = {starts: lowEnds.map(k => events[k + 1].index), boundaries: lowEnds.map(k => mk(k, lowStrength[k]))};
  if (!upper) return {version: VERSION, breath, phrases: null, inputWarnings};
  // cadence evidence: only where a cadence can close (arrival note >= a beat, or followed by a rest)
  const cad = new Map();
  let unresolvedCadences = 0;
  if (cadenceAt) {
    const closable = cues.flatMap((c, i) => (events[i].end - events[i].onset >= events[i].beat - EPS || c.rest > 0 ? [i] : []));
    const found = cadenceAt(closable.map(i => events[i + 1].index));
    const byIndex = new Map(events.map((e, k) => [e.index, k]));
    for (const [noteIndex, c] of found || []) {
      const v = CADENCE_VALUE[c?.type] ?? 0, k = byIndex.get(noteIndex);
      if (!(v > 0 && k > 0)) continue;
      if (!finite(c.strength) || Number(c.strength) < cadenceMinStrength) { unresolvedCadences++; continue; }
      cad.set(k - 1, {value: v, type: c.type, strength: Number(c.strength)});
    }
  }
  const hiStrength = cues.map((c, i) => weigh(c, PHRASE_WEIGHTS, cad.get(i)?.value ?? 0));
  const allowed = new Set([...lowEnds, ...[...cad].filter(([, c]) => c.value >= 0.5).map(([i]) => i)]);
  const hiEnds = segment(events, hiStrength.map((s, i) => [i, s]), [...allowed], PHRASE_WEIGHTS, PHRASE_PRIOR).slice(0, -1);
  const phrases = {starts: hiEnds.map(k => events[k + 1].index),
    boundaries: hiEnds.map(k => mk(k, hiStrength[k], {cadence: cad.get(k) ? {type: cad.get(k).type, strength: cad.get(k).strength} : null,
      breathEnd: lowEnds.includes(k)}))};
  return {version: VERSION, label: 'two-layer phrase segmentation (phrase ends at breath ends or accepted cadences)', breath, phrases,
    cadenceSource: cadenceAt ? 'caller (other-voice harmony)' : 'none (melody only)', cadenceMinStrength, unresolvedCadences, key,
    inputWarnings};
}
