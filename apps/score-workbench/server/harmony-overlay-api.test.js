import {describe,expect,it} from 'vitest';
import {createAutomaticHarmonyReviewRecord,extractBracketedRomanLabels} from './harmony-overlay-api.mjs';

describe('automatic harmony feedback',()=>{
  it('stores hypotheses separately from non-training human review',()=>{
    const record=createAutomaticHarmonyReviewRecord({workId:'work-1',sourceId:'score.xml',streamId:'P1:1:1',engineVersion:'blind-v1',reason:'wrong_key',note:'G major가 더 적절함',keyHypothesis:{label:'C major'},segment:{analysisId:'auto_harmony_1',span:{start:0,end:2,semantics:'[start,end)'},displayLocation:{startMeasure:1,startBeat:1},selected:{romanLabel:'I'},alternatives:[],reviewReasons:['small_candidate_margin']}},new Date('2026-09-25T00:00:00Z'),'fixed');
    expect(record.reviewId).toBe('ahr_fixed');
    expect(record.human.status).toBe('wrong_key');
    expect(record.hypothesis.selected.romanLabel).toBe('I');
    expect(record.trainingEligible).toBe(false);
    expect(record.ruleUpdateEligible).toBe(false);
  });
  it('rejects unknown decisions',()=>expect(()=>createAutomaticHarmonyReviewRecord({workId:'w',streamId:'s',reason:'gold',segment:{analysisId:'a',span:{start:0,end:1}}})).toThrow());
  it('extracts bracketed Roman corrections as pending case candidates with local context',()=>{
    const context={previous:{selected:{romanLabel:'i'}},current:{selected:{romanLabel:'#iv°'}},next:{selected:{romanLabel:'V'}}};
    const record=createAutomaticHarmonyReviewRecord({workId:'work-2',sourceId:'score.xml',streamId:'P1:1:1',engineVersion:'blind-v1',reason:'wrong_chord',note:'이 화음은 [viio/V]이고 뒤의 V에서 해결됩니다.',context,segment:{analysisId:'auto_harmony_4',span:{start:2,end:3,semantics:'[start,end)'},selected:{romanLabel:'#iv°'},alternatives:[],reviewReasons:[]}},new Date('2026-09-25T00:00:00Z'),'secondary');
    expect(extractBracketedRomanLabels(record.human.comment)).toEqual(['viio/V']);
    expect(record.human.suggestedRomanLabel).toBe('viio/V');
    expect(record.hypothesis.context.next.selected.romanLabel).toBe('V');
    expect(record.caseCandidate).toEqual({adjudicationStatus:'pending',tags:['secondary-function'],retrievalEligible:false});
    expect(record.trainingEligible).toBe(false);
  });
});
