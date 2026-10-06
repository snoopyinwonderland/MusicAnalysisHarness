import {describe,it,expect} from 'vitest';
import {analyzeStructuralSource as analyze,normalizeStructuralSource,rational,metricSupport} from './structural-reduction.mjs';
const source=()=>({sourceHash:'fixture',events:[60,62,64].map((pitchMidi,i)=>({id:'n'+i,kind:'note',pitchMidi,diatonicPitch:28+i,
  partId:'p',voiceId:'1',staffId:'1',onset:[0,1,.0+1.25][i],durationRatio:[1,.25,1][i],meter:'4/4',beatQ:[0,1,1.25][i],
  harmony:{id:'I',confidence:'high',chordTone:i!==1}}))});
describe('source-only structural reduction',()=>{
 it('retains exact rational tuplets and does not guess rounded timing',()=>{
  expect(rational({n:2,d:6})).toEqual({n:1,d:3});expect(rational(.33203125)).toEqual({n:85,d:256});
  expect(()=>rational({n:1,d:0})).toThrow();
 });
 it('requires identity, explicit voice and time',()=>{
  const s=source();delete s.events[0].voiceId;expect(()=>analyze(s)).toThrow();
  const t=source();delete t.events[0].onset;expect(()=>analyze(t)).toThrow();
 });
 it('does not invent meter/grouping or pickup downbeat',()=>{
  const metric=(meter,beatQ,extra={})=>metricSupport({meter,beatQ:rational(beatQ),...extra});
  expect(metric('4/4',0)).toBe(1);expect(metric('6/8',1.5)).toBe(.55);
  expect(metric('3/2',2)).toBe(.55);expect(metric('6/4',0)).toBe(null);
  expect(metric('7/8',1)).toBe(null);expect(metric('7/8',1,{grouping:[2,2,3]})).toBe(.55);
  expect(metric('4/4',0,{pickup:true})).toBe(null);
 });
 it('explains a short passing tone and keeps complete source mapping',()=>{
  const s=source(),copy=structuredClone(s),r=analyze(s);
  expect(r.alternatives.map(x=>x.layer)).toEqual(['L0','L1']);
  expect(r.alternatives[1].eventIds).toEqual(['n0','n2']);expect(r.relations[0].ruleId).toBe('R02');
  expect(r.relations[0].originalEventIds).toEqual(['n0','n1','n2']);expect(s).toEqual(copy);
  expect(r.rankingChanged).toBe(false);
 });
 it('keeps unknown harmony or spelling as provisional without reducing',()=>{
  for(const field of ['harmony','diatonicPitch']){const s=source();s.events.forEach(e=>delete e[field]);expect(analyze(s).alternatives).toHaveLength(1)}
 });
 it('protects characteristic middle tones and harmony changes',()=>{
  const s=source();s.events[1].protectedAnchor=true;expect(analyze(s).relations[0].contradictions).toContain('protected-characteristic-tone');
  const t=source();t.events[1].harmony.id='V';expect(analyze(t).alternatives).toHaveLength(1);
 });
 it('blocks silent gaps, overlaps, phrase boundaries and unresolved attacks',()=>{
  for(const change of [e=>e.onset+=.1,e=>e.onset-=.1,e=>e.phraseBoundary={confidence:'high',kind:'closing'},e=>e.tieStop=true]){
   const s=source();change(s.events[1]);expect(analyze(s).alternatives).toHaveLength(1);
  }
 });
 it('does not cross voices/staves or skip a rest',()=>{
  for(const field of ['voiceId','staffId']){const s=source();s.events[1][field]='2';expect(analyze(s).relations).toHaveLength(0)}
  const s=source();s.events[1].kind='rest';s.events[1].pitchMidi=null;expect(analyze(s).relations).toHaveLength(0);
 });
 it('represents neighbors separately and does not call repetition passing',()=>{
  const s=source();Object.assign(s.events[2],{pitchMidi:60,diatonicPitch:28});expect(analyze(s).relations[0].ruleId).toBe('R03');
  s.events[1].pitchMidi=60;expect(analyze(s).relations).toHaveLength(0);
 });
 it('merges only verified tie chains and retains notation IDs',()=>{
  const s=source();s.events=[{...s.events[0],tieChainId:'t',durationQ:{n:1,d:3}},
   {...s.events[0],id:'tie2',tieChainId:'t',onsetQ:{n:1,d:3},durationQ:{n:2,d:3},isAttack:false,tieStop:true}];
  const r=analyze(s);expect(r.soundingEvents).toHaveLength(1);expect(r.soundingEvents[0].durationQ).toEqual({n:1,d:1});
  expect(r.soundingEvents[0].xmlNoteIds).toEqual(['n0','tie2']);
  s.events[1].pitchMidi=61;const bad=analyze(s);expect(bad.soundingEvents).toHaveLength(2);expect(bad.issues[0].reason).toBe('unverified-tie-chain');
 });
 it('does not force anchors or label every strong beat a pillar',()=>{
  const s=source();s.events.forEach(e=>{delete e.harmony;e.durationRatio=1;e.beatQ=0});expect(analyze(s).anchors).toHaveLength(0);
 });
 it('preserves original source attributes and IDs without mutation',()=>{
  const s=source();s.events[0].originalMeasureLabel='0';s.events[0].spelling='C4';
  const n=normalizeStructuralSource(s);expect(n.events[0].originalMeasureLabel).toBe('0');expect(n.events[0].spelling).toBe('C4');
  n.events[0].harmony.id='changed';expect(s.events[0].harmony.id).toBe('I');
 });
 it('is invariant to global transposition and independent of unrelated metadata',()=>{
  const s=source(),a=analyze(s);s.events.forEach(e=>{e.pitchMidi+=12;e.diatonicPitch+=7});
  s.title='not a ranking rule';s.counterpart='ignored';const b=analyze(s);
  expect(b.relations).toEqual(a.relations);expect(b.alternatives).toEqual(a.alternatives);
 });
 it('preserves ambiguous polyphonic overlap rather than reducing it',()=>{
  const s=source();s.events[0].durationRatio=2;expect(analyze(s).relations[0].contradictions).toContain('gap-or-overlap');
  expect(analyze(s).alternatives).toHaveLength(1);
 });
});
