import {readFileSync,writeFileSync} from 'node:fs';
import {singleOmissionAlignment} from '../server/single-omission.mjs';
import {annotateStructural,alignLocal,sparseAlignmentAllowed} from '../server/search-api.mjs';
const [path,out]=process.argv.slice(2),suite=JSON.parse(readFileSync(path)),rows=[];
for(const c of suite.cases.filter(c=>c.kind==='delete-one')){
 const b=suite.bases.find(b=>b.baseId===c.baseId);let cursor=0;
 const q=c.query.events.map(e=>{const n={...e,onset:cursor,beat:cursor+1};cursor+=e.durationRatio;return n}).filter(e=>e.kind==='note');
 const candidate=annotateStructural(b.focus.map(n=>({pitchMidi:n.p,durationRatio:n.d,onset:n.o,beat:n.b,measure:n.m})),b.query.meter,true),query=annotateStructural(q,c.query.meter);
 const old=alignLocal(query,candidate,c.query.mode),next=singleOmissionAlignment(query,candidate);
 rows.push({caseId:c.caseId,deletedAnchorCandidate:c.deletedAnchorCandidate,baselineForced:{similarity:old.similarity,coverage:old.coverage,sparseAllowed:sparseAlignmentAllowed(old.path,candidate),path:old.path},experimentalForced:next});
}
writeFileSync(out,JSON.stringify({warning:'Forced known source span, NOT full database retrieval or rank improvement.',rows},null,2),{flag:'wx'});
console.log(JSON.stringify({total:rows.length,recognized:rows.filter(r=>r.experimentalForced).length,previousSparseBlocked:rows.filter(r=>!r.baselineForced.sparseAllowed).length}));
