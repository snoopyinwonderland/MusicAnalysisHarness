import type {CorpusNote} from '../types';
import {compareMotifs} from './motifSimilarity.ts';

/** Offline evidence, never an automatic merge decision. */
export function alignStructureTemplate(left:CorpusNote[],right:CorpusNote[]){
  if(left.length>128||right.length>128)return {status:'budget-exceeded' as const};
  if(!left.length||!right.length||[...left,...right].some(n=>!Number.isFinite(n.onset)||!Number.isFinite(n.durationRatio)||n.durationRatio<=0||!Number.isFinite(n.pitchMidi)))return {status:'invalid-input' as const};
  const result=compareMotifs(left,right);
  const pairs=result.alignment.filter(s=>s.leftIndex!==null&&s.rightIndex!==null);
  const unit=(notes:CorpusNote[])=>[...notes].map(n=>n.durationRatio).sort((a,b)=>a-b)[Math.floor(notes.length/2)];
  const lu=unit(left),ru=unit(right);
  const gaps=(notes:CorpusNote[])=>notes.map((n,i)=>i?Math.max(0,Number(n.onset)-Number(notes[i-1].onset)-notes[i-1].durationRatio):0);
  const lg=gaps(left),rg=gaps(right);
  const restComparisons=pairs.filter(p=>lg[p.leftIndex!]||rg[p.rightIndex!]).map(p=>({leftEventId:left[p.leftIndex!].id,rightEventId:right[p.rightIndex!].id,leftGapUnits:lg[p.leftIndex!]/lu,rightGapUnits:rg[p.rightIndex!]/ru,kind:'inferred-stream-gap'}));
  let prefix=0;
  for(const step of result.alignment){if(step.type!=='match'||step.leftIndex!==prefix||step.rightIndex!==prefix)break;prefix++}
  const last=result.alignment.at(-1)!;
  return {status:'compared' as const,version:'structure-template-alignment-v0.1',calibrated:false,...result,
    prefix:{alignedAttackCount:prefix,leftRatio:prefix/left.length,rightRatio:prefix/right.length,meaning:'contiguous leading match, not a inferred musical section'},
    terminal:{bothEndpointsPaired:last.leftIndex===left.length-1&&last.rightIndex===right.length-1,leftDuration:left.at(-1)!.durationRatio,rightDuration:right.at(-1)!.durationRatio},
    restComparisons,alignmentRefs:result.alignment.map(s=>({...s,leftEventId:s.leftIndex===null?null:left[s.leftIndex].id,rightEventId:s.rightIndex===null?null:right[s.rightIndex].id})),
    limitations:['gap channel is diagnostic only and not added to similarity','beam and metric grouping are observations, not scored here','no harmonic prolongation or cadence judgment']};
}
