import {it,expect} from 'vitest';
import {checkpointCache} from './cache-checkpoint.mjs';
it('commits complete batches while retaining a short pending tail',()=>{
 const pending=new Map(),saved=new Map();let calls=0;
 const flush=()=>{calls++;for(const [k,v] of pending)saved.set(k,v);pending.clear()};
 for(let i=0;i<70;i++){pending.set(i,{meter:'6/8'});checkpointCache(pending,flush,()=>{})}
 expect(calls).toBe(2);expect(saved.size).toBe(64);expect(pending.size).toBe(6);
});
it('does not propagate persistence errors into musical processing',()=>{
 const pending=new Map(Array.from({length:32},(_,i)=>[i,'3/4']));let failed=false;
 expect(()=>checkpointCache(pending,()=>{throw new Error('disk full')},()=>{failed=true})).not.toThrow();expect(failed).toBe(true);expect(pending.get(0)).toBe('3/4');
});
it('supports a legacy control with no intermediate writes',()=>{
 const pending=new Map([[1,1]]);expect(checkpointCache(pending,()=>{throw Error()},()=>{},{minimum:1,enabled:false})).toBe(false);
});
