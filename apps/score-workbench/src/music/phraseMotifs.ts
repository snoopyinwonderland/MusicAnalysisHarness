import type {CorpusNote} from '../types';
import {compareMotifs} from './motifSimilarity';

export const PHRASE_MOTIF_VERSION='phrase-first-v1';
type Range={startIndex:number;endIndex:number;phraseNumber?:number};
const attack=(n:CorpusNote)=>n.kind==='note'&&n.pitchMidi!==null&&(n as any).isAttack!==false&&!(n as any).tieStop;
const median=(a:number[])=>[...a].sort((x,y)=>x-y)[Math.floor(a.length/2)]||1;
const related=(e:ReturnType<typeof compareMotifs>)=>e.similarity>=84&&e.coverage>=70&&e.melodic>=85&&e.shape>=80;

/** Phrase boundaries are authoritative for this first release. Core is untouched.
 * Every Phrase retains a complete candidate, including non-repeating material.
 * A work-wide proposal pool is compared before selecting internal boundaries.
 */
export function phraseMotifs(notes:CorpusNote[],phrases:Range[]){
  const contexts=phrases.filter(p=>p.startIndex>=0&&p.endIndex<notes.length).map((p,index)=>{
    const ids=Array.from({length:p.endIndex-p.startIndex+1},(_,i)=>p.startIndex+i).filter(i=>attack(notes[i]));
    const cuts=[0], gaps=new Set<number>();
    for(let k=3;k<=ids.length-3;k++){
      const previous=notes[ids[k-1]],next=notes[ids[k]];
      const unit=median(ids.slice(Math.max(0,k-4),k-1).map(i=>notes[i].durationRatio));
      const gap=Number(next.onset)-Number(previous.onset)-previous.durationRatio;
      const long=previous.durationRatio>=Math.max(1,unit*2);
      if(gap>=Math.max(.5,unit)-1e-8){cuts.push(k);gaps.add(k)}
      else if(long)cuts.push(k);
    }
    cuts.push(ids.length);
    return {p,number:p.phraseNumber??index+1,ids,cuts,gaps};
  });
  type Proposal={context:number;left:number;right:number;events:CorpusNote[];match?:number};
  const proposals:Proposal[]=[], lookup=new Map<string,number>();
  // Bounded candidate pool. Whole phrases are always retained even on large scores.
  let truncated=false;
  const add=(context:number,left:number,right:number)=>{
    const key=`${context}:${left}:${right}`;if(lookup.has(key))return;
    lookup.set(key,proposals.length);proposals.push({context,left,right,events:contexts[context].ids.slice(left,right).map(i=>notes[i])});
  };
  contexts.forEach((c,i)=>add(i,0,c.ids.length));
  contexts.forEach((c,i)=>{for(let a=0;a<c.cuts.length-1;a++)for(let b=a+1;b<c.cuts.length;b++){
    const left=c.cuts[a],right=c.cuts[b];
    if(right-left<3||right-left>32)continue;
    if(proposals.length>=400){truncated=true;continue}add(i,left,right);
  }});
  let comparisons=0;
  for(let i=0;i<proposals.length;i++)for(let j=i+1;j<proposals.length;j++){
    const a=proposals[i],b=proposals[j];
    if(!a.events.length||!b.events.length||Math.min(a.events.length,b.events.length)/Math.max(a.events.length,b.events.length)<.7)continue;
    if(a.context===b.context&&a.left<b.right&&b.left<a.right)continue;
    if(comparisons>=20000){truncated=true;continue}comparisons++;
    if(related(compareMotifs(a.events,b.events))){a.match??=j;b.match??=i}
  }
  const selected:Array<{context:number;left:number;right:number;reason:string}>=[];
  contexts.forEach((c,context)=>{
    const partition=(left:number,right:number,depth=0):void=>{
      if(depth>=8){selected.push({context,left,right,reason:'split-depth-limit'});return}
      const possible=c.cuts.filter(k=>k-left>=3&&right-k>=3).map(k=>{
        const a=proposals[lookup.get(`${context}:${left}:${k}`)??-1],b=proposals[lookup.get(`${context}:${k}:${right}`)??-1];
        const repeated=a?.match!==undefined&&b?.match!==undefined;
        return {k,repeated,gap:c.gaps.has(k)};
      }).filter(x=>x.gap||x.repeated).sort((a,b)=>Number(b.gap)-Number(a.gap)||Number(b.repeated)-Number(a.repeated)||Math.abs((left+right)/2-a.k)-Math.abs((left+right)/2-b.k));
      if(possible.length){partition(left,possible[0].k,depth+1);partition(possible[0].k,right,depth+1)}
      else selected.push({context,left,right,reason:left===0&&right===c.ids.length?'phrase-whole-unresolved':'phrase-internal-evidence'});
    };
    if(c.ids.length)partition(0,c.ids.length);
  });
  const families:Array<{base:CorpusNote[];variants:CorpusNote[][]}>=[];
  return selected.map((s,index)=>{
    const c=contexts[s.context],events=c.ids.slice(s.left,s.right).map(i=>notes[i]);
    const matches=families.map((f,i)=>({i,e:compareMotifs(f.base,events)})).filter(x=>related(x.e)).sort((a,b)=>b.e.similarity-a.e.similarity);
    let familyIndex=matches[0]?.i;
    if(familyIndex===undefined){familyIndex=families.length;families.push({base:events,variants:[events]})}
    const f=families[familyIndex];
    let variant=f.variants.findIndex(v=>{const e=compareMotifs(v,events);return e.melodic>=99&&e.shape>=99&&e.rhythm>=98&&e.coverage>=98});
    if(variant<0){variant=f.variants.length;f.variants.push(events)}
    const startIndex=s.left===0?c.p.startIndex:c.ids[s.left],endIndex=s.right===c.ids.length?c.p.endIndex:c.ids[s.right]-1;
    const proposal=proposals[lookup.get(`${s.context}:${s.left}:${s.right}`)??-1],reference=proposal?.match===undefined?undefined:proposals[proposal.match];
    return {motifNumber:index+1,familyNumber:familyIndex+1,variantIndex:variant,label:`Motif ${familyIndex+1}-${variant+1}`,startIndex,endIndex,startNote:events[0],endNote:events.at(-1)!,similarity:compareMotifs(f.base,events),
      analysisScope:s.reason,parentPhraseNumber:c.number,algorithmVersion:PHRASE_MOTIF_VERSION,
      recurrenceEvidence:reference?{phraseNumber:contexts[reference.context].number,startIndex:contexts[reference.context].ids[reference.left],endIndex:contexts[reference.context].ids[reference.right-1]}:null,
      searchTruncated:truncated,containedFragments:[]};
  });
}
