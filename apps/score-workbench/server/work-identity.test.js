import {it,expect} from 'vitest';
import {readFileSync} from 'node:fs';
import {createWorkIdentityResolver,suggestWorkFamilies} from './work-identity.mjs';
import {aggregatePreclearanceResults} from './preclearance-search.mjs';
const registry=()=>({schema:'musicanote-work-identities/1',version:'test',index:{size:1,mtimeMs:2},families:[{id:'c1',title:'Song',composer:'Person',status:'verified',evidence:{method:'review',reference:'fixture'},editions:[{sourceId:'a',rightsStatus:'unknown'},{sourceId:'b',rightsStatus:'unknown'}]}]});
it('requires reviewed source mapping and matching metadata/index',()=>{
 const resolve=createWorkIdentityResolver(registry(),{size:1,mtimeMs:2});
 expect(resolve({sourceId:'a',title:' SONG ',artist:'Composed by Person'}).canonicalWorkId).toBe('c1');
 expect(resolve({sourceId:'unmapped',title:'Song',artist:'Person'})).toBe(null);
 expect(resolve({sourceId:'a',title:'Song',artist:'Other'}).status).toBe('metadata-conflict');
 expect(createWorkIdentityResolver(registry(),{size:1,mtimeMs:3})({sourceId:'a'}).status).toBe('stale-index');
});
it('rejects conflicting membership and ignores pending candidates',()=>{
 const r=registry();r.families[0].editions.push({sourceId:'a'});
 expect(()=>createWorkIdentityResolver(r,r.index)).toThrow('Conflicting');
 r.families[0].status='needs-review';
 expect(createWorkIdentityResolver(r,r.index)({sourceId:'a'})).toBe(null);
});
it('suggests matching metadata without automatically merging homonymous works',()=>{
 const works=[{sourceId:'a',title:'Song',artist:'Person'},{sourceId:'b',title:'Song',artist:'Person'},{sourceId:'c',title:'Song',artist:'Other'}];
 const suggestions=suggestWorkFamilies([{result:{exact:works.map(work=>({work}))}}]);
 expect(suggestions).toHaveLength(1);expect(suggestions[0].editions).toHaveLength(2);expect(suggestions[0].automaticMerge).toBe(false);
});
it('merges the verified real editions without losing alignments or inflating score',()=>{
 const report=JSON.parse(readFileSync(new URL('../evaluation/runs/preclearance-search-2026-09-14.json',import.meta.url),'utf8'));
 const r=JSON.parse(readFileSync(new URL('../data/work-identities.json',import.meta.url),'utf8'));
 const before=aggregatePreclearanceResults(null,report.runs),after=aggregatePreclearanceResults(null,report.runs,createWorkIdentityResolver(r,report.runtime.database));
 expect(after.length).toBe(before.length-2);
 const group=after.find(w=>w.canonicalWorkId==='composition-endless-love-lionel-richie');
 expect(group.editionCount).toBe(3);expect(group.matches).toHaveLength(23);expect(group.similarity).toBe(100);expect(group.coverage).toBe(1);
 expect(group.matches.every(m=>m.alignment.length&&m.rightsStatus==='unknown')).toBe(true);
 expect(after.reduce((s,w)=>s+w.matches.length,0)).toBe(before.reduce((s,w)=>s+w.matches.length,0));
});
