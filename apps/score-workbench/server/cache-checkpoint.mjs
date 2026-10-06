/** Persistence is optional: a failed checkpoint must not alter parsed music data. */
export function checkpointCache(pending,flush,onFailure,{minimum=32,enabled=true}={}){
 if(!enabled||pending.size<minimum)return false;
 try{flush();return true}catch(error){onFailure(error);return false}
}
