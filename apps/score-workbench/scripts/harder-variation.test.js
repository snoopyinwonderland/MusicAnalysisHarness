import {it,expect} from 'vitest';
import {harderVariation,harderKinds} from './harder-variation.mjs';
const original=[60,64,67,62,65,69,61,67,64,60].map((pitchMidi,i)=>({id:String(i),kind:'note',pitchMidi,durationRatio:1}));
it('makes deterministic two-site changes without modifying source',()=>{for(const kind of harderKinds){const a=harderVariation(original,kind);expect(a).toEqual(harderVariation(original,kind));expect(a.changes.length).toBeGreaterThanOrEqual(2);expect(a.events.filter(n=>n.kind==='note')).toHaveLength(10);}expect(original.every(n=>n.durationRatio===1)).toBe(true);});
it('preserves total duration in rhythm and rest variants',()=>{for(const k of ['two-rhythm-pairs','two-rest-splits'])expect(harderVariation(original,k).events.reduce((s,n)=>s+n.durationRatio,0)).toBe(10);});
