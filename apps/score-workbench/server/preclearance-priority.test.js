import {it,expect} from 'vitest';
import {queryInformation,prioritizePreclearance} from './preclearance-priority.mjs';
const events=p=>p.map((pitchMidi,i)=>({id:String(i),kind:'note',pitchMidi,durationRatio:1}));
const fixture=()=>{const e=events([60,62,65,64,67,69,65,60]);return {runs:[{taskId:'t',selection:{task:{query:{events:e}}}}],works:[{key:'a',matches:[{taskId:'t',similarity:95,queryIds:e.map(n=>n.id),structureStatus:'completed',candidateImportance:{matchedAttackCount:8,spanAttackCount:8},importanceComparison:{jointSupport:.5,query:.5,candidate:.5}}]}]}};
it('penalizes repetitive low-information queries without claiming rarity',()=>{
 expect(queryInformation(events([60,60,60,60])).score).toBe(0);
 expect(queryInformation(events([60,62,65,64])).score).toBeGreaterThan(.5);
 expect(queryInformation(events([60,62,65,64])).corpusDistinctiveness).toBeNull();
});
it('does not multiply priority for duplicate matches',()=>{
 const a=fixture(),b=fixture();b.works[0].matches.push(structuredClone(b.works[0].matches[0]));
 expect(prioritizePreclearance(a).priorityReview.ranking[0].score).toBe(prioritizePreclearance(b).priorityReview.ranking[0].score);
});
it('preserves original order and scores and stays below similarity',()=>{
 const a=fixture(),r=prioritizePreclearance(a);expect(a.works[0].priorityAssessment).toBeUndefined();
 expect(r.works[0].matches).toEqual(a.works[0].matches);expect(r.priorityReview.ranking[0].score).toBeLessThanOrEqual(95);
});
it('reduces priority for skipped or unmatched notes',()=>{
 const a=fixture(),b=fixture();b.works[0].matches[0].candidateImportance.spanAttackCount=16;b.works[0].matches[0].queryIds=['0','1'];
 expect(prioritizePreclearance(b).priorityReview.ranking[0].score).toBeLessThan(prioritizePreclearance(a).priorityReview.ranking[0].score);
});
it('does not impute missing structure',()=>{
 const a=fixture();a.works[0].matches[0].structureStatus='needs-review';expect(prioritizePreclearance(a).priorityReview.ranking[0].score).toBeNull();
});
it('keeps short-query information finite and transposition invariant',()=>{
 expect(Number.isFinite(queryInformation(events([60,62])).score)).toBe(true);
 expect(queryInformation(events([60,62,65,64]))).toEqual(queryInformation(events([67,69,72,71])));
});
