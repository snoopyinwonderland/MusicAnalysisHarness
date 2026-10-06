import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { QueryEvent } from '../types';

class FakeParam {
  value = 1;
  setValueAtTime = vi.fn();
  linearRampToValueAtTime = vi.fn();
  exponentialRampToValueAtTime = vi.fn();
  cancelScheduledValues = vi.fn();
}
class FakeNode {
  connect = vi.fn((out: FakeNode) => out);
  disconnect = vi.fn();
}
class FakeGain extends FakeNode { gain = new FakeParam(); }
class FakeOscillator extends FakeNode {
  frequency = new FakeParam();
  start = vi.fn();
  stop = vi.fn();
  onended: (() => void) | null = null;
}
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
  static instances: FakeContext[] = [];
  currentTime = 10;
  state = 'suspended';
  destination = new FakeNode();
  oscillators: FakeOscillator[] = [];
  sources: FakeSource[] = [];
  gains: FakeGain[] = [];
  resume = vi.fn(async () => { this.state = 'running'; });
  decodeAudioData = vi.fn(async () => ({ duration: 2 }) as AudioBuffer);
  constructor() { FakeContext.instances.push(this); }
  createGain() { const node = new FakeGain(); this.gains.push(node); return node; }
  createOscillator() { const node = new FakeOscillator(); this.oscillators.push(node); return node; }
  createBufferSource() { const node = new FakeSource(); this.sources.push(node); return node; }
}
const note = (id: string, pitchMidi: number, durationRatio = 1): QueryEvent => ({ id, kind: 'note', pitchMidi, durationRatio });
const rest = (durationRatio: number): QueryEvent => ({ id: 'rest', kind: 'rest', pitchMidi: null, durationRatio });
let playback: typeof import('./audioPlayback');
let samples: typeof import('./samplePlayback');
let fetchMock: ReturnType<typeof vi.fn>;

beforeEach(async () => {
  vi.resetModules();
  FakeContext.instances = [];
  const stored = new Map<string, string>();
  vi.stubGlobal('localStorage', { getItem: (key: string) => stored.get(key) ?? null, setItem: (key: string, value: string) => stored.set(key, value) });
  vi.stubGlobal('AudioContext', FakeContext);
  fetchMock = vi.fn(async (url: string) => url.endsWith('manifest.json')
    ? { ok: true, json: async () => ({ instruments: { piano: [60, 63], violin: [60, 63] } }) }
    : { ok: true, arrayBuffer: async () => new ArrayBuffer(4) });
  vi.stubGlobal('fetch', fetchMock);
  playback = await import('./audioPlayback');
  samples = await import('./samplePlayback');
});
afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs(); });

