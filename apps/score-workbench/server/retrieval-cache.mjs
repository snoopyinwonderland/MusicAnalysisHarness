/** Cache exact SQL arguments; never change row order, limits or admission. */
export function createRetrievalCache(maxBytes=32*1024*1024){
  const entries=new Map();let bytes=0,version=null;
  return {
    reset(next){if(next!==version){entries.clear();bytes=0;version=next;}},
    get(key,load,weight=()=>64){
      if(entries.has(key)){const item=entries.get(key);entries.delete(key);entries.set(key,item);return {value:item.value,hit:true};}
      const value=load(),size=weight(value);
      if(size<=maxBytes){while(bytes+size>maxBytes&&entries.size){const [old,item]=entries.entries().next().value;entries.delete(old);bytes-=item.size;}entries.set(key,{value,size});bytes+=size;}
      return {value,hit:false};
    },
    stats(){return {entries:entries.size,bytes};}
  };
}
