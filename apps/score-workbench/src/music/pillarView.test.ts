import {expect,it} from 'vitest';
import {selectPillarView} from './pillarView';
import type {PillarCandidate} from './pillarCandidates';
it('shared view is a reversible subset and retains provenance',()=>{
 const all=[{index:0,correspondences:[]},{index:1,correspondences:[{otherNoteId:'peer',transposition:5,timeScale:2,ruleVersion:'pillar-variation-0.1'}]}] as PillarCandidate[];
 const before=JSON.stringify(all),shared=selectPillarView(all,'shared');
 expect(shared).toEqual([all[1]]);expect(shared[0]).toBe(all[1]);
 expect(selectPillarView(all,'surface')).toBe(all);expect(JSON.stringify(all)).toBe(before);
});
it('does not fall back to all notes when shared evidence is absent',()=>{
 expect(selectPillarView([{correspondences:[]}] as unknown as PillarCandidate[],'shared')).toEqual([]);
 expect(selectPillarView([],'shared')).toEqual([]);
});
