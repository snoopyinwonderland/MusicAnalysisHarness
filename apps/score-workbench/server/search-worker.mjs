import {parentPort} from 'node:worker_threads';
import {searchDatabase} from './search-api.mjs';
parentPort.on('message',({query,limit,trace})=>{
  try {parentPort.postMessage({result:searchDatabase(query,limit,{onProgress:trace?progress=>parentPort.postMessage({type:'progress',progress}):undefined})});}
  catch(error){parentPort.postMessage({error:String(error.message??error)});}
});
