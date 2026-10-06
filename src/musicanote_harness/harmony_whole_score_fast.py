"""Score-equivalent v0.2 performance adapter; sealed providers remain intact.

Sweep original events, cache span facts, and project only the old features
which survive the beat conversion. No musical coefficient or beam change.
The selected path is checked by the original direct v0.2 scorer.
"""
import argparse
from bisect import bisect_right
from collections import Counter
from dataclasses import replace
from fractions import Fraction as F
from functools import lru_cache
from pathlib import Path

from . import harmony_whole_score_units as original
from .harmony_evidence_scoring import metric, meter_at, key_alters, pitch_token
from .harmony_temporal_scoring import beat_extent
from .harmony_member_timing import TimingContext, timing_feature
from .harmony_root_context_scoring import SUPPORTED_DELAY_FACTOR
from .harmony_functional_scoring import pair_features, dominant_pairs, shapes, six_four_surface
from .harmony_scored_decoder import feature_cost
from .harmony_reading_voice_context import spelled_height
from .harmony_window_workspace import bind, WindowWorkspace

VERSION='local-beat-whole-score-supported-domain-0.2.1-performance'


def sweep(events, points, start, end):
    """Exact half-open cell membership, retaining original event ordering."""
    starts={};ends={};pointset=set(points)
    for i,event in enumerate(events):
        a,b=start(event),end(event)
        if a>=b:raise ValueError('nonpositive_sweep_event')
        if a not in pointset or b not in pointset:raise ValueError('sweep_missing_source_boundary')
        starts.setdefault(a,[]).append(i);ends.setdefault(b,[]).append(i)
    active={};cells=[]
    for a in points[:-1]:
        for i in ends.get(a,()):active.pop(i,None)
        for i in starts.get(a,()):active[i]=events[i]
        cells.append(tuple(active[i] for i in sorted(active)))
    return tuple(cells)


