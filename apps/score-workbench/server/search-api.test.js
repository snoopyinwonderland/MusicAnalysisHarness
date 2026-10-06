import { describe, expect, it } from 'vitest';
import { alignLocal, alignRhythmDtw, annotateRepeatAttackRelations, annotateStructural, calibratedResultRanking, catalogTitleMatches, compareStructural, createWeightedLru, displayMeasure, diversifyCandidates, explainOctaveEditAlignment, findAbsoluteExact, findAbsoluteExactMatches, firstMeasureIsPickup, fullResearchScoreEnabled, intervalRetrievalBonus, intervalShape, metricWeightAt, metricalEvidence, metricalSkeleton, metricalSkeletonEvidence, motifImportance, normalizeYoutubeTitle, optionalPositiveNumber, parseMeter, phraseAlignmentEvidence, pitchEqualitySimilarity, preferredExactSpan, prepareQueryNotes, primaryStreamOrder, queryDiscrimination, rankedMotifs, repairMetadataInXml, repairMetadataText, reflowRestrictedPreview, restrictedPreviewXml, resultAdmissionAllowed, retrievalRowLimit, rhythmRankFactor, rhythmShapeSimilarity, score, searchCatalog, searchDatabase, singlePitchSubstitutionCandidates, singlePitchSubstitutionMatch, sparseAlignmentAllowed, splitIntervalSeedBonus, strictExactRhythmMatch, strictOmissionAdmissionException, translateInstrumentName, transpositionResidualScore, youtubeId } from './search-api.mjs';

const notes = pitches => pitches.map((pitchMidi, i) => ({
  id: String(i), kind: 'note', pitchMidi, durationRatio: 1,
}));

describe('bounded parsed-work cache',()=>{
 it('refreshes recency and evicts the least recently used weight',()=>{const cache=createWeightedLru(5);cache.set('a',1,2);cache.set('b',2,2);expect(cache.get('a')).toBe(1);cache.set('c',3,2);expect(cache.get('b')).toBeUndefined();expect(cache.get('a')).toBe(1);expect(cache.stats()).toEqual({entries:2,weight:4})});
 it('does not retain an item larger than the cache budget',()=>{const cache=createWeightedLru(2);cache.set('large',1,3);expect(cache.stats()).toEqual({entries:0,weight:0})});
});

describe('motif analysis payload',()=>{
  it('keeps a representative notated sequence and occurrence locations',()=>{
    const raw=[60,62,64,65,67,69,60,62,64,65,67,69].map((p,index)=>({p,s:['C4','D4','E4','F4','G4','A4'][index%6],d:index%2?.5:1,o:index,m:index<6?1:2}));
    const motif=rankedMotifs(raw)[0];
    expect(motif.events).toHaveLength(6);
    expect(motif.events.map(event=>event.pitchMidi)).toEqual([60,62,64,65,67,69]);
    expect(motif.events.map(event=>event.durationRatio)).toEqual([1,.5,1,.5,1,.5]);
    expect(motif.occurrences).toHaveLength(2);
    expect(motif.startMeasure).toBe(1);
  });
  it('excludes low-information same-note repetition from principal motifs',()=>{
    const repeated=Array.from({length:16},(_,index)=>({p:index<12?60:62,s:index<12?'C4':'D4',d:.5,o:index*.5,m:1}));
    expect(rankedMotifs(repeated)).toEqual([]);
  });
  it('also excludes a four-note motif that only alternates two pitches',()=>{
    const alternating=Array.from({length:12},(_,index)=>({p:index%2?62:60,s:index%2?'D4':'C4',d:.5,o:index*.5,m:1}));
    expect(rankedMotifs(alternating)).toEqual([]);
  });
});

describe('displayed result score calibration',()=>{
  it('does not let hidden bonuses reverse a clearly stronger evidence profile',()=>{
    const weaker={interval:90,rhythm:55,meter:90,structural:34};
    const stronger={interval:98,rhythm:69,meter:91,structural:87};
    expect(calibratedResultRanking(false,100,weaker,'melody_rhythm',20,true)).toBeLessThan(calibratedResultRanking(false,70,stronger,'melody_rhythm',-20,true));
  });
  it('keeps hidden corrections bounded and each visible component monotonic',()=>{
    const base={interval:85,rhythm:70,meter:75,structural:65};
    const value=calibratedResultRanking(false,80,base,'melody_rhythm',0,true);
    for(const key of Object.keys(base))expect(calibratedResultRanking(false,80,{...base,[key]:base[key]+5},'melody_rhythm',0,true)).toBeGreaterThanOrEqual(value);
    expect(calibratedResultRanking(false,100,base,'melody_rhythm',100,true)-calibratedResultRanking(false,0,base,'melody_rhythm',-100,true)).toBeLessThanOrEqual(3);
  });
  const scores={interval:93,contour:100,rhythm:81};
  it('reserves 100 for exact results',()=>expect(calibratedResultRanking(true,96,scores,'melody_rhythm',5)).toBe(100));
  it('keeps surface mismatch visible despite retrieval and structure bonuses',()=>{
    const value=calibratedResultRanking(false,96,scores,'melody_rhythm',20);
    expect(value).toBeLessThan(97);expect(value).toBeGreaterThan(90);
  });
});

