import {it,expect} from 'vitest';
import {discoverMotifs,linkMotifSpanFamilies,transformTokens} from './motif-discovery.mjs';

// 4/4, C major: a 5-note idea starting on beat 2 (anacrusis-like), stated at three pitch levels
const LETTERS='CDEFGAB';
const name=(dia)=>`${LETTERS[((dia%7)+7)%7]}${Math.floor(dia/7)}`;
const MAJOR=[0,2,4,5,7,9,11];
const midi=(dia)=>12*(Math.floor(dia/7)+1)+MAJOR[((dia%7)+7)%7];
function piece(statements){
 const notes=[];let t=0;
 for(const [base,shape] of statements){
  t=Math.ceil(t/4)*4+1;  // each statement starts on beat 2 of a new bar
  for(const [step,d] of shape){const dia=base+step;notes.push({pitchMidi:midi(dia),spelling:name(dia),onset:t,durationRatio:d});t+=d;}
  t+=1;  // a rest closes the statement
 }
 return notes.map(n=>({...n,measureOrdinal:Math.floor(n.onset/4)+1,mstart:Math.floor(n.onset/4)*4,meterCount:4,meterUnit:4}));
}
const IDEA=[[0,.5],[1,.5],[2,1],[4,.5],[3,.5]];   // C D E G F (diatonic steps)
const OTHER=[[0,1],[-2,1],[0,1],[-1,.5],[-3,.5]];

it('finds a motif from any onset under tonal transposition and keeps occurrences apart',()=>{
 const notes=piece([[28,IDEA],[29,IDEA],[25,OTHER],[31,IDEA],[26,OTHER]]);
 const r=discoverMotifs(notes,{minGain:4,breathStarts:new Set()});
 const fam=r.families.find(f=>f.occurrences.length===3);
 expect(fam).toBeTruthy();
 expect(fam.occurrences.map(o=>notes[o.startIndex].onset%4)).toEqual([1,1,1]);  // starts on beat 2, not the barline
 const ranges=r.families.flatMap(f=>f.occurrences.map(o=>[o.startIndex,o.endIndex])).sort((a,b)=>a[0]-b[0]);
 for(let k=1;k<ranges.length;k++)expect(ranges[k][0]).toBeGreaterThan(ranges[k-1][1]);  // non-overlapping cover
});

it('adds retrograde statements to the family and labels them',()=>{
 // retrograde = onsets mirrored in time (the inter-onset intervals reversed) and pitches reversed
 const steps=IDEA.map(([s])=>s).reverse(),iois=IDEA.slice(0,-1).map(([,d])=>d).reverse();
 const retroShape=steps.map((s,k)=>[s,k<iois.length?iois[k]:.5]);
 const notes=piece([[28,IDEA],[29,IDEA],[25,retroShape],[26,OTHER]]);
 const r=discoverMotifs(notes,{minGain:4,breathStarts:new Set()});
 const fam=r.families.find(f=>f.notes===IDEA.length);
 expect(fam.occurrences.map(o=>o.variant)).toEqual([null,null,'retrograde']);
});

it('transforms token strings (inversion, retrograde)',()=>{
 const proto=[[.5,1],[1,2]];
 expect(transformTokens(proto,'inversion')).toEqual([[.5,-1],[1,-2]]);
 expect(transformTokens(proto,'retrograde')).toEqual([[1,-2],[.5,-1]]);
});

it('unions page families with discovery links without changing spans',()=>{
 const notes=piece([[28,IDEA],[29,IDEA],[25,OTHER]]);
 const spans=[{startIndex:0,endIndex:4,familyNumber:1},{startIndex:5,endIndex:9,familyNumber:2},{startIndex:10,endIndex:14,familyNumber:3}];
 const disc={families:[{id:'M1',occurrences:[{start:notes[0].onset,end:notes[4].onset+notes[4].durationRatio},{start:notes[5].onset,end:notes[9].onset+notes[9].durationRatio}]}]};
 const out=linkMotifSpanFamilies(notes,spans,disc);
 expect(out.map(s=>s.linkedFamily)).toEqual([1,1,2]);
 expect(out.map(s=>[s.startIndex,s.endIndex])).toEqual(spans.map(s=>[s.startIndex,s.endIndex]));
 expect(out[0].linkSources).toEqual(['page','discovery']);
});

it('declines without spelling information instead of guessing',()=>{
 const notes=piece([[28,IDEA],[29,IDEA]]).map(({spelling,...n})=>n);
 expect(discoverMotifs(notes).skipped).toBe('spelling/tpc missing');
});
