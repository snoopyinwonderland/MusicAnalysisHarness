import type { QueryEvent } from '../types';
import { playSample, preloadSamples, sampleBank, sampledPlaybackEnabled, type SampleInstrument } from './samplePlayback';

export type ScheduledPlayback = { context: AudioContext; stop: () => void };

let sharedContext: AudioContext | null = null;
const audioContext = () => sharedContext ??= new AudioContext({ latencyHint: 'interactive' });
const resumePlayback = (context: AudioContext) => {
  try { void context.resume().catch(() => { /* A browser may still require a user gesture. */ }); }
  catch { /* Context unavailable/closed; avoid an unhandled gesture callback error. */ }
};

/** Prefetch on view appearance without attempting a gesture-gated resume. */
export function preloadPlayback(instrument: SampleInstrument = 'piano'): Promise<boolean> {
  if (!sampledPlaybackEnabled()) return Promise.resolve(false);
  try { return preloadSamples(audioContext(), instrument).then(bank => bank !== null).catch(() => false); }
  catch { return Promise.resolve(false); } // AudioContext can be unsupported or unavailable at mount.
}

export function warmPlayback(instruments: SampleInstrument[] = ['piano']): void {
  const context = audioContext();
  if (context.state === 'suspended') resumePlayback(context);
  const gain = context.createGain(); gain.gain.value = 0;
  gain.connect(context.destination); gain.disconnect();
  for (const instrument of instruments) void preloadSamples(context, instrument);
}

/** Schedule the complete phrase on the Web Audio clock.
 * Browser timers may be delayed by Verovio layout; AudioContext events are not.
 */
export function schedulePhrase(events: QueryEvent[], millisecondsPerBeat = 625, instrument: SampleInstrument = 'piano'): ScheduledPlayback {
  const context = audioContext();
  const startTime = context.currentTime + .06;
  const stops: (() => void)[] = [];
  const bank = sampleBank(instrument);
  // A Play interaction may start a preload, but this phrase never waits for it or
  // switches voices halfway through. The original AudioContext clock stays intact.
  void preloadSamples(context, instrument);
  let elapsed = 0;
  for (const event of events) {
    const seconds = Math.max(.01, millisecondsPerBeat * event.durationRatio / 1000);
    if (event.kind === 'note' && event.pitchMidi !== null) {
      const attack = startTime + elapsed, release = attack + Math.max(.06, seconds);
      const sampledStop = bank ? playSample(context, context.destination, bank, instrument, event.pitchMidi, attack, release - attack) : null;
      if (sampledStop) {
        stops.push(sampledStop);
        elapsed += seconds;
        continue;
      }
      const oscillator = context.createOscillator(), gain = context.createGain();
      oscillator.frequency.value = 440 * 2 ** ((event.pitchMidi - 69) / 12);
      gain.gain.setValueAtTime(.0001, attack);
      gain.gain.linearRampToValueAtTime(.06, attack + .006);
      gain.gain.exponentialRampToValueAtTime(.001, Math.max(attack + .04, release - .025));
      oscillator.connect(gain).connect(context.destination);
      let cleaned = false, stopped = false;
      const cleanup = () => {
        if (cleaned) return;
        cleaned = true;
        oscillator.disconnect();
        gain.disconnect();
      };
      oscillator.onended = cleanup;
      oscillator.start(attack);
      oscillator.stop(release);
      stops.push(() => {
        if (stopped) return;
        stopped = true;
        const now = context.currentTime;
        gain.gain.cancelScheduledValues(now);
        gain.gain.setValueAtTime(0, now);
        try { oscillator.stop(now); } catch { /* already ended */ }
        cleanup();
      });
    }
    elapsed += seconds;
  }
  resumePlayback(context);
  return { context, stop: () => { for (const stop of stops) stop(); } };
}
