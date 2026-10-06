import {describe,it,expect} from 'vitest';
import type {Query,MatchResult,CorpusNote} from '../types';
import {suggestQueries} from './querySuggestions';
const pitches=[60,62,64,65,67,69,71,72];
function fixture(change:'pitch'|'octave'|'insert'='pitch',transpose=0,tempo=1){
 const events=pitches.map((p,i)=>({id:'q'+i,kind:'note' as const,pitchMidi:p,spelling:'N'+p,durationRatio:1}));
 if(change==='insert')events.splice(3,1);else events[3]={...events[3],pitchMidi:change==='octave'?77:66};
 const query:Query={version:1,mode:'melody_rhythm',meter:'4/4',startsOnDownbeat:true,events};
 const notes=pitches.map((p,i)=>({id:'n'+i,kind:'note',pitchMidi:p+transpose,durationRatio:tempo,onset:10+i*tempo,
  measure:3,beat:1,metricStrength:.5,structuralSalience:.5,structuralConfidence:.5,chordRole:'unknown'})) as CorpusNote[];
 const alignment=pitches.map((_,i)=>({queryIndex:change==='insert'?(i===3?null:i>3?i-1:i):i,candidateIndex:i,cost:0,type:'match' as const}));
 const result={kind:'similar',ranking:85,scores:{interval:90},work:{workId:'w',sourceId:'source',title:'fixture',streamId:'P1:1:1',notes},alignment,startMeasure:3,endMeasure:4} as MatchResult;
 return {query,result};
}
describe('conservative query completion',()=>{
 it('repairs one semitone and preserves input',()=>{
  const {query,result}=fixture();const before=JSON.stringify(query);const [s]=suggestQueries(query,[result]);
  expect(s.kind).toBe('pitch');expect(s.query.events[3].pitchMidi).toBe(65);expect(s.evidence[0].notes.length).toBe(8);expect(JSON.stringify(query)).toBe(before);
 });
 it('maps transposition and tempo back to query register',()=>{
  const {query,result}=fixture('octave',5,2);const [s]=suggestQueries(query,[result]);expect(s.kind).toBe('octave');expect(s.query.events[3].pitchMidi).toBe(65);expect(s.evidence[0].tempoRatio).toBe(2);
 });
 it('inserts one internal note and duration',()=>{
  const {query,result}=fixture('insert',-3,.5);const [s]=suggestQueries(query,[result]);expect(s.kind).toBe('insert');expect(s.query.events.length).toBe(8);expect(s.query.events[3].durationRatio).toBe(1);expect(s.query.events[3].pitchMidi).toBe(65);
 });
 it('rejects mismatched rest timing and preserves supported rests',()=>{
  const {query,result}=fixture();query.events.splice(2,0,{id:'rest',kind:'rest',pitchMidi:null,durationRatio:.5});
  expect(suggestQueries(query,[result])).toHaveLength(0);result.work.notes.slice(2).forEach(n=>n.onset!+=.5);
  expect(suggestQueries(query,[result])[0].query.events[2].kind).toBe('rest');
 });
 it('does not insert across explicit rest',()=>{
  const {query,result}=fixture('insert');query.events.splice(3,0,{id:'rest',kind:'rest',pitchMidi:null,durationRatio:.5});expect(suggestQueries(query,[result])).toHaveLength(0);
 });
 it.each(['exactPitchOnly','exactIntervalOnly','exactRhythmOnly','absoluteExactOnly'] as const)('respects %s',flag=>{
  const {query,result}=fixture();query[flag]=true;expect(suggestQueries(query,[result])).toHaveLength(0);
 });
 it('rejects two pitch errors, rhythm changes and short queries',()=>{
  const {query,result}=fixture();query.events[5].pitchMidi=68;expect(suggestQueries(query,[result])).toHaveLength(0);
  query.events[5].pitchMidi=69;query.events[2].durationRatio=.5;expect(suggestQueries(query,[result])).toHaveLength(0);
  query.events=query.events.slice(0,4);expect(suggestQueries(query,[result])).toHaveLength(0);
 });
 it('rejects incomplete alignment and tied input',()=>{
  const {query,result}=fixture();result.alignment[7].queryIndex=null;expect(suggestQueries(query,[result])).toHaveLength(0);
  result.alignment[7].queryIndex=7;query.events[2].tieGroup='t';expect(suggestQueries(query,[result])).toHaveLength(0);
 });
 it('deduplicates proposals and source evidence',()=>{
  const {query,result}=fixture();const duplicate={...result,work:{...result.work,workId:'other'}};
  expect(suggestQueries(query,[result,duplicate])).toHaveLength(1);expect(suggestQueries(query,[result,duplicate])[0].evidence).toHaveLength(1);
 });
 it('rejects rhythm, contour, weak and exact matches',()=>{
  const {query,result}=fixture();expect(suggestQueries({...query,mode:'contour'},[result])).toHaveLength(0);
  expect(suggestQueries({...query,mode:'rhythm'},[result])).toHaveLength(0);
  expect(suggestQueries(query,[{...result,ranking:60}])).toHaveLength(0);
  expect(suggestQueries(query,[{...result,kind:'exact'}])).toHaveLength(0);
 });
});
