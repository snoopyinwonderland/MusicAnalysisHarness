import {it,expect} from 'vitest';
import {auditEvidence,groupPillarEvidence,type EvidenceNode} from './pillarEvidence';
import {pillarCandidates} from './pillarCandidates';
import type {CorpusNote} from '../types';
const node=(id:string,parents:string[]=[],observationKey?:string):EvidenceNode=>({id,parents,observationKey,revision:'r1',analysisRefs:[],complete:true});
it('deduplicates shared primitive observations instead of counting rule labels',()=>{
 const graph=[node('duration',[],'duration:n1'),node('long',['duration']),node('arrival',['duration'])];
 const a=auditEvidence(graph,['long','arrival'],'r1','phrase1',['duration']);
 expect(a.status).toBe('verified');expect(a.observations).toEqual(['duration:n1']);expect(a.additional).toEqual([]);expect(a.alreadyUsed).toEqual(['duration:n1']);expect(a.autoApply).toBe(false);
});
it('fails closed without a baseline ledger',()=>{
 const a=auditEvidence([node('a',[],'x')],['a'],'r1','phrase1');expect(a.status).toBe('baseline-unverified');expect(a.additional).toEqual([]);
});
it('rejects indirect phrase dependencies',()=>{
 const a=node('a',[],'x');a.analysisRefs=['phrase1'];
 const r=auditEvidence([a,node('b',['a'])],['b'],'r1','phrase1',[]);
 expect(r.issues).toContain('phrase-dependent:a');expect(r.additional).toEqual([]);
});
it('blocks cycles, missing parents, mismatched revisions and duplicate IDs',()=>{
 const bad=node('bad',[],'x');bad.revision='r2';
 const r=auditEvidence([node('a',['b']),node('b',['a','missing']),bad,bad],['a','bad'],'r1','phrase1',[]);
 expect(r.status).toBe('blocked');expect(r.issues).toEqual(expect.arrayContaining(['cycle:a','missing:missing','revision:bad','duplicate-id:bad']));expect(r.additional).toEqual([]);
});
it('requires complete leaf provenance',()=>{
 const a=node('a');a.complete=false;
 expect(auditEvidence([a],['a'],'r1','p',[]).issues).toEqual(['incomplete:a','untraced:a']);
});
it('emits typed rule reasons but does not treat related metric rules as separate families',()=>{
 const ns=[0,1,2,3].map(i=>({id:String(i),pitchMidi:60+i,durationRatio:1,onset:i,beat:i+1,measure:1})) as CorpusNote[];
 const c=pillarCandidates(ns,{meters:{1:{count:4,unit:4}}})[0];
 expect(c.reasons).toEqual(c.evidence.map(e=>e.label));
 const metric=groupPillarEvidence(c.evidence).find(g=>g.family==='metric')!;
 expect(metric.rules.map(e=>e.ruleId)).toEqual(['beat-position','downbeat']);
 expect(c.evidence.every(e=>e.reviewEligibility==='unverified')).toBe(true);
});
