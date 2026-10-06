import {describe,it,expect} from 'vitest';
import {indexedSoundingEvidence} from './sounding-evidence.mjs';
describe('optional sounding evidence',()=>{
 it('preserves separate sounding duration without mutation',()=>{
  const n={m:1,d:1,sd:2,stm:1};expect(indexedSoundingEvidence(n)).toEqual({soundingEvidence:{durationQuarters:2,endMeasureOrdinal:1,origin:'validated-source-tie'}});expect(n.d).toBe(1);
 });
 it('does not invent evidence for legacy rows',()=>expect(indexedSoundingEvidence({m:1,d:1})).toEqual({}));
 it('rejects invalid evidence',()=>{for(const n of [{m:1,d:2,sd:1,stm:1},{m:2,d:1,sd:2,stm:1},{m:1,d:1,sd:NaN,stm:1}])expect(indexedSoundingEvidence(n)).toEqual({});});
});
