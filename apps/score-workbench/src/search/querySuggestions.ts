import type { MatchResult, Query, QueryEvent } from '../types';
import { pitchName } from '../music/pitch';

export const SUGGESTION_VERSION = 'query-completion-v1';
export interface QuerySuggestion {
  id: string; kind: 'insert' | 'pitch' | 'octave'; query: Query;
  changedIds: string[]; reason: string; beforeFit: number; afterFit: number;
  evidence: { workId: string; sourceId: string; title: string; streamId: string;
    startMeasure: number; endMeasure: number; transposition: number; tempoRatio: number;
    notes: MatchResult['work']['notes']; alignment: MatchResult['alignment'] }[];
}
const near = (a: number, b: number) => Math.abs(a-b) < 1e-4;
const median = (xs: number[]) => [...xs].sort((a,b)=>a-b)[Math.floor(xs.length/2)];
export const queryFingerprint = (q: Query) => JSON.stringify(q);

/** Conservative proposals from returned alignments; no extra retrieval or ranking changes. */
export function suggestQueries(query: Query, results: MatchResult[]): QuerySuggestion[] {
  if (!['melody','melody_rhythm'].includes(query.mode) || query.absoluteExactOnly ||
      query.exactIntervalOnly || query.exactPitchOnly || query.exactRhythmOnly ||
      query.events.some(e=>e.tieGroup || e.tupletGroup || e.cue)) return [];
  const ns = query.events.filter(e=>e.kind==='note' && e.pitchMidi!==null);
  if (ns.length<6 || ns.length>32 || new Set(ns.map(n=>n.pitchMidi)).size<4) return [];
  const proposals = new Map<string, QuerySuggestion>();
  for (const result of results.slice(0,20)) {
    if (result.kind==='exact' || result.ranking<75 || result.scores.interval<80) continue;
    const pairs=result.alignment.filter(p=>p.queryIndex!==null && p.candidateIndex!==null);
    if (pairs.length!==ns.length || pairs.some((p,i)=>p.queryIndex!==i) ||
        new Set(pairs.map(p=>p.candidateIndex)).size!==ns.length) continue;
    const ci=pairs.map(p=>p.candidateIndex!);
    if(ci.some((v,i)=>i>0&&v<=ci[i-1]))continue;
    const cn=ci.map(i=>result.work.notes[i]);
    if(cn.some(n=>!n || n.kind!=='note' || n.pitchMidi===null || !Number.isFinite(n.onset)))continue;
    const offsets=cn.map((n,i)=>n.pitchMidi!-ns[i].pitchMidi!);
    const shift=median(offsets), wrong=offsets.flatMap((s,i)=>s!==shift?[i]:[]);
    const holes=ci.slice(1).flatMap((v,i)=>Array.from({length:Math.max(0,v-ci[i]-1)},(_,k)=>ci[i]+1+k));
    if(wrong.length+holes.length!==1)continue;
    const ratio=median(cn.map((n,i)=>n.durationRatio/ns[i].durationRatio));
    if(!Number.isFinite(ratio)||ratio<.25||ratio>4||
       cn.some((n,i)=>!near(n.durationRatio/ratio,ns[i].durationRatio)))continue;
    let events:QueryEvent[]=query.events.map(e=>({...e,onset:undefined})),kind:QuerySuggestion['kind'],changedId:string,reason:string;
    if(holes.length){
      const index=holes[0], note=result.work.notes[index], after=ci.findIndex(v=>v>index);
      if(!note||note.kind!=='note'||note.pitchMidi===null||after<=0||after>=ns.length)continue;
      const previous=events.findIndex(e=>e.id===ns[after-1].id),next=events.findIndex(e=>e.id===ns[after].id);
      // No insertion across an existing rest; preserve the user's phrase boundary.
      if(next!==previous+1)continue;
      const duration=note.durationRatio/ratio, pitch=note.pitchMidi-shift;
      if(![.0625,.125,.25,.5,.75,1,1.5,2].some(v=>near(v,duration))||pitch<24||pitch>108)continue;
      changedId='suggest-insert-'+index+'-'+ns[after].id;
      const inserted:QueryEvent={id:changedId,kind:'note',pitchMidi:pitch,durationRatio:duration,spelling:pitchName(pitch,/b|♭/.test(ns[after].spelling||''))};
      events.splice(next,0,inserted);kind='insert';
      reason=after+'번째 음 뒤에 '+inserted.spelling+' ('+duration+'박) 추가';
    }else{
      const index=wrong[0],pitch=cn[index].pitchMidi!-shift,delta=pitch-ns[index].pitchMidi!;
      if(pitch<24||pitch>108||!(Math.abs(delta)<=2||Math.abs(delta)===12))continue;
      changedId=ns[index].id;kind=Math.abs(delta)===12?'octave':'pitch';
      const spelling=pitchName(pitch,/b|♭/.test(ns[index].spelling||''));
      events=events.map(e=>e.id===changedId?{...e,pitchMidi:pitch,spelling}:e);
      reason=(index+1)+'번째 음 '+ns[index].spelling+' → '+spelling;
    }
    // Validate the complete proposed timing, including rests, against contiguous source notes.
    let at=0;
    const proposed=events.flatMap(e=>{const t=at;if(e.kind==='note'||query.includeRests!==false)at+=e.durationRatio;return e.kind==='note'?[{e,t}]:[]});
    const target=result.work.notes.slice(ci[0],ci.at(-1)!+1);
    if(target.length!==proposed.length||target.some((n,i)=>n.kind!=='note'||n.pitchMidi!==proposed[i].e.pitchMidi!+shift||
       !near(n.durationRatio/ratio,proposed[i].e.durationRatio)||
       !near((n.onset!-target[0].onset!)/ratio,proposed[i].t-proposed[0].t)))continue;
    const signature=JSON.stringify(events.map(e=>[e.kind,e.pitchMidi,e.durationRatio]));
    const evidence={workId:result.work.workId,sourceId:result.work.sourceId,title:result.work.title,streamId:result.work.streamId,
      startMeasure:result.startMeasure,endMeasure:result.endMeasure,transposition:shift,tempoRatio:ratio,
      notes:target.map(n=>({...n})),alignment:result.alignment.map(p=>({...p}))};
    const existing=proposals.get(signature);
    if(existing){if(!existing.evidence.some(e=>e.sourceId===evidence.sourceId))existing.evidence.push(evidence);continue;}
    proposals.set(signature,{id:SUGGESTION_VERSION+'-'+proposals.size,kind,query:{...query,events},changedIds:[changedId],reason,
      beforeFit:(ns.length-(kind==='insert'?0:1))/(ns.length+(kind==='insert'?1:0)),afterFit:1,evidence:[evidence]});
  }
  return [...proposals.values()].sort((a,b)=>b.evidence.length-a.evidence.length||b.beforeFit-a.beforeFit).slice(0,3);
}
