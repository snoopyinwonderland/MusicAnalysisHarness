import type {CorpusNote} from '../types';
import type {PillarCandidate,PillarPhraseStart} from './pillarCandidates';
export type DisplayPillar=PillarCandidate&{origin:'independent'|'phrase-hint-only';phraseHints:PillarPhraseStart[]};
// Display-only union. Never fed back into independent candidate calculation.
export function composePillarDisplay(notes:CorpusNote[],independent:PillarCandidate[],starts:PillarPhraseStart[]=[]):DisplayPillar[]{
 const hints=new Map<string,PillarPhraseStart[]>();
 for(const p of starts){if(!Number.isInteger(p.phraseNumber)||p.phraseNumber<=0)continue;
  const list=hints.get(p.noteId)??[];if(!list.some(h=>h.phraseNumber===p.phraseNumber))hints.set(p.noteId,[...list,p]);
 }
 const byId=new Map(independent.map(c=>[c.note.id,c]));
 return notes.flatMap<DisplayPillar>((note,index)=>{
  const c=byId.get(note.id),phraseHints=hints.get(note.id)??[];
  if(c)return [{...c,origin:'independent' as const,phraseHints}];
  if(!phraseHints.length||note.pitchMidi===null||!Number.isFinite(note.pitchMidi)||note.durationRatio<=0)return [];
  return [{index,note,reasons:[],level:'tentative' as const,harmony:[],correspondences:[],evidence:[],origin:'phrase-hint-only' as const,phraseHints}];
 });
}
