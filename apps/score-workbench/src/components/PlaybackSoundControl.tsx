import { useEffect, useRef, useState } from 'react';
import { preloadPlayback, warmPlayback } from '../music/audioPlayback';
import { sampledPlaybackEnabled, setSampledPlayback, samplePlaybackStatus, type SampleInstrument } from '../music/samplePlayback';
import { PLAYBACK_SOUND_CHANGE_EVENT, playbackInstrumentLabels } from '../music/playbackInstrument';
import './playback-sound-control.css';

/** Every caller stops its active phrase when the shared sound preference changes. */
export function usePlaybackSoundChange(stop: () => void): void {
  const stopRef = useRef(stop);
  stopRef.current = stop;
  useEffect(() => {
    const changed = () => stopRef.current();
    window.addEventListener(PLAYBACK_SOUND_CHANGE_EVENT, changed);
    return () => window.removeEventListener(PLAYBACK_SOUND_CHANGE_EVENT, changed);
  }, []);
}

export function PlaybackSoundControl({ instrument = 'piano', pianoFallback = false, partLabel }: {
  instrument?: SampleInstrument; pianoFallback?: boolean; partLabel?: string;
}) {
  const [enabled, setEnabled] = useState(sampledPlaybackEnabled);
  const [load, setLoad] = useState(() => ({ instrument, status: samplePlaybackStatus(instrument) }));
  const setStatus = (status: ReturnType<typeof samplePlaybackStatus>) => setLoad({ instrument, status });
  useEffect(() => {
    const changed = () => { setEnabled(sampledPlaybackEnabled()); setStatus(samplePlaybackStatus(instrument)); };
    window.addEventListener(PLAYBACK_SOUND_CHANGE_EVENT, changed);
    const storageChanged = (event: StorageEvent) => {
      if (event.key === 'musicanote.sampledPlayback') {
        changed();
        window.dispatchEvent(new Event(PLAYBACK_SOUND_CHANGE_EVENT));
      }
    };
    window.addEventListener('storage', storageChanged);
    return () => {
      window.removeEventListener(PLAYBACK_SOUND_CHANGE_EVENT, changed);
      window.removeEventListener('storage', storageChanged);
    };
  }, [instrument]);
  useEffect(() => {
    let live = true;
    setStatus(samplePlaybackStatus(instrument));
    if (enabled) {
      try {
        const pending = preloadPlayback(instrument);
        setStatus(samplePlaybackStatus(instrument));
        void pending.then(ready => {
          if (!live) return;
          const current = samplePlaybackStatus(instrument);
          setStatus(!ready && current === 'idle' ? 'fallback' : current);
        }).catch(() => { if (live) setStatus('fallback'); });
      } catch { setStatus('fallback'); }
    }
    return () => { live = false; };
  }, [enabled, instrument]);
  const name = playbackInstrumentLabels[instrument] + (pianoFallback ? ' 대체' : '');
  const currentStatus = samplePlaybackStatus(instrument);
  // Do not briefly show the previous part's readiness, or keep a stale failure
  // after a later Play interaction successfully retries its sample bank.
  const status = currentStatus === 'idle' && load.instrument === instrument && load.status === 'fallback' ? 'fallback' : currentStatus;
  const description = !enabled ? '기본 음색' : status === 'ready' ? `${name} 준비됨` : status === 'fallback' ? `${name} 로드 실패 · 기본 음색` : `${name} 준비 중 · 지금 재생 시 기본 음색`;
  return <div className="playback-sound-control" title={partLabel ? `실제 재생 성부: ${partLabel}${pianoFallback ? ' · 지원되지 않는 악기는 피아노로 대체합니다.' : ''}` : undefined}>
    <label className="playback-sound-toggle"><input type="checkbox" checked={enabled} onChange={event => {
      setSampledPlayback(event.target.checked);
      window.dispatchEvent(new Event(PLAYBACK_SOUND_CHANGE_EVENT));
      if (event.target.checked) try { warmPlayback([instrument]); } catch { setStatus('fallback'); }
    }} /><span>샘플 악기 소리</span></label>
    <small role="status">{description}</small>
  </div>;
}
