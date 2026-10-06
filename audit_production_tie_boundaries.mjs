import fs from 'node:fs';
import path from 'node:path';
import {analyzePhraseBoundaries} from 'file:///K:/MusicSearch/server/phrase-boundaries.mjs';
import {compareBoundaries} from './audit_phrase_transposition.mjs';
const root='reports/production-tie-notation-2026-09-22',summary=[];
// corpusNotes fields relevant to the raw boundary engine, including tie provenance.
const notes=raw=>raw.map((n,i)=>({id:`test-${i}`,kind:'note',pitchMidi:n.p,spelling:n.s,durationRatio:n.d,onset:n.o,cue:Boolean(n.u),tieStart:Boolean(n.ts),tieStop:Boolean(n.te),tieEndMeasure:n.tm,measure:n.m,beat:n.b,metricStrength:n.b===1?1:.5,structuralSalience:.5,structuralConfidence:.65,chordRole:'unknown'}));
for(const dir of fs.readdirSync(root,{withFileTypes:true}).filter(d=>d.isDirectory())){
 const folder=path.join(root,dir.name),input=JSON.parse(fs.readFileSync(path.join(folder,'parser-check.json'))),checks=[];
 for(const a of input.before.streams){
  const b=input.after.streams.find(s=>s.id===a.id);if(!b)continue;
  const before=analyzePhraseBoundaries(notes(a.notes)),after=analyzePhraseBoundaries(notes(b.notes));
  checks.push({stream:a.id,differences:compareBoundaries(before,after),fullEqual:JSON.stringify(before)===JSON.stringify(after),before,after});
 }
 fs.writeFileSync(path.join(folder,'boundary-check.json'),JSON.stringify(checks));
 summary.push({case:dir.name,checks:checks.map(c=>({stream:c.stream,differences:c.differences.length,fullEqual:c.fullEqual}))});
}
fs.writeFileSync(path.join(root,'boundary-summary.json'),JSON.stringify(summary,null,2));console.log(JSON.stringify(summary,null,2));
