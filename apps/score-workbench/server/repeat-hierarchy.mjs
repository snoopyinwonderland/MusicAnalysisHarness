import {alignStructureTemplate} from '../src/music/structureTemplateAlignment.ts';
const beat=n=>[6,9,12].includes(n?.meterCount)&&n.meterUnit===8?1.5:[2,3,4].includes(n?.meterCount)&&[2,4,8].includes(n?.meterUnit)?4/n.meterUnit:null;
/** Boundary-independent span evidence. Long arrivals are candidates, NOT cadences. */
export function discoverRepeatHierarchy(notes,{maxSeedChecks=250000,maxAlignments=20000}={}){
 if(!Number.isInteger(maxSeedChecks)||maxSeedChecks<0||!Number.isInteger(maxAlignments)||maxAlignments<0)throw Error('Invalid budget');
 if(notes.some((n,i)=>!n.id||![n.pitchMidi,n.onset,n.durationRatio].every(Number.isFinite)||n.durationRatio<=0||(i&&n.onset<=notes[i-1].onset))||new Set(notes.map(n=>n.id)).size!==notes.length)throw Error('Expected unique monophonic attacks');
 const gaps=notes.map((n,i)=>i?n.onset-notes[i-1].onset-notes[i-1].durationRatio:0);
 const protectedCuts=new Set(notes.flatMap((n,i)=>{const u=beat(n);return i+1<notes.length&&(n.breathSymbols?.length||(u&&(gaps[i+1]>=4*u||(gaps[i+1]>=2*u&&n.durationRatio>=2*u))))?[i+1]:[]}));
 function ends(s,limit){
  const result=[],u=beat(notes[s]);if(!u)return result;
  for(let e=s+1;e<=Math.min(notes.length,s+64,limit);e++){
   const n=notes[e-1];
   if(beat(n)!==u||n.meterCount!==notes[s].meterCount||n.meterUnit!==notes[s].meterUnit||n.tieStop||n.isAttack===false||(e>s+1&&gaps[e-1]<-1e-6))break;
   if(e-s>=8&&n.durationRatio>=2*u)result.push(e);
   if(protectedCuts.has(e))break;
  }
  return result;
 }
 const jobs=[];let seedChecks=0,seedPartial=false;
 // Diagonal traversal spreads the seed budget across the score, not just its opening.
 seed:for(let distance=8;distance+4<=notes.length;distance++)for(let i=0;i+distance+4<=notes.length;i++){
  if(seedChecks>=maxSeedChecks){seedPartial=true;break seed;}seedChecks++;
  const j=i+distance,lu=notes[i+1].onset-notes[i].onset,ru=notes[j+1].onset-notes[j].onset;
  let rhythm=0,melody=0,contour=0;
  for(let k=1;k<4;k++){
   rhythm+=Math.abs(Math.log2(((notes[j+k].onset-notes[j+k-1].onset)/ru)/((notes[i+k].onset-notes[i+k-1].onset)/lu)));
   const a=notes[i+k].pitchMidi-notes[i+k-1].pitchMidi,b=notes[j+k].pitchMidi-notes[j+k-1].pitchMidi;
   melody+=Math.abs(a-b);if(Math.sign(a)!==Math.sign(b))contour++;
  }
  if(rhythm>1||melody>6||contour>1)continue;
  const tasks=[];
  for(const le of ends(i,j))for(const re of ends(j,notes.length))if(Math.abs((le-i)-(re-j))<=4)tasks.push({i,j,le,re});
  if(tasks.length)jobs.push({tasks,cursor:0});
 }
 const candidates=[];let alignments=0,active=true;
 while(active&&alignments<maxAlignments){active=false;
  for(const job of jobs){if(job.cursor>=job.tasks.length)continue;active=true;if(alignments>=maxAlignments)break;
   const {i,j,le,re}=job.tasks[job.cursor++],left=notes.slice(i,le),right=notes.slice(j,re),m=alignStructureTemplate(left,right);alignments++;
   if(m.status!=='compared'||!m.terminal.bothEndpointsPaired||m.alignment[0]?.leftIndex!==0||m.alignment[0]?.rightIndex!==0||m.coverage<80||m.melodic<85||m.rhythm<75)continue;
   const ref=(s,e)=>({startIndex:s,endIndexExclusive:e,startEventId:notes[s].id,lastEventId:notes[e-1].id});
   candidates.push({id:`repeat:${notes[i].id}:${notes[le-1].id}:${notes[j].id}:${notes[re-1].id}`,left:ref(i,le),right:ref(j,re),alignment:m,lowInformation:new Set(left.map(n=>n.pitchMidi)).size<3,extentStatus:'arrival-bounded-candidate-not-proven-phrase',decision:'cannot_judge'});
  }
 }
 const partial=seedPartial||jobs.some(j=>j.cursor<j.tasks.length);
 const buckets=new Map();for(const c of candidates){const key=c.left.startIndex+':'+c.right.startIndex;if(!buckets.has(key))buckets.set(key,[]);buckets.get(key).push(c);}
 const containment=[];
 for(const bucket of buckets.values())for(const c of bucket){
  const parents=bucket.filter(p=>p.left.endIndexExclusive>c.left.endIndexExclusive&&p.right.endIndexExclusive>c.right.endIndexExclusive).sort((a,b)=>(a.left.endIndexExclusive+a.right.endIndexExclusive)-(b.left.endIndexExclusive+b.right.endIndexExclusive));
  if(parents.length)containment.push({childId:c.id,parentId:parents[0].id,relation:'shared-start-contained-repeat',meaning:'shorter correspondence must not independently determine the enclosing Phrase boundary'});
 }
 return {version:'repeat-hierarchy-v0.1',status:partial?'partial':'complete-within-bounds',seedChecks,alignments,candidates,containment,protectedCuts:[...protectedCuts],policy:{maxSeedChecks,maxAlignments,minAttacks:8,maxAttacks:64,calibrated:false},limitations:['Arrival duration is an extent candidate, not harmonic closure','Four-note seeds miss some insertion/deletion variants','No family membership by transitive similarity','Budgets and duration landmarks can omit valid repeats','Containment currently covers common starts only, not all internal motif relationships']};
}