describe('restricted score preview',()=>{
  it('shows the complete research score locally while retaining the production restriction',()=>{
    expect(fullResearchScoreEnabled({NODE_ENV:'development'})).toBe(true);
    expect(fullResearchScoreEnabled({NODE_ENV:'production'})).toBe(false);
    expect(fullResearchScoreEnabled({NODE_ENV:'production',KYSING_FULL_SCORE_TEST_MODE:'1'})).toBe(true);
    expect(fullResearchScoreEnabled({NODE_ENV:'development',KYSING_FULL_SCORE_TEST_MODE:'0'})).toBe(false);
  });
  it('removes encoded system and page layout only when explicitly reflowing',()=>{
    const xml='<measure number="1"><print new-page="yes"><system-layout><system-distance>140</system-distance></system-layout></print><note/></measure><measure number="2"><print new-system="yes"/><note/></measure><measure number="3"><print><measure-numbering>system</measure-numbering></print></measure>';
    const reflowed=reflowRestrictedPreview(xml);
    expect(reflowed).not.toContain('new-page');expect(reflowed).not.toContain('new-system');expect(reflowed).not.toContain('system-distance');
    expect(reflowed).toContain('<measure-numbering>system</measure-numbering>');
  });
  it('does not interpret an omitted ordinal as measure zero',()=>{
    expect(Number.isNaN(optionalPositiveNumber(null))).toBe(true);
    expect(Number.isNaN(optionalPositiveNumber(''))).toBe(true);
    expect(optionalPositiveNumber('79')).toBe(79);
  });
  it('returns only the matched part and a bounded measure neighborhood',()=>{
    const measures=Array.from({length:10},(_,index)=>`<measure number="${index+1}">${index===0?'<attributes><divisions>1</divisions></attributes>':''}<note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration></note></measure>`).join('');
    const xml=`<score-partwise version="4.0"><part-list><score-part id="P1"><part-name>Voice</part-name></score-part><score-part id="P2"><part-name>Piano</part-name></score-part></part-list><part id="P1">${measures}</part><part id="P2">${measures}</part></score-partwise>`;
    const preview=restrictedPreviewXml(xml,'P1:1:1',5,6,2);
    expect(preview).toContain('<part id="P1">');expect(preview).not.toContain('<part id="P2">');expect(preview).not.toContain('<score-part id="P2">');
    expect((preview.match(/<measure\b/g)||[])).toHaveLength(6);expect(preview).toContain('<divisions>1</divisions>');
  });
  it('keeps inherited divisions before a mid-measure clef change',()=>{
    const xml='<score-partwise><part-list><score-part id="P1"><part-name>Voice</part-name></score-part></part-list><part id="P1"><measure number="1"><attributes><divisions>4</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes><note><rest/><duration>16</duration></note></measure><measure number="2"><note><rest/><duration>4</duration></note></measure><measure number="3"><note><pitch><step>C</step><octave>4</octave></pitch><duration>4</duration></note><attributes><clef><sign>G</sign><line>2</line></clef></attributes></measure></part></score-partwise>';
    const preview=restrictedPreviewXml(xml,'P1:1:1',3,3,0),body=preview.match(/<measure[^>]*>([\s\S]*?)<\/measure>/)?.[1]||'';
    expect(body.indexOf('<divisions>4</divisions>')).toBeLessThan(body.indexOf('<note>'));
  });
  it('fills missing inherited fields when the first kept measure has partial attributes',()=>{
    const xml='<score-partwise><part-list><score-part id="P1"><part-name>降B調小號</part-name></score-part></part-list><part id="P1"><measure number="1"><attributes><divisions>12</divisions><time><beats>4</beats><beat-type>4</beat-type></time><measure-style><multiple-rest>2</multiple-rest></measure-style></attributes><note><rest/><duration>48</duration><time-modification><actual-notes>3</actual-notes><normal-notes>2</normal-notes></time-modification></note></measure><measure number="2"><attributes><clef><sign>G</sign><line>2</line></clef></attributes><note><pitch><step>C</step><octave>4</octave></pitch><duration>6</duration></note></measure></part></score-partwise>';
    const preview=restrictedPreviewXml(xml,'P1:1:1',2,2,0),body=preview.match(/<measure[^>]*>([\s\S]*?)<\/measure>/)?.[1]||'';
    expect(body.indexOf('<divisions>12</divisions>')).toBeLessThan(body.indexOf('<note>'));
    expect(body).toContain('<time><beats>4</beats><beat-type>4</beat-type></time>');
    expect(preview).toContain('<part-name>B-flat Trumpet</part-name>');
    expect(translateInstrumentName('降B調小號')).toBe('B-flat Trumpet');
    expect(translateInstrumentName('グランドピアノ')).toBe('Grand Piano');
    expect((preview.match(/<measure(?=[\s>])/g)||[])).toHaveLength(1);
    expect(body).not.toContain('<time-modification>');
  });
});

describe('YouTube title cache', () => {
  it('shares a representative video across arrangement editions by normalized song title', () => {
    expect(normalizeYoutubeTitle('3. A Whole New World, Violin, Cello and Piano Trio.musicxml.xml')).toBe('a whole new world');
    expect(normalizeYoutubeTitle('10,000 Hours.xml')).toBe('10 000 hours');
    expect(normalizeYoutubeTitle('13 Jours en France.xml')).toBe('13 jours en france');
    expect(repairMetadataText('³» ÁÖ¸¦ °¡±îÀÌ ÇÏ°Ô ÇÔÀº')).toBe('내 주를 가까이 하게 함은');
    expect(repairMetadataText('\x93\xfa\x96{\x8c\xea\x83^\x83C\x83g\x83\x8b')).toBe('日本語タイトル');
    expect(repairMetadataText('\xbc\xf2\xcc\xe5\xd6\xd0\xce\xc4\xb1\xea\xcc\xe2')).toBe('简体中文标题');
    expect(repairMetadataText('\xc1c\xc5\xe9\xa4\xa4\xa4\xe5\xbc\xd0\xc3D')).toBe('繁體中文標題');
    expect(repairMetadataText('Prélude in C♯ minor')).toBe('Prélude in C♯ minor');
    expect(repairMetadataText('Chant du départ')).toBe('Chant du départ');
    expect(repairMetadataText('Étienne Nicolas Méhul 1763-1817')).toBe('Étienne Nicolas Méhul 1763-1817');
    expect(repairMetadataText('Claude-Michel Sch鰊berg')).toBe('Claude-Michel Schönberg');
    expect(repairMetadataText('Claude-Michel Sch錯berg')).toBe('Claude-Michel Schönberg');
    expect(repairMetadataInXml('<credit-words>Composed by Claude-Michel Sch鰊berg</credit-words>')).toContain('Claude-Michel Schönberg');
    expect(intervalRetrievalBonus(12,12)).toBe(10000);
    expect(intervalRetrievalBonus(11,12)).toBeGreaterThan(800);
    expect(intervalRetrievalBonus(5,12)).toBe(0);
    expect(retrievalRowLimit('i',50000,0)).toBe(50000);
    expect(retrievalRowLimit('i',300000,-1)).toBe(100000);
    expect(retrievalRowLimit('i',300000,3)).toBe(16000);
    expect(retrievalRowLimit('i',50000,0,false)).toBe(16000);
    expect(retrievalRowLimit('i',50000,3,false)).toBe(4000);
    expect(retrievalRowLimit('i5',50000,1)).toBe(18000);
    expect(retrievalRowLimit('r',50000,0)).toBe(3000);
    expect(retrievalRowLimit('i',2750,0)).toBe(2750);
    expect(splitIntervalSeedBonus([0,5],10)).toBe(650);
    expect(splitIntervalSeedBonus([0,1],10)).toBe(0);
    expect(splitIntervalSeedBonus([5],10)).toBe(0);
    expect(resultAdmissionAllowed('melody_rhythm',false,78.5,{interval:94.6,contour:92.3,rhythm:41.8},73,14)).toBe(true);
    expect(resultAdmissionAllowed('melody_rhythm',false,78.5,{interval:94.6,contour:92.3,rhythm:47.2},73,6)).toBe(false);
    const queryNotes=[60,64,67,71,74,72,67].map(pitchMidi=>({pitchMidi,durationRatio:1}));
    const oneChanged=[60,64,67,71,74,73,67].map(pitchMidi=>({pitchMidi,durationRatio:1}));
    expect(transpositionResidualScore(queryNotes,oneChanged)).toBe(98);
    expect(score(queryNotes,oneChanged).interval).toBeGreaterThan(95);
    expect(youtubeId({ works: { 'a whole new world': { videoId: 'video-1', validationVersion: 2 } } }, 'unused-work', 'A WHOLE NEW WORLD')).toBe('video-1');
    expect(youtubeId({ works: { 'a whole new world': { videoId: 'legacy-video' } } }, 'unused-work', 'A WHOLE NEW WORLD')).toBeUndefined();
    expect(primaryStreamOrder('P1:1:1')).toEqual([0,1,1,1,'P1:1:1']);
    expect(primaryStreamOrder('P1:2:2')).toEqual([0,1,2,2,'P1:2:2']);
  });
});

