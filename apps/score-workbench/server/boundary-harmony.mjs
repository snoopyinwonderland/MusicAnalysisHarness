// Phrase-boundary-focused harmony/cadence evidence.
// This is deliberately not a full-score chord labeller. Scores are
// uncalibrated hypothesis strengths, never correctness probabilities.
const VERSION='boundary-harmony-cadence-v0.2';
const clamp=value=>Math.max(0,Math.min(1,value));
const round=value=>Math.round(value*1e6)/1e6;
const pc=value=>((Number(value)%12)+12)%12;
const MAJOR_TONIC_BY_FIFTHS={[-7]:11,[-6]:6,[-5]:1,[-4]:8,[-3]:3,[-2]:10,[-1]:5,0:0,1:7,2:2,3:9,4:4,5:11,6:6,7:1};
const SHARP=['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'];
const FLAT=['C','Db','D','Eb','E','F','Gb','G','Ab','A','Bb','B'];
const TEMPLATES=[
  {quality:'major',suffix:'',intervals:[0,4,7]},
  {quality:'minor',suffix:'m',intervals:[0,3,7]},
  {quality:'diminished',suffix:'°',intervals:[0,3,6]},
  {quality:'dominant-seventh',suffix:'7',intervals:[0,4,7,10]},
];
const finite=value=>Number.isFinite(Number(value));

function noteName(pitch,keyFifths){return (Number(keyFifths)<0?FLAT:SHARP)[pc(pitch)]}
function dedupeEvents(streams){
  const events=new Map();
  for(const stream of streams||[]){
    if(String(stream.streamId||'').endsWith(':structural'))continue;
    for(const note of stream.notes||[]){
      if(!finite(note.p)||!finite(note.o)||!finite(note.d)||Number(note.d)<=0||note.u)continue;
      const onset=Number(note.o),duration=Number(note.d),key=`${stream.streamId}|${onset}|${note.p}|${duration}`;
      events.set(key,{streamId:stream.streamId,onset,end:onset+duration,pitch:Number(note.p),pitchClass:pc(note.p),spelling:note.s,measure:note.m,beat:note.b,tieContinuation:Boolean(note.te&&!note.ts)});
    }
  }
  return [...events.values()].sort((a,b)=>a.onset-b.onset||a.pitch-b.pitch);
}

function chordCandidates(active,keyFifths){
  const observed=new Set(active.map(note=>note.pitchClass)),bass=active.length?pc(Math.min(...active.map(note=>note.pitch))):null;
  if(observed.size<2)return[];
  const candidates=[];
  for(let root=0;root<12;root++)for(const template of TEMPLATES){
    const wanted=new Set(template.intervals.map(interval=>pc(root+interval))),matched=[...observed].filter(value=>wanted.has(value)).length,precision=matched/observed.size,completeness=matched/wanted.size,extras=observed.size-matched;
    let fit=.52*precision+.36*completeness+.12*Number(bass===root)-.08*Math.min(2,extras);
    if(matched<2)fit-=.3;
    if(template.quality==='dominant-seventh'&&(observed.size<3||!observed.has(pc(root+4))))fit-=.18;
    candidates.push({label:`${noteName(root,keyFifths)}${template.suffix}`,rootPc:root,quality:template.quality,bassPc:bass,fit:round(clamp(fit)),observedPitchClasses:[...observed].sort((a,b)=>a-b),missingPitchClasses:[...wanted].filter(value=>!observed.has(value)).sort((a,b)=>a-b),extraPitchClasses:[...observed].filter(value=>!wanted.has(value)).sort((a,b)=>a-b)});
  }
  candidates.sort((a,b)=>b.fit-a.fit||a.missingPitchClasses.length-b.missingPitchClasses.length||a.rootPc-b.rootPc);
  const first=candidates[0],parallel=candidates.find(candidate=>candidate.rootPc===first?.rootPc&&candidate.quality!==first.quality&&['major','minor'].includes(candidate.quality)&&['major','minor'].includes(first.quality)&&Math.abs(candidate.fit-first.fit)<1e-6),thirdPresent=first&&observed.has(pc(first.rootPc+(first.quality==='major'?4:3)));
  if(first&&parallel&&!thirdPresent){const ambiguous={...first,label:`${noteName(first.rootPc,keyFifths)}(no3)`,quality:'third-ambiguous',fit:round(clamp(first.fit-.08)),missingPitchClasses:[pc(first.rootPc+3),pc(first.rootPc+4)],ambiguity:'major/minor third absent'};return[ambiguous,first,parallel]}
  return candidates.slice(0,3);
}

