import {it,expect} from 'vitest';
import {comparisonNotation,candidateEvents,htmlEscape} from './preclearance-report.mjs';
it('splits long logical tones with ties instead of truncating them',()=>{
 const r=comparisonNotation([{id:'a',kind:'note',pitchMidi:60,durationRatio:6}],'4/4','safe',['a']);
 expect(r.mei).toContain('tie="i"');expect(r.mei).toContain('tie="t"');expect(r.mei).toContain('dur="1"');expect(r.mei).toContain('dur="2"');expect(r.redIds).toHaveLength(2);
});
it('renders dotted short notes and decomposes ordinary additive durations without fake tuplets',()=>{
 const r=comparisonNotation([{id:'a',kind:'note',pitchMidi:60,durationRatio:.375}],'4/4','safe');expect(r.mei).toContain('dur="16" dots="1"');expect(r.mei).not.toContain('<tuplet');
 const long=comparisonNotation([{id:'a',kind:'note',pitchMidi:60,durationRatio:3.5}],'4/4','safe');expect(long.mei).toContain('tie="i"');expect(long.mei).not.toContain('<tuplet');
});
it('keeps unaligned interior notes and restores timing gaps',()=>{
 const s={events:[{id:'a',onset:0,durationRatio:1},{id:'b',onset:2,durationRatio:1}]};expect(candidateEvents(s,['a','b'])[1].kind).toBe('rest');expect(()=>candidateEvents(s,['missing'])).toThrow();
});
it('escapes externally supplied report text',()=>{expect(htmlEscape('<script>"&')).toBe('&lt;script&gt;&quot;&amp;')});
