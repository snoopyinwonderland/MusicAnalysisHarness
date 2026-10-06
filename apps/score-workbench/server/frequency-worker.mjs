import {parentPort} from 'node:worker_threads';
import {DatabaseSync} from 'node:sqlite';
parentPort.on('message',({query})=>{
 let db;
 try{
  db=new DatabaseSync(query.dbPath,{readOnly:true});db.exec('PRAGMA query_only=ON; PRAGMA cache_size=-65536;');
  const sources=new Map(db.prepare('SELECT id,source FROM works').all().map(r=>[r.id,r.source]));
  const totalSources=new Set(sources.values()).size;
  const statement=db.prepare('SELECT DISTINCT work_id FROM grams WHERE token=?');
  const counts=Object.fromEntries(query.tokens.map(token=>{
   const found=new Set();for(const row of statement.iterate(token)){
    if(!sources.has(row.work_id))throw new Error('Orphan gram posting');found.add(sources.get(row.work_id));
   }return [token,found.size];
  }));
  parentPort.postMessage({result:{totalSources,counts}});
 }catch(error){parentPort.postMessage({error:String(error.message??error)})}
 finally{db?.close()}
});
