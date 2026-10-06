import { afterEach, describe, expect, it, vi } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { sampledPlaybackEnabled, samplePlaybackStatus } from '../music/samplePlayback';
import { PlaybackSoundControl } from './PlaybackSoundControl';

vi.mock('../music/audioPlayback', () => ({ preloadPlayback: vi.fn(), warmPlayback: vi.fn() }));
vi.mock('../music/samplePlayback', () => ({
  sampledPlaybackEnabled: vi.fn(() => true),
  samplePlaybackStatus: vi.fn(() => 'ready'),
  setSampledPlayback: vi.fn(),
  instrumentForPart: vi.fn(() => 'piano'),
}));

afterEach(() => {
  vi.mocked(sampledPlaybackEnabled).mockReturnValue(true);
  vi.mocked(samplePlaybackStatus).mockReturnValue('ready');
});

describe('playback sound status labels', () => {
  it('shows an enabled, ready instrument without claiming a different part is sounding', () => {
    const html = renderToStaticMarkup(<PlaybackSoundControl instrument="viola" partLabel="Inner voice" />);
    expect(html).toContain('checked=""');
    expect(html).toContain('비올라 준비됨');
    expect(html).toContain('실제 재생 성부: Inner voice');
    expect(html).toContain('class="playback-sound-toggle"');
  });

  it('marks unknown instruments as a piano substitution', () => {
    const html = renderToStaticMarkup(<PlaybackSoundControl pianoFallback partLabel="Clarinet" />);
    expect(html).toContain('피아노 대체 준비됨');
    expect(html).toContain('지원되지 않는 악기는 피아노로 대체합니다.');
  });

  it('does not claim sampled sound while loading or after failure', () => {
    vi.mocked(samplePlaybackStatus).mockReturnValue('loading');
    expect(renderToStaticMarkup(<PlaybackSoundControl />)).toContain('지금 재생 시 기본 음색');
    vi.mocked(samplePlaybackStatus).mockReturnValue('fallback');
    expect(renderToStaticMarkup(<PlaybackSoundControl />)).toContain('로드 실패 · 기본 음색');
  });

  it('reflects a disabled persisted preference even when the bank was ready', () => {
    vi.mocked(sampledPlaybackEnabled).mockReturnValue(false);
    const html = renderToStaticMarkup(<PlaybackSoundControl />);
    expect(html).not.toContain('checked=""');
    expect(html).toContain('기본 음색');
    expect(html).not.toContain('준비됨');
  });
});
