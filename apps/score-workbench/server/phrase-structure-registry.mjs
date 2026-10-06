import {alignStructureTemplate} from '../src/music/structureTemplateAlignment.ts';

/** Frozen baseline entries are comparison references, NOT approved templates.
 * No proposal is promoted during this run. Every decision remains review-only.
 */
export function structureRegistry(notes,spans,{maxComparisons=10000}={}){
 if(!Number.isInteger(maxComparisons)||maxComparisons<0)throw Error('Invalid comparison budget');
 if(spans.some((s,i)=>!Number.isInteger(s.startIndex)||!Number.isInteger(s.endIndexExclusive)||s.startIndex<0||s.endIndexExclusive>notes.length||s.endIndexExclusive<=s.startIndex||(i>0&&spans[i-1].endIndexExclusive!==s.startIndex)))throw Error('Expected ordered contiguous nonempty baseline spans');
 const registry=spans.map(s=>({...s,referenceId:`baseline:${notes[s.startIndex].id}:${notes[s.endIndexExclusive-1].id}`,approval:'unreviewed-baseline'}));
 const proposals=[];let comparisons=0,partial=false;
 for(let i=0;i+1<registry.length;i++){
  const a=registry[i],b=registry[i+1],target={startIndex:a.startIndex,endIndexExclusive:b.endIndexExclusive,startEventId:notes[a.startIndex].id,lastEventId:notes[b.endIndexExclusive-1].id};
  const candidates=[];
  for(const ref of registry){
   if(!(ref.endIndexExclusive<=target.startIndex||ref.startIndex>=target.endIndexExclusive))continue;
   if(comparisons+3>maxComparisons){partial=true;break;}
   const left=notes.slice(ref.startIndex,ref.endIndexExclusive);
   const merge=alignStructureTemplate(left,notes.slice(target.startIndex,target.endIndexExclusive));
   const keepFirst=alignStructureTemplate(left,notes.slice(a.startIndex,a.endIndexExclusive));
   const keepSecond=alignStructureTemplate(left,notes.slice(b.startIndex,b.endIndexExclusive));
   comparisons+=3;
   const missingEvidence=[];
   if(merge.status!=='compared')missingEvidence.push(merge.status);
   else{
    if(!merge.prefix.alignedAttackCount)missingEvidence.push('start-not-aligned');
    if(!merge.terminal.bothEndpointsPaired)missingEvidence.push('end-not-aligned');
    if(merge.coverage<100)missingEvidence.push('incomplete-coverage-requires-review');
   }
   candidates.push({referenceId:ref.referenceId,direction:ref.startIndex>=target.endIndexExclusive?'later':'earlier',missingEvidence,merge,keepFirst,keepSecond});
  }
  proposals.push({target,internalBoundaryEventId:notes[b.startIndex].id,decision:'cannot_judge',alternatives:['keep','merge'],status:partial?'partial':'compared',candidates});
  if(partial)break;
 }
 return {schema:'phrase-structure-registry/v0.1',mode:'shadow',registry,proposals,comparisons,maxComparisons,status:partial?'partial':'complete',unvisitedPairs:Math.max(0,registry.length-1-proposals.length),limitations:['baseline references are not approved templates','no calibrated merge margin','source and meter protection must be checked separately','completion means comparisons finished, not analysis validated']};
}
