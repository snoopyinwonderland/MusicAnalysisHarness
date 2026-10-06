import test from 'node:test';
import assert from 'node:assert/strict';
import {repeatedBoundaryChecks,alternativeChecks} from './audit_phrase_consistency.mjs';
test('internal mismatches deduplicated; motif starts not compared',()=>{
 const notes=Array.from({length:8},(_,i)=>({id:String(i)}));
 const relation={previousIndex:0,currentIndex:4,length:4};
 const boundaries=notes.map((_,i)=>({supported:i===1,cues:[]}));
 const result=repeatedBoundaryChecks(notes,{boundaries,motifRelations:[relation,relation]});
 assert.equal(result.length,3);assert.equal(result.filter(r=>r.mismatch).length,1);
});
test('absent relations do not report success',()=>assert.deepEqual(repeatedBoundaryChecks([],{motifRelations:[]}),[]));
test('unmapped alternative is not a musical failure',()=>{
 const r=alternativeChecks([],{boundaries:[]},{alternatives:[{id:'A',span:{lastEventId:'a'}}]},[{id:'a',onset:{n:0,d:1},pitch:60}]);
 assert.equal(r[0].status,'unmapped-not-failed');
});