function harmonicSegments(events,start,end,keyFifths){
  const relevant=events.filter(note=>note.end>start&&note.onset<end),points=[start,end,...relevant.flatMap(note=>[Math.max(start,note.onset),Math.min(end,note.end)])].filter(value=>value>=start&&value<=end).sort((a,b)=>a-b),unique=[...new Set(points)],atoms=[];
  for(let index=0;index<unique.length-1;index++){
    const left=unique[index],right=unique[index+1];if(right-left<1e-6)continue;
    const middle=(left+right)/2,active=relevant.filter(note=>note.onset<=middle&&middle<note.end),candidates=chordCandidates(active,keyFifths);
    atoms.push({start:left,end:right,active,selected:candidates[0]||null,alternatives:candidates.slice(1)});
  }
  const merged=[];
  for(const atom of atoms){const previous=merged.at(-1),identity=atom.selected?`${atom.selected.rootPc}:${atom.selected.quality}`:'unknown';if(previous&&previous.identity===identity&&Math.abs(previous.end-atom.start)<1e-6){previous.end=atom.end;previous.duration=round(previous.end-previous.start);previous.fit=round((previous.fit+Number(atom.selected?.fit||0))/2);previous.observedPitchClasses=[...new Set([...previous.observedPitchClasses,...(atom.selected?.observedPitchClasses||[])])].sort((a,b)=>a-b);continue}merged.push({identity,start:round(atom.start),end:round(atom.end),duration:round(atom.end-atom.start),label:atom.selected?.label||'unknown',rootPc:atom.selected?.rootPc??null,quality:atom.selected?.quality||'unknown',bassPc:atom.selected?.bassPc??null,fit:Number(atom.selected?.fit||0),observedPitchClasses:atom.selected?.observedPitchClasses||[],alternatives:atom.alternatives})}
  return merged.filter(segment=>segment.label!=='unknown'&&segment.fit>=.38);
}

function degree(root,tonic){return pc(root-tonic)}
function functionOf(segment,key){
  if(!segment)return'unknown';const relative=degree(segment.rootPc,key.tonicPc);
  if(relative===0)return'tonic';if(relative===7||relative===11&&segment.quality==='diminished')return'dominant';if(relative===2||relative===5)return'predominant';return'other';
}
function romanOf(segment,key){
  if(!segment)return'unknown';const degrees={0:'I',1:'bII',2:'II',3:'bIII',4:'III',5:'IV',6:'#IV',7:'V',8:'bVI',9:'VI',10:'bVII',11:'VII'},base=degrees[degree(segment.rootPc,key.tonicPc)]||'?';if(segment.quality==='minor')return base.toLowerCase();if(segment.quality==='diminished')return `${base.toLowerCase()}°`;if(segment.quality==='dominant-seventh')return `${base}7`;return base;
}
function keyCandidates(keyFifths){
  const fifths=Math.max(-7,Math.min(7,Number(keyFifths)||0)),major=MAJOR_TONIC_BY_FIFTHS[fifths]??0,minor=pc(major+9);
  return[{tonicPc:major,mode:'major',label:`${noteName(major,fifths)} major`,prior:'key-signature-relative-major'},{tonicPc:minor,mode:'minor',label:`${noteName(minor,fifths)} minor`,prior:'key-signature-relative-minor'}];
}
function fullScoreKeyCandidates(events,segments,keyFifths){
  const scales={major:[0,2,4,5,7,9,11],minor:[0,2,3,5,7,8,10]};
  return keyCandidates(keyFifths).map(key=>{
    const scale=new Set(scales[key.mode].map(interval=>pc(key.tonicPc+interval))),total=events.reduce((sum,note)=>sum+Math.max(0,note.end-note.onset),0),diatonic=events.reduce((sum,note)=>sum+(scale.has(note.pitchClass)?Math.max(0,note.end-note.onset):0),0);
    const segmentDuration=segments.reduce((sum,segment)=>sum+segment.duration,0),functional=segments.reduce((sum,segment)=>sum+(['tonic','dominant','predominant'].includes(functionOf(segment,key))?segment.duration:0),0),final=segments.at(-1),finalTonic=Number(functionOf(final,key)==='tonic');
    const score=clamp(.62*(total?diatonic/total:0)+.28*(segmentDuration?functional/segmentDuration:0)+.1*finalTonic);
    return{...key,score:round(score),evidence:{diatonicDurationRatio:round(total?diatonic/total:0),functionalSegmentRatio:round(segmentDuration?functional/segmentDuration:0),finalTonicCandidate:Boolean(finalTonic)}};
  }).sort((a,b)=>b.score-a.score);
}

