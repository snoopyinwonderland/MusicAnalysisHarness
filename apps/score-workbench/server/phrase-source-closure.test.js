import {it,expect} from 'vitest';
import {sourceClosure} from './phrase-source-closure.mjs';
import {readFileSync} from 'node:fs';
const note=(id,pos,tie=[],kind='note')=>({id,kind,pitch:{step:'C',alter:'0',octave:'4'},source:{staff:'1',measureOrdinal:1},quarterPositionInMeasure:pos,durationQuarter:{n:1,d:1},tie});
const fixture=()=>({observed:[note('a',0,['start']),note('b',1,['stop']),note('r',2,[],'rest'),note('c',3)],mappings:[{index:0,sourceEventId:'a'},{index:1,sourceEventId:'c'}]});
const notes=[{id:'n1',onset:0,durationRatio:2},{id:'n2',onset:3,durationRatio:1}];
it('verifies a tied duration and explicit rest separately without mutation',()=>{
 const e=fixture(),before=JSON.stringify(e),r=sourceClosure(e,notes,0);
 expect(r.status).toBe('observed');expect(r.sourceNoteIds).toEqual(['a','b']);expect(r.sourceRestIds).toEqual(['r']);expect(r.durationMatches&&r.gapMatches).toBe(true);expect(JSON.stringify(e)).toBe(before);
});
it('does not bridge a rest to complete a tie',()=>{const e=fixture();e.observed[1].kind='rest';expect(sourceClosure(e,notes,0).status).toBe('unknown')});
it('does not silently accept a spelling mismatch',()=>{const e=fixture();e.observed[1].pitch.step='D';expect(sourceClosure(e,notes,0).status).toBe('unknown')});
it('reports flattened duration disagreement',()=>{expect(sourceClosure(fixture(),[{...notes[0],durationRatio:1},notes[1]],0).durationMatches).toBe(false)});
it('abstains on gaps in the source timeline',()=>{const e=fixture();e.observed[2].quarterPositionInMeasure=2.5;expect(sourceClosure(e,notes,0).status).toBe('unknown')});
it('preserves the actual case internal breath and tied terminal observations',()=>{
 const root='evaluation/case-assets/S-STRUCT-006/';
 const evidence=JSON.parse(readFileSync(root+'phrase-structure-v1-baseline/notation-evidence.json'));
 const notes=JSON.parse(readFileSync(root+'review-snapshot.json')).work.notes;
 const internal=sourceClosure(evidence,notes,50),terminal=sourceClosure(evidence,notes,56);
 expect(internal.explicitRestDuration).toBe(.5);expect(terminal.explicitRestDuration).toBe(5.5);
 expect(terminal.sourceNoteIds).toHaveLength(2);expect(terminal.sourceDuration).toBe(2.5);
 expect([internal,terminal].every(r=>r.durationMatches&&r.gapMatches)).toBe(true);
});
