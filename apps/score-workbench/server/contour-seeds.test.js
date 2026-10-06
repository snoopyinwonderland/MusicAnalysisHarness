import {it,expect} from 'vitest';
import {compareDetailedContour,detailedContour,contourString,contourSeedCandidates,CONTOUR_SEED_VERSION} from './contour-seeds.mjs';
import {DatabaseSync} from 'node:sqlite';
import {mkdtempSync,writeFileSync,statSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join,dirname} from 'node:path';
it('is invariant to global transposition and octave shift and ignores durations',()=>{
 const p=[60,60,64,67,65,62,64,60];expect(compareDetailedContour(p,p.map(x=>x+12)).score).toBe(100);expect(contourString(p)).toBe('SUUDDUD');
});
it('distinguishes relative leaps even with identical directions',()=>{
 const p=[60,62,64,66,68,66,64],q=[60,62,64,76,78,76,74];const r=compareDetailedContour(p,q);expect(r.direction).toBe(100);expect(r.relativeSteps).toBeLessThan(100);expect(r.score).toBeLessThan(100);
});
it('marks constant pitch as low-information, not distinctive evidence',()=>{expect(compareDetailedContour([60,60,60,60],[70,70,70,70]).status).toBe('low-information')});
it('preserves repeats and turning runs',()=>{expect(detailedContour([60,60,62,64,62,62]).runs).toEqual([{direction:'S',length:1},{direction:'U',length:2},{direction:'D',length:1},{direction:'S',length:1}])});
it('degrades under a local edit without all-or-nothing direction equality',()=>{const p=[60,62,65,64,67,69,65,60],q=[...p];q[3]++;expect(compareDetailedContour(p,q).score).toBeGreaterThan(75);expect(compareDetailedContour(p,q).score).toBeLessThan(100)});
it('retrieves a later corpus row, respects exclusion, and rejects a stale cached sidecar',()=>{
 const dir=mkdtempSync(join(tmpdir(),'contour-test-'));try{
  const source=join(dir,'source'),path=join(dir,'side.sqlite');writeFileSync(source,'fixture');const s=statSync(source),db=new DatabaseSync(path);
  db.exec('CREATE TABLE metadata(value TEXT); CREATE TABLE streams(id TEXT,contour TEXT,pitches TEXT)');db.prepare('INSERT INTO metadata VALUES(?)').run(JSON.stringify({version:CONTOUR_SEED_VERSION,sourceSize:s.size,sourceMtime:s.mtimeMs,complete:true}));
  const q=[60,62,65,64,67,69,65,60],p=q.map(x=>x+12),add=db.prepare('INSERT INTO streams VALUES(?,?,?)');add.run('first','UUUUUUU',Buffer.from([50,51,52,53,54,55,56,57]).toString('base64'));add.run('later',contourString(p),Buffer.from(p).toString('base64'));db.close();
  expect(contourSeedCandidates(path,source,q)[0].id).toBe('later');expect(contourSeedCandidates(path,source,q,{excluded:new Set(['later'])})).toHaveLength(0);
  writeFileSync(source,'changed-fixture');expect(()=>contourSeedCandidates(path,source,q)).toThrow('Stale');
 }finally{if(dirname(dir)===tmpdir()&&dir.startsWith(join(tmpdir(),'contour-test-')))rmSync(dir,{recursive:true,force:true})}
});