class FastBeatIndex(original.BeatIndex):
    def __init__(self,ev,points):
        self.source,self.points=ev.source,points
        self.position={t:i for i,t in enumerate(points)}
        self.active=sweep(ev.source.events,points,
                          lambda e:e.start,lambda e:e.end)
        self.beats=[F()];self.unknown=[F()]
        self.metric_bad,self.durable_bad,self.bass_bad,self.key_bad=[F()],[F()],[F()],[F()]
        self.exposure,self.metric_exposure,self.durable,self.lowest,self.foreign={},{},{},{},{}
        tokens={e.pitch for e in ev.source.events if e.pitch is not None}
        for table in (self.exposure,self.metric_exposure,self.durable,self.lowest,self.foreign):
            table.update({t:[F()] for t in tokens})
        strengths={e.event_id:metric(ev.source,e.start) for e in ev.source.events}
        self.key_cells=[]
        for (a,b),active in zip(zip(points,points[1:]),self.active):
            dt=beat_extent(ev.source,a,b)
            if dt is None:raise ValueError('meter_unavailable_no_quarter_fallback')
            n=len(active);exposure=Counter();met=Counter();dur=Counter();bass=Counter()
            mb=db=bb=False;known=[]
            for e in active:
                strength,unit=strengths[e.event_id];mb|=strength is None;db|=unit is None
                if e.pitch is None:continue
                exposure[e.pitch]+=dt/n
                if strength is not None:met[e.pitch]+=dt*strength/n
                if unit is not None and e.end-e.start>=unit:dur[e.pitch]+=dt/n
                row=ev.source.rows.get(e.event_id)
                if row is None or row.get('pitch') is None:bb=True
                else:known.append((row['pitch'],e.pitch))
            if active and not bb and len(known)==n:
                height=min(p for p,t in known);lowest=[t for p,t in known if p==height]
                for t in lowest:bass[t]+=dt/len(lowest)
            elif active:bb=True
            grid=meter_at(ev.source,a);alters=key_alters(grid[2]) if grid else None
            self.key_cells.append((dt,alters))
            for table,values in ((self.exposure,exposure),(self.metric_exposure,met),
                                 (self.durable,dur),(self.lowest,bass)):
                for t,prefix in table.items():prefix.append(prefix[-1]+values[t])
            for t,prefix in self.foreign.items():
                prefix.append(prefix[-1]+(dt*int(alters[t[0]]!=t[1]) if alters is not None else F()))
            self.beats.append(self.beats[-1]+dt)
            self.unknown.append(self.unknown[-1]+(dt*sum(e.pitch is None for e in active)/n if n else F()))
            for prefix,bad in ((self.metric_bad,mb),(self.durable_bad,db),(self.bass_bad,bb),
                               (self.key_bad,alters is None)):
                prefix.append(prefix[-1]+(dt if bad else F()))
        self.total_beats=self.beats[-1]
        if not self.total_beats:raise ValueError('nonpositive_beats')
        self.totals={id(table):[sum((p[i] for p in table.values()),F()) for i in range(len(points))]
            for table in (self.exposure,self.metric_exposure,self.durable,self.lowest)}
        self.span_facts=lru_cache(8192)(self._span_facts)

    def _span_facts(self,a,b):
        known=frozenset(t for t,p in self.exposure.items() if self.delta(p,a,b)>0)
        return self.delta(self.beats,a,b),known,self.delta(self.unknown,a,b)

    def first(self,token,a,b):
        p=self.exposure.get(token);i,j=self.position[a],self.position[b]
        return self.points[bisect_right(p,p[i],i+1,j+1)-1] if p is not None and p[j]>p[i] else None

    def nonmembers(self,table,a,b,members):
        return self.delta(self.totals[id(table)],a,b)-sum(
            (self.delta(table[t],a,b) for t in members if t in table),F())

    def convert(self,old,a,b,sig):
        result={k:None if v is None else v*(1 if k in original.COUNT_FEATURES else self.total_beats)
                for k,v in old.items()}
        members=set(sig[1]);root=sig[0];span,known,unresolved=self.span_facts(a,b)
        present=bool(known) and not unresolved
        result.update(nonmember_exposure=self.nonmembers(self.exposure,a,b,members),
            unresolved_spelling_exposure=unresolved,
            missing_member_fraction=span*F(len(members-known),len(members)) if present and members else None,
            missing_root=span*int(root not in known) if present and root is not None else None,
            extra_member_complexity=span*max(0,len(members)-3),unknown_root=span*int(root is None),
            metric_nonmember_exposure=None if self.delta(self.metric_bad,a,b) else self.nonmembers(self.metric_exposure,a,b,members),
            durable_nonmember_exposure=None if self.delta(self.durable_bad,a,b) else self.nonmembers(self.durable,a,b,members),
            lowest_nonmember_exposure=None if self.delta(self.bass_bad,a,b) else self.nonmembers(self.lowest,a,b,members),
            key_signature_foreign_member=None if self.delta(self.key_bad,a,b) or not members else
                sum((self.delta(self.foreign_prefix(t),a,b) for t in members),F())/len(members))
        roles=original.roles(sig)
        for name,t in zip(('absent_third_exposure','absent_altered_fifth_exposure','absent_seventh_exposure'),roles or (None,None,None)):
            result[name]=span*int(t is not None and t not in known) if present and roles is not None else None
        if old.get('root_deferred_presence') is not None:
            first=self.first(root,a,b)
            raw=F() if first is None else (first-a)/(self.points[-1]-self.points[0])
            factor=old['root_deferred_presence']/raw if raw else F()
            result['root_deferred_presence']=self.delta(self.beats,a,first)*factor if first is not None else F()
        credit=result.get('conditional_step_ornament_exposure')
        if credit is not None:result['conditional_step_ornament_exposure']=min(credit,result['nonmember_exposure'])
        return result


