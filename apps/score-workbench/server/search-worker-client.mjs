import {Worker} from 'node:worker_threads';

/** One persistent worker preserves bounded caches; termination interrupts sync SQL/JS. */
export function createSearchWorker({url=new URL('./search-worker.mjs',import.meta.url),timeoutMs=180000}={}) {
  if(!Number.isFinite(timeoutMs)||timeoutMs<=0)throw new Error('Positive timeoutMs required');
  let worker=null,busy=false;
  return {
    async search(query,limit,{signal,onProgress}={}){
      if(busy)throw new Error('Search worker is busy');
      if(signal?.aborted)throw new Error('Search cancelled');
      busy=true;worker??=new Worker(url);const current=worker;
      return new Promise((resolve,reject)=>{
        let settled=false;
        const finish=async(error,result,terminate=false)=>{
          if(settled)return;settled=true;clearTimeout(timer);
          signal?.removeEventListener('abort',abort);
          current.off('message',message);current.off('error',failure);current.off('exit',exit);
          if(terminate){worker=null;await current.terminate();}
          busy=false;error?reject(error):resolve(result);
        };
        const abort=()=>finish(new Error('Search cancelled'),null,true);
        const message=payload=>{if(payload.type==='progress'){try{onProgress?.(payload.progress)}catch{}return;}finish(payload.error?new Error(payload.error):null,payload.result);};
        const failure=error=>finish(error,null,true);
        const exit=code=>finish(new Error(`Search worker exited (${code})`),null,true);
        const timer=setTimeout(()=>finish(new Error(`Search timed out after ${timeoutMs}ms`),null,true),timeoutMs);
        current.on('message',message);current.once('error',failure);current.once('exit',exit);
        signal?.addEventListener('abort',abort,{once:true});
        if(signal?.aborted)abort();else current.postMessage({query,limit,trace:typeof onProgress==='function'});
      });
    },
    async close(){if(worker){const current=worker;worker=null;await current.terminate();}}
  };
}
