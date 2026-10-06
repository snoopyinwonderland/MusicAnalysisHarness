import {describe,it,expect} from 'vitest';
import {sustainedEndingEvidence,analyzePhraseBoundaries} from './phrase-boundaries.mjs';
const make=(durations,count=4,unit=4)=>{let onset=0;return durations.map((durationRatio,i)=>{const n={onset,durationRatio,pitchMidi:60+i%5,meterCount:count,meterUnit:unit,measure:Math.floor(onset/(count*4/unit))+1,beat:1+onset%(count*4/unit)/(4/unit)};onset+=durationRatio;return n;});};
describe('last sustained ending with rhythmic restart',()=>{
  it('supports a whole-note ending without silence',()=>{
    const n=make([1,1,1,1,4,1,.5,.5]);
    expect(sustainedEndingEvidence(n,5)).not.toBeNull();
    expect(analyzePhraseBoundaries(n).boundaries[5].supported).toBe(true);
  });
  it('does not split a succession of whole notes; considers only its last',()=>{
    const n=make([4,4,4,1,.5,.5]);
    expect(sustainedEndingEvidence(n,1)).toBeNull();
    expect(sustainedEndingEvidence(n,2)).toBeNull();
    expect(sustainedEndingEvidence(n,3)).not.toBeNull();
  });
  it('requires meter-relative sustained duration, not the whole-note glyph',()=>{
    expect(sustainedEndingEvidence(make([4,1,1,1],4,2),1)).toBeNull();
    expect(sustainedEndingEvidence(make([8,2,1,1],4,2),1)).not.toBeNull();
  });
  it('rejects continuation, overlap, unknown meter/onset and slow texture',()=>{
    for(const change of [{tieStop:true},{isAttack:false},{onset:3},{meterCount:undefined}]){
      const n=make([4,1,1,1]);Object.assign(n[1],change);expect(sustainedEndingEvidence(n,1)).toBeNull();
    }
    const n=make([4,1,1,1]);delete n[0].onset;expect(sustainedEndingEvidence(n,1)).toBeNull();
    expect(sustainedEndingEvidence(make([4,1,4,4]),1)).toBeNull();
  });
  it('does not mutate notes or infer terminal boundary without restart context',()=>{
    const n=make([4,4]);const copy=structuredClone(n);analyzePhraseBoundaries(n);expect(n).toEqual(copy);
    expect(sustainedEndingEvidence(n,1)).toBeNull();
  });
});