describe('catalog text search', () => {
  it('finds catalog titles case-insensitively and collapses only streams from the same file', () => {
    const items = searchCatalog('whole new world');
    expect(items.length).toBeGreaterThan(0);
    expect(items[0].title.toLowerCase()).toContain('whole new world');
    expect(new Set(items.map(item => item.source)).size).toBe(items.length);
  });

  it('keeps separate score files even when their normalized titles are identical', () => {
    const items=searchCatalog('a whole new world',20).filter(result=>normalizeYoutubeTitle(result.title)==='a whole new world');
    expect(items.some(item=>item.source.startsWith('kysing/'))).toBe(true);
    expect(items.some(item=>!item.source.startsWith('kysing/'))).toBe(true);
    expect(new Set(items.map(item=>item.source)).size).toBe(items.length);
  });

  it('matches separated title words with AND semantics',()=>{
    const items=searchCatalog('I christmas',20);
    expect(items.length).toBeGreaterThan(0);
    expect(items.every(item=>catalogTitleMatches(item.title,'I christmas'))).toBe(true);
    expect(items.some(item=>item.title.toLowerCase().includes('all i want for christmas'))).toBe(true);
  });

  it('treats a one-letter term as a word rather than an arbitrary substring',()=>{
    expect(catalogTitleMatches('White Christmas','I christmas')).toBe(false);
    expect(catalogTitleMatches('CHRISTMAS IN OUR HEARTS','I christmas')).toBe(false);
    expect(catalogTitleMatches("I'LL BE HOME FOR CHRISTMAS",'I christmas')).toBe(true);
  });

});

describe('pickup measure inference', () => {
  it('recognizes an incomplete first measure without implicit=yes', () => {
    expect(firstMeasureIsPickup('<attributes><divisions>256</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes><note><duration>128</duration></note><note><rest/><duration>128</duration></note>')).toBe(true);
  });

  it('keeps a complete first measure as measure 1', () => {
    expect(firstMeasureIsPickup('<attributes><divisions>4</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes><note><duration>16</duration></note>')).toBe(false);
  });
});

describe('exact interval search', () => {
  const timed = (pitches, durations) => {
    let onset = 0;
    return pitches.map((pitchMidi, index) => { const note = { pitchMidi, durationRatio: durations[index], onset }; onset += durations[index]; return note; });
  };

  it('accepts a uniformly transposed but otherwise identical interval sequence', () => {
    expect(findAbsoluteExact(timed([60, 62, 65, 64], [1, 1, 1, 1]), timed([72, 74, 77, 76], [1, 1, 1, 1]))).toEqual({ start: 0, end: 3 });
  });

  it('ignores enharmonic spelling when MIDI intervals and rhythm are exact', () => {
    const query = timed([70, 68, 67, 71], [.5, .5, 1, 2]).map((note, index) => ({ ...note, spelling: ['A#4', 'G#4', 'G4', 'B4'][index] }));
    const candidate = timed([70, 68, 67, 71], [.5, .5, 1, 2]).map((note, index) => ({ ...note, spelling: ['Bb4', 'Ab4', 'G4', 'B4'][index] }));
    expect(findAbsoluteExact(query, candidate, true)).toEqual({ start: 0, end: 3 });
  });

  it('rejects even one changed interval', () => {
    expect(findAbsoluteExact(timed([60, 62, 65, 64], [1, 1, 1, 1]), timed([72, 74, 78, 76], [1, 1, 1, 1]))).toBeNull();
  });

  it('requires exact internal timing only in Melody + Rhythm mode', () => {
    const query = timed([60, 62, 65, 64], [1, 2, 1, 1]);
    const candidate = timed([72, 74, 77, 76], [1, 1, 1, 1]);
    expect(findAbsoluteExact(query, candidate, false)).not.toBeNull();
    expect(findAbsoluteExact(query, candidate, true)).toBeNull();
  });

  it('allows one global tempo multiplier in exact rhythm', () => {
    expect(findAbsoluteExact(timed([60, 62, 65, 64], [.5, .5, 1, 2]), timed([72, 74, 77, 76], [1, 1, 2, 4]), true)).toEqual({ start: 0, end: 3 });
  });

  it('returns every occurrence so phrase context can choose among them', () => {
    const query = timed([60, 62, 65, 64], [1, 1, 1, 1]);
    const candidate = timed([72, 74, 77, 76, 70, 72, 74, 77, 76], [1, 1, 1, 1, 1, 1, 1, 1, 1]);
    expect(findAbsoluteExactMatches(query, candidate)).toEqual([{ start: 0, end: 3 }, { start: 5, end: 8 }]);
  });
});

describe('strict Exact rhythm classification',()=>{
  const candidate=(pitches,durations,gaps=[])=>{let onset=0;return pitches.map((pitchMidi,index)=>{const note={pitchMidi,durationRatio:durations[index],onset};onset+=durations[index]+(gaps[index]||0);return note})};
  const note=(pitchMidi,durationRatio,tieGroup)=>({kind:'note',pitchMidi,durationRatio,...(tieGroup?{tieGroup}:{})});
  const rest=durationRatio=>({kind:'rest',pitchMidi:null,durationRatio});

  it('accepts the same note/rest structure under one global tempo scale',()=>{
    const query=[note(60,.5),rest(.25),note(62,.5),note(64,1),note(65,.5)];
    const corpus=candidate([72,74,76,77],[1,1,2,1],[.5,0,0,0]);
    expect(strictExactRhythmMatch(query,corpus,0)).toBe(true);
  });

  it('does not collapse a shorter note plus rest into a sustained note',()=>{
    const query=[note(60,.5),rest(.5),note(62,1),note(64,1),note(65,1)];
    const corpus=candidate([72,74,76,77],[1,1,1,1]);
    expect(strictExactRhythmMatch(query,corpus,0)).toBe(false);
  });

  it('rejects an added terminal rest when the candidate does not contain it',()=>{
    const query=[note(60,1),note(62,1),note(64,1),note(65,.5),rest(.5)];
    const corpus=candidate([72,74,76,77,79],[1,1,1,1,1]);
    expect(strictExactRhythmMatch(query,corpus,0)).toBe(false);
  });

  it('normalizes tied query notes before checking durations',()=>{
    const query=[note(60,.5,'a'),note(60,.5,'a'),note(62,1),note(64,1),note(65,1)];
    const corpus=candidate([72,74,76,77],[1,1,1,1]);
    expect(strictExactRhythmMatch(query,corpus,0)).toBe(true);
  });
});

