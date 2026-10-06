import {it,expect} from 'vitest';
import {mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {DatabaseSync} from 'node:sqlite';
import {createSearchWorker} from './search-worker-client.mjs';
import {intervalTokens,frequencyEvidence,compareCorpusPriority} from './preclearance-frequency.mjs';
const events=p=>p.map(pitchMidi=>({kind:'note',pitchMidi}));
it('counts source files once across multiple parts and repeated postings',async()=>{
 const dir=mkdtempSync(join(tmpdir(),'musicanote-frequency-')),dbPath=join(dir,'fixture.sqlite');
 const db=new DatabaseSync(dbPath);db.exec("CREATE TABLE works(id TEXT,source TEXT); CREATE TABLE grams(token TEXT,work_id TEXT); INSERT INTO works VALUES('1','a'),('2','a'),('3','b'); INSERT INTO grams VALUES('i5:0,0,0,0,0','1'),('i5:0,0,0,0,0','1'),('i5:0,0,0,0,0','2');");db.close();
 const client=createSearchWorker({url:new URL('./frequency-worker.mjs',import.meta.url),timeoutMs:5000});
 try{const r=await client.search({dbPath,tokens:['i5:0,0,0,0,0','absent']},0);expect(r).toEqual({totalSources:2,counts:{'i5:0,0,0,0,0':1,absent:0}});}
 finally{await client.close();rmSync(dir,{recursive:true,force:true})}
});
it('uses index-compatible unique 5-interval tokens, invariant to transposition',()=>{
 expect(intervalTokens(events([60,62,64,65,67,69]))).toEqual(['i5:2,2,1,2,2']);
 expect(intervalTokens(events([67,69,71,72,74,76]))).toEqual(['i5:2,2,1,2,2']);
 expect(intervalTokens(events([60,60,60,60,60,60,60]))).toEqual(['i5:0,0,0,0,0']);
});
it('rare observed grams are less penalized than common grams',()=>{
 expect(frequencyEvidence(['a'],{a:1},100).factor).toBeGreaterThan(frequencyEvidence(['a'],{a:100},100).factor);
 expect(frequencyEvidence(['a'],{a:100},100).factor).toBe(.85);
});
it('does not interpret absent or invalid evidence as originality',()=>{
 for(const counts of [{},{a:0},{a:101},{a:-1}])expect(frequencyEvidence(['a'],counts,100).factor).toBeNull();
 expect(frequencyEvidence([],{},100).factor).toBeNull();
});
it('keeps original and baseline reports intact',()=>{
 const r={runs:[{taskId:'t',selection:{task:{query:{events:events([60,60,60,60,60,60])}}}}],works:[{key:'w',title:'x',matches:[{taskId:'t'}],priorityAssessment:{score:90,assessments:[{index:0,score:90}]}}],priorityReview:{ranking:[{key:'w',reviewRank:1}]}};
 const out=compareCorpusPriority(r,{counts:{'i5:0,0,0,0,0':100},totalSources:100});
 expect(out.works).toEqual(r.works);expect(out.priorityReview).toEqual(r.priorityReview);expect(out.corpusPriorityReview.ranking[0].score).toBeCloseTo(76.5);expect(r.corpusPriorityReview).toBeUndefined();
});
