import {createHash} from 'node:crypto';
import {createRetrievalCache} from './retrieval-cache.mjs';

// v8 serialization can differ between equal cloned objects (integer/double
// storage representation), so use a stable content key instead.
const stable=value=>{
 if(value===null)return 'null';
 if(Array.isArray(value))return '['+value.map(stable).join(',')+']';
 if(typeof value==='object')return '{'+Object.keys(value).sort().map(key=>JSON.stringify(key)+':'+stable(value[key])).join(',')+'}';
 return typeof value+':'+(typeof value==='number'&&!Number.isFinite(value)?String(value):String(JSON.stringify(value)??value));
};

// Process-local only. Hash every input property, not just pitches/durations.
// Values are private, read-only analyses; callers must not mutate them.
export function createPhraseContextCache(analyze,{maxBytes=64*1024*1024,version='1'}={}){
 const cache=createRetrievalCache(maxBytes);
 return {
  get(notes,revision=version){
   cache.reset(revision);
   const key=createHash('sha256').update(stable(notes)).digest('hex');
   const cached=cache.get(key,()=>{
    const result=analyze(notes);
    // Candidate side of comparePhraseBoundaries reads these four fields only.
    // Do not use this projection as a query-side analysis or report artifact.
    const length=result.boundaries.length,numbers=new Float64Array(length*2),flags=new Uint8Array(length);
    result.boundaries.forEach((b,i)=>{numbers[i*2]=b.strength;numbers[i*2+1]=b.continuity;flags[i]=Number(Boolean(b.supported))|Number(Boolean(b.reliable))*2});
    return {version:result.version,numbers,flags};
   },value=>512+value.numbers.byteLength+value.flags.byteLength);
   const packed=cached.value;
   // comparePhraseBoundaries only accesses length and mapped indices. Avoid
   // expanding thousands of unused boundary objects on every cache hit.
   const boundaries=new Proxy({length:packed.flags.length},{get(target,key){
    if(key==='length')return target.length;
    const index=typeof key==='string'?Number(key):NaN;
    if(!Number.isInteger(index)||index<0||index>=target.length)return undefined;
    return {strength:packed.numbers[index*2],continuity:packed.numbers[index*2+1],supported:Boolean(packed.flags[index]&1),reliable:Boolean(packed.flags[index]&2)};
   }});
   return {hit:cached.hit,value:{version:packed.version,boundaries}};
  },
  stats:()=>cache.stats()
 };
}