/** Attach baseline only after discovery; larger correspondences constrain short-cell claims. */
export function reviewHierarchyBoundaries(notes,boundaries,discovery){
 const protectedCuts=new Set(discovery.protectedCuts),rows=[];
 for(const c of discovery.candidates){
  const differences=c.alignment.alignment.flatMap(p=>{
   if(p.leftIndex===null||p.rightIndex===null||!p.leftIndex||!p.rightIndex)return[];
   const li=c.left.startIndex+p.leftIndex,ri=c.right.startIndex+p.rightIndex,l=boundaries[li],r=boundaries[ri];
   if(!l||!r||l.supported===r.supported)return[];
   return [{leftEventId:notes[li].id,rightEventId:notes[ri].id,leftIndex:li,rightIndex:ri,protected:protectedCuts.has(li)||protectedCuts.has(ri),leftSupported:l.supported,rightSupported:r.supported,partialFrameConflict:[...l.cues,...r.cues].some(x=>x.name==='recurring-motif-answer-continuation'),gapDifference:(notes[ri].onset-notes[ri-1].onset-notes[ri-1].durationRatio)-(notes[li].onset-notes[li-1].onset-notes[li-1].durationRatio)}];
  });
  const startEvidence=[c.left,c.right].map(r=>({eventId:r.startEventId,index:r.startIndex,supported:r.startIndex===0||!!boundaries[r.startIndex]?.supported,previousDuration:r.startIndex?notes[r.startIndex-1].durationRatio:null,gap:r.startIndex?notes[r.startIndex].onset-notes[r.startIndex-1].onset-notes[r.startIndex-1].durationRatio:null}));
  rows.push({candidateId:c.id,left:c.left,right:c.right,startEvidence,differences,decision:'cannot_judge',alternatives:['keep-baseline-segmentation','group-as-upper-phrase-with-internal-motif-candidates'],autoApply:false});
 }
 return {version:'repeat-hierarchy-review-v0.1',status:discovery.status,rows};
}