describe('downbeat evidence', () => {
  const query = [{ onset: 0 }, { onset: 1 }, { onset: 4 }];
  const pairs = [0, 1, 2].map(index => ({ queryIndex: index, candidateIndex: index, cost: 0 }));

  it('adds a small bonus only when important query beats align with candidate downbeats', () => {
    const evidence = metricalEvidence(query, [{ beat: 1 }, { beat: 2 }, { beat: 1 }], pairs, '4/4');
    expect(evidence.matches).toBe(2);
    expect(evidence.adjustment).toBe(6);
  });

  it('penalizes a melodic alignment that displaces important beats', () => {
    const evidence = metricalEvidence(query, [{ beat: 2 }, { beat: 3 }, { beat: 2 }], pairs, '4/4');
    expect(evidence.conflicts).toBe(2);
    expect(evidence.adjustment).toBeLessThan(-14);
  });
  it('penalizes a sparse candidate that promotes weak query notes onto downbeats',()=>{
    const query=[0,.5,1.5,2.5].map((onset,index)=>({pitchMidi:60+index,onset,durationRatio:.5}));
    const candidate=[1,1,1,1].map((beat,index)=>({pitchMidi:60+index,beat,durationRatio:1}));
    const pairs=query.map((_,index)=>({queryIndex:index,candidateIndex:index,cost:0,type:'match'}));
    const evidence=metricalEvidence(query,candidate,pairs,'4/4','4/4');
    expect(evidence.overAccents).toBeGreaterThan(0);
    expect(evidence.score).toBeLessThan(100);
  });
});

describe('metrical skeleton retrieval', () => {
  const line = (pitches, durations) => { let onset = 0; return pitches.map((pitchMidi, index) => { const durationRatio = durations[index]; const note = { pitchMidi, durationRatio, onset, beat: onset % 4 + 1 }; onset += durationRatio; return note; }); };
  it('retains metrically supported pillars while dropping weak passing notes', () => {
    const notes = annotateStructural(line([67, 68, 69, 72, 71, 69], [1, .25, .75, 1, .25, .75]), '4/4');
    const skeleton = metricalSkeleton(notes, '4/4');
    expect(skeleton.length).toBeGreaterThanOrEqual(3);
    expect(skeleton.some(note => note.pitchMidi === 68 && note.weakBeat)).toBe(false);
  });

  it('compares transposed metric skeletons independently from surface ornaments', () => {
    const query = line([60, 62, 64, 67, 69], [1, 1, 1, 1, 1]);
    const candidate = line([67, 68, 69, 71, 74, 76], [1, .25, .75, 1, 1, 1]);
    expect(metricalSkeletonEvidence(query, candidate, '4/4', '4/4').similarity).toBeGreaterThan(60);
  });
});

describe('motif importance',()=>{
  it('increases when a motif repeats more often in the same stream',()=>{expect(motifImportance(.7,4,6,100)).toBeGreaterThan(motifImportance(.7,1,6,100))});
  it('increases when repeated occurrences occupy more of the work',()=>{expect(motifImportance(.7,3,8,40)).toBeGreaterThan(motifImportance(.7,3,8,400))});
});

describe('candidate diversity',()=>{
  it('does not let many occurrences from one work evict another work before refinement',()=>{const crowded=Array.from({length:400},(_,index)=>[`crowded\u0000${index}`,10]),entries=[...crowded,['trepak\u00000',9]];expect(diversifyCandidates(entries,10,3).some(([key])=>key.startsWith('trepak\u0000'))).toBe(true)});
  it('recognizes exactly one pitch substitution under one transposition',()=>{const query=[60,62,64,65,67,69,71,72].map(pitchMidi=>({pitchMidi})),candidate=[65,67,69,72,72,74,76,77].map(pitchMidi=>({pitchMidi}));expect(singlePitchSubstitutionMatch(query,candidate)).toMatchObject({transpose:5,mismatchIndex:3,matched:7});candidate[5].pitchMidi=75;expect(singlePitchSubstitutionMatch(query,candidate)).toBeNull()});
  it('uses bounded edge-anchor scans to nominate a single-substitution work',()=>{const query=[60,62,64,65,67,69,71,72].map(pitchMidi=>({pitchMidi})),entries=[['noise\u00000',20],['target\u000012',4]],positions=new Map([['noise\u00000',new Set([0])],['target\u000012',new Set([4])]]),works={noise:Array(20).fill({p:60}),target:[...Array(12).fill({p:40}),...[65,67,69,72,72,74,76,77].map(p=>({p}))]};expect(singlePitchSubstitutionCandidates(query,entries,positions,id=>works[id])).toEqual([['target\u000012',4]])});
  it('gives the first and last anchor separate substitution slots',()=>{const query=[60,62,64,65,67,69,71,72].map(pitchMidi=>({pitchMidi})),good=[65,67,69,72,72,74,76,77].map(p=>({p})),entries=[['front\u00000',9],['back\u00000',8]],positions=new Map([['front\u00000',new Set([0])],['back\u00000',new Set([4])]]),selected=singlePitchSubstitutionCandidates(query,entries,positions,()=>good,{limit:2,scanPerAnchor:2});expect(selected.map(([key])=>key)).toEqual(['front\u00000','back\u00000'])});
  it('can require strong tempo-normalized rhythm evidence for substitution retrieval',()=>{const query=[60,62,64,65,67,69,71,72].map((pitchMidi,index)=>({pitchMidi,durationRatio:index===3?2:1,onset:index<4?index:index+1})),pitches=[65,67,69,72,72,74,76,77],entries=[['wrong-rhythm\u00000',9],['matching-rhythm\u00000',8]],positions=new Map(entries.map(([key])=>[key,new Set([0,4])])),works={'wrong-rhythm':pitches.map((p,index)=>({p,d:index%2?.125:4,o:index*4})),'matching-rhythm':pitches.map((p,index)=>({p,d:index===3?4:2,o:(index<4?index:index+1)*2}))};expect(singlePitchSubstitutionCandidates(query,entries,positions,id=>works[id],{minimumRhythm:90}).map(([key])=>key)).toEqual(['matching-rhythm\u00000'])});
});

