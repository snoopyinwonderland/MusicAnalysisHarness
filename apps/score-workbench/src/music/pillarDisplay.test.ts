import {it,expect} from 'vitest';
import {pillarCandidates} from './pillarCandidates';
import {composePillarDisplay} from './pillarDisplay';
import {selectPillarView} from './pillarView';
import type {CorpusNote} from '../types';
const notes=[0,1,2,3].map((i)=>({id:String(i),pitchMidi:60+i,durationRatio:1,onset:i,beat:i+1,measure:1})) as CorpusNote[];
it('moving and removing starts never changes independent reasons, grade or evidence',()=>{
 const options={meters:{1:{count:4,unit:4}}};
 const independent=pillarCandidates(notes,options),before=JSON.stringify(independent);
 for(const phraseStarts of [[],[{noteId:'1',phraseNumber:1}],[{noteId:'2',phraseNumber:2}]]){
  const display=composePillarDisplay(notes,independent,phraseStarts);
  for(const c of display){const original=independent.find(x=>x.note.id===c.note.id)!;
   expect(c.reasons).toEqual(original.reasons);expect(c.level).toBe(original.level);expect(c.correspondences).toEqual(original.correspondences);
  }
  const unrelatedInput={...options,phraseStarts};
  expect(pillarCandidates(notes,unrelatedInput)).toEqual(independent);
 }
 expect(JSON.stringify(independent)).toBe(before);
});
it('preserves short offbeat hints separately and excludes them from shared view',()=>{
 const ns=notes.map(n=>({...n,durationRatio:.25,onset:n.onset!+.5,beat:n.beat+.5}));
 const independent=pillarCandidates(ns);
 const display=composePillarDisplay(ns,independent,[{noteId:'1',phraseNumber:1},{noteId:'missing',phraseNumber:2}]);
 const hint=display.find(c=>c.note.id==='1')!;
 expect(hint.origin).toBe('phrase-hint-only');expect(hint.reasons).toEqual([]);
 expect(selectPillarView(display,'shared').some(c=>c.note.id==='1')).toBe(false);
 expect(composePillarDisplay(ns,independent,[]).map(c=>c.note.id)).toEqual(independent.map(c=>c.note.id));
});