class RemainingFeatures:
    """Only features not replaced by v0.2 beat conversion; exact old semantics."""
    def __init__(self,problem,ev,units,args):
        self.problem,self.source,self.units=problem,ev.source,units
        self.context=TimingContext(ev,**args)
        self.positions,self.points=units.position,problem.points
        # Consumers use positivity and first positive cell only, not magnitudes.
        self.presence,self.unresolved=units.exposure,units.unknown
        self.patterns=[]
        for e in ev.source.events:
            pair=ev.source.neighbors.get(e.event_id);row=ev.source.rows.get(e.event_id)
            strength,unit=metric(ev.source,row['start'] if row else e.start)
            if not pair or e.pitch is None or strength is None or strength>1:continue
            p,n=pair;r=ev.source.rows[e.event_id];kind=None
            if r['end']-r['start']<=unit/2:
                h=[spelled_height(z['pitch_data']) for z in (p,r,n)]
                if all(v is not None for v in h):
                    approach,departure=r['pitch']-p['pitch'],n['pitch']-r['pitch']
                    if abs(h[1]-h[0])==abs(h[2]-h[1])==1 and 0<abs(approach)<=2 and 0<abs(departure)<=2:
                        kind='neighbor_like' if p['pitch_data']==n['pitch_data'] else 'passing_like' if approach*departure>0 else None
            self.patterns.append((e,p,n,pitch_token(p['pitch_data']),pitch_token(n['pitch_data']),kind))
        self.domain=lru_cache(8192)(lambda a,b:tuple(row for row in self.patterns if row[0].start<b and a<row[0].end))

    def features(self,a,b,sig):
        members=set(sig[1]);assessed=0;credit=F()
        for e,p,n,pt,nt,kind in self.domain(a,b):
            if e.pitch in members:continue
            assessed+=1
            if kind and p['start']>=a and n['end']<=b and pt in members and nt in members:
                credit+=(min(e.end,b)-max(e.start,a))/self.problem.total_note_time
        root=None
        if sig[0] is not None and not self.units.delta(self.units.unknown,a,b):
            first=self.units.first(sig[0],a,b)
            root=F() if first is None else (first-a)/(self.points[-1]-self.points[0])
            if root and self.context.support(a,first,sig):root*=SUPPORTED_DELAY_FACTOR
        late=timing_feature(self.problem,self.source,a,b,sig,context=self.context,index=self)[0]
        return dict(harmonic_run_count=F(1),root_deferred_presence=root,
            conditional_step_ornament_exposure=credit if assessed else None,
            late_identifying_member_exposure=late,
            nonmember_exposure=self.units.nonmembers(self.units.exposure,a,b,members),
            unresolved_spelling_exposure=self.units.delta(self.units.unknown,a,b)),[]


class FastSearch(original.UnitSearch):
    def __init__(self,problem,ev,weights,*,beam_width=8,operations=2_000_000,grace_notes=(),history_gate=None):
        if type(beam_width) is not int or beam_width<1 or type(operations) is not int or operations<1:
            raise ValueError('invalid_search_budget')
        self.problem,self.ev=problem,ev
        from .harmony_full_score import coefficients
        self.weights=coefficients(weights);self.width,self.budget=beam_width,operations
        self.args=dict(grace_notes=grace_notes,history_gate=history_gate)
        self.units=FastBeatIndex(ev,problem.points);self.index=RemainingFeatures(problem,ev,self.units,self.args)
        self.frontier={(None,None):(F(),())};self.at=self.operations=self.discarded=0
        self.status='pending';self.ledger={}
        self.run_cost=lru_cache(8192)(self._run_cost);self.pair_cost=lru_cache(8192)(self._pair_cost)
        self.change_cost=lru_cache(8192)(self._change_cost)
        self.pair_ev=replace(ev,_surface_cache={},_pair_cache={})
        self.row_cells=sweep(ev.rows,problem.points,lambda r:r['start'],lambda r:r['end'])
        self.bound_pair=bind(pair_features,{'interval_surface':self.last_surface})

    def last_surface(self,ev,a,b):
        j=self.units.position[b];rows=self.row_cells[j-1]
        if not rows:return []
        low=min(r['pitch'] for r in rows)
        return [(self.problem.points[j-1],b,frozenset(r['token'] for r in rows),
            frozenset(r['token'] for r in rows if r['pitch']==low),rows)]

    def _pair_cost(self,a,b,sig,next_sig):
        surface=six_four_surface(sig)
        functional=bool(surface and next_sig[0]==sig[0] and any(q in ('M','Mm7') for q in shapes(next_sig)))
        if not functional and not dominant_pairs(sig,next_sig):return F()
        start,end=self.problem.points[a],self.problem.points[b]
        values,_=self.bound_pair(self.pair_ev,start,end,self.problem.points[b+1],sig,next_sig)
        factor=min(F(1),self.units.delta(self.units.beats,start,end))
        return feature_cost({k:v*factor for k,v in values.items()},self.weights)


def infer(ir,total):
    leases=[]
    def propose(view,span,context_span=None):
        if not leases:leases.append(WindowWorkspace(view,max_entries=4))
        workspace=leases[0]
        if view is not workspace.ir:raise ValueError('workspace_foreign_source')
        return workspace._catalog(view,span,context_span)
    # Private dependency binding leaves the sealed modules and functions intact.
    spans,details,catalogs=bind(original.infer,{'UnitSearch':FastSearch,'propose':propose})(ir,total)
    details.update(version=VERSION,optimization_changes_score_semantics=False,
        optimization_changes_candidates=False,optimization_changes_beam=False,
        performance_adapter='source_sweep_span_reuse_exact_residual_projection_pair_last_surface',
        window_reuse=leases[0].receipt() if leases else None)
    return spans,details,catalogs


worker=bind(original.worker,{'infer':infer})

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--worker',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True);args=ap.parse_args();worker(args.worker,args.output)
