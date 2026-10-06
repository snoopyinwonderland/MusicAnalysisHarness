import {it,expect} from 'vitest';
// @ts-expect-error Server adapter used as integration test fixture.
import {phraseEvidenceLedger} from '../../server/phrase-evidence-ledger.mjs';
// @ts-expect-error Server analyzer used as integration test fixture.
import {analyzePhraseBoundaries} from '../../server/phrase-boundaries.mjs';
import {pillarCandidates} from './pillarCandidates';
import {comparePillarGaps} from './pillarGapAudit';
import type {CorpusNote} from '../types';
const candidates=(ns:CorpusNote[])=>pillarCandidates(ns,{meters:{1:{count:4,unit:4}}});
const notes=[0,1,2,5,6,7].map((onset,i)=>({id:`n${i}`,onset,durationRatio:1,pitchMidi:60+i,measure:1,beat:onset+1})) as CorpusNote[];
function setup(){const traces:unknown[]=[];const a=analyzePhraseBoundaries(notes,{traceSink:(t:unknown)=>traces.push(t)});
 return phraseEvidenceLedger(notes,a,{xml:'<score/>',streamId:'P1',analyzerRevision:'test',gapTraces:traces});}
it('identifies shared raw duration/onsets without changing either analysis',async()=>{
 const ledger=setup(),c=candidates(notes),before=JSON.stringify({ledger,c,notes});
 const result=await comparePillarGaps(notes,c,ledger,'<score/>','P1');
 expect(result.length).toBeGreaterThan(0);expect(result[0].status).toBe('compared');
 expect(result[0].shared.length).toBeGreaterThanOrEqual(3);
 expect(JSON.stringify({ledger,c,notes})).toBe(before);
});
it('rejects stale inputs, XML, streams and missing observation references',async()=>{
 const ledger=setup(),c=candidates(notes);
 for(const [ns,xml,stream] of [[notes,'wrong','P1'],[notes,'<score/>','P2'],[notes.map(n=>({...n,durationRatio:2})),'<score/>','P1']] as [CorpusNote[],string,string][]){
  const r=await comparePillarGaps(ns,c,ledger,xml,stream);expect(r.every(x=>x.status==='unverified'&&x.shared.length===0)).toBe(true);
 }
 ledger.observations=[];
 expect((await comparePillarGaps(notes,c,ledger,'<score/>','P1'))[0].status).toBe('unverified');
});
it('does not interpret an absent or partial gap rule as unused evidence',async()=>{
 const ledger=setup();ledger.records=[];
 expect((await comparePillarGaps(notes,candidates(notes),ledger,'<score/>','P1'))[0].status).toBe('unverified');
});
