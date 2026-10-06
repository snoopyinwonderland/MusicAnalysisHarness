import {it,expect} from 'vitest';
import {createRetrievalCache} from './retrieval-cache.mjs';
it('preserves SQL row order and arguments, evicts within budget, invalidates by index',()=>{
 const cache=createRetrievalCache(128);cache.reset('v1');let calls=0;
 const load=()=>{calls++;return [{pos:3},{pos:1}];};
 expect(cache.get('a:2',load).value).toEqual([{pos:3},{pos:1}]);
 expect(cache.get('a:2',load).hit).toBe(true);expect(calls).toBe(1);
 cache.get('a:3',load);cache.get('b:2',load);expect(cache.stats().bytes).toBeLessThanOrEqual(128);
 expect(cache.get('a:2',load).hit).toBe(false);
 cache.reset('v2');expect(cache.get('a:2',load).hit).toBe(false);
});
