/** Experimental, source-only reduction evidence. NOT imported by production search. */
export const STRUCTURAL_REDUCTION_VERSION = 'structural-reduction/1';
const gcd = (a,b) => b ? gcd(b,a%b) : a;
export function rational(value) {
  if (value && typeof value === 'object') {
    const {n,d}=value;
    if (!Number.isSafeInteger(n)||!Number.isSafeInteger(d)||d<=0) throw new Error('Invalid rational time');
    const g=gcd(Math.abs(n),d); return {n:n/g,d:d/g};
  }
  if (!Number.isFinite(value)) throw new Error('Explicit finite time required');
  // Decimal inputs remain decimal: never silently turn rounded tuplets into thirds.
  for(let d=1;d<=1e9;d*=10) {
    const n=Math.round(value*d);
    if(Number.isSafeInteger(n)&&Math.abs(n/d-value)<1e-12) return rational({n,d});
  }
  throw new Error('Use {n,d} for non-decimal time');
}
const num = q => q.n/q.d;
const add = (a,b) => rational({n:a.n*b.d+b.n*a.d,d:a.d*b.d});
const equal = (a,b) => a.n*b.d===b.n*a.d;
const end = e => add(e.onsetQ,e.durationQ);
const lane = e => JSON.stringify([e.partId,e.voiceId,e.staffId]);

/** Explicit source adapter boundary: no implicit 4/4, onset or voice guessing. */
export function normalizeStructuralSource(input) {
  if(!input.sourceHash||!Array.isArray(input.events)) throw new Error('sourceHash/events required');
  const ids=new Set();
  const events=input.events.map(raw=>{
    if(!raw.id||ids.has(raw.id)) throw new Error('Unique event ids required');
    ids.add(raw.id);
    if(!['note','rest'].includes(raw.kind)) throw new Error('Explicit note/rest kind required');
    if(raw.partId==null||raw.voiceId==null||raw.staffId==null) throw new Error('Explicit part/voice/staff required');
    if(raw.kind==='note'&&!Number.isFinite(raw.pitchMidi)) throw new Error('Note pitch required');
    const onsetQ=rational(raw.onsetQ??raw.onset),durationQ=rational(raw.durationQ??raw.durationRatio);
    if(num(durationQ)<0||num(onsetQ)<0) throw new Error('Negative time');
    return {...structuredClone(raw),onsetQ,durationQ,
      xmlNoteIds:[...(raw.xmlNoteIds??[raw.xmlNoteId??raw.id])],
      meter:raw.meter??null,beatQ:raw.beatQ==null?null:rational(raw.beatQ)};
  });
  return {version:STRUCTURAL_REDUCTION_VERSION,sourceHash:input.sourceHash,
    phraseAnalyzerVersion:input.phraseAnalyzerVersion??null,events};
}

/** beatQ is ZERO-based offset in quarter-note units, never displayed beat number. */
export function metricSupport(e) {
  if(!e.meter||!e.beatQ||e.pickup===true) return null;
  const match=/^(\d+)\/(\d+)$/.exec(e.meter);if(!match)return null;
  const beats=Number(match[1]),unit=Number(match[2]),position=num(e.beatQ);
  if(!beats||!unit||position<0||position>=beats*4/unit) return null;
  let grouping=e.grouping;
  if(!grouping) {
    if(unit===8&&[6,9,12].includes(beats)) grouping=Array(beats/3).fill(3);
    else if([2,3,4].includes(beats)) grouping=Array(beats).fill(1);
    else return null; // 5/8, 7/8, 6/4 etc. require known grouping.
  }
  if(!Array.isArray(grouping)||grouping.some(x=>!Number.isInteger(x)||x<=0)||grouping.reduce((a,b)=>a+b,0)!==beats)return null;
  if(position===0)return 1;
  let cursor=0;
  for(let i=0;i<grouping.length-1;i++){
    cursor+=grouping[i]*4/unit;
    if(Math.abs(position-cursor)<1e-10)return grouping.length===4&&i===1?.65:.55;
  }
  return .2;
}

