import {it,expect} from 'vitest';
import {analyzePhraseBoundaries} from './phrase-boundaries.mjs';
import {phraseEvidenceLedger} from './phrase-evidence-ledger.mjs';
const notes=[0,1,2,5,6,7].map((onset,i)=>({id:`n${i}`,onset,durationRatio:1,pitchMidi:60+i}));
const context={xml:'<score/>',streamId:'P1:1:1',analyzerRevision:'test-code'};
it('records real phrase cues and gap inputs without changing the analysis',()=>{
 const analysis=analyzePhraseBoundaries(notes),before=JSON.stringify({notes,analysis});
 const ledger=phraseEvidenceLedger(notes,analysis,context);
 expect(ledger.records.length).toBe(analysis.boundaries.reduce((n,b)=>n+b.cues.length,0));
 const gap=ledger.records.find(r=>r.ruleId==='observed-gap');expect(gap.observationRefs).toHaveLength(3);
 expect(ledger.observations.find(o=>o.index===3&&o.field==='onset').value).toBe(5);
 expect(ledger.complete).toBe(false);expect(ledger.autoApply).toBe(false);expect(JSON.stringify({notes,analysis})).toBe(before);
});
it('binds IDs to input, XML, stream and engine revision',()=>{
 const a=analyzePhraseBoundaries(notes),first=phraseEvidenceLedger(notes,a,context);
 expect(phraseEvidenceLedger(notes,a,context)).toEqual(first);
 for(const c of [{...context,xml:'changed'},{...context,streamId:'other'},{...context,analyzerRevision:'new'}])expect(phraseEvidenceLedger(notes,a,c).runId).not.toBe(first.runId);
 expect(phraseEvidenceLedger(notes.map(n=>({...n,durationRatio:2})),a,context).inputRevision).not.toBe(first.inputRevision);
});
it('does not invent full lineage for unknown rules or missing onset values',()=>{
 const a={version:'test',boundaries:[{index:1,cues:[{name:'new-rule',strength:1},{name:'observed-gap',strength:1}]}]};
 const l=phraseEvidenceLedger([{durationRatio:1},{}],a,context);
 expect(l.records.every(r=>!r.complete)).toBe(true);expect(l.tracedCueCount).toBe(0);
 expect(l.records[0].observationRefs).toEqual([]);
});
it('traces the local gap unit and preserves every boundary when tracing is enabled',()=>{
 const before=JSON.stringify(notes),traces=[];
 const baseline=analyzePhraseBoundaries(notes),traced=analyzePhraseBoundaries(notes,{traceSink:t=>traces.push(t)});
 expect(traced).toEqual(baseline);expect(JSON.stringify(notes)).toBe(before);
 const l=phraseEvidenceLedger(notes,traced,{...context,gapTraces:traces});
 const gap=l.records.find(r=>r.ruleId==='observed-gap');
 expect(gap.complete).toBe(true);expect(gap.trace.unitTrace.unit).toBe(1);
 expect(gap.trace.gapQuarters).toBe(2);expect(gap.trace.unitTrace.reads.length).toBeGreaterThan(3);
 expect(gap.selectionObservationRefs.length).toBe(notes.length*2);
 expect(l.complete).toBe(false);expect(l.autoApply).toBe(false);
});
it('keeps a gap trace incomplete if neighboring timing was inferred',()=>{
 const ns=structuredClone(notes);delete ns[0].onset;const traces=[];
 const a=analyzePhraseBoundaries(ns,{traceSink:t=>traces.push(t)});
 const l=phraseEvidenceLedger(ns,a,{...context,gapTraces:traces});
 expect(l.records.filter(r=>r.ruleId==='observed-gap').every(r=>!r.complete)).toBe(true);
});
