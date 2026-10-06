import test from 'node:test';
import assert from 'node:assert/strict';
import {transposeInput,compareBoundaries} from './audit_phrase_transposition.mjs';
test('preserves source, rhythm and missing/rest pitch',()=>{
 const notes=[{pitchMidi:60,onset:1,durationRatio:.5,spelling:'C4',nested:{a:1}},{kind:'rest',pitchMidi:null},{onset:2}];
 const before=structuredClone(notes),after=transposeInput(notes,7);
 assert.deepEqual(notes,before);assert.equal(after[0].pitchMidi,67);assert.equal(after[0].onset,1);assert.equal(after[0].durationRatio,.5);
 assert.equal(after[1].pitchMidi,null);assert.equal(after[2].pitchMidi,undefined);assert.equal(after[0].spelling,undefined);
});
test('rejects invalid shift and pitch range',()=>{
 assert.throws(()=>transposeInput([{pitchMidi:127}],1));assert.throws(()=>transposeInput([],0.5));
});
test('comparison catches changed classification and score',()=>{
 const b={supported:false,state:'unknown',strength:.2,continuity:0};
 assert.equal(compareBoundaries({boundaries:[b]},{boundaries:[{...b,strength:.3}]}).length,1);
 assert.equal(compareBoundaries({boundaries:[b]},{boundaries:[{...b,supported:true}]}).length,1);
 assert.equal(compareBoundaries({boundaries:[b]},{boundaries:[b]}).length,0);
 assert.equal(compareBoundaries({boundaries:[b]},{boundaries:[]}).length,1);
});