function soundingEvents(source) {
  const chains=new Map(),issues=[],output=[];
  for(const e of source.events){
    if(e.tieChainId){const key=JSON.stringify([e.partId,e.voiceId,e.tieChainId]);const list=chains.get(key)??[];list.push(e);chains.set(key,list)}
    else {output.push({...e,sourceEventIds:[e.id]});if(e.tieStop||e.isAttack===false)issues.push({eventId:e.id,reason:'unresolved-tie-continuation'})}
  }
  for(const chain of chains.values()){
    chain.sort((a,b)=>num(a.onsetQ)-num(b.onsetQ));
    const first=chain[0],valid=first.kind==='note'&&first.isAttack!==false&&!first.tieStop&&chain.every((e,i)=>
      e.kind==='note'&&e.pitchMidi===first.pitchMidi&&e.staffId===first.staffId&&
      (i===0||e.isAttack===false&&equal(end(chain[i-1]),e.onsetQ)));
    if(!valid){issues.push({eventIds:chain.map(e=>e.id),reason:'unverified-tie-chain'});output.push(...chain.map(e=>({...e,sourceEventIds:[e.id],unresolvedTie:true})));continue}
    output.push({...first,durationQ:chain.reduce((s,e)=>add(s,e.durationQ),rational(0)),
      sourceEventIds:chain.map(e=>e.id),xmlNoteIds:chain.flatMap(e=>e.xmlNoteIds),verifiedTie:true});
  }
  return {events:output.sort((a,b)=>num(a.onsetQ)-num(b.onsetQ)||a.id.localeCompare(b.id)),issues};
}

function step(a,b){
  const semitone=Math.abs(a.pitchMidi-b.pitchMidi);
  if(semitone===0)return false;
  if(Number.isInteger(a.diatonicPitch)&&Number.isInteger(b.diatonicPitch))return Math.abs(a.diatonicPitch-b.diatonicPitch)===1;
  return semitone<=2;
}
const median = xs => [...xs].sort((a,b)=>a-b)[Math.floor(xs.length/2)]??0;

