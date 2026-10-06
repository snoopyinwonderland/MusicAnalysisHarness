// Recorded FluidR3_GM instrument samples (CC BY 3.0, Frank Wen).
// Attribution and the sparse MIDI-note manifest live in public/samples.
export type SampleInstrument = 'piano' | 'violin' | 'viola' | 'cello';
export type SampleBank = { midis: number[]; buffers: Map<number, AudioBuffer> };
export type SamplePlaybackStatus = 'disabled' | 'idle' | 'loading' | 'ready' | 'fallback';
type SampleManifest = Partial<Record<SampleInstrument, number[]>>;

let manifest: Promise<SampleManifest | null> | null = null;
const loading = new Map<SampleInstrument, Promise<SampleBank | null>>();
const ready = new Map<SampleInstrument, SampleBank>();
const incomplete = new Set<SampleInstrument>();
const failed = new Set<SampleInstrument>();
const LS_KEY = 'musicanote.sampledPlayback';
let memoryPreference = true;
let memoryPreferenceOverridesStorage = false;

/** Browser preference, default on; blocked storage still preserves the session choice. */
export function sampledPlaybackEnabled(): boolean {
  if (memoryPreferenceOverridesStorage) return memoryPreference;
  try { memoryPreference = localStorage.getItem(LS_KEY) !== 'off'; } catch { /* use session preference */ }
  return memoryPreference;
}

export function setSampledPlayback(on: boolean): void {
  memoryPreference = on;
  try {
    localStorage.setItem(LS_KEY, on ? 'on' : 'off');
    memoryPreferenceOverridesStorage = false;
  } catch {
    // Readable storage can still reject writes (quota/security); an old stored
    // choice must not override the user's newly selected in-memory preference.
    memoryPreferenceOverridesStorage = true;
  }
}

const sampleUrl = (path: string) => {
  const base = import.meta.env.BASE_URL || '/';
  return `${base.endsWith('/') ? base : `${base}/`}samples/${path}`;
};
const fetchSample = (path: string): Promise<Response> => {
  try { return fetch(sampleUrl(path)); }
  catch (error) { return Promise.reject(error); }
};

function readManifest(value: unknown): SampleManifest | null {
  if (!value || typeof value !== 'object' || !('instruments' in value)) return null;
  const instruments = value.instruments;
  if (!instruments || typeof instruments !== 'object') return null;
  const parsed: SampleManifest = {};
  for (const instrument of ['piano', 'violin', 'viola', 'cello'] as const) {
    const notes = (instruments as Record<string, unknown>)[instrument];
    if (!Array.isArray(notes)) continue;
    const midis = [...new Set(notes.filter((m): m is number =>
      typeof m === 'number' && Number.isInteger(m) && m >= 0 && m <= 127))].sort((a, b) => a - b);
    if (midis.length) parsed[instrument] = midis;
  }
  return Object.keys(parsed).length ? parsed : null;
}

function loadManifest(): Promise<SampleManifest | null> {
  if (!manifest) {
    const pending = fetchSample('manifest.json')
      .then(response => response.ok ? response.json() : null)
      .then(readManifest)
      .catch(() => null)
      .then(value => {
        // Do not permanently cache an outage, malformed JSON, or an empty manifest.
        if (!value && manifest === pending) manifest = null;
        return value;
      });
    manifest = pending;
  }
  return manifest;
}

/** Explicit, deduplicated preload. Never resumes the context or delays a scheduled phrase.
 * A failed/empty bank is removed from the in-flight cache so a later interaction can retry.
 */
export function preloadSamples(context: BaseAudioContext, instrument: SampleInstrument = 'piano'): Promise<SampleBank | null> {
  if (!sampledPlaybackEnabled()) return Promise.resolve(null);
  const existing = loading.get(instrument);
  if (existing) return existing;
  const bank = ready.get(instrument);
  if (bank && !incomplete.has(instrument)) return Promise.resolve(bank);
  const manifestPending = loadManifest();
  const pending = manifestPending.then(async man => {
    if (!sampledPlaybackEnabled()) return null;
    const midis = man?.[instrument];
    if (!midis?.length) {
      // A later explicit preload may see an updated manifest with this bank restored.
      if (manifest === manifestPending) manifest = null;
      return null;
    }
    const buffers = new Map<number, AudioBuffer>(ready.get(instrument)?.buffers);
    // Explicit later preloads repair a partial bank without re-fetching its good notes.
    await Promise.all(midis.filter(midi => !buffers.has(midi)).map(async midi => {
      try {
        const response = await fetchSample(`${instrument}/${midi}.mp3`);
        if (!response.ok) return;
        const buffer = await context.decodeAudioData(await response.arrayBuffer());
        if (Number.isFinite(buffer.duration) && buffer.duration > 0) buffers.set(midi, buffer);
      } catch { /* The original oscillator covers missing or undecodable notes. */ }
    }));
    if (midis.some(midi => !buffers.has(midi))) incomplete.add(instrument);
    else incomplete.delete(instrument);
    if (!buffers.size) return null;
    const loaded = { midis: [...buffers.keys()].sort((a, b) => a - b), buffers };
    ready.set(instrument, loaded);
    return loaded;
  }).catch(() => null).then(bank => {
    if (bank) failed.delete(instrument);
    else failed.add(instrument);
    return bank;
  }).finally(() => {
    if (loading.get(instrument) === pending) loading.delete(instrument);
  });
  loading.set(instrument, pending);
  return pending;
}

