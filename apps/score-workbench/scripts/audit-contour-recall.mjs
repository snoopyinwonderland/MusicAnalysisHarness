import {readFileSync,writeFileSync} from 'node:fs';
import {contourSeedCandidates} from '../server/contour-seeds.mjs';
import {prepareQueryNotes,queryDiscrimination} from '../server/search-api.mjs';
const [baseline,referenceFile,sidecar,out]=process.argv.slice(2);if(!out)throw Error('Baseline search JSON, references, sidecar, NEW output required');
const baselineReport=JSON.parse(readFileSync(baseline)),refs=JSON.parse(readFileSync(referenceFile)),watched=new Set(refs.map(r=>r.id)),results=[];
for(const run of baselineReport.runs){const notes=prepareQueryNotes(run.query.events),info=queryDiscrimination(notes);
 if(info.lowInformation){results.push({taskId:run.taskId,status:'skipped-low-information',info});continue;}
 const start=Date.now();let ranking;
 const candidates=contourSeedCandidates(sidecar,'data/search-index-v2/search.sqlite',notes.map(n=>n.pitchMidi),{onRank:rows=>{ranking={total:rows.length,referenceRows:rows.filter(r=>watched.has(r.id))}}});
 results.push({taskId:run.taskId,status:'completed',elapsedMs:Date.now()-start,ranking,returned:candidates.length});console.log(JSON.stringify(results.at(-1)));
}
writeFileSync(out,JSON.stringify({schema:'contour-recall-audit/1',referenceIdsUsedOnlyInObserver:true,results},null,2),{flag:'wx'});
