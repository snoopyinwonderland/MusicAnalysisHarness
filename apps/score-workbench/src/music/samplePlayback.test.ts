import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

class FakeParam {
  value = 1;
  setValueAtTime = vi.fn();
  linearRampToValueAtTime = vi.fn();
  cancelScheduledValues = vi.fn();
}
class FakeNode {
  connect = vi.fn((out: FakeNode) => out);
  disconnect = vi.fn();
}
class FakeGain extends FakeNode { gain = new FakeParam(); }
class FakeSource extends FakeNode {
  buffer: AudioBuffer | null = null;
  playbackRate = new FakeParam();
  loop = false;
  loopStart = 0;
  loopEnd = 0;
  start = vi.fn();
  stop = vi.fn();
  onended: (() => void) | null = null;
}
class FakeContext {
  currentTime = 4;
  destination = new FakeNode();
  sources: FakeSource[] = [];
  gains: FakeGain[] = [];
  decodeAudioData = vi.fn(async () => ({ duration: 2 }) as AudioBuffer);
  createBufferSource() { const node = new FakeSource(); this.sources.push(node); return node; }
  createGain() { const node = new FakeGain(); this.gains.push(node); return node; }
}
let samples: typeof import('./samplePlayback');
let context: FakeContext;
let fetchMock: ReturnType<typeof vi.fn>;
const audioContext = () => context as unknown as AudioContext;
const response = (instruments: unknown = { piano: [60, 63], violin: [60, 63] }) => ({ ok: true, json: async () => ({ instruments }) });

beforeEach(async () => {
  vi.resetModules();
  const stored = new Map<string, string>();
  vi.stubGlobal('localStorage', { getItem: (key: string) => stored.get(key) ?? null, setItem: (key: string, value: string) => stored.set(key, value) });
  fetchMock = vi.fn(async (url: string) => url.endsWith('manifest.json') ? response() : { ok: true, arrayBuffer: async () => new ArrayBuffer(4) });
  vi.stubGlobal('fetch', fetchMock);
  context = new FakeContext();
  samples = await import('./samplePlayback');
});
afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs(); });

describe('instrument identification', () => {
  it.each([
    ['Violin I', 'violin'], ['바이올린', 'violin'], ['Vln. II', 'violin'], ['Vln1', 'violin'], ['Vl. 1', 'violin'],
    ['Viola', 'viola'], ['비올라', 'viola'], ['Vla.', 'viola'], ['Vla2', 'viola'],
    ['Violoncello', 'cello'], ['Cello', 'cello'], ['첼로', 'cello'], ['Vc.', 'cello'], ['Vc1', 'cello'],
    ['Piano, S1', 'piano'], ['피아노', 'piano'], ['Pno.', 'piano'], ['Pf.', 'piano'],
    ['Flute', 'piano'], ['Percussion vocal', 'piano'], ['', 'piano'],
  ] as const)('maps %s to %s', (name, instrument) => { expect(samples.instrumentForPart(name)).toBe(instrument); });

  it('accepts joined header names and only uses 1-based GM when names are unrecognized', () => {
    expect(samples.instrumentForPart('Strings · Vln. I')).toBe('violin');
    expect(samples.instrumentForPart(undefined, 41)).toBe('violin');
    expect(samples.instrumentForPart(null, 42)).toBe('viola');
    expect(samples.instrumentForPart('Strings', 43)).toBe('cello');
    expect(samples.instrumentForPart('Pno.', 41)).toBe('piano');
    expect(samples.instrumentForPart('Vc.', 41)).toBe('cello');
    expect(samples.instrumentForPart(undefined, 40)).toBe('piano');
    expect(samples.instrumentForPart(undefined)).toBe('piano');
  });
});

