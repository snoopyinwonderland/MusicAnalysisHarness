import {readFileSync,mkdirSync,writeFileSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
import {join} from 'node:path';
import {analyzeStructuralSource} from '../server/structural-reduction.mjs';
const dir=process.argv[2];if(!dir)throw Error('Output directory required');mkdirSync(dir,{recursive:false});
const suite=JSON.parse(readFileSync('evaluation/runs/harder-100-2026-09-15/suite.json'));
const results=[];
for(const b of suite.bases){
 const source=b.expected.sourceId,path=source.startsWith('kysing/')?'U:/KYSing_MusicXML/'+source.slice(7):'K:/Music Analysis/musicxml/'+source;
 try{
  const run=spawnSync('K:/Music Analysis/.venv/Scripts/python.exe',['scripts/structural-xml-source.py',path],{encoding:'utf8',maxBuffer:64*1024*1024});
  if(run.status!==0)throw Error(run.stderr);const input=JSON.parse(run.stdout),[part,staff,voice]=b.expected.streamId.split(':');
  const focus=input.events.filter(e=>e.partId===part&&e.staffId===staff&&e.voiceId===voice&&e.measureOrdinal>=b.focus[0].m-2&&e.measureOrdinal<=b.focus.at(-1).m+2);
  // Index absolute time may include padded pickup measures. Link by source-local
  // measure/beat/pitch, never overwrite the original XML timeline to hide drift.
  const indexLinks=b.focus.map(n=>{const candidates=focus.filter(e=>e.kind==='note'&&e.measureOrdinal===n.m&&e.pitchMidi===n.p&&Math.abs(e.beatQ.n/e.beatQ.d-(n.b-1))<1e-6);return {indexNote:n,xmlEventIds:candidates.map(e=>e.id),status:candidates.length===1?'unique':candidates.length?'ambiguous':'missing'}});
  const analysis=analyzeStructuralSource({...input,events:focus});
  const row={baseId:b.baseId,source,status:'completed',events:focus.length,anchors:analysis.anchors.length,
   supported:analysis.relations.filter(r=>r.confidence==='supported').length,provisional:analysis.relations.filter(r=>r.status==='eligible').length,
   l1:analysis.alternatives.some(a=>a.layer==='L1'),mappedFocus:b.focus.filter(n=>focus.some(e=>e.pitchMidi===n.p&&Math.abs(e.onsetQ.n/e.onsetQ.d-n.o)<1e-6)).length,focusCount:b.focus.length,
   uniqueCoordinateLinks:indexLinks.filter(x=>x.status==='unique').length};
  writeFileSync(join(dir,b.baseId+'.json'),JSON.stringify({baseId:b.baseId,expected:b.expected,indexLinks,input:{...input,events:focus},analysis},null,2),{flag:'wx'});results.push(row);
 }catch(e){results.push({baseId:b.baseId,source,status:'failed',error:e.message})}
}
writeFileSync(join(dir,'summary.json'),JSON.stringify({schema:'structural-source-audit/1',results,rankingChanged:false},null,2),{flag:'wx'});console.log(JSON.stringify(results,null,2));
