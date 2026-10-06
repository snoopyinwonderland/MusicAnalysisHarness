import {it,expect} from 'vitest';
import {singleOmissionAlignment as align} from './single-omission.mjs';
const pitches=[60,64,67,65,62,69,71,67,64,60];
const events=ps=>ps.map((pitchMidi,i)=>({pitchMidi,onset:i,durationRatio:1,structuralWeight:.7}));
it('recognizes one internal omitted attack under one transposition',()=>{
 const c=events(pitches),q=events(pitches.filter((_,i)=>i!==5).map(p=>p+2)),r=align(q,c);
 expect(r.singleOmission.candidateIndex).toBe(5);expect(r.singleOmission.transpose).toBe(-2);expect(r.coverage).toBe(1);expect(r.similarity).toBeLessThan(100);
});
it('preserves rhythm ratios and allows uniform tempo',()=>{
 const c=events(pitches).map(e=>({...e,onset:e.onset*2,durationRatio:2})),q=events(pitches.filter((_,i)=>i!==4));
 expect(align(q,c).singleOmission.tempo).toBe(2);q[3].durationRatio=.5;expect(align(q,c)).toBe(null);
});
it('rejects additional wrong pitch, two omissions and edges',()=>{
 const c=events(pitches),q=events(pitches.filter((_,i)=>i!==5));q[2].pitchMidi++;expect(align(q,c)).toBe(null);
 expect(align(events(pitches.filter((_,i)=>![3,6].includes(i))),c)).toBe(null);
 expect(align(events(pitches.slice(1)),c)).toBe(null);
});
it('does not equate deletion to a rest substitution',()=>{
 const q=events(pitches).filter((_,i)=>i!==5);expect(align(q,events(pitches))).toBe(null);
});
it('rejects repetitive underspecified queries and polyphonic overlap',()=>{
 expect(align(events(Array(9).fill(60)),events(Array(10).fill(60)))).toBe(null);
 const c=events(pitches);c[5].onset=4.5;expect(align(events(pitches.filter((_,i)=>i!==5)),c)).toBe(null);
});
it('penalizes omission of a supported pillar more than a weak note',()=>{
 const c=events(pitches),q=events(pitches.filter((_,i)=>i!==5));c[5].structuralWeight=1;const strong=align(q,c);c[5].structuralWeight=.1;expect(align(q,c).similarity).toBeGreaterThan(strong.similarity);
});
