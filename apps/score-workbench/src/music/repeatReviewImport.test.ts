import {it,expect} from 'vitest';
// @ts-expect-error Test-only Node import; browser tsconfig intentionally omits Node types.
import {readFileSync} from 'node:fs';
import {validateRepeatReview} from './repeatReviewImport';
const work=JSON.parse(readFileSync('evaluation/case-assets/S-STRUCT-008/review-snapshot.json','utf8')).work;
const report=JSON.parse(readFileSync('evaluation/reports/repeat-review-ui-008-v1/review-ui.json','utf8'));
it('accepts the matching source-linked snapshot and rejects changed durations',()=>{
 expect(validateRepeatReview(report,work).rows.length).toBeGreaterThan(0);
 const changed=structuredClone(work);changed.notes[0].durationRatio+=.25;
 expect(()=>validateRepeatReview(report,changed)).toThrow();
});
it('rejects another work, stream and invalid range references',()=>{
 expect(()=>validateRepeatReview(report,{...work,workId:'other'})).toThrow();
 expect(()=>validateRepeatReview(report,{...work,streamId:'other'})).toThrow();
 const bad=structuredClone(report);bad.rows[0].left.endIndexExclusive=999999;
 expect(()=>validateRepeatReview(bad,work)).toThrow();
});