describe('representative exact occurrence',()=>{
  const interval={start:232,end:237},rhythm={start:249,end:254};
  it('prefers the rhythm-exact occurrence for Melody + Rhythm',()=>{expect(preferredExactSpan('melody_rhythm',{interval,rhythm})).toBe(rhythm)});
  it('falls back to the interval occurrence when no rhythm-exact occurrence exists',()=>{expect(preferredExactSpan('melody_rhythm',{interval,rhythm:null})).toBe(interval)});
  it('keeps the interval occurrence for Melody Only',()=>{expect(preferredExactSpan('melody',{interval,rhythm})).toBe(interval)});
  it('honors a span required by an Exact option',()=>{const required={start:12,end:17};expect(preferredExactSpan('melody_rhythm',{interval,rhythm},required)).toBe(required)});
});

describe('strict omission admission exception',()=>{
  const verified={coverage:1,singleOmission:{verifiedAllRetainedPitches:true,verifiedRetainedTiming:true}};
  it('allows a fully verified single omission only for a long low-information query',()=>{expect(strictOmissionAdmissionException(Array(11).fill({}),{lowInformation:true},verified)).toBe(true)});
  it('does not relax the floor for an 8-note boundary query',()=>{expect(strictOmissionAdmissionException(Array(8).fill({}),{lowInformation:true},verified)).toBe(false)});
  it('requires both retained pitch and timing evidence',()=>{expect(strictOmissionAdmissionException(Array(11).fill({}),{lowInformation:true},{coverage:1,singleOmission:{verifiedAllRetainedPitches:true,verifiedRetainedTiming:false}})).toBe(false)});
  it('does not create an exception for an ordinary discriminative query',()=>{expect(strictOmissionAdmissionException(Array(11).fill({}),{lowInformation:false},verified)).toBe(false)});
});

describe('repetitive-query discrimination',()=>{
  it('marks a dominant repeated pitch as low information',()=>{expect(queryDiscrimination([71,71,71,71,71,73,71,75,75,73,73,71].map(pitchMidi=>({pitchMidi,durationRatio:.5}))).lowInformation).toBe(true)});
  it('compares the positions of repeated pitches independently of transposition',()=>{const q=[60,60,62,60,64].map(pitchMidi=>({pitchMidi})),good=[67,67,69,67,71].map(pitchMidi=>({pitchMidi})),bad=[67,69,69,67,71].map(pitchMidi=>({pitchMidi}));expect(pitchEqualitySimilarity(q,good)).toBe(100);expect(pitchEqualitySimilarity(q,bad)).toBeLessThan(100)});
});

describe('meter-aware metric hierarchy', () => {
  it('uses the actual quarter-note length of simple and compound meters', () => {
    expect(parseMeter('3/4').quarterLength).toBe(3);
    expect(parseMeter('6/8').quarterLength).toBe(3);
    expect(parseMeter('12/8').quarterLength).toBe(6);
  });

  it('does not promote beat 3 in 3/4 as if it were 4/4', () => {
    expect(metricWeightAt(2, '3/4')).toBe(metricWeightAt(3, '3/4'));
    expect(metricWeightAt(3, '3/4')).toBeLessThan(metricWeightAt(3, '4/4'));
  });

  it('recognizes dotted-quarter group starts in compound meters', () => {
    expect(metricWeightAt(2.5, '6/8')).toBeGreaterThan(metricWeightAt(3, '6/8'));
    expect(metricWeightAt(2.5, '9/8')).toBeGreaterThan(metricWeightAt(2, '9/8'));
    expect(metricWeightAt(4, '12/8')).toBeGreaterThan(metricWeightAt(4.5, '12/8'));
  });

  it('supports default groupings for asymmetric 5/4 and 7/8', () => {
    expect(metricWeightAt(4, '5/4')).toBeGreaterThan(metricWeightAt(2, '5/4'));
    expect(metricWeightAt(2, '7/8')).toBeGreaterThan(metricWeightAt(1.5, '7/8'));
    expect(metricWeightAt(3, '7/8')).toBeGreaterThan(metricWeightAt(3.5, '7/8'));
  });

  it('compares each side using its own meter hierarchy', () => {
    const query = [{ onset: 0 }, { onset: 1.5 }], candidate = [{ beat: 1 }, { beat: 2.5 }], pairs = [0, 1].map(index => ({ queryIndex: index, candidateIndex: index, cost: 0 }));
    expect(metricalEvidence(query, candidate, pairs, '6/8', '6/8').matches).toBe(2);
  });
});

describe('spelling-aware contour shape', () => {
  it('treats an augmented second as a diatonic step but a minor third as a leap', () => {
    expect(intervalShape(3, { spelling: 'F4' }, { spelling: 'G#4' })).toBe('STEP_U');
    expect(intervalShape(3, { spelling: 'C4' }, { spelling: 'Eb4' })).toBe('LEAP_U');
  });
});

