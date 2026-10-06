import { instrumentForPart, type SampleInstrument } from './samplePlayback';

export const PLAYBACK_SOUND_CHANGE_EVENT = 'musicanote-playback-sound-change';

export const playbackInstrumentLabels: Record<SampleInstrument, string> = {
  piano: '피아노', violin: '바이올린', viola: '비올라', cello: '첼로',
};

type PlaybackWork = { streamId?: string; partName?: string; xml?: string };
export type PlaybackInstrument = {
  instrument: SampleInstrument;
  partLabel: string;
  pianoFallback: boolean;
  source: 'xml' | 'part-name' | 'default';
};

const decodeXmlText = (text: string) => text
  .replace(/<[^>]*>/g, '')
  .replace(/&#(x[\da-f]+|\d+);/gi, (entity, code: string) => {
    const value = code[0].toLowerCase() === 'x' ? parseInt(code.slice(1), 16) : Number(code);
    return Number.isFinite(value) && value > 0 && value <= 0x10ffff ? String.fromCodePoint(value) : entity;
  })
  .replace(/&(?:amp|lt|gt|quot|apos);/g, entity => ({ '&amp;': '&', '&lt;': '<', '&gt;': '>', '&quot;': '"', '&apos;': "'" })[entity]!)
  .replace(/\s+/g, ' ').trim();

function tagText(xml: string, tag: string): string {
  return decodeXmlText(xml.match(new RegExp(`<(?:(?:[\\w.-]+):)?${tag}\\b[^>]*>([\\s\\S]*?)<\\/(?:(?:[\\w.-]+):)?${tag}\\s*>`, 'i'))?.[1] || '');
}

/** Metadata only: do not parse the score body or infer sound from the displayed/analysis part. */
export function playbackInstrumentForWork(work: PlaybackWork | null | undefined): PlaybackInstrument {
  const streamPart = work?.streamId?.split(':')[0] || '';
  // A fixed header bound also keeps missing/malformed part-lists cheap on large scores.
  const header = (work?.xml || '').slice(0, 256 * 1024);
  const partList = header.match(/<(?:(?:[\w.-]+):)?part-list\b[^>]*>([\s\S]*?)<\/(?:(?:[\w.-]+):)?part-list\s*>/i)?.[1];
  let names = work?.partName || '', partLabel = names || streamPart || '재생 성부';
  let midiProgram: number | undefined, source: PlaybackInstrument['source'] = names ? 'part-name' : 'default';
  if (partList && streamPart) {
    for (const match of partList.matchAll(/<(?:(?:[\w.-]+):)?score-part\b([^>]*)>([\s\S]*?)<\/(?:(?:[\w.-]+):)?score-part\s*>/gi)) {
      const id = match[1].match(/\bid\s*=\s*(["'])(.*?)\1/i)?.[2];
      if (decodeXmlText(id || '') !== streamPart) continue;
      const instrumentName = tagText(match[2], 'instrument-name');
      const partName = tagText(match[2], 'part-name');
      const abbreviation = tagText(match[2], 'part-abbreviation');
      names = [instrumentName, partName, abbreviation].filter(Boolean).join(' ') || work?.partName || '';
      partLabel = partName || instrumentName || work?.partName || streamPart;
      const program = Number(tagText(match[2], 'midi-program'));
      midiProgram = Number.isInteger(program) && program >= 1 && program <= 128 ? program : undefined;
      source = 'xml';
      break;
    }
  }
  const instrument = instrumentForPart(names, midiProgram);
  const knownPiano = /piano|피아노|\b(?:pno|pf)(?=\b|\d)/i.test(names.normalize('NFKC')) || midiProgram === 1;
  return { instrument, partLabel, pianoFallback: instrument === 'piano' && !knownPiano, source };
}