export function analyzeFullHarmony({streams,keyFifths=0,meter='4/4'}){
  const events=dedupeEvents(streams),end=events.reduce((value,note)=>Math.max(value,note.end),0),absoluteSegments=end>0?harmonicSegments(events,0,end,keyFifths):[],keys=fullScoreKeyCandidates(events,absoluteSegments,keyFifths),selectedKey=keys[0]||null;
  const rawSegments=absoluteSegments.map((segment,index)=>{
    const starts=events.filter(note=>Math.abs(note.onset-segment.start)<1e-6),active=events.filter(note=>note.onset<segment.end&&note.end>segment.start),last=[...active].sort((a,b)=>b.onset-a.onset)[0],alternatives=(segment.alternatives||[]).map(candidate=>({absoluteLabel:candidate.label,romanLabel:selectedKey?romanOf(candidate,selectedKey):'unknown',fit:candidate.fit,quality:candidate.quality,rootPc:candidate.rootPc})),margin=alternatives.length?segment.fit-Number(alternatives[0].fit||0):segment.fit,reasons=[];
    if(segment.fit<.5)reasons.push('low_template_fit');
    if(margin<.03&&segment.fit<.7)reasons.push('small_candidate_margin');
    if(segment.quality==='third-ambiguous'&&segment.duration>=1)reasons.push('third_missing');
    if(segment.observedPitchClasses.length>4&&segment.fit<.62)reasons.push('dense_or_nct_surface');
    const reviewScore=(1-segment.fit)+Math.max(0,.05-margin)*2+.12*Number(segment.quality==='third-ambiguous')+.1*Number(segment.observedPitchClasses.length>4);
    return{analysisId:`auto_harmony_${index+1}`,span:{start:segment.start,end:segment.end,semantics:'[start,end)'},displayLocation:{startMeasure:starts[0]?.measure??active[0]?.measure??null,startBeat:starts[0]?.beat??active[0]?.beat??null,endMeasure:last?.measure??null,endBeat:last?.beat??null},selected:{absoluteLabel:segment.label,romanLabel:selectedKey?romanOf(segment,selectedKey):'unknown',fit:segment.fit,quality:segment.quality,rootPc:segment.rootPc,bassPc:segment.bassPc,observedPitchClasses:segment.observedPitchClasses},alternatives,reviewCandidate:false,reviewPriority:'none',reviewReasons:reasons,_reviewScore:reviewScore};
  });
  const reviewLimit=Math.min(80,Math.max(12,Math.ceil(rawSegments.length*.1))),reviewIds=new Set(rawSegments.filter(segment=>segment.reviewReasons.length).sort((a,b)=>b._reviewScore-a._reviewScore).slice(0,reviewLimit).map(segment=>segment.analysisId));
  const segments=rawSegments.map(({_reviewScore,...segment})=>({...segment,reviewCandidate:reviewIds.has(segment.analysisId),reviewPriority:reviewIds.has(segment.analysisId)?segment.selected.fit<.5?'high':'medium':'none'}));
  return{version:'blind-full-score-harmony-v0.1',calibrated:false,inputPolicy:'blind-score-events-only',scope:'whole-score-surface-and-sustained-events',meter,selectedKey:selectedKey?{label:selectedKey.label,tonicPc:selectedKey.tonicPc,mode:selectedKey.mode,score:selectedKey.score,source:selectedKey.prior,evidence:selectedKey.evidence}:null,keyHypotheses:keys,segments,summary:{segmentCount:segments.length,reviewCandidateCount:segments.filter(segment=>segment.reviewCandidate).length},limitations:['Roman numerals depend on an uncalibrated key hypothesis.','Templates cover major, minor, diminished, and dominant-seventh sonorities only.','Non-chord tones are not yet explicitly classified.','Fit and key scores are heuristic evidence strengths, not correctness probabilities.','Imported annotations are reserved for evaluation and calibration; they are not visible to this prediction pass.']};
}
function cadenceHypotheses(preparation,arrival,boundary,key,events){
  const previousFunction=functionOf(preparation,key),arrivalFunction=functionOf(arrival,key),gap=boundary.cues?.find(item=>item.name==='observed-gap'),arrivalNotes=events.filter(note=>note.onset<=arrival?.start&&arrival?.start<note.end),soprano=arrivalNotes.length?pc(Math.max(...arrivalNotes.map(note=>note.pitch))):null,bassRoot=arrival?.bassPc===arrival?.rootPc,sopranoTonic=soprano===key.tonicPc,arrivalBeat=arrivalNotes.find(note=>Math.abs(note.onset-arrival.start)<1e-6)?.beat,strongMetric=Number(arrivalBeat)===1||Number(arrivalBeat)===3;
  const incomplete=arrival?.quality==='third-ambiguous'||arrival?.observedPitchClasses?.length<3,evidence=[{code:'phrase_boundary_strength',value:boundary.strength},{code:'observed_gap',value:Boolean(gap),strength:gap?.strength||0},{code:'preparation_function',value:previousFunction},{code:'arrival_function',value:arrivalFunction},{code:'arrival_root_position',value:bassRoot},{code:'soprano_arrival_on_tonic',value:sopranoTonic},{code:'arrival_metric_position',value:arrivalBeat??null},{code:'arrival_incomplete',value:incomplete}];
  const results=[];
  if(previousFunction==='dominant'&&arrivalFunction==='tonic'){
    const pac=.46+.12*Number(bassRoot)+.12*Number(sopranoTonic)+.08*Number(strongMetric)+.1*Number(Boolean(gap))-.14*Number(incomplete);
    results.push({type:bassRoot&&sopranoTonic?'PAC':'IAC',strength:round(clamp(pac)),evidence,against:[...(!bassRoot?['tonic_not_in_root_position']:[]),...(!sopranoTonic?['soprano_not_on_tonic']:[]),...(!strongMetric?['arrival_not_metrically_strong']:[])]});
    if(!(bassRoot&&sopranoTonic))results.push({type:'PAC',strength:round(clamp(pac-.22)),evidence,against:['complete_PAC_conditions_not_observed']});
  }
  if(arrivalFunction==='dominant')results.push({type:'HC',strength:round(clamp(.48+.16*Number(Boolean(gap))+.08*Number(strongMetric)+.08*Number(arrival.fit>=.65)-.16*Number(incomplete)-.08*Number(!bassRoot))),evidence,against:[...(!gap?['no_observed_post-arrival_gap']:[]),...(incomplete?['arrival_chord_is_incomplete']:[]),...(!bassRoot?['dominant_root_not_in_bass']:[])]});
  if(previousFunction==='dominant'&&arrivalFunction==='other')results.push({type:'DC',strength:round(clamp(.42+.14*Number(Boolean(gap))+.08*Number(strongMetric))),evidence,against:['non-tonic target requires contextual confirmation']});
  if(degree(preparation?.rootPc,key.tonicPc)===5&&arrivalFunction==='tonic')results.push({type:'plagal',strength:round(clamp(.44+.14*Number(Boolean(gap))+.08*Number(strongMetric))),evidence,against:['style profile not yet classified']});
  if(!results.length)results.push({type:'no_clear_cadence',strength:round(clamp(.52+.12*Number(!gap))),evidence,against:['recognized cadential harmonic syntax not observed']});
  return results.sort((a,b)=>b.strength-a.strength);
}

