export const normalizeWorkMetadata=value=>String(value??'').normalize('NFC').replace(/^composed by\s+/i,'').replace(/\s+/g,' ').trim().toLocaleLowerCase('en');

/** Explicit upload bindings only; a title match is never sufficient. */
export function resolveUploadIdentity(registry,indexIdentity,identity){
 if(registry.index.size!==indexIdentity?.size||registry.index.mtimeMs!==indexIdentity?.mtimeMs)return null;
 const binding=(registry.uploadBindings??[]).find(b=>b.status==='verified'&&b.sourceId===identity.sourceId&&b.workId===identity.workId&&b.evidence);
 return binding&&registry.families.some(f=>f.id===binding.canonicalWorkId&&f.status==='verified')?binding.canonicalWorkId:null;
}

/** Only a reviewed registry maps editions. Similar titles generate suggestions only. */
export function createWorkIdentityResolver(registry,indexIdentity){
  if(registry.schema!=='musicanote-work-identities/1')throw new Error('Unsupported work identity registry');
  const bySource=new Map(),ids=new Set();
  for(const family of registry.families){
    if(!family.id||ids.has(family.id))throw new Error('Duplicate or missing canonical work ID');ids.add(family.id);
    if(family.status!=='verified')continue;
    if(!family.evidence?.method||!family.evidence?.reference)throw new Error('Verified identity requires evidence');
    for(const edition of family.editions){
      if(bySource.has(edition.sourceId))throw new Error('Conflicting source mapping');
      bySource.set(edition.sourceId,{family,edition});
    }
  }
  const current=registry.index.size===indexIdentity?.size&&registry.index.mtimeMs===indexIdentity?.mtimeMs;
  return work=>{
    const mapped=bySource.get(work.sourceId);
    if(!mapped)return null;
    if(!current)return {status:'stale-index'};
    if(normalizeWorkMetadata(work.title)!==normalizeWorkMetadata(mapped.family.title)||normalizeWorkMetadata(work.artist)!==normalizeWorkMetadata(mapped.family.composer))return {status:'metadata-conflict'};
    return {status:'verified',canonicalWorkId:mapped.family.id,registryVersion:registry.version,
      evidence:mapped.family.evidence,edition:mapped.edition};
  };
}

export function suggestWorkFamilies(runs){
  const buckets=new Map();
  for(const run of runs)for(const result of [...(run.result?.exact??[]),...(run.result?.similar??[])]){
    const w=result.work,title=normalizeWorkMetadata(w.title),composer=normalizeWorkMetadata(w.artist);
    if(!title||!composer||composer==='unknown'||!w.sourceId)continue;
    const key=JSON.stringify([title,composer]);if(!buckets.has(key))buckets.set(key,new Map());
    buckets.get(key).set(w.sourceId,{sourceId:w.sourceId,title:w.title,composer:w.artist});
  }
  return [...buckets.values()].filter(b=>b.size>1).map(b=>({status:'needs-review',reason:'same-normalized-title-and-composer',editions:[...b.values()],automaticMerge:false}));
}
