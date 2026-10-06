import {it,expect} from 'vitest';
import {createSearchWorker} from './search-worker-client.mjs';
const url=new URL('./fixtures/slow-search-worker.mjs',import.meta.url);
it('does not treat progress as completion and retains it before timeout',async()=>{
 const client=createSearchWorker({url,timeoutMs:500}),events=[];
 try{expect(await client.search({progress:true,value:7},1,{onProgress:e=>events.push(e)})).toEqual({value:7});
  await expect(client.search({progress:true,hang:true},1,{onProgress:e=>events.push(e)})).rejects.toThrow('timed out');expect(events).toHaveLength(2);
 }finally{await client.close()}
});
it('terminates synchronous work on timeout and can start another worker',async()=>{
 const client=createSearchWorker({url,timeoutMs:500});
 try{await expect(client.search({hang:true},1)).rejects.toThrow('timed out');expect(await client.search({value:3},1)).toEqual({value:3});}finally{await client.close();}
});
it('cancels active work and rejects already cancelled requests',async()=>{
 const client=createSearchWorker({url,timeoutMs:5000}),controller=new AbortController();
 try{const pending=client.search({hang:true},1,{signal:controller.signal});controller.abort();await expect(pending).rejects.toThrow('cancelled');await expect(client.search({},1,{signal:controller.signal})).rejects.toThrow('cancelled');}finally{await client.close();}
});