describe('Schenker-informed structural reduction', () => {
  const line = (pitches, durations) => {
    let onset = 0;
    return pitches.map((pitchMidi, index) => { const durationRatio = durations[index]; const note = { pitchMidi, durationRatio, onset, beat: onset % 4 + 1 }; onset += durationRatio; return note; });
  };

  it('gives passing and neighbor tones less influence than pillars', () => {
    const passing = annotateStructural(line([60, 62, 64], [2, .25, 2]), '4/4', false);
    const neighbor = annotateStructural(line([60, 62, 60], [2, .25, 2]), '4/4', false);
    expect(passing[1].structuralRole).toBe('passing');
    expect(neighbor[1].structuralRole).toBe('neighbor');
    expect(passing[1].structuralWeight).toBeLessThan(passing[0].structuralWeight);
    expect(neighbor[1].structuralWeight).toBeLessThan(neighbor[0].structuralWeight);
  });

  it('finds the same pillar line through extra ornaments and changed surface rhythm', () => {
    const query = annotateStructural(line([60, 67, 72], [2, 2, 2]), '4/4', false);
    const decorated = annotateStructural(line([72, 74, 76, 79, 84], [2, .25, .25, 3, 1]), '4/4', true);
    const result = compareStructural(query, decorated);
    expect(result.similarity).toBeGreaterThan(85);
    expect(result.bonus).toBeGreaterThan(0);
  });

  it('does not apply a large negative adjustment when pillar lines differ', () => {
    const query = annotateStructural(line([60, 67, 72], [2, 2, 2]), '4/4', false);
    const different = annotateStructural(line([72, 71, 65], [1, 3, 2]), '4/4', true);
    expect(compareStructural(query, different).bonus).toBe(0);
  });

  it('keeps a long strong-beat tone structural even when its neighbors form a stepwise line', () => {
    const decorated = annotateStructural(line([60, 62, 64], [2, 2, 1]), '4/4', false);
    expect(decorated[1].structuralRole).not.toBe('passing');
    expect(decorated[1].structuralWeight).toBeGreaterThan(.45);
  });

  it('treats a rest boundary and a long tied arrival as corresponding phrase pillars', () => {
    const query = annotateStructural(prepareQueryNotes([
      ...[64, 65, 69, 67].map((pitchMidi, index) => ({ kind: 'note', pitchMidi, durationRatio: index ? 1 : .5 })),
      { kind: 'rest', durationRatio: 1 },
      ...[64, 65, 69, 67].map((pitchMidi, index) => ({ kind: 'note', pitchMidi, durationRatio: index ? 1 : .5 })),
    ]), '4/4', false);
    const onsets = [0, .5, 1.5, 2.5, 8, 8.5, 9.5, 10.5], beats = [2.5, 3, 4, 1, 2.5, 3, 4, 1], durations = [.5, 1, 1, 5, .5, 1, 1, .5];
    const candidate = annotateStructural([66, 67, 71, 69, 66, 67, 71, 69].map((pitchMidi, index) => ({ pitchMidi, onset: onsets[index], beat: beats[index], durationRatio: durations[index], tieEndMeasure: index === 3 ? 2 : undefined })), '4/4', true);
    expect(query[3].structuralRole).toBe('pillar');
    expect(query[4].structuralRole).toBe('pillar');
    expect(candidate[3].structuralRole).toBe('pillar');
    expect(candidate[4].structuralRole).toBe('pillar');
    expect(candidate[3].isTied).toBe(true);
  });

  it('treats a tied sustain before a rest as a phrase ending, not a new opening', () => {
    const candidate = annotateStructural([
      { pitchMidi: 65, onset: 0, beat: 1, durationRatio: 2, measure: 1, tieStart: true, tieEndMeasure: 2 },
      { pitchMidi: 67, onset: 3, beat: 2, durationRatio: .5, measure: 2 },
      { pitchMidi: 69, onset: 3.5, beat: 2.5, durationRatio: 1, measure: 2 },
    ], '4/4', true);
    expect(candidate[0].phraseClosingConfidence).toBeGreaterThan(.6);
    expect(candidate[0].phraseStart).toBe(false);
    expect(candidate[1].phraseOpeningConfidence).toBeGreaterThan(.6);
    expect(candidate[1].isAttack).toBe(true);
  });

  it('prefers the same interval sequence at a matching phrase opening', () => {
    const query = annotateStructural([
      { pitchMidi: 60, onset: 0, durationRatio: .5 },
      { pitchMidi: 62, onset: .5, durationRatio: 1 },
      { pitchMidi: 65, onset: 1.5, durationRatio: 1 },
      { pitchMidi: 64, onset: 2.5, durationRatio: 1 },
    ], '4/4', false);
    const candidate = annotateStructural([
      { pitchMidi: 72, onset: 0, beat: 1, durationRatio: 1, measure: 1, tieStart: true, tieEndMeasure: 2 },
      { pitchMidi: 74, onset: 2, beat: 3, durationRatio: 1, measure: 2 },
      { pitchMidi: 77, onset: 3, beat: 4, durationRatio: 1, measure: 2 },
      { pitchMidi: 76, onset: 4, beat: 1, durationRatio: 1, measure: 3 },
      { pitchMidi: 70, onset: 5, beat: 2, durationRatio: 1, measure: 3 },
      { pitchMidi: 72, onset: 7, beat: 2.5, durationRatio: .5, measure: 4 },
      { pitchMidi: 74, onset: 7.5, beat: 3, durationRatio: 1, measure: 4 },
      { pitchMidi: 77, onset: 8.5, beat: 4, durationRatio: 1, measure: 4 },
      { pitchMidi: 76, onset: 9.5, beat: 1, durationRatio: 1, measure: 5 },
    ], '4/4', true);
    expect(phraseAlignmentEvidence(query, candidate, { start: 5, end: 8 }).score)
      .toBeGreaterThan(phraseAlignmentEvidence(query, candidate, { start: 0, end: 3 }).score);
  });
});

describe('result admission threshold', () => {
  it('rejects a low local score even when contour happens to be perfect', () => {
    expect(resultAdmissionAllowed('melody_rhythm', false, 40, { interval: 84, rhythm: 50 }, 43)).toBe(false);
  });

  it('keeps exact interval evidence and a high-confidence structural exception', () => {
    expect(resultAdmissionAllowed('melody_rhythm', true, 40, { interval: 100, rhythm: 20 }, 20)).toBe(true);
    expect(resultAdmissionAllowed('melody_rhythm', false, 52, { interval: 72, rhythm: 50 }, 90)).toBe(true);
  });
});

describe('strict sparse melody evidence', () => {
  const path = [0, 1, 2, 3, 4].map(candidateIndex => ({ type: candidateIndex ? 'insertion' : 'match', candidateIndex }));

  it('rejects skipping ordinary surface notes that cannot be explained as ornaments', () => {
    expect(sparseAlignmentAllowed(path, [{}, { structuralRole: 'surface' }, { structuralRole: 'surface' }, { structuralRole: 'passing' }, { structuralRole: 'surface' }])).toBe(false);
  });

  it('allows a sparse line when at least 80% of skipped notes are explicit or inferred auxiliaries', () => {
    expect(sparseAlignmentAllowed(path, [{}, { structuralRole: 'cue' }, { structuralRole: 'passing', isShort: true }, { structuralRole: 'neighbor', weakBeat: true }, { structuralRole: 'cue' }])).toBe(true);
  });

  it('does not skip a long or metrically important note merely because it resembles a passing tone', () => {
    expect(sparseAlignmentAllowed(path, [{}, { structuralRole: 'passing' }, { structuralRole: 'passing' }, { structuralRole: 'neighbor' }, { structuralRole: 'surface' }])).toBe(false);
  });

  it('trusts a dedicated structural stream backed by source notation', () => {
    expect(sparseAlignmentAllowed(path, [], true)).toBe(true);
  });
});