export function analyzeBoundaryHarmony({melodyNotes,boundaries,streams,keyFifths=0,meter='4/4'}){
  const events=dedupeEvents(streams),keys=keyCandidates(keyFifths),records=[];
  for(const boundary of boundaries||[]){
    if(!boundary.supported)continue;const target=melodyNotes?.[boundary.index];if(!target||!finite(target.o??target.onset))continue;
    const time=Number(target.o??target.onset),segments=harmonicSegments(events,Math.max(0,time-8),time+2,keyFifths),before=segments.filter(segment=>segment.end<=time+1e-6),after=segments.filter(segment=>segment.start>=time-1e-6),terminal=melodyNotes?.[boundary.index-1],terminalStart=finite(terminal?.o??terminal?.onset)?Number(terminal.o??terminal.onset):null,terminalEnd=terminalStart!==null&&finite(terminal?.d??terminal?.durationRatio)?terminalStart+Number(terminal.d??terminal.durationRatio):null,terminalReachesBoundary=terminalEnd!==null&&terminalEnd>=time-1e-6,terminalCrossesBarline=finite(terminal?.tm??terminal?.tieEndMeasure)&&finite(terminal?.m??terminal?.measure)&&Number(terminal.tm??terminal.tieEndMeasure)>Number(terminal.m??terminal.measure),tieContinuationOnset=terminalCrossesBarline&&terminalStart!==null&&terminalEnd!==null?[...events].filter(note=>note.pitch===Number(terminal?.p??terminal?.pitchMidi)&&note.tieContinuation&&note.onset>terminalStart+1e-6&&note.onset<terminalEnd+1e-6).sort((a,b)=>a.onset-b.onset)[0]?.onset:null,terminalSegments=terminalStart===null||terminalEnd===null||(!terminalReachesBoundary&&!terminalCrossesBarline)?[]:before.filter(segment=>segment.end>terminalStart&&segment.start<Math.min(time,terminalEnd)).map(segment=>({...segment,terminalOverlap:round(Math.max(0,Math.min(segment.end,terminalEnd,time)-Math.max(segment.start,terminalStart)))})).filter(segment=>segment.terminalOverlap>0),tieContinuationArrival=finite(tieContinuationOnset)?terminalSegments.filter(segment=>segment.start<=Number(tieContinuationOnset)+1e-6&&Number(tieContinuationOnset)<segment.end-1e-6).sort((a,b)=>b.observedPitchClasses.length-a.observedPitchClasses.length||b.fit-a.fit)[0]||null:null,terminalArrival=tieContinuationArrival||(terminalReachesBoundary?[...terminalSegments].sort((a,b)=>(b.terminalOverlap*(.65+.35*b.fit))-(a.terminalOverlap*(.65+.35*a.fit))||a.start-b.start)[0]||null:null),recentArrival=before.at(-1)||null,arrival=terminalArrival||(recentArrival&&time-recentArrival.end<=2?recentArrival:null),preparation=arrival?[...before].filter(segment=>segment.end<=arrival.start+1e-6).reverse().find(segment=>segment.identity!==arrival.identity&&(segment.duration>=.25||segment.fit>=.85))||null:null,next=after[0]||null;
    const keyResults=keys.map(key=>{const cadence=cadenceHypotheses(preparation,arrival,boundary,key,events),syntaxBonus=cadence[0].type==='no_clear_cadence'?0:.12;return{...key,score:round(clamp(.45+.2*Number(functionOf(arrival,key)!=='other')+syntaxBonus)),preparationRoman:romanOf(preparation,key),arrivalRoman:romanOf(arrival,key),cadenceHypotheses:cadence}}).sort((a,b)=>b.score-a.score),selectedKey=keyResults[0],cadences=selectedKey?.cadenceHypotheses||[],selectedCadence=cadences[0]?.type!=='no_clear_cadence'&&cadences[0]?.strength>=.58?cadences[0]:null;
    const beforeLabels=[preparation,arrival].filter(Boolean).map(segment=>segment.label),progression=`${beforeLabels.join(' → ')||'판정 보류'}${next?` | ${next.label}`:''}`;
    const beforeRomans=[selectedKey?.preparationRoman,selectedKey?.arrivalRoman].filter(label=>label&&label!=='unknown'),romanProgression=`${beforeRomans.join(' → ')||'판정 보류'}${next&&selectedKey?` | ${romanOf(next,selectedKey)}`:''}`;
    records.push({analysisId:`bh_${boundary.index}`,boundaryIndex:boundary.index,boundaryTime:round(time),scope:{leftWindowQuarters:8,rightWindowQuarters:2,intervalSemantics:'[start,end)',arrivalSelection:tieContinuationArrival?'tie-continuation-onset':terminalArrival?'max-overlap-with-terminal-sounding-event':'latest-recent-harmony'},observed:{eventCount:events.filter(note=>note.end>time-8&&note.onset<time+2).length,terminalMelodySpan:terminalStart===null?null:{start:round(terminalStart),end:round(terminalEnd),pitch:Number(terminal?.p??terminal?.pitchMidi),tieContinuationOnset:finite(tieContinuationOnset)?round(Number(tieContinuationOnset)):null},terminalHarmonyCandidates:terminalSegments,preparation,arrival,next},harmonyProgression:{display:progression,romanDisplay:romanProgression,preparationRoman:selectedKey?.preparationRoman||null,arrivalRoman:selectedKey?.arrivalRoman||null,afterBoundaryRoman:next&&selectedKey?romanOf(next,selectedKey):null,beforeBoundary:beforeLabels,afterBoundary:next?.label||null},keyHypotheses:keyResults.map(({cadenceHypotheses,...key})=>key),selectedKey:selectedKey?{label:selectedKey.label,score:selectedKey.score,source:selectedKey.prior}:null,cadenceHypotheses:cadences,selectedCadence,status:arrival?'provisional':'insufficient_evidence'});
  }
  return{version:VERSION,calibrated:false,scope:'phrase-boundary-windows-only',meter,records,limitations:['Indexed note streams are a transitional input; Canonical IR attack/sounding IDs are not connected yet.','Arrival harmony is selected by overlap with the terminal melody sounding event; explicit Canonical IR tie chains remain required for durable provenance.','Chord and cadence strengths are uncalibrated evidence scores, not probabilities.','No cadence is inferred from a phrase boundary alone.','Surface templates are intentionally limited to major, minor, diminished, and dominant-seventh chords.']};
}
