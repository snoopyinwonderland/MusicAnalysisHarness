import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
const previous=JSON.parse(readFileSync('evaluation/reports/structural-100-preview-v1/suite.json'));
const dir=process.argv[2];if(!dir)throw Error('New directory required');mkdirSync(dir);
const cases=[];
for(const b of previous.bases){
 const notes=b.query.events.filter(e=>e.kind==='note'),index=Math.floor(notes.length/2),removed=notes[index];
 const deletion=structuredClone(b.query);deletion.events=deletion.events.filter(e=>e.id!==removed.id);
 cases.push({caseId:`NEXT-${b.baseId}-delete`,baseId:b.baseId,kind:'delete-one',query:deletion,removed,
  changes:[{type:'delete-note-and-duration',event:removed}],deletedAnchorCandidate:b.analyzerInferredIds.includes(removed.id),sourceToQueryMap:notes.map(e=>({sourceId:e.id,queryIds:e.id===removed.id?[]:[e.id]}))});
 const previousCase=previous.cases.find(c=>c.baseId===b.baseId&&c.kind==='combined'),combined=structuredClone(previousCase.query),changed=combined.events.find(e=>e.id===removed.id),before=changed.pitchMidi;
 changed.pitchMidi+=1;delete changed.spelling;
 cases.push({caseId:`NEXT-${b.baseId}-extra`,baseId:b.baseId,kind:'combined-plus-one-semitone',parentCaseId:previousCase.caseId,query:combined,
  changes:[...previousCase.changes,{type:'pitch-change',id:changed.id,before,after:changed.pitchMidi}],changedAnchorCandidate:b.analyzerInferredIds.includes(changed.id)});
}
writeFileSync(dir+'/suite.json',JSON.stringify({schema:'structural-next40/1',bases:previous.bases,cases,selection:'Same 20 sources; delete middle original attack and its duration; combined variant plus one semitone at same original attack. Fixed selection, no result-dependent tuning.'},null,2),{flag:'wx'});
console.log({cases:cases.length});
