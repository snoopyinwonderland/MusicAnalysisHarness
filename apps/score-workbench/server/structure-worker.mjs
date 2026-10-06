import {parentPort} from 'node:worker_threads';
import {getStructureSource} from './search-api.mjs';
import {analyzeStructureSnapshot,structureHash} from './structure-analysis-adapter.mjs';
parentPort.on('message',({query})=>{
 try{
  const source=getStructureSource(query.workId);
  if(source.events.length>query.maxNotes)throw new Error(`Stream exceeds ${query.maxNotes} attack budget; deferred, not truncated`);
  const snapshot=analyzeStructureSnapshot({...source,sourceHash:structureHash(source)});
  snapshot.warnings.push(...(source.warnings??[]));parentPort.postMessage({result:snapshot});
 }catch(error){parentPort.postMessage({error:String(error.message??error)})}
});
