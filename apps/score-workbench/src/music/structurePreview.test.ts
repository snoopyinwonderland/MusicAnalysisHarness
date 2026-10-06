import {it,expect} from 'vitest';
import {validateStructurePreview} from './structurePreview';
import {reviewNoteIdentity} from './repeatReviewImport';
const work:any={workId:'work-a',streamId:'p',notes:[{id:'n0',pitchMidi:60,onset:0,durationRatio:1,measure:1,beat:1},{id:'n1',pitchMidi:62,onset:1,durationRatio:1,measure:1,beat:2}]};
const report=()=>({schema:'structure-preview/v1',workId:work.workId,streamId:work.streamId,noteIdentity:reviewNoteIdentity(work.notes),ranges:[{startIndex:0,endIndexExclusive:2,startEventId:'n0',lastEventId:'n1'}]});
it('accepts aligned evidence but rejects stale identities and overlapping spans',()=>{
 expect(validateStructurePreview(report(),work).ranges).toHaveLength(1);
 expect(()=>validateStructurePreview(report(),{...work,workId:'work-b'})).toThrow();
 const bad=report();bad.ranges.push(bad.ranges[0]);expect(()=>validateStructurePreview(bad,work)).toThrow();
});