describe('production local alignment', () => {
  it('repairs a delete-shift-insert display path into one local octave displacement',()=>{
    const query=[60,64,76,67].map((pitchMidi,index)=>({pitchMidi,durationRatio:1,onset:index})),candidate=[72,76,76,79].map((pitchMidi,index)=>({pitchMidi,durationRatio:1,onset:index})),path=[{queryIndex:0,candidateIndex:0,cost:0,type:'match'},{queryIndex:1,candidateIndex:1,cost:0,type:'match'},{queryIndex:2,candidateIndex:null,cost:.4,type:'deletion'},{queryIndex:3,candidateIndex:2,cost:.2,type:'substitution'},{queryIndex:null,candidateIndex:3,cost:.4,type:'insertion'}];
    const repaired=explainOctaveEditAlignment(path,query,candidate);
    expect(repaired).toHaveLength(4);expect(repaired[2]).toMatchObject({queryIndex:2,candidateIndex:2,type:'substitution',relation:'octave-displacement'});expect(repaired.some(step=>step.type==='insertion'||step.type==='deletion')).toBe(false);
  });

  it('can preserve one genuine omission while identifying one octave displacement',()=>{
    const query=[60,64,76,67].map((pitchMidi,index)=>({pitchMidi,durationRatio:1,onset:index})),candidate=[72,74,76,76,79].map((pitchMidi,index)=>({pitchMidi,durationRatio:1,onset:index})),path=[{queryIndex:0,candidateIndex:0,cost:0,type:'match'},{queryIndex:1,candidateIndex:1,cost:.3,type:'substitution'},{queryIndex:2,candidateIndex:2,cost:.3,type:'substitution'},{queryIndex:3,candidateIndex:3,cost:.3,type:'substitution'},{queryIndex:null,candidateIndex:4,cost:.4,type:'insertion'}];
    const repaired=explainOctaveEditAlignment(path,query,candidate);
    expect(repaired.filter(step=>step.type==='insertion')).toHaveLength(1);expect(repaired.find(step=>step.relation==='octave-displacement')).toMatchObject({queryIndex:2,candidateIndex:3});expect(repaired.filter(step=>step.type==='substitution'&&!step.relation)).toHaveLength(0);
  });

  it('does not invent an octave explanation when an ordinary substitution remains',()=>{
    const query=[60,64,76,67].map((pitchMidi,index)=>({pitchMidi,durationRatio:1,onset:index})),candidate=[72,77,64,79].map((pitchMidi,index)=>({pitchMidi,durationRatio:1,onset:index})),path=query.map((_,index)=>({queryIndex:index,candidateIndex:index,cost:index?.3:0,type:index?'substitution':'match'}));
    expect(explainOctaveEditAlignment(path,query,candidate)).toEqual(path);
  });

  it('labels a repeated attack split without erasing the deletion or making it exact',()=>{
    const query=[{pitchMidi:60,durationRatio:.5,onset:0},{pitchMidi:60,durationRatio:.5,onset:.5},{pitchMidi:62,durationRatio:1,onset:1}],candidate=[{pitchMidi:72,durationRatio:1,onset:0},{pitchMidi:74,durationRatio:1,onset:1}],path=[{queryIndex:0,candidateIndex:0,cost:0,type:'match'},{queryIndex:1,candidateIndex:null,cost:.4,type:'deletion'},{queryIndex:2,candidateIndex:1,cost:0,type:'match'}];
    const annotated=annotateRepeatAttackRelations(path,query,candidate);
    expect(annotated[1]).toMatchObject({type:'deletion',relation:'repeat-split'});
  });

  it('labels the reverse repeated-attack merge and rejects loose duration resemblance',()=>{
    const query=[{pitchMidi:60,durationRatio:1,onset:0},{pitchMidi:62,durationRatio:1,onset:1}],candidate=[{pitchMidi:72,durationRatio:.5,onset:0},{pitchMidi:72,durationRatio:.5,onset:.5},{pitchMidi:74,durationRatio:1,onset:1}],path=[{queryIndex:0,candidateIndex:0,cost:0,type:'match'},{queryIndex:null,candidateIndex:1,cost:.4,type:'insertion'},{queryIndex:1,candidateIndex:2,cost:0,type:'match'}];
    expect(annotateRepeatAttackRelations(path,query,candidate)[1]).toMatchObject({type:'insertion',relation:'repeat-merge'});
    candidate[1]={...candidate[1],durationRatio:.25,onset:.5};
    expect(annotateRepeatAttackRelations(path,query,candidate)[1].relation).toBeUndefined();
  });

  it('keeps held arrivals on the actual long attacks through a neighboring ornament', () => {
    const line=(pitches,durations)=>{let onset=0;return pitches.map((pitchMidi,index)=>{const note={pitchMidi,durationRatio:durations[index],onset};onset+=durations[index];return note})};
    const query=line([65,66,66,73,74,78,76,74,73],[3,1,3,1,2,.5,.5,.5,2]);
    const original=line([65,66,66,73,74,78,76,74,73],[3,1,3,1,2,.5,.5,.5,2]);
    const scaled=line([65,66,66,73,74,78,76,74,73],[6,2,6,2,4,1,1,1,4]);
    const ornament=line([65,66,65,66,73,74,78,76,74,73],[3,.5,.5,3,1,2,.5,.5,.5,2]);
    const shortRepeat=line([65,66,65,66,73,74,78,76,74,73],[.5,.5,.5,3,1,2,.5,.5,.5,2]);
    expect(alignLocal(query,original,'melody_rhythm').similarity).toBe(100);
    expect(alignLocal(query,scaled,'melody_rhythm').similarity).toBe(100);
    const absorbed=alignLocal(query,ornament,'melody_rhythm');
    expect(absorbed.start).toBe(0);
    expect(absorbed.path.find(step=>step.queryIndex===2)?.candidateIndex).toBe(3);
    expect(absorbed.path.some(step=>step.candidateIndex===2&&step.type==='insertion')).toBe(true);
    expect(absorbed.similarity).toBeGreaterThan(70);
    expect(alignLocal(query,shortRepeat,'melody_rhythm').similarity).toBeLessThan(absorbed.similarity-15);
  });

  it('does not trade away phrase coverage merely to lower raw retry cost',()=>{
    const line=(pitches,durations)=>{let onset=0;return pitches.map((pitchMidi,index)=>{const note={pitchMidi,durationRatio:durations[index],onset};onset+=durations[index];return note})};
    const query=line([76,75,75,76,76,74,73,80,73,77,80,81,78,80,81,83,83],[3,.5,.5,3,.5,.5,3,.25,.25,.25,.25,4,3,.5,.5,1,1]);
    const candidate=line([76,83,85,83,78,76,75,76,76,74,73,80,73,77,80,81,78,80,81,83,83],[3,1,3,1,4,3,1,3,.5,.5,3,.25,.25,.25,.25,4,3,.5,.5,1,1]);
    const result=alignLocal(query,candidate,'melody_rhythm');
    expect(result.coverage).toBeGreaterThan(.9);expect(result.path.filter(step=>step.queryIndex!==null&&step.candidateIndex!==null)).toHaveLength(16);expect(result.start).toBe(4);
  });

  it('finds a transposed motif inside a wider candidate window', () => {
    const result = alignLocal(notes([60, 62, 64, 67]), notes([50, 55, 72, 74, 76, 79, 48]), 'melody');
    expect(result.start).toBe(2);
    expect(result.end).toBe(5);
    expect(result.coverage).toBe(1);
    expect(result.similarity).toBe(100);
  });

  it('keeps a match when the candidate contains an ornament note', () => {
    const c = notes([72, 74, 74, 76, 79, 81]);
    c[2].structuralRole = 'passing'; c[2].structuralWeight = .25;
    const result = alignLocal(notes([60, 62, 64, 67, 69]), c, 'melody');
    expect(result.coverage).toBe(1);
    expect(result.path.some(step => step.type === 'insertion')).toBe(true);
    expect(result.similarity).toBeGreaterThan(60);
  });

  it('records a missing query note instead of shifting the whole motif', () => {
    const result = alignLocal(notes([60, 62, 64, 65, 67]), notes([72, 74, 77, 79]), 'melody');
    expect(result.path.some(step => step.type === 'deletion')).toBe(true);
    expect(result.coverage).toBeGreaterThanOrEqual(.75);
  });

  it('returns alignment indexes that point into each production excerpt', () => {
    const events = notes([60, 62, 64, 67]);
    const result = searchDatabase({ version: 1, mode: 'melody', meter: '4/4', startsOnDownbeat: true, events }, 3);
    const matches = [...result.exact, ...result.similar];
    expect(matches.length).toBeGreaterThan(0);
    for (const match of matches) for (const step of match.alignment) {
      if (step.candidateIndex !== null) {
        expect(step.candidateIndex).toBeGreaterThanOrEqual(0);
        expect(step.candidateIndex).toBeLessThan(match.work.notes.length);
      }
    }
  }, 15_000);

  it('limits a refinement search to the supplied current-result work IDs', () => {
    const events = notes([60, 62, 64, 67]);
    const initial = searchDatabase({ version: 1, mode: 'melody', meter: '4/4', startsOnDownbeat: true, events }, 5);
    const first = [...initial.exact, ...initial.similar][0];
    expect(first).toBeTruthy();
    const refined = searchDatabase({ version: 1, mode: 'melody', meter: '4/4', startsOnDownbeat: true, events, scopeWorkIds: [first.work.workId] }, 20);
    expect([...refined.exact, ...refined.similar].every(result => result.work.workId === first.work.workId)).toBe(true);
  }, 15_000);

  it('evaluates an explicitly scoped work even when retrieval grams do not nominate it', () => {
    const initial = searchDatabase({ version: 1, mode: 'melody', meter: '4/4', startsOnDownbeat: true, events: notes([60, 62, 64, 67]) }, 1);
    const workId = [...initial.exact, ...initial.similar][0]?.work.workId;
    expect(workId).toBeTruthy();
    const trace = [];
    searchDatabase({
      version: 1, mode: 'melody', meter: '4/4', startsOnDownbeat: true,
      events: notes([1, 13, 2, 14, 3, 15, 4, 16]), scopeWorkIds: [workId],
    }, 20, { onProgress: event => trace.push(event) });
    const inventory = trace.find(event => event.stage === 'retrieval-inventory');
    expect(inventory?.candidateWorks).toContain(workId);
  }, 15_000);
});

