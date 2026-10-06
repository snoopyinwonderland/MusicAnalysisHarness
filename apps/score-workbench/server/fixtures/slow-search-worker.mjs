import {parentPort} from 'node:worker_threads';
parentPort.on('message',({query})=>{
  if(query.progress)parentPort.postMessage({type:'progress',progress:{stage:'started'}});
  if(query.hang)while(true){}
  parentPort.postMessage({result:{value:query.value}});
});
