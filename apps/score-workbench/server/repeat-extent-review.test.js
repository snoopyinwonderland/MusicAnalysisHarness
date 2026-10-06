import {it,expect} from 'vitest';
import {readFileSync} from 'node:fs';
import {discoverRepeats} from './repeat-first.mjs';
import {reviewRepeatExtents} from './repeat-extent-review.mjs';
const w=JSON.parse(readFileSync('evaluation/case-assets/S-STRUCT-008/review-snapshot.json')).work;
it('collapses contained windows and recovers the reviewed extent without Phrase input',()=>{
 const before=JSON.stringify(w.notes),r=discoverRepeats(w.notes),review=reviewRepeatExtents(w.notes,r);
 expect(review.groups.length).toBeLessThan(r.candidates.length);
 const g=review.groups.find(g=>g.anchor.left.startIndex===0&&g.anchor.right.startIndex===30);
 expect(g).toBeDefined();expect(g.windowCount).toBeGreaterThan(1);
 expect(g.endpoints.some(e=>e.left.endExclusiveIndex===30&&e.right.endExclusiveIndex===60&&e.status==='review-candidate')).toBe(true);
 expect(new Set(g.variants.map(v=>v.leftEventId+'|'+v.rightEventId)).size).toBe(g.variants.length);
 expect(JSON.stringify(w.notes)).toBe(before);
});
it('does not cross an explicit internal breath even in a repeated figure',()=>{
 const notes=w.notes.map(n=>({...n}));notes[34].breathSymbols=[{type:'caesura'}];
 const g=reviewRepeatExtents(notes,discoverRepeats(notes)).groups.find(g=>g.anchor.left.startIndex===0&&g.anchor.right.startIndex===30);
 expect(g.endpoints.find(e=>e.right.endExclusiveIndex===60).status).toBe('blocked-by-protected-interior');
});
it('abstains on missing meter and does not alter partial-search status',()=>{
 const n=w.notes.map(n=>({...n,meterCount:null,meterUnit:null})),r=reviewRepeatExtents(n,discoverRepeats(n));
 expect(r.searchStatus).toBe('partial');expect(r.groups.every(g=>g.endpoints.length===0)).toBe(true);
});
