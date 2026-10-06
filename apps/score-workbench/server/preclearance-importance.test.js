import {describe,it,expect} from 'vitest';
import {segmentImportance,compareImportance,mapCandidateTargets,enrichPreclearanceImportance} from './preclearance-importance.mjs';
const fixture=()=>({snapshotId:'fixture',meter:'3/4',units:[],events:[60,62,64,65,67,69,71,72].map((pitchMidi,i)=>({id:`e${i}`,kind:'note',pitchMidi,onset:i,durationRatio:1,beat:i%3+1}))});
describe('candidate structural importance evidence',()=>{
 it('does not schedule analysis after cancellation',async()=>{
  const controller=new AbortController();controller.abort();let calls=0;
  const r=await enrichPreclearanceImportance(fixture(),{snapshotId:'fixture',runs:[],works:[{matches:[{workId:'x'}]}]},
   {signal:controller.signal,analyzeSource:()=>{calls++}});
  expect(calls).toBe(0);expect(r.report.structureEnrichment.status).toBe('cancelled');expect(r.report.structureEnrichment.cancelled).toBe(1);
 });
 it('accepts externally analyzed snapshots and preserves scores',async()=>{
  const s=fixture();s.identity={sourceId:'s',streamId:'P1'};
  const match={workId:'w',sourceId:'s',streamId:'P1',taskId:'t',similarity:88,targets:s.events.slice(0,4)};
  const report={snapshotId:s.snapshotId,runs:[{taskId:'t',selection:{task:{query:{events:s.events.slice(0,4)}}}}],works:[{matches:[match]}]};
  const r=await enrichPreclearanceImportance(s,report,{analyzeSource:async()=>s});
  expect(r.report.structureEnrichment.completed).toBe(1);expect(r.report.works[0].matches[0].similarity).toBe(88);
 });
 it('counts nonoverlapping transposed repetitions across the full stream',()=>{
  const s=fixture(),r=segmentImportance(s,['e0','e1','e2','e3']);expect(r.occurrenceCount).toBe(2);expect(r.durationShare).toBe(.5);expect(r.components.cadence).toBeNull();
 });
 it('does not create a cherry-picked sequence from skipped notes',()=>{
  const r=segmentImportance(fixture(),['e0','e3']);expect(r.spanAttackCount).toBe(4);expect(r.interveningAttackCount).toBe(2);
 });
 it('resolves by source time and pitch, not excerpt-local IDs',()=>{
  expect(mapCandidateTargets(fixture(),[{id:'e0',onset:5,pitchMidi:69}])).toEqual(['e5']);
  expect(()=>mapCandidateTargets(fixture(),[{onset:5,pitchMidi:70}])).toThrow();
  const s=fixture();s.events.push({...s.events[0],id:'duplicate'});expect(()=>mapCandidateTargets(s,[s.events[0]])).toThrow('ambiguous');
 });
 it('keeps unknown meter unknown and compares only shared components',()=>{
  const a=fixture(),b=fixture();b.events.forEach(e=>e.meter=null);
  const q=segmentImportance(a,['e0','e1','e2','e3']),c=segmentImportance(b,['e0','e1','e2','e3']);
  expect(c.components.metricalDuration).toBeNull();expect(compareImportance(q,c).commonComponents).toEqual(['repetition']);
 });
 it('uses one-based quarter beats and compound meter',()=>{
  const s=fixture();s.events=s.events.slice(0,4);s.events.forEach(e=>{e.meter='6/8';e.beat=1});
  expect(segmentImportance(s,s.events.map(e=>e.id)).components.metricalDuration).toBe(.75);
  s.events.forEach(e=>e.beat=2.5);expect(segmentImportance(s,s.events.map(e=>e.id)).components.metricalDuration).toBeCloseTo(.59);
 });
 it('includes silent gaps in repeat signatures',()=>{
  const s=fixture();s.events[6].onset+=.25;expect(segmentImportance(s,['e0','e1','e2','e3']).occurrenceCount).toBe(1);
 });
 it('rejects stale query snapshots',async()=>{
  await expect(enrichPreclearanceImportance(fixture(),{snapshotId:'other'},{loadSource:()=>{}})).rejects.toThrow('mismatch');
 });
 it('records unavailable sources without changing rankings or targets',async()=>{
  const match={workId:'missing',targets:[{onset:1,pitchMidi:62}]},report={snapshotId:'fixture',runs:[],works:[{key:'a',similarity:90,matches:[match]}]};
  const r=await enrichPreclearanceImportance(fixture(),report,{loadSource:()=>{throw new Error('not found')}});
  expect(r.report.works[0].similarity).toBe(90);expect(r.report.works[0].matches[0].targets).toEqual(match.targets);expect(r.report.structureEnrichment.failed).toBe(1);expect(match.structureStatus).toBeUndefined();
 });
});