/** No counterpart/query input. Every omitted event must have a typed relation. */
export function analyzeStructuralSource(input) {
  const source=normalizeStructuralSource(input),sounding=soundingEvents(source),lanes=new Map();
  for(const e of sounding.events){const key=lane(e),list=lanes.get(key)??[];list.push(e);lanes.set(key,list)}
  const relations=[],anchors=[];
  for(const ns of lanes.values()){
    const supports=ns.map((e,i)=>{
      const nearby=ns.slice(Math.max(0,i-4),i+5).filter(n=>n.kind==='note').map(n=>num(n.durationQ));
      const typical=median(nearby),m=metricSupport(e),groups=[];
      if(m!==null&&m>=.55)groups.push('meter');
      if(typical>0&&num(e.durationQ)>=1.5*typical)groups.push('duration');
      if(e.harmony?.confidence==='high'&&e.harmony.chordTone===true)groups.push('harmony');
      if(e.phraseBoundary?.confidence==='high'&&e.phraseBoundary.kind==='closing')groups.push('phrase');
      if(e.repetitionStable===true)groups.push('within-source-repetition');
      return {groups,metric:m,typical};
    });
    ns.forEach((e,i)=>{
      const s=supports[i];
      if(e.kind==='note'&&e.isAttack!==false&&!e.tieStop&&!e.unresolvedTie&&!e.grace&&!e.cue&&num(e.durationQ)>0&&s.groups.length>=2)
        anchors.push({eventId:e.id,sourceEventIds:e.sourceEventIds,support:s.groups,confidence:'heuristic',lane:lane(e)});
    });
    for(let i=1;i<ns.length-1;i++){
      const [l,m,r]=[ns[i-1],ns[i],ns[i+1]];
      if([l,m,r].some(e=>e.kind!=='note'))continue;
      const a=m.pitchMidi-l.pitchMidi,b=r.pitchMidi-m.pitchMidi;
      const passing=step(l,m)&&step(m,r)&&Math.sign(a)===Math.sign(b);
      const neighbor=step(l,m)&&step(m,r)&&l.pitchMidi===r.pitchMidi;
      if(!passing&&!neighbor)continue;
      const ls=supports[i-1],ms=supports[i],rs=supports[i+1],reasons=[],contradictions=[];
      if(!equal(end(l),m.onsetQ)||!equal(end(m),r.onsetQ))contradictions.push('gap-or-overlap');
      if([l,m,r].some(e=>e.isAttack===false||e.tieStop||e.unresolvedTie))contradictions.push('unresolved-attack');
      if([l,m,r].some(e=>e.grace||e.cue||num(e.durationQ)===0))contradictions.push('grace-or-cue-context');
      if([l,m,r].some(e=>e.phraseBoundary?.confidence==='high'))contradictions.push('phrase-boundary');
      if(m.repetitionStable||m.protectedAnchor)contradictions.push('protected-characteristic-tone');
      if(ms.groups.length>=2)contradictions.push('independent-middle-support');
      if(ls.groups.length&&rs.groups.length)reasons.push('supported-endpoints');
      if(num(m.durationQ)<Math.min(num(l.durationQ),num(r.durationQ)))reasons.push('relatively-short');
      if(ms.metric!==null&&ls.metric!==null&&rs.metric!==null&&ms.metric<Math.min(ls.metric,rs.metric))reasons.push('relatively-weak');
      const h=[l,m,r].map(e=>e.harmony);
      if(h.every(x=>x?.confidence==='high'&&x.id!=null)){
        if(h.some(x=>x.id!==h[0].id))contradictions.push('harmony-change');
        else if(h[1].chordTone===false&&h[0].chordTone===true&&h[2].chordTone===true)reasons.push('harmonic-elaboration');
      }
      const spellingKnown=[l,m,r].every(e=>Number.isInteger(e.diatonicPitch));
      if(!spellingKnown)reasons.push('semitone-shape-only');
      const allowed=contradictions.length===0&&reasons.includes('supported-endpoints')&&
        (reasons.includes('relatively-short')||reasons.includes('relatively-weak'));
      relations.push({ruleId:passing?'R02':'R03',leftAnchor:l.id,rightAnchor:r.id,interiorEvents:[m.id],
        originalEventIds:[...l.sourceEventIds,...m.sourceEventIds,...r.sourceEventIds],
        support:reasons,contradictions,status:allowed?'eligible':'blocked',
        confidence:allowed&&spellingKnown&&reasons.includes('harmonic-elaboration')?'supported':'provisional',
        lane:lane(m),contextRange:{startQ:l.onsetQ,endQ:end(r)}});
    }
  }
  // One deterministic non-conflicting L1 proposal. No recursive deletion and no
  // forced minimum anchors. Untouched source is always the first alternative.
  const removed=new Set(),usedEndpoints=new Set(),selected=[];
  for(const relation of relations){
    if(relation.status!=='eligible'||relation.confidence!=='supported')continue;
    const mid=relation.interiorEvents[0];
    if(usedEndpoints.has(mid)||removed.has(relation.leftAnchor)||removed.has(relation.rightAnchor))continue;
    removed.add(mid);usedEndpoints.add(relation.leftAnchor);usedEndpoints.add(relation.rightAnchor);selected.push(relation);
  }
  return {version:STRUCTURAL_REDUCTION_VERSION,sourceHash:source.sourceHash,
    source, soundingEvents:sounding.events,issues:sounding.issues,anchors,relations,
    alternatives:[{layer:'L0',eventIds:sounding.events.map(e=>e.id),relations:[]},
      ...(removed.size?[{layer:'L1',eventIds:sounding.events.filter(e=>!removed.has(e.id)).map(e=>e.id),relations:selected}]:[])],
    rankingChanged:false,limitations:['Local three-event hypotheses only; not a Schenkerian analysis.',
      'Cross-staff and complex ornaments remain unmerged.','Unknown harmony/spelling cannot authorize L1 removal.']};
}
