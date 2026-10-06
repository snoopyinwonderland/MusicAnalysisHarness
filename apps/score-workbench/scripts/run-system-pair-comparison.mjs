import {readFileSync,writeFileSync,mkdirSync,existsSync} from 'node:fs';
import {resolve,join} from 'node:path';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {DatabaseSync} from 'node:sqlite';
import {analyzeStructureSnapshot} from '../server/structure-analysis-adapter.mjs';
import {selectStructureQueries,SELECTION_CONFIG} from '../server/preclearance-search.mjs';
const out=resolve(process.argv[2]||'');if(!process.argv[2]||existsSync(out))throw Error('NEW directory required');mkdirSync(out,{recursive:true});mkdirSync(join(out,'xml'));
const save=(name,value)=>writeFileSync(join(out,name),JSON.stringify(value,null,2),{flag:'wx'});
// Only parsed source data is consumed: no annotations, nominated measures or labels.
const records=['upload','reference'].map(role=>JSON.parse(readFileSync(`evaluation/runs/real-pair-input-audit-v1/RC-004-${role}.json`)));
const works=records.map((r,i)=>{const name=`source-${i}.xml`;writeFileSync(join(out,'xml',name),readFileSync(r.path));return {...r.parsed,id:'pair-source-'+i,source:name,title:i?'Ma Boy':'Twinkle',normalizedTitle:i?'ma boy':'twinkle',metadata:{accessPolicy:'research-preview'}};});
writeFileSync(join(out,'works.jsonl'),works.map(w=>JSON.stringify(w)).join('\n')+'\n');
execFileSync(process.execPath,['scripts/build-search-sqlite.mjs',join(out,'works.jsonl'),join(out,'search.sqlite')],{stdio:'inherit'});
process.env.MUSICANOTE_SEARCH_DB=join(out,'search.sqlite');process.env.MUSICANOTE_METER_CONTEXT_DB=join(out,'meter.sqlite');process.env.MUSICANOTE_MUSICXML_ROOT=join(out,'xml')+'/';delete process.env.MUSICANOTE_CONTOUR_SIDECAR;
process.env.MUSICANOTE_RETRIEVAL_CACHE='1';
const {searchDatabase}=await import('../server/search-api.mjs');
const db=new DatabaseSync(join(out,'search.sqlite'),{readOnly:true}),indexed=db.prepare('SELECT id,source,stream_id FROM works').all();db.close();
const runs=[],selections=[];
for(let i=0;i<works.length;i++)for(const stream of works[i].streams){
 const record=records[i],part=record.parts.find(p=>p.partId===stream.part),events=stream.notes.map((n,j)=>({id:`s${i}-${stream.id}-${j}`,kind:'note',pitchMidi:n.p,spelling:n.s,onset:n.o,durationRatio:n.d,measure:n.mn,measureOrdinal:n.m,beat:n.b,meter:part.measures[n.m-1].meter,partId:stream.part,voice:stream.voice,staff:stream.staff}));
 const snapshot=analyzeStructureSnapshot({identity:{sourceId:works[i].source,streamId:stream.id,melodyRoleScore:stream.role},sourceHash:record.parsed.hash,parserVersion:'existing-audit',meter:'4/4',events});
 const selection=selectStructureQueries(snapshot,{...SELECTION_CONFIG,segmentStrategy:'hybrid'});selections.push({source:works[i].title,streamId:stream.id,noteCount:events.length,selection});
 for(const selected of selection.selected){const query={...selected.task.query,scopeWorkIds:indexed.filter(r=>r.source===works[1-i].source).map(r=>r.id)};const stages=[];const start=performance.now();
  const result=searchDatabase(query,100,{onProgress:e=>{if(['retrieval-inventory','candidate-rejected','evaluation-end','ranked-inventory'].includes(e.stage))stages.push(e)}});
  const run={source:works[i].title,streamId:stream.id,taskId:selected.task.taskId,query,result,elapsedMs:performance.now()-start,stages};runs.push(run);save(`task-${runs.length}.json`,run);console.log(JSON.stringify({task:runs.length,source:run.source,stream:stream.id,exact:result.exact.length,similar:result.similar.length,ms:Math.round(run.elapsedMs)}));
 }
}
save('report.json',{schema:'system-pair-comparison/1',engine:'server/search-api.mjs::searchDatabase',engineHash:createHash('sha256').update(readFileSync('server/search-api.mjs')).digest('hex'),createdAt:new Date().toISOString(),humanAnnotationsUsed:false,humanRegionsUsed:false,experimentalSegmentComparisonUsed:false,legalDetermination:false,scope:'two-source corpus; all parsed streams; automatic hybrid selection; not exhaustive',sourceHashes:records.map(r=>r.parsed.hash),selections,runs});