describe('sample preloading and preference', () => {
  it('deduplicates concurrent bank and manifest requests, then reuses decoded banks', async () => {
    let resolveManifest!: (value: unknown) => void;
    fetchMock.mockImplementationOnce(() => new Promise(resolve => { resolveManifest = resolve; }));
    expect(samples.samplePlaybackStatus()).toBe('idle');
    const first = samples.preloadSamples(audioContext());
    const same = samples.preloadSamples(audioContext());
    const violin = samples.preloadSamples(audioContext(), 'violin');
    expect(first).toBe(same);
    expect(fetchMock).toHaveBeenCalledOnce();
    expect(samples.samplePlaybackStatus()).toBe('loading');
    resolveManifest(response());
    const [pianoBank, violinBank] = await Promise.all([first, violin]);
    expect(pianoBank?.midis).toEqual([60, 63]);
    expect(violinBank?.midis).toEqual([60, 63]);
    expect(fetchMock).toHaveBeenCalledTimes(5);
    expect(context.decodeAudioData).toHaveBeenCalledTimes(4);
    expect(samples.samplePlaybackStatus()).toBe('ready');
    expect(await samples.preloadSamples(audioContext())).toBe(pianoBank);
    expect(fetchMock).toHaveBeenCalledTimes(5);
  });

  it.each(['http', 'network', 'empty', 'malformed'] as const)('retries a failed %s manifest on a later explicit preload only', async failure => {
    if (failure === 'http') fetchMock.mockResolvedValueOnce({ ok: false });
    if (failure === 'network') fetchMock.mockRejectedValueOnce(new Error('offline'));
    if (failure === 'empty') fetchMock.mockResolvedValueOnce(response({ piano: [] }));
    if (failure === 'malformed') fetchMock.mockResolvedValueOnce({ ok: true, json: async () => { throw new Error('invalid JSON'); } });
    expect(await samples.preloadSamples(audioContext())).toBeNull();
    expect(samples.samplePlaybackStatus()).toBe('fallback');
    expect(fetchMock).toHaveBeenCalledOnce();
    await Promise.resolve(); await Promise.resolve();
    expect(fetchMock).toHaveBeenCalledOnce(); // no retry loop
    expect(await samples.preloadSamples(audioContext())).not.toBeNull();
    expect(fetchMock).toHaveBeenCalledTimes(4);
    expect(samples.samplePlaybackStatus()).toBe('ready');
  });

  it('converts synchronous fetch setup errors into retryable fallback', async () => {
    fetchMock.mockImplementationOnce(() => { throw new Error('fetch setup failed'); });
    await expect(samples.preloadSamples(audioContext())).resolves.toBeNull();
    expect(samples.samplePlaybackStatus()).toBe('fallback');
    await expect(samples.preloadSamples(audioContext())).resolves.not.toBeNull();
    expect(fetchMock).toHaveBeenCalledTimes(4);
  });

  it('retries an empty bank without redownloading a valid manifest and does not decode HTTP errors', async () => {
    let missing = true;
    fetchMock.mockImplementation(async (url: string) => url.endsWith('manifest.json') ? response({ piano: [60] })
      : missing ? { ok: false, arrayBuffer: vi.fn() } : { ok: true, arrayBuffer: async () => new ArrayBuffer(4) });
    expect(await samples.preloadSamples(audioContext())).toBeNull();
    expect(context.decodeAudioData).not.toHaveBeenCalled();
    expect(fetchMock).toHaveBeenCalledTimes(2);
    missing = false;
    expect(await samples.preloadSamples(audioContext())).not.toBeNull();
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(context.decodeAudioData).toHaveBeenCalledOnce();
  });

  it('retries decode failure and invalid-duration banks, and sanitizes manifest notes', async () => {
    fetchMock.mockImplementation(async (url: string) => url.endsWith('manifest.json') ? response({ piano: [60, 60, '63', -1, 200, 1.5] })
      : { ok: true, arrayBuffer: async () => new ArrayBuffer(4) });
    context.decodeAudioData.mockRejectedValueOnce(new Error('cannot decode'));
    expect(await samples.preloadSamples(audioContext())).toBeNull();
    context.decodeAudioData.mockResolvedValueOnce({ duration: Number.NaN } as AudioBuffer);
    expect(await samples.preloadSamples(audioContext())).toBeNull();
    expect((await samples.preloadSamples(audioContext()))?.midis).toEqual([60]);
    expect(fetchMock).toHaveBeenCalledTimes(4);
  });

  it('refetches a manifest missing the requested instrument on explicit retry', async () => {
    fetchMock.mockResolvedValueOnce(response({ violin: [60] }));
    expect(await samples.preloadSamples(audioContext())).toBeNull();
    expect(await samples.preloadSamples(audioContext())).not.toBeNull();
    expect(fetchMock).toHaveBeenCalledTimes(4);
  });

  it('repairs partial banks only on an explicit preload and reuses already decoded notes', async () => {
    let missing = true;
    fetchMock.mockImplementation(async (url: string) => url.endsWith('manifest.json') ? response({ piano: [60, 63] })
      : missing && url.endsWith('/63.mp3') ? { ok: false } : { ok: true, arrayBuffer: async () => new ArrayBuffer(4) });
    const first = await samples.preloadSamples(audioContext());
    expect(first?.midis).toEqual([60]);
    expect(context.decodeAudioData).toHaveBeenCalledOnce();
    const goodBuffer = first?.buffers.get(60);
    await Promise.resolve();
    expect(fetchMock).toHaveBeenCalledTimes(3);
    missing = false;
    const retry = samples.preloadSamples(audioContext());
    expect(samples.preloadSamples(audioContext())).toBe(retry);
    expect((await retry)?.midis).toEqual([60, 63]);
    expect(samples.sampleBank('piano')?.buffers.get(60)).toBe(goodBuffer);
    expect(fetchMock).toHaveBeenCalledTimes(4);
    expect(fetchMock).toHaveBeenLastCalledWith('/samples/piano/63.mp3');
    expect(context.decodeAudioData).toHaveBeenCalledTimes(2);
  });

  it('keeps disabled banks unused, skips fetches while disabled, and retains ready data for re-enabling', async () => {
    const bank = await samples.preloadSamples(audioContext());
    samples.setSampledPlayback(false);
    expect(samples.sampledPlaybackEnabled()).toBe(false);
    expect(samples.samplePlaybackStatus()).toBe('disabled');
    expect(samples.sampleBank('piano')).toBeUndefined();
    expect(await samples.preloadSamples(audioContext(), 'violin')).toBeNull();
    expect(fetchMock).toHaveBeenCalledTimes(3);
    samples.setSampledPlayback(true);
    expect(samples.sampleBank('piano')).toBe(bank);
    expect(await samples.preloadSamples(audioContext())).toBe(bank);
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it('does not start bank requests when disabled while its manifest is in flight', async () => {
    let resolveManifest!: (value: unknown) => void;
    fetchMock.mockImplementationOnce(() => new Promise(resolve => { resolveManifest = resolve; }));
    const pending = samples.preloadSamples(audioContext());
    samples.setSampledPlayback(false);
    resolveManifest(response());
    expect(await pending).toBeNull();
    expect(fetchMock).toHaveBeenCalledOnce();
  });

  it('defaults on and remembers an in-memory choice when localStorage is unavailable', async () => {
    vi.stubGlobal('localStorage', { getItem: () => { throw new Error('blocked'); }, setItem: () => { throw new Error('blocked'); } });
    expect(samples.sampledPlaybackEnabled()).toBe(true);
    samples.setSampledPlayback(false);
    expect(samples.sampledPlaybackEnabled()).toBe(false);
    expect(await samples.preloadSamples(audioContext())).toBeNull();
    expect(fetchMock).not.toHaveBeenCalled();
    samples.setSampledPlayback(true);
    expect(samples.sampledPlaybackEnabled()).toBe(true);
    expect(await samples.preloadSamples(audioContext())).not.toBeNull();
  });

  it('keeps a new preference when storage reads work but writes fail', async () => {
    vi.stubGlobal('localStorage', { getItem: () => 'on', setItem: () => { throw new Error('quota exceeded'); } });
    expect(samples.sampledPlaybackEnabled()).toBe(true);
    samples.setSampledPlayback(false);
    expect(samples.sampledPlaybackEnabled()).toBe(false);
    expect(await samples.preloadSamples(audioContext())).toBeNull();
    expect(fetchMock).not.toHaveBeenCalled();
    samples.setSampledPlayback(true);
    expect(samples.sampledPlaybackEnabled()).toBe(true);
  });

  it('uses the Vite base path for both the manifest and notes', async () => {
    vi.stubEnv('BASE_URL', '/nested/music/');
    await samples.preloadSamples(audioContext());
    expect(fetchMock.mock.calls.map(call => call[0])).toEqual([
      '/nested/music/samples/manifest.json', '/nested/music/samples/piano/60.mp3', '/nested/music/samples/piano/63.mp3',
    ]);
  });
});

describe('sample voice safety', () => {
  const bank = (midis = [60, 63], duration = 2) => ({ midis, buffers: new Map(midis.map(midi => [midi, { duration } as AudioBuffer])) });
  const play = (midi: number, seconds: number, instrument: import('./samplePlayback').SampleInstrument = 'violin') =>
    samples.playSample(audioContext(), context.destination as unknown as AudioNode, bank(), instrument, midi, 4.06, seconds);

  it('uses playback-rate-adjusted duration for string loops and keeps buffer loop points unscaled', () => {
    expect(play(61, 1.55)).not.toBeNull();
    const higher = context.sources[0];
    expect(higher.loop).toBe(true); // 1.55 > 2 / (2 ** (1/12)) * .8
    expect(higher.loopStart).toBeCloseTo(.7);
    expect(higher.loopEnd).toBeCloseTo(1.7);
    expect(higher.stop).toHaveBeenCalledWith(expect.closeTo(5.61, 9));
    play(62, 1.65);
    expect(context.sources[1].loop).toBe(false); // lower pitch makes the buffer last longer
    play(61, 3, 'piano');
    expect(context.sources[2].loop).toBe(false);
  });

  it('starts at silence with conservative gain and has no release tail beyond the supplied duration', () => {
    play(60, .5, 'piano');
    const gain = context.gains[0];
    expect(gain.gain.value).toBe(0);
    expect(gain.gain.setValueAtTime).toHaveBeenNthCalledWith(1, 0, 4.06);
    expect(gain.gain.linearRampToValueAtTime).toHaveBeenNthCalledWith(1, .06, expect.closeTo(4.066, 9));
    expect(gain.gain.linearRampToValueAtTime).toHaveBeenLastCalledWith(0, 4.56);
    expect(context.sources[0].start).toHaveBeenCalledWith(4.06);
    expect(context.sources[0].stop).toHaveBeenCalledExactlyOnceWith(4.56);
  });

  it('rejects missing, out-of-range, widely shifted and invalid-duration samples before making nodes', () => {
    const invalid = [
      { midi: 59, seconds: 1, bank: bank() }, { midi: 64, seconds: 1, bank: bank() },
      { midi: 63, seconds: 1, bank: bank([60, 66]) }, { midi: 60, seconds: 1, bank: bank([], 2) },
      { midi: 60, seconds: 1, bank: { midis: [60], buffers: new Map<number, AudioBuffer>() } },
      { midi: 60, seconds: 1, bank: bank([60], 0) }, { midi: 60, seconds: 1, bank: bank([60], Number.NaN) },
      { midi: Number.NaN, seconds: 1, bank: bank() }, { midi: 60, seconds: 0, bank: bank() },
    ];
    for (const entry of invalid) expect(samples.playSample(audioContext(), context.destination as unknown as AudioNode,
      entry.bank, 'piano', entry.midi, 4.06, entry.seconds)).toBeNull();
    expect(context.sources).toHaveLength(0);
    expect(context.gains).toHaveLength(0);
  });
});
