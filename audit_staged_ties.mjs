import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {analyzePhraseBoundaries} from 'file:///K:/MusicSearch/server/phrase-boundaries.mjs';
const root='reports/tie-staging-2026-09-22';
const rows=JSON.parse(fs.readFileSync(path.join(root,'staged-rows.json'))),summary=[];
const toNotes=raw=>raw.map((n,i)=>({id:`staged-${i}`,kind:'note',pitchMidi:n.p,spelling:n.s,onset:n.o,durationRatio:n.d,measure:n.m,beat:n.b,tieStart:Boolean(n.ts),tieStop:Boolean(n.te),tieEndMeasure:n.tm,
 // Evidence only: never overwrite projected durationRatio or invent a new attack.
 ...(Number.isFinite(n.sd)?{soundingEvidence:{durationQuarters:n.sd,endMeasureOrdinal:n.stm,origin:'validated-source-tie'}}:{})}));
for(const row of rows){
 const previous=JSON.parse(fs.readFileSync(`reports/production-tie-notation-2026-09-22/${row.case}/parser-check.json`)).before;
 const old=previous.streams.find(s=>s.id===row.stream).notes;
 const snap=JSON.parse(fs.readFileSync(`reports/phrase-consistency-2026-09-22/${row.case}/snapshot.json`));
 const work=snap.work??snap;
 // Preserve the API's meter/notation context for the selected reviewed stream.
 // New attacks inherit only measure meter, never another note's breath labels.
 const reviewed=work.streamId===row.stream;
 const enrich=ns=>ns.map(n=>{
  if(!reviewed)return n;
  const exact=work.notes.find(x=>x.onset===n.onset&&x.pitchMidi===n.pitchMidi);
  const meter=work.notes.find(x=>(x.measureOrdinal??x.measure)===n.measure);
  return {...(exact??{}),...n,...(meter?{meterCount:meter.meterCount,meterUnit:meter.meterUnit}:{}),measureOrdinal:n.measure};
 });
 const before=analyzePhraseBoundaries(enrich(toNotes(old))),notes=enrich(toNotes(row.notes)),after=analyzePhraseBoundaries(notes);
 const withoutEvidence=analyzePhraseBoundaries(notes.map(({soundingEvidence,...n})=>n));
 if(JSON.stringify(after)!==JSON.stringify(withoutEvidence))throw Error('Evidence unexpectedly affected scoring');
 // Match unique time/pitch anchors, never carry old integer indices across insertion.
 const key=n=>`${n.o}:${n.p}`,positions=new Map();
 row.notes.forEach((n,i)=>{const k=key(n);positions.set(k,[...(positions.get(k)||[]),i]);});
 const mappings=old.map((n,i)=>{const matches=positions.get(key(n))??[];return {oldIndex:i,newIndex:matches.length===1?matches[0]:null,status:matches.length===1?'mapped':'unresolved'};});
 const differences=mappings.filter(m=>m.newIndex!==null).flatMap(m=>{
  const a=before.boundaries[m.oldIndex],b=after.boundaries[m.newIndex];
  return a.supported!==b.supported||a.strength!==b.strength?[{...m,onset:old[m.oldIndex].o,pitch:old[m.oldIndex].p,before:a,after:b}]:[];
 });
 const oldKeys=new Set(old.map(key)),added=row.notes.map((n,i)=>({n,i})).filter(({n})=>!oldKeys.has(key(n))).map(({n,i})=>({index:i,measure:n.m,onset:n.o,pitch:n.p,boundary:after.boundaries[i]}));
 const preferences=reviewed?({'S-STRUCT-005':{keep:[33,46,79],suppress:[31,37,43,77]},'S-STRUCT-006':{keep:[13,29,42,57],suppress:[51]}}[row.case]):null;
 const checks=preferences?Object.entries(preferences).flatMap(([want,indices])=>indices.map(i=>{const m=mappings[i];return {oldIndex:i,newIndex:m?.newIndex,expected:want,status:'documented-preference-not-gold',matchesPreference:m?.newIndex==null?null:after.boundaries[m.newIndex].supported===(want==='keep')};})):[];
 const report={case:row.case,stream:row.stream,sourceHash:row.sourceHash,notes,before,after,mappings,differences,added,checks,evidenceDoesNotAffectScoring:true};
 fs.writeFileSync(path.join(root,row.case,row.stream.replaceAll(':','-')+'-regression.json'),JSON.stringify(report));
 summary.push({case:row.case,stream:row.stream,beforeNotes:old.length,afterNotes:notes.length,unresolved:mappings.filter(m=>m.newIndex===null).length,changedBoundaries:differences.length,addedAttacks:added.length,evidenceNotes:notes.filter(n=>n.soundingEvidence).length,preferenceChecks:checks.length,preferenceMismatches:checks.filter(c=>c.matchesPreference===false).length});
}
const hash=x=>createHash('sha256').update(x).digest('hex');
const files=['stage_tie_index.py','audit_staged_ties.mjs','K:/MusicSearch/scripts/build-musicxml-search-index.py',...['phrase-boundaries.mjs','phrase-breath-symbols.mjs','repeated-breath-rule.mjs','short-cell-continuity.mjs'].map(f=>'K:/MusicSearch/server/'+f)];
fs.writeFileSync(path.join(root,'regression-summary.json'),JSON.stringify({summary,codeHashes:Object.fromEntries(files.map(f=>[f,hash(fs.readFileSync(f))]))},null,2));console.log(JSON.stringify(summary,null,2));
