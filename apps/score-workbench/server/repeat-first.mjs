import {alignStructureTemplate} from '../src/music/structureTemplateAlignment.ts';
const near=(a,b)=>Math.abs(a-b)<1e-6;
export function durationRestVariants(left,right,alignment){
 const result=[];
 for(let k=1;k<alignment.length;k++){
  const a=alignment[k-1],b=alignment[k];
  if(a.leftIndex===null||a.rightIndex===null||b.leftIndex!==a.leftIndex+1||b.rightIndex!==a.rightIndex+1)continue;
  const l=left[a.leftIndex],ln=left[b.leftIndex],r=right[a.rightIndex],rn=right[b.rightIndex];
  const li=ln.onset-l.onset,ri=rn.onset-r.onset,lg=li-l.durationRatio,rg=ri-r.durationRatio;
  if(li<=0||lg<0||rg<0||!near(li,ri)||near(l.durationRatio,r.durationRatio)||!near(ln.pitchMidi-l.pitchMidi,rn.pitchMidi-r.pitchMidi))continue;
  result.push({leftEventId:l.id,rightEventId:r.id,leftNextEventId:ln.id,rightNextEventId:rn.id,ioiQuarter:li,leftDuration:l.durationRatio,rightDuration:r.durationRatio,leftInferredGap:lg,rightInferredGap:rg,type:'duration-rest-redistribution',status:'candidate-not-boundary-decision',restProvenance:'inferred-not-xml-verified'});
 }
 return result;
}
export function discoverRepeats(notes,{maxSeedChecks=250000,maxAlignments=300,windowLengths=[12,24,32]}={}){
 if(!Number.isInteger(maxSeedChecks)||maxSeedChecks<0||!Number.isInteger(maxAlignments)||maxAlignments<0||windowLengths.some(x=>!Number.isInteger(x)||x<5||x>128))throw Error('Invalid budget/window');
 if(new Set(notes.map(n=>n.id)).size!==notes.length||notes.some((n,i)=>!n.id||![n.onset,n.durationRatio,n.pitchMidi].every(Number.isFinite)||n.durationRatio<=0||(i&&n.onset<=notes[i-1].onset)))throw Error('Expected unique, ordered monophonic attack events');
 const candidates=[];let seedChecks=0,alignments=0,partial=false;
 outer:for(let i=0;i+5<=notes.length;i++)for(let j=i+5;j+5<=notes.length;j++){
  if(seedChecks>=maxSeedChecks){partial=true;break outer;}seedChecks++;
  let cost=0,contourMismatch=0,timing=0;
  const lu=notes[i+1].onset-notes[i].onset,ru=notes[j+1].onset-notes[j].onset;
  for(let k=1;k<5;k++){
   timing+=Math.abs(Math.log2(((notes[i+k].onset-notes[i+k-1].onset)/lu)/((notes[j+k].onset-notes[j+k-1].onset)/ru)));
  }
  // Rhythm first: permit duration/rest redistribution with the same attack grid.
  if(timing>1)continue;
  for(let k=1;k<5;k++){
   const a=notes[i+k].pitchMidi-notes[i+k-1].pitchMidi,b=notes[j+k].pitchMidi-notes[j+k-1].pitchMidi;
   cost+=Math.abs(a-b);if(Math.sign(a)!==Math.sign(b))contourMismatch++;
  }
  // Prototype retrieval tolerance, NOT a family-membership or boundary threshold.
  if(cost>8||contourMismatch>2)continue;
  const lengths=[...new Set(windowLengths.map(len=>Math.min(len,j-i,notes.length-j)))].filter(len=>len>=5);
  for(const length of lengths){
   if(alignments>=maxAlignments){partial=true;break outer;}alignments++;
   const left=notes.slice(i,i+length),right=notes.slice(j,j+length),alignment=alignStructureTemplate(left,right);
   candidates.push({left:{startEventId:left[0].id,lastEventId:left.at(-1).id,startIndex:i,endIndexExclusive:i+length},right:{startEventId:right[0].id,lastEventId:right.at(-1).id,startIndex:j,endIndexExclusive:j+length},extent:'comparison-window-not-complete-motif',lowInformation:new Set(left.slice(0,5).map(n=>n.pitchMidi)).size<3,seed:{length:5,intervalCost:cost,contourMismatch,timingCost:timing},alignment,variants:alignment.status==='compared'?durationRestVariants(left,right,alignment.alignment):[]});
  }
 }
 return {version:'repeat-first-shadow-v0.1',status:partial?'partial':'complete',decision:'review-only',seedChecks,alignments,budget:{maxSeedChecks,maxAlignments,windowLengths},candidates,limitations:['unreviewed candidates, no family or complete extent','seed insertion/deletion and scaled duration-rest evidence not yet supported','lexicographic budget traversal can miss later pairs','no harmony, no automatic boundary changes']};
}