describe('shared AudioContext phrase scheduling', () => {
  it('returns synchronously and retains the oscillator clock, rests, durations and supplied pitch/tie/tuplet data', () => {
    fetchMock.mockImplementation(() => new Promise(() => {}));
    const events = [
      { ...note('tie', 60, 2), tieGroup: 'already-collapsed' }, rest(.5),
      { ...note('triplet', 73, 1 / 3), writtenDuration: .5, actualNotes: 3, normalNotes: 2, tupletGroup: 't' },
      note('last', 64, .5),
    ];
    const original = structuredClone(events);
    const handle = playback.schedulePhrase(events);
    expect(handle).not.toBeInstanceOf(Promise);
    expect(handle.context).toBe(FakeContext.instances[0]);
    const context = FakeContext.instances[0];
    expect(context.sources).toHaveLength(0);
    expect(context.oscillators).toHaveLength(3);
    const onsets = [10.06, 10.06 + 1.25 + .3125, 10.06 + 1.25 + .3125 + .625 / 3];
    const durations = [1.25, .625 / 3, .3125];
    context.oscillators.forEach((oscillator, index) => {
      expect(oscillator.start).toHaveBeenCalledWith(expect.closeTo(onsets[index], 9));
      expect(oscillator.stop).toHaveBeenCalledWith(expect.closeTo(onsets[index] + durations[index], 9));
    });
    expect(context.oscillators[1].frequency.value).toBeCloseTo(440 * 2 ** ((73 - 69) / 12));
    expect(context.gains[0].gain.linearRampToValueAtTime).toHaveBeenCalledWith(.06, 10.066);
    expect(context.resume).toHaveBeenCalledOnce();
    expect(events).toEqual(original);
  });

  it('does not wait for asynchronous preload or shift already scheduled notes when it completes', async () => {
    let resolveManifest!: (response: unknown) => void;
    fetchMock.mockImplementationOnce(() => new Promise(resolve => { resolveManifest = resolve; }));
    const pending = playback.preloadPlayback();
    const context = FakeContext.instances[0];
    expect(context.resume).not.toHaveBeenCalled();
    expect(samples.samplePlaybackStatus()).toBe('loading');
    playback.schedulePhrase([note('first', 60)], 500);
    expect(context.oscillators[0].start).toHaveBeenCalledWith(10.06);
    context.currentTime = 14;
    resolveManifest({ ok: true, json: async () => ({ instruments: { piano: [60, 63] } }) });
    expect(await pending).toBe(true);
    expect(samples.samplePlaybackStatus()).toBe('ready');
    expect(context.sources).toHaveLength(0);
    expect(context.oscillators[0].start).toHaveBeenCalledExactlyOnceWith(10.06);
    playback.schedulePhrase([note('next', 61)], 500);
    expect(context.sources[0].start).toHaveBeenCalledWith(14.06);
    expect(context.sources[0].stop).toHaveBeenCalledWith(14.56);
    expect(FakeContext.instances).toHaveLength(1);
  });

  it('uses ready samples with the same rest onsets and note release, and falls back outside the bank', async () => {
    await playback.preloadPlayback();
    playback.schedulePhrase([note('a', 61), rest(.5), note('b', 63, .5), note('low', 20, .25)], 500);
    const context = FakeContext.instances[0];
    expect(context.sources).toHaveLength(2);
    expect(context.sources[0].start).toHaveBeenCalledWith(10.06);
    expect(context.sources[0].stop).toHaveBeenCalledWith(10.56);
    expect(context.sources[0].playbackRate.value).toBeCloseTo(2 ** (1 / 12));
    expect(context.sources[1].start).toHaveBeenCalledWith(10.81);
    expect(context.sources[1].stop).toHaveBeenCalledWith(11.06);
    expect(context.oscillators[0].start).toHaveBeenCalledWith(11.06);
    expect(context.oscillators[0].stop).toHaveBeenCalledWith(11.185);
    context.sources[0].onended?.();
    expect(context.sources[0].disconnect).toHaveBeenCalledOnce();
    expect(context.gains[0].disconnect).toHaveBeenCalledOnce();
  });

  it('silences active and future sample/synth notes and cleans every node exactly once on stop', async () => {
    await playback.preloadPlayback();
    const handle = playback.schedulePhrase([note('a', 60), rest(2), note('future', 20)]);
    const context = FakeContext.instances[0];
    context.currentTime = 10.1;
    handle.stop(); handle.stop();
    expect(context.sources[0].stop).toHaveBeenLastCalledWith(10.1);
    expect(context.oscillators[0].stop).toHaveBeenLastCalledWith(10.1);
    expect(context.sources[0].stop).toHaveBeenCalledTimes(2); // scheduled release + cancellation
    expect(context.oscillators[0].stop).toHaveBeenCalledTimes(2);
    for (const gain of context.gains) {
      expect(gain.gain.cancelScheduledValues).toHaveBeenCalledExactlyOnceWith(10.1);
      expect(gain.gain.setValueAtTime).toHaveBeenLastCalledWith(0, 10.1);
      expect(gain.disconnect).toHaveBeenCalledOnce();
    }
    context.sources[0].onended?.(); context.oscillators[0].onended?.();
    expect(context.sources[0].disconnect).toHaveBeenCalledOnce();
    expect(context.oscillators[0].disconnect).toHaveBeenCalledOnce();
  });

  it('retains the original minimum duration and supplied separate tie attacks', async () => {
    await playback.preloadPlayback();
    playback.schedulePhrase([{ ...note('a', 60, .001), tieGroup: 't' }, { ...note('b', 60, .001), tieGroup: 't' }]);
    const context = FakeContext.instances[0];
    expect(context.sources).toHaveLength(2);
    expect(context.sources[0].start).toHaveBeenCalledWith(10.06);
    expect(context.sources[0].stop).toHaveBeenCalledWith(expect.closeTo(10.12, 9));
    expect(context.sources[1].start).toHaveBeenCalledWith(10.07);
  });

  it('shares one context for warming/preloading/playback and does not fetch while disabled', async () => {
    samples.setSampledPlayback(false);
    expect(await playback.preloadPlayback()).toBe(false);
    expect(FakeContext.instances).toHaveLength(0);
    playback.warmPlayback(['piano', 'violin']);
    playback.schedulePhrase([note('a', 60)]);
    expect(fetchMock).not.toHaveBeenCalled();
    expect(FakeContext.instances).toHaveLength(1);
    const context = FakeContext.instances[0];
    expect(context.oscillators).toHaveLength(1);
    expect(context.sources).toHaveLength(0);
    samples.setSampledPlayback(true);
    expect(await playback.preloadPlayback('violin')).toBe(true);
    playback.warmPlayback(['violin']);
    playback.schedulePhrase([note('b', 60)], 625, 'violin');
    expect(context.sources).toHaveLength(1);
    expect(FakeContext.instances).toHaveLength(1);
  });

  it('turns mount-time AudioContext construction failure into a safe false preload result', async () => {
    vi.stubGlobal('AudioContext', class { constructor() { throw new Error('audio unavailable'); } });
    await expect(playback.preloadPlayback()).resolves.toBe(false);
    expect(fetchMock).not.toHaveBeenCalled();
    vi.stubGlobal('AudioContext', FakeContext);
    await expect(playback.preloadPlayback()).resolves.toBe(true);
    expect(FakeContext.instances).toHaveLength(1);
  });

  it('handles gesture-gated resume rejection without delaying scheduling or throwing unhandled errors', async () => {
    await playback.preloadPlayback();
    const context = FakeContext.instances[0];
    context.resume.mockRejectedValue(new Error('gesture required'));
    expect(() => playback.warmPlayback()).not.toThrow();
    const handle = playback.schedulePhrase([note('a', 60)]);
    expect(handle.context).toBe(context);
    expect(context.sources[0].start).toHaveBeenCalledWith(10.06);
    await Promise.resolve();
    expect(context.resume).toHaveBeenCalledTimes(2);
  });
});
