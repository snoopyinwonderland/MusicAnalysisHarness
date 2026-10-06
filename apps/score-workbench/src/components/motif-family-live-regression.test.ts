// Explicit local audit, not a default slow test. Run with MUSICANOTE_MOTIF_LIVE_AUDIT=1.
// @ts-nocheck
import {it,expect} from 'vitest';
import {readFileSync,writeFileSync,existsSync,statSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {getWork,getWorkScoreSha256} from '../../server/search-api.mjs';
import {buildMotifSpans,buildPhraseSpans} from './FullScorePage';
import {compareMotifFamilies,motifFamilyDisplaySpans} from '../music/motifDiscoveryComparison';
const sha=v=>createHash('sha256').update(typeof v==='string'||Buffer.isBuffer(v)?v:JSON.stringify(v)).digest('hex');
const projected=w=>w?Object.fromEntries(['workId','streamId','sourceId','notes','phraseAnalysis','boundaryHarmony','fullHarmony','phraseEvidenceLedger','structureSelection','stats'].filter(k=>k in w).map(k=>[k,sha(w[k])])):null;
const spansFor=w=>buildMotifSpans(w.notes,w.phraseAnalysis?.motifRelations||[],buildPhraseSpans(w.notes,(w.phraseAnalysis?.boundaries||[]).filter(b=>b.supported)),w.phraseAnalysis?.motifCells||[],w.phraseAnalysis?.recurringMotifPhraseFrames?.frames||[]);
it.skipIf(process.env.MUSICANOTE_MOTIF_LIVE_AUDIT!=='1')('preserves legacy output across ten live works with both comparison layers',()=>{
 const root='K:/Music Analysis/output/motif-family-merge-2026-10-05';
 const baselinePath=process.env.MUSICANOTE_MOTIF_AUDIT_BASELINE??root+'/baseline.json',output=process.env.MUSICANOTE_MOTIF_AUDIT_OUTPUT??root+'/comparison.json';
 const baseline=JSON.parse(readFileSync(baselinePath,'utf8'));
 expect(existsSync(output)).toBe(false);
 const hashFiles=files=>Object.fromEntries(files.map(f=>[f,sha(readFileSync(f))]));
 const preserved=hashFiles(Object.keys(baseline.preserved)),engines=hashFiles(Object.keys(baseline.engines));
 expect(preserved).toEqual(baseline.preserved);expect(engines).toEqual(baseline.engines);
 const db=statSync('data/search-index-v2/search.sqlite');expect({size:db.size,mtimeMs:db.mtimeMs}).toEqual(baseline.database);
 const works=[];
 for(const prior of baseline.works){
  const off=getWork(prior.workId,{structure:'1'}),on=getWork(prior.workId,{structure:'1',phraseLayers:'1',motifDiscovery:'1'});
  expect({main:projected(off),upper:projected(off.structureWork)}).toEqual(prior.stable);
  expect({main:projected(on),upper:projected(on.structureWork)}).toEqual(prior.stable);
  expect(getWorkScoreSha256(prior.workId)).toBe(prior.sourceSha);expect(off.motifDiscovery).toBeUndefined();
  const old=off.structureWork??off,current=on.structureWork??on,discovery=current.motifDiscovery;
  expect(discovery?.error).toBeUndefined();expect(discovery?.provenance.streamId).toBe(current.streamId);expect(discovery?.provenance.sourceId).toBe(current.sourceId);
  expect(current.phraseLayers?.error).toBeUndefined();
  const oldSpans=spansFor(old),newSpans=spansFor(current);expect(newSpans).toEqual(oldSpans);
  const comparison=compareMotifFamilies(current,newSpans);
  if(discovery.status==='ready'){
   expect(comparison.error).toBe(null);
   const {spans}=comparison;
   expect(spans.map(({linkedFamily,linkSources,...s})=>s)).toEqual(oldSpans);
   expect(motifFamilyDisplaySpans(spans,true).map(s=>[s.motifNumber,s.startIndex,s.endIndex,s.familyNumber])).toEqual(oldSpans.map(s=>[s.motifNumber,s.startIndex,s.endIndex,s.familyNumber]));
   for(const f of discovery.families)for(const o of f.occurrences){expect(o.startEventId).toBe(current.notes[o.startIndex].id);expect(o.endEventId).toBe(current.notes[o.endIndex].id);expect(o.eventIds).toEqual(current.notes.slice(o.startIndex,o.endIndex+1).map(n=>n.id))}
  }
  const cached=getWork(prior.workId,{structure:'1',phraseLayers:'1',motifDiscovery:'1'}),warm=(cached.structureWork??cached).motifDiscovery;
  expect(warm.provenance.cacheKey).toBe(discovery.provenance.cacheKey);expect(warm.runtime.cacheHit).toBe(true);
  const entry={workId:prior.workId,title:current.title,sourceId:current.sourceId,streamId:current.streamId,noteCount:current.notes.length,status:discovery.status,skipped:discovery.skipped??null,runtime:discovery.runtime,
   warmRuntime:warm.runtime,discoveredFamilies:discovery.families.length,oldSpanCount:oldSpans.length,oldFamilies:new Set(oldSpans.map(s=>s.familyNumber)).size,linkedFamilies:new Set(comparison.spans.map(s=>s.linkedFamily??s.familyNumber)).size,
   phraseCounts:{breath:current.phraseLayers.breath.ranges.length,upper:current.phraseLayers.phrases.ranges.length},warnings:discovery.inputWarnings??[],
   provenance:discovery.provenance,stable:prior.stable};
  works.push(entry);console.log(JSON.stringify({workId:entry.workId,status:entry.status,oldFamilies:entry.oldFamilies,linkedFamilies:entry.linkedFamilies,runtime:entry.runtime}));
 }
 expect(hashFiles(Object.keys(preserved))).toEqual(preserved);expect(hashFiles(Object.keys(engines))).toEqual(engines);
 writeFileSync(output,JSON.stringify({version:'motif-family-integration-regression/1',createdAt:new Date().toISOString(),database:baseline.database,preserved,engines,works},null,2));
},120000);
