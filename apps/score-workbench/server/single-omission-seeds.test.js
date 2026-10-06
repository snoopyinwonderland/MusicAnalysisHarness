import {it,expect} from 'vitest';
import {singleOmissionSeeds as seeds} from './single-omission-seeds.mjs';
it('connects disjoint query seeds shifted by one candidate attack',()=>{
 const m=new Map([['work\u000020',new Set([0,1])],['work\u000021',new Set([5])]]);
 expect(seeds(m,9)[0].start).toBe(20);
});
it('does not connect same-offset, overlapping, distant or other-work evidence',()=>{
 expect(seeds(new Map([['a\u00000',new Set([0,5])]]),9)).toEqual([]);
 expect(seeds(new Map([['a\u00000',new Set([0])],['a\u00001',new Set([2])]]),9)).toEqual([]);
 expect(seeds(new Map([['a\u00000',new Set([0])],['a\u00002',new Set([5])],['b\u00001',new Set([5])]]),9)).toEqual([]);
});
it('bounds candidates per work and globally',()=>{
 const m=new Map();for(let i=0;i<9;i++){m.set(`a\u0000${i*10}`,new Set([0]));m.set(`a\u0000${i*10+1}`,new Set([5]))}
 expect(seeds(m,9,{perWork:2,limit:1})).toHaveLength(1);
});
