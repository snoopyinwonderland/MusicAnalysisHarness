import {it,expect} from 'vitest';
import {DatabaseSync} from 'node:sqlite';
import {aggregateSqlSeeds} from './sql-seed-aggregation.mjs';
function legacy(db,rs){const maps=Object.fromEntries(['hits','intervalHits','intervalSeedEvidence','rhythmSeedEvidence','contourWorkEvidence','interval3Seeds','splitIntervalPositions'].map(k=>[k,new Map()]));
 const add=(m,k,n)=>m.set(k,(m.get(k)||0)+n);
 for(const r of rs){const rows=db.prepare('SELECT work_id,pos FROM grams WHERE token=? LIMIT ?').all(r.token,r.limit),contour=new Set();if(r.token.startsWith('i:'))maps.interval3Seeds.set(r.pos,rows.map(n=>n.work_id+'\u0000'+Math.max(0,n.pos-r.pos)));
 for(const n of rows){const key=n.work_id+'\u0000'+Math.max(0,n.pos-r.pos),i=r.token.startsWith('i:')||r.token.startsWith('i5:'),w=r.token.startsWith('i5:')?50:i?3:1;add(maps.hits,key,w);if(i){add(maps.intervalHits,key,1);add(maps.intervalSeedEvidence,key,w)}if(r.token.startsWith('r:'))add(maps.rhythmSeedEvidence,key,1);if(r.token.startsWith('c:'))contour.add(n.work_id);if(r.token.startsWith('i:')){if(!maps.splitIntervalPositions.has(key))maps.splitIntervalPositions.set(key,new Set());maps.splitIntervalPositions.get(key).add(r.pos)}}for(const id of contour)add(maps.contourWorkEvidence,id,1)}return maps;
}
const serialized=x=>JSON.stringify(Object.fromEntries(Object.entries(x).filter(([k])=>k!=='profile').map(([k,v])=>[k,[...v].map(([key,value])=>[key,value instanceof Set?[...value]:value])])));
it('preserves values and insertion order for duplicated tokens, clamped starts and unequal prefixes',()=>{
 const db=new DatabaseSync(':memory:');try{db.exec('CREATE TABLE grams(token TEXT,work_id TEXT,pos INTEGER); CREATE INDEX grams_token ON grams(token)');
 const put=db.prepare('INSERT INTO grams VALUES(?,?,?)');for(const token of ['i:x','i5:x','r:x','c:x'])for(const [work,pos] of [['z',0],['a',1],['z',1],['a',7],['z',0]])put.run(token,work,pos);
 const rs=[{token:'r:x',pos:2,limit:3},{token:'i:x',pos:3,limit:5},{token:'i:x',pos:4,limit:2},{token:'c:x',pos:1,limit:5},{token:'i5:x',pos:0,limit:4},{token:'i:absent',pos:5,limit:0}];
 expect(serialized(aggregateSqlSeeds(db,rs))).toBe(serialized(legacy(db,rs)));
 }finally{db.close()}
});
it('matches deterministic randomized fixtures in every map order',()=>{
 const db=new DatabaseSync(':memory:');let seed=17;const random=n=>{seed=(seed*1664525+1013904223)>>>0;return seed%n};
 try{db.exec('CREATE TABLE grams(token TEXT,work_id TEXT,pos INTEGER);CREATE INDEX grams_token ON grams(token)');const tokens=['i:a','i:b','i5:a','r:a','c:a'],put=db.prepare('INSERT INTO grams VALUES(?,?,?)');
 for(let j=0;j<300;j++)put.run(tokens[random(5)],'w'+random(9),random(20));
 for(let run=0;run<30;run++){const rs=Array.from({length:12},(_,pos)=>({token:tokens[random(5)],pos,limit:random(60)}));expect(serialized(aggregateSqlSeeds(db,rs))).toBe(serialized(legacy(db,rs)))}
 }finally{db.close()}
});
it('guards unsupported request sizes without changing the old path',()=>{expect(aggregateSqlSeeds(null,[]).hits.size).toBe(0);expect(aggregateSqlSeeds(null,Array(401).fill({}))).toBe(null);expect(()=>aggregateSqlSeeds(null,[{pos:-1,limit:2}])).toThrow()});