export function sampleBank(instrument: SampleInstrument): SampleBank | undefined {
  return sampledPlaybackEnabled() ? ready.get(instrument) : undefined;
}

export function samplePlaybackStatus(instrument: SampleInstrument = 'piano'): SamplePlaybackStatus {
  if (!sampledPlaybackEnabled()) return 'disabled';
  if (loading.has(instrument)) return 'loading';
  if (ready.has(instrument)) return 'ready';
  return failed.has(instrument) ? 'fallback' : 'idle';
}

/** English/Korean names and common score abbreviations. MIDI fallback is MusicXML's
 * 1-based GM program (41 violin, 42 viola, 43 cello), NOT the 0-based MIDI wire value.
 */
export function instrumentForPart(name: string | undefined | null, midiProgram?: number | null): SampleInstrument {
  const n = (name || '').normalize('NFKC').toLowerCase();
  if (/viola|비올라|\bvla(?=\b|\d)/.test(n)) return 'viola';
  if (/violoncello|cello|첼로|\b(?:vc|vcl)(?=\b|\d)/.test(n)) return 'cello';
  if (/violin|바이올린|\b(?:vln|vl)(?=\b|\d)/.test(n)) return 'violin';
  if (/piano|피아노|\b(?:pno|pf)(?=\b|\d)/.test(n)) return 'piano';
  return midiProgram === 41 ? 'violin' : midiProgram === 42 ? 'viola' : midiProgram === 43 ? 'cello' : 'piano';
}

// Conservative peak gains, close to the legacy oscillator's 0.06 rather than the
// reference engine's 0.3–0.5. Every note starts at silence, including the first note.
const LEVEL: Record<SampleInstrument, number> = { piano: .06, violin: .05, viola: .05, cello: .055 };

/** Returns null when a note cannot safely use the sparse sample bank. */
export function playSample(context: AudioContext, out: AudioNode, bank: SampleBank, instrument: SampleInstrument,
  midi: number, at: number, seconds: number): (() => void) | null {
  if (!bank.midis.length || !Number.isFinite(midi) || !Number.isFinite(at) || !Number.isFinite(seconds) || seconds <= 0) return null;
  if (midi < bank.midis[0] || midi > bank.midis[bank.midis.length - 1]) return null;
  const base = bank.midis.reduce((best, note) => Math.abs(note - midi) < Math.abs(best - midi) ? note : best);
  // A lost sparse-bank sample must not cause a large pitch shift of its neighbours.
  if (Math.abs(base - midi) > 1) return null;
  const buffer = bank.buffers.get(base);
  if (!buffer || !Number.isFinite(buffer.duration) || buffer.duration <= 0) return null;
  const source = context.createBufferSource(), gain = context.createGain();
  source.buffer = buffer;
  const rate = 2 ** ((midi - base) / 12);
  source.playbackRate.value = rate;
  if (instrument !== 'piano' && seconds > buffer.duration / rate * .8) {
    source.loop = true;
    // Loop points are in the unpitched buffer's seconds; the threshold is wall time.
    source.loopStart = buffer.duration * .35;
    source.loopEnd = buffer.duration * .85;
  }
  const attackSeconds = Math.min(instrument === 'piano' ? .006 : .03, seconds / 3);
  const end = at + seconds, fadeSeconds = Math.min(instrument === 'piano' ? .025 : .04, seconds / 3);
  gain.gain.value = 0;
  gain.gain.setValueAtTime(0, at);
  gain.gain.linearRampToValueAtTime(LEVEL[instrument], at + attackSeconds);
  gain.gain.setValueAtTime(LEVEL[instrument], Math.max(at + attackSeconds, end - fadeSeconds));
  gain.gain.linearRampToValueAtTime(0, end);
  source.connect(gain).connect(out);
  let cleaned = false, stopped = false;
  const cleanup = () => {
    if (cleaned) return;
    cleaned = true;
    source.disconnect();
    gain.disconnect();
  };
  source.onended = cleanup;
  source.start(at);
  source.stop(end);
  return () => {
    if (stopped) return;
    stopped = true;
    const now = context.currentTime;
    gain.gain.cancelScheduledValues(now);
    gain.gain.setValueAtTime(0, now);
    try { source.stop(now); } catch { /* already ended */ }
    cleanup(); // Also disconnect future, not-yet-started notes immediately.
  };
}
