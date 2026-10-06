import type {CorpusNote} from '../types';
import {pillarRuleFamilies,type PillarEvidence,type PillarRule} from './pillarEvidence';
import {pillarVariationEvidence,type PillarCorrespondence} from './pillarVariation';
export type PillarHarmonyEvidence={noteId:string;analysisId:string;engineVersion:string;evidenceRefs:string[];label:string;effect:'supports'|'conflicts';status:'hypothesis'|'human-validated'};
export type PillarCandidate={index:number;note:CorpusNote;reasons:string[];level:'combined'|'tentative';harmony:PillarHarmonyEvidence[];correspondences:PillarCorrespondence[];evidence:PillarEvidence[]};
export type PillarMeter={count:number;unit:number};
export type PillarPhraseStart={noteId:string;phraseNumber:number};
export function pillarCandidates(notes:CorpusNote[],options:{harmonyEvidence?:PillarHarmonyEvidence[];meters?:Record<number,PillarMeter>}={}):PillarCandidate[]{
 const med=(v:number[])=>{const s=v.filter(x=>x>0&&Number.isFinite(x)).sort((a,b)=>a-b);return s.length?s[Math.floor(s.length/2)]:null;};
 const repeated=new Set<number>(),seen=new Map<string,number[]>();
 const variation=pillarVariationEvidence(notes);
 const noteById=new Map(notes.map(n=>[n.id,n]));
 // Bounded, transposition-invariant four-attack signatures. No title/measure rules.
 for(let i=0;i+3<notes.length;i++){
  const ns=notes.slice(i,i+4),unit=ns[0].durationRatio;
  if(!unit||ns.some(n=>n.pitchMidi===null||!Number.isFinite(n.onset)||n.durationRatio<=0))continue;
  const intervals=ns.slice(1).map((n,k)=>n.pitchMidi!-ns[k].pitchMidi!);
  if(new Set(intervals).size<2)continue;
  const key=JSON.stringify([intervals,ns.map(n=>Math.round(n.durationRatio/unit*100)),ns.map(n=>Math.round((n.onset!-ns[0].onset!)/unit*100))]);
  const prior=seen.get(key)??[];
  if(prior.some(j=>i-j>=4)){for(const j of [...prior,i])for(let k=0;k<4;k++)repeated.add(j+k);}
  seen.set(key,[...prior.slice(-3),i]);
 }
 return notes.flatMap((n,i)=>{
  if(n.pitchMidi===null||n.durationRatio<=0)return [];
  const unit=med(notes.slice(Math.max(0,i-4),i+5).map(x=>x.durationRatio));
  if(!unit)return [];
  const reasons:string[]=[],evidence:PillarEvidence[]=[];
  const emit=(ruleId:PillarRule,label:string)=>{evidence.push({ruleId,ruleVersion:'pillar-evidence-0.1',family:pillarRuleFamilies[ruleId],eventRefs:notes.slice(Math.max(0,i-4),i+5).map(n=>n.id),label,provenance:'local-input',reviewEligibility:'unverified'});reasons.push(label);};
  const meter=options.meters?.[n.measureOrdinal??n.measure];
  const pulse=meter&&meter.count>0&&meter.unit>0?(meter.count>=6&&meter.count%3===0?12:4)/meter.unit:null;
  const duration=Math.max(n.durationRatio,n.soundingEvidence?.durationQuarters??0);
  const pos=n.beat-1;
  const aligned=pulse!==null&&Math.abs(pos/pulse-Math.round(pos/pulse))<1e-6;
  if(pulse!==null&&duration>=pulse-1e-6)emit('beat-duration','기준 박 이상 지속');
  if(aligned)emit('beat-position','기준 박 위치');
  if(meter?.count===4&&Math.abs(pos-8/meter.unit)<1e-6)emit('middle-beat','마디 중간 강박');
  const prior=notes[i-1];
  const before=prior&&Number.isFinite(n.onset)&&Number.isFinite(prior.onset)?n.onset!-prior.onset!-Math.max(prior.durationRatio,prior.soundingEvidence?.durationQuarters??0):(!prior?pos:0);
  if(pulse!==null&&before>=pulse*.5&&duration>=pulse*.5)emit('rest-entry','쉼 뒤 선율 진입');
  if(pulse!==null&&!aligned&&duration>=pulse){
   const boundary=(Math.floor(pos/pulse)+1)*pulse;
   if(pos+duration>boundary+1e-6)emit('syncopated-sustain','엇박에서 다음 박을 이어받는 지속');
  }
  // A–B–A supports a local reduction hypothesis, not a harmonic NCT label.
  const middle=notes[i+1],back=notes[i+2];
  const returning=pulse!==null&&aligned&&middle?.pitchMidi!==null&&back?.pitchMidi===n.pitchMidi
   &&Math.abs(middle.pitchMidi!-n.pitchMidi)>0&&Math.abs(middle.pitchMidi!-n.pitchMidi)<=2
   &&Number.isFinite(n.onset)&&Number.isFinite(middle.onset)&&Number.isFinite(back.onset)
   &&Math.abs(middle.onset!-n.onset!-duration)<1e-6
   &&Math.abs(back.onset!-middle.onset!-middle.durationRatio)<1e-6
   &&back.onset!+back.durationRatio-n.onset!>=pulse
   &&back.onset!+back.durationRatio-n.onset!<=pulse*2;
  if(returning)emit('neighbor-return','한두 박 안의 순차 왕복 음형 기준음 · 축약 가설');
  if(n.durationRatio>=unit*1.5)emit('relative-duration','주변 음가보다 긴 지속');
  if(n.beat===1)emit('downbeat','기보 마디 첫 박');
  const next=notes[i+1],gap=next&&Number.isFinite(n.onset)&&Number.isFinite(next.onset)?next.onset!-n.onset!-n.durationRatio:0;
  if(gap>=unit*.5&&n.durationRatio>=unit)emit('following-gap','지속 뒤 선율 공백');
  const prev=notes[i-1];
  if(prev&&prev.pitchMidi!==null&&Math.abs(n.pitchMidi-prev.pitchMidi)<=2&&n.durationRatio>=prev.durationRatio*2)emit('step-arrival','짧은 순차진행 뒤 긴 도착음');
  if(repeated.has(i))emit('exact-repeat','작품 내부 4음 반복의 대응 위치');
  const correspondences=variation.get(i)??[];
  if(correspondences.length){
   const ref=noteById.get(correspondences[0].otherNoteId);
   emit('variation-match',`반복·장식 변형에서 유지된 음정·리듬 대응${ref?` · ${ref.measure}마디 ${ref.beat}박` : ''}`);
  }
  // Repetition and meter alone cannot assert a structural pillar.
  const temporal=returning||evidence.some(e=>['beat-duration','syncopated-sustain','relative-duration','following-gap','step-arrival'].includes(e.ruleId));
  const harmony=(options.harmonyEvidence??[]).filter(e=>e.noteId===n.id&&e.analysisId&&e.engineVersion&&e.evidenceRefs.length&&e.label);
  // Harmony is an independent channel: retain contradictions and alternatives.
  // v0.1 does not silently convert harmony labels into calibrated weights.
  return (temporal&&reasons.length>=2)||harmony.length?[{index:i,note:n,reasons,level:reasons.length>=3&&!harmony.some(e=>e.effect==='conflicts')?'combined' as const:'tentative' as const,harmony,correspondences,evidence}]:[];
 });
}