describe('constrained rhythm DTW', () => {
  const rhythm = durations => durations.map((durationRatio, i) => ({ id: String(i), kind: 'note', pitchMidi: 60 + i, durationRatio }));

  it('is invariant under global tempo augmentation', () => {
    expect(alignRhythmDtw(rhythm([1, .5, .5, 1]), rhythm([2, 1, 1, 2])).similarity).toBe(100);
  });

  it('allows one duration to be divided into two notes', () => {
    expect(alignRhythmDtw(rhythm([1, 1, 2, 1]), rhythm([1, 1, 1, 1, 1])).similarity).toBeGreaterThan(75);
  });

  it('penalizes a substantially different rhythm', () => {
    const matching = alignRhythmDtw(rhythm([1, .5, .5, 2]), rhythm([2, 1, 1, 4])).similarity;
    const different = alignRhythmDtw(rhythm([1, .5, .5, 2]), rhythm([.25, 2, .25, 1])).similarity;
    expect(matching).toBeGreaterThan(different);
  });

  it('keeps small timing variations inside a gentle tolerance zone', () => {
    expect(alignRhythmDtw(rhythm([1, 1, 1, 1]), rhythm([1, 1.06, .94, 1])).similarity).toBeGreaterThan(97);
  });

  it('includes an internal rest in the next inter-onset interval', () => {
    const query = prepareQueryNotes([
      { id: 'a', kind: 'note', pitchMidi: 60, durationRatio: 1 },
      { id: 'r', kind: 'rest', pitchMidi: null, durationRatio: 1 },
      { id: 'b', kind: 'note', pitchMidi: 62, durationRatio: 1 },
      { id: 'c', kind: 'note', pitchMidi: 64, durationRatio: 1 },
    ]);
    expect(query.map(x => x.onset)).toEqual([0, 2, 3]);
    expect(alignRhythmDtw(query, [{ durationRatio: 1, onset: 0 }, { durationRatio: 1, onset: 2 }, { durationRatio: 1, onset: 3 }]).similarity).toBe(100);
    expect(alignRhythmDtw(query, [{ durationRatio: 1, onset: 0 }, { durationRatio: 1, onset: 1 }, { durationRatio: 1, onset: 2 }]).similarity).toBeLessThan(90);
  });

  it('strongly demotes low rhythm scores while leaving high scores alone', () => {
    expect(rhythmRankFactor(90)).toBe(1);
    expect(rhythmRankFactor(44)).toBeLessThan(.68);
  });

  it('recognizes short-normal phrase shape despite a long tied pillar', () => {
    const timed = durations => { let onset = 0; return durations.map(durationRatio => { const note = { durationRatio, onset }; onset += durationRatio; return note; }); };
    const query = prepareQueryNotes([.5, 1, 1, 1].map((durationRatio, index) => ({ kind: 'note', pitchMidi: 60 + index, durationRatio })).concat([{ kind: 'rest', durationRatio: 1 }], [.5, 1, 1, 1].map((durationRatio, index) => ({ kind: 'note', pitchMidi: 64 + index, durationRatio }))));
    const wholeNewWorld = timed([.5, 1, 1, 5, .5, 1, 1, .5]);
    const powerOfLove = timed([1, 2, 1, 2, 1, 2, 1, 2]);
    expect(rhythmShapeSimilarity(query, wholeNewWorld)).toBeGreaterThan(rhythmShapeSimilarity(query, powerOfLove));
  });
});

describe('MusicXML measure labels', () => {
  it('preserves pickup measure zero instead of falling back to ordinal one', () => {
    expect(displayMeasure('0')).toBe(0);
  });
});
