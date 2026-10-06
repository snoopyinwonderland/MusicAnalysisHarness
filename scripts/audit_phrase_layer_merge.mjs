// Read-only live-work regression; generated receipts stay in Music Analysis.
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync,writeFileSync,existsSync,mkdirSync,statSync} from 'node:fs';
import {pathToFileURL} from 'node:url';
import path from 'node:path';
const [mode,root,output,baselinePath]=process.argv.slice(2);
assert(['baseline','compare'].includes(mode)&&root&&output);
assert(!existsSync(output),'Never overwrite a sealed receipt');
const sha=v=>createHash('sha256').update(typeof v==='string'||Buffer.isBuffer(v)?v:JSON.stringify(v)).digest('hex');
const preserved=['data/kysing-metadata/kumyoung-official-backfill-state.json','data/kysing-metadata/kumyoung-official-backfill.json','data/youtube-backfill-state.json','data/youtube-matches.json','docs/development-log.md','docs/ky-collection-log.md','docs/youtube-collection-log.md',...Array.from({length:7},(_,i)=>`docs/ky-collection/${i<3?'2026-09-'+(28+i):'2026-10-0'+(i-2)}.md`)];
const engines=['server/phrase-boundaries.mjs','server/boundary-harmony.mjs','server/phrase-evidence-ledger.mjs','server/structure-stream.mjs','server/sounding-evidence.mjs'];
const fileHashes=files=>Object.fromEntries(files.map(f=>[f,sha(readFileSync(path.join(root,f)))]));
const before={preserved:fileHashes(preserved),engines:fileHashes(engines)};
const dbStat=statSync(path.join(root,'data/search-index-v2/search.sqlite'));
const database={size:dbStat.size,mtimeMs:dbStat.mtimeMs};
const api=await import(pathToFileURL(path.join(root,'server/search-api.mjs')));
const baseline=mode==='compare'?JSON.parse(readFileSync(baselinePath,'utf8')):null;
const ids=baseline?.works.map(w=>w.workId)??[
 'work-fd275425506cc192','work-fd275425506cc192-5f596005',
 'work-f9eccdf1fc19fb03-88a85b71','work-33c3a5e1b3de42b9-a71ddd21',
 'work-4229f41fc20f9574','work-4b5fce9858d70665-142c87e9',
 'work-104a3e7d61b751c7-d08f9a8a','work-474e82a835aa3acb',
 'work-9b94778a6ef069b8','work-b4fdcba72f89a969',
];
const project=w=>w?Object.fromEntries(['workId','streamId','sourceId','notes','phraseAnalysis','boundaryHarmony','fullHarmony','phraseEvidenceLedger','structureSelection','stats'].filter(k=>k in w).map(k=>[k,sha(w[k])])):null;
const works=[];
for(const workId of ids){
 const t=performance.now();const off=api.getWork(workId,{structure:'1'});
 const elapsedMs=performance.now()-t;
 if(!off){works.push({workId,missing:true});console.log(JSON.stringify({workId,missing:true}));continue;}
 const stable={main:project(off),upper:project(off.structureWork)};
 const record={workId,title:off.title,sourceId:off.sourceId,streamId:off.streamId,upperStreamId:off.structureWork?.streamId??off.streamId,sourceSha:api.getWorkScoreSha256(workId),stable,defaultMs:elapsedMs};
 if(baseline){
  const prior=baseline.works.find(w=>w.workId===workId);
  assert.deepEqual(stable,prior.stable,`${workId}: legacy/default changed`);
  assert.equal(record.sourceSha,prior.sourceSha,'source changed');
  const t2=performance.now();const on=api.getWork(workId,{structure:'1',phraseLayers:'1'});record.enabledMs=performance.now()-t2;
  assert.deepEqual({main:project(on),upper:project(on.structureWork)},stable,`${workId}: enabled layer changes legacy`);
  assert(!off.phraseLayers,'Default must not compute new layers');
  const a=on.structureWork??on;record.layerError=a.phraseLayers?.error??null;
  assert(a.phraseLayers,'Flag did not reach upper structure stream');
  if(!record.layerError){
   record.layerRuntime=a.phraseLayers.runtime;
   assert.equal(a.phraseLayers.provenance.streamId,a.streamId);
   assert.equal(a.phraseLayers.provenance.sourceId,a.sourceId);
   for(const layer of ['breath','phrases'])for(const range of a.phraseLayers[layer]?.ranges??[]){
    assert.equal(range.startEventId,a.notes[range.startIndex]?.id);
    assert.equal(range.endEventId,a.notes[range.endIndexExclusive-1]?.id);
    assert(range.span.start.den>0&&range.span.end.den>0);
   }
   const t3=performance.now();const cached=api.getWork(workId,{structure:'1',phraseLayers:'1'});record.warmEnabledMs=performance.now()-t3;
   assert.equal((cached.structureWork??cached).phraseLayers.provenance.cacheKey,a.phraseLayers.provenance.cacheKey);
   record.cacheHit=(cached.structureWork??cached).phraseLayers.runtime.cacheHit;
   record.warmLayerRuntime=(cached.structureWork??cached).phraseLayers.runtime;
   record.layerCounts=Object.fromEntries(['breath','phrases'].map(l=>[l,a.phraseLayers[l]?.ranges.length??0]));
  }
 }
 works.push(record);console.log(JSON.stringify({workId,title:record.title,layerError:record.layerError,defaultMs:record.defaultMs,enabledMs:record.enabledMs,layerRuntime:record.layerRuntime,cacheHit:record.cacheHit}));
}
assert.deepEqual(fileHashes(preserved),before.preserved,'Pre-existing files changed during audit');
assert.deepEqual(fileHashes(engines),before.engines,'Legacy engine files changed');
if(baseline){assert.deepEqual(before.preserved,baseline.preserved);assert.deepEqual(before.engines,baseline.engines);assert.deepEqual(database,baseline.database);}
mkdirSync(path.dirname(output),{recursive:true});
writeFileSync(output,JSON.stringify({version:'phrase-layer-merge-regression/1',mode,createdAt:new Date().toISOString(),root,database,...before,works},null,2));
console.log(`Receipt ${output}`);
