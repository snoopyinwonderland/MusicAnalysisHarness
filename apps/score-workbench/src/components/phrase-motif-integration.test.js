import {it,expect} from 'vitest';
import {readFileSync} from 'node:fs';
import {buildMotifSpans,buildPhraseSpans} from './FullScorePage';
it('uses phrase-first path and preserves complete score coverage in saved review',()=>{
 const {work:w}=JSON.parse(readFileSync('evaluation/case-assets/S-STRUCT-004/review-snapshot.json','utf8'));
 const phrases=buildPhraseSpans(w.notes,w.phraseAnalysis.boundaries);
 const s=buildMotifSpans(w.notes,w.phraseAnalysis.motifRelations,phrases,w.phraseAnalysis.motifCells,w.phraseAnalysis.recurringMotifPhraseFrames?.frames);
 expect(s.every(x=>x.algorithmVersion==='phrase-first-v1')).toBe(true);
 for(const phrase of phrases){
   const pieces=s.filter(x=>x.parentPhraseNumber===phrase.phraseNumber);
   expect(pieces[0].startIndex).toBe(phrase.startIndex);expect(pieces.at(-1).endIndex).toBe(phrase.endIndex);
   for(let i=1;i<pieces.length;i++)expect(pieces[i].startIndex).toBe(pieces[i-1].endIndex+1);
 }
});
