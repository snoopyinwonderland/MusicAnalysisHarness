import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {join} from 'node:path';
import {compareSegments} from '../server/segment-comparison.mjs';
const out=process.argv[2];if(!out)throw Error('New output directory required');mkdirSync(out);
const records=['upload','reference'].map(role=>JSON.parse(readFileSync(`evaluation/runs/real-pair-input-audit-v1/RC-004-${role}.json`)));
for(let i=0;i<records.length;i++)writeFileSync(join(out,(i?'reference':'upload')+'.musicxml'),readFileSync(records[i].path),{flag:'wx'});
const analyses=['xml-label','pickup-adjusted'].map(numbering=>{
 const segments=records.map((r,i)=>{
  const all=r.parsed.streams.find(s=>s.id==='P1:1:1').notes;
  const label=n=>Number(numbering==='xml-label'?r.parts[0].measures[n.m-1].xmlLabel:n.mn);
  let notes=all.filter(n=>label(n)>=10&&label(n)<=(i===0?14:13));
  if(i===0){const first=notes.find(n=>label(n)===14);if(first)notes=notes.filter(n=>n.o<=first.o);}
  return {source:r.path,sourceHash:r.parsed.hash,streamId:'P1:1:1',notes:notes.map(n=>({...n,xmlLabel:r.parts[0].measures[n.m-1].xmlLabel,reviewMeasure:label(n)})),context:all.filter(n=>label(n)>=9&&label(n)<=15)};
 });
 return {numbering,segments,comparison:compareSegments(...segments.map(s=>s.notes))};
});
writeFileSync(join(out,'analysis.json'),JSON.stringify({schema:'human-region-review/1',
 userObservation:'Twinkle 10 through first attack of 14 and Ma Boy 10–13 sound very similar despite few exact matches. Also test ascending/descending inversion.',
 humanSimilarityLabel:true,legalPositiveLabel:false,numberingConfirmed:false,sourceKind:'provided-piano-xml-not-karaoke-db',analyses},null,2),{flag:'wx'});
for(const a of analyses){console.log(a.numbering,JSON.stringify(a.comparison));for(const s of a.segments)console.log(s.notes.map(n=>`${n.reviewMeasure}:${n.s}/${n.d}@${n.b}`).join(' '));}
