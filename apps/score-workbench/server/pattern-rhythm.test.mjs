import {it,expect} from 'vitest';
import {simpleQueryPattern} from './query-pattern-policy.mjs';
import {patternRhythmSimilarity,patternRhythmLocal,patternRhythmRanking} from './pattern-rhythm.mjs';
const notes=(ds,ps=[60,62,64,65,67,69])=>{let onset=0;return ds.map((durationRatio,i)=>{const n={pitchMidi:ps[i],onset,durationRatio};onset+=durationRatio;return n;});};
it('uses one tempo ratio and does not penalize uniform scaling',()=>{const q=notes([.25,.25,.5,.25,.25,1]);expect(patternRhythmSimilarity(q,notes([.5,.5,1,.5,.5,2]))).toBe(100);});
it('distinguishes long-note changes and silence from equivalent rhythms',()=>{const q=notes([.25,.25,.5,.25,.25,1]);expect(patternRhythmSimilarity(q,notes([.25,.25,.5,.25,.25,2]))).toBeLessThan(98);const c=notes([.25,.25,.5,.25,.25,1]);c.slice(3).forEach(n=>n.onset+=1);expect(patternRhythmSimilarity(q,c)).toBeLessThan(98);});
it('small variation costs less than a doubled duration',()=>{const q=notes([1,1,1,1,1,1]);expect(patternRhythmSimilarity(q,notes([1,1,1.05,1,1,1]))).toBeGreaterThan(patternRhythmSimilarity(q,notes([1,1,2,1,1,1])));});
it('rhythm outweighs a small melodic advantage with bounded role bonuses',()=>expect(patternRhythmRanking(false,patternRhythmLocal(98,95),-12)).toBeGreaterThan(patternRhythmRanking(false,patternRhythmLocal(100,60),8)));
it('only pure continuous patterns are eligible',()=>{expect(simpleQueryPattern(notes([1,1,1,1,1,1]))).toBe('stepwise');expect(simpleQueryPattern(notes([1,1,1,1,1,1],[60,60,60,60,60,60]))).toBe('repeated');expect(simpleQueryPattern(notes([1,1,1,1,1,1],[60,62,64,62,67,69]))).toBeNull();});
