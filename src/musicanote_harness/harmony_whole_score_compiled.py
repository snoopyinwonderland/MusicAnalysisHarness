"""Exact weighted-prefix run costs; unchanged musical score and direct audit.

Compilation uses integer numerators on source-derived LCM scales, never
floating point, quantization, candidate removal or coefficient fitting.
"""
import argparse
from bisect import bisect_left,bisect_right
from fractions import Fraction as F
from functools import lru_cache
from math import lcm
from pathlib import Path
from types import SimpleNamespace

from . import harmony_whole_score_fast as fast
from . import harmony_whole_score_units as original
from . import harmony_whole_score_phases as phases
from .harmony_window_workspace import bind
from .harmony_evidence_scoring import metric
from .harmony_member_timing import TimingContext
from .harmony_root_context_scoring import RootReturnContext
from .harmony_functional_scoring import six_four_surface

VERSION='local-beat-whole-score-supported-domain-0.2.2-compiled'


class WeightedPrefix:
    """Exact cost projection of one full prefix table; includes negative costs."""
    def __init__(self,table,weight,length):
        denominator=lcm(*(v.denominator for p in table.values() for v in p))
        self.scale=denominator*weight.denominator
        self.members={t:tuple(v.numerator*(denominator//v.denominator)*weight.numerator for v in p)
                      for t,p in table.items()}
        self.total=tuple(sum(p[i] for p in self.members.values()) for i in range(length))

    def nonmembers(self,i,j,members):
        value=self.total[j]-self.total[i]-sum(p[j]-p[i] for t in members if (p:=self.members.get(t)) is not None)
        return F(value,self.scale)


class SourceEvents:
    """All original source fields, only the loop's already-filtered root rows."""
    def __init__(self,source,events):self.source,self.events=source,events
    def __getattr__(self,name):return getattr(self.source,name)


class IndexedContext(TimingContext):
    def __init__(self,ev,units,**args):
        super().__init__(ev,**args);self.units=units
        roots={}
        for e in self.source.events:roots.setdefault(e.pitch,[]).append(e)
        self.root_sources={t:SourceEvents(self.source,tuple(es)) for t,es in roots.items()}
        cells=fast.sweep(self.rows,units.points,lambda r:r['start'],lambda r:r['end'])
        self.lowest_cells=[]
        for rows in cells:
            self.lowest_cells.append(None if not rows or any(not r['clock_valid'] or r['token'] is None for r in rows)
                else min(r['pitch'] for r in rows))

    def extent(self,a,b):
        if a==b:return F()
        if a in self.units.position and b in self.units.position:
            return self.units.delta(self.units.beats,a,b)
        return super().extent(a,b)

    def lowest(self,row,time,*,before=False):
        at=self.units.position.get(time)
        if at is None:return super().lowest(row,time,before=before)
        at-=int(before)
        low=self.lowest_cells[at] if 0<=at<len(self.lowest_cells) else None
        return low is not None and row['pitch']==low

    def _support(self,start,first,sig):
        root=sig[0];_,unit=metric(self.source,start)
        if first<=start or unit is None or root is None:return []
        ends=self.root_ends.get(root,())
        if bisect_left(ends,start-unit)==bisect_right(ends,start):return []
        # Original _support filters source.events by this exact spelled root.
        # Bound methods (lowest/step_group) still inspect full source geometry.
        proxy=SimpleNamespace(**(self.__dict__|dict(source=self.root_sources.get(root,SourceEvents(self.source,())),
            lowest=self.lowest,step_group=self.step_group)))
        return RootReturnContext._support(proxy,start,first,sig)


class CompiledSearch(fast.FastSearch):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.index.context=IndexedContext(self.ev,self.units,**self.args)
        self.weighted={name:WeightedPrefix(getattr(self.units,table),self.weights[name],len(self.problem.points))
            for name,table in (('nonmember_exposure','exposure'),('metric_nonmember_exposure','metric_exposure'),
                ('durable_nonmember_exposure','durable'),('lowest_nonmember_exposure','lowest'))}
        self.signature_facts=lru_cache(8192)(self._signature_facts)

    def _signature_facts(self,sig):
        return frozenset(sig[1]),original.roles(sig),six_four_surface(sig) is not None

    def _run_cost(self,i,j,sig):
        a,b=self.problem.points[i],self.problem.points[j]
        old,_=self.index.features(a,b,sig)
        members,roles,functional=self.signature_facts(sig);root=sig[0]
        span,known,unresolved=self.units.span_facts(a,b)
        present=bool(known) and not unresolved;w=self.weights
        cost=self.weighted['nonmember_exposure'].nonmembers(i,j,members)
        for name,bad in (('metric_nonmember_exposure','metric_bad'),
                         ('durable_nonmember_exposure','durable_bad'),('lowest_nonmember_exposure','bass_bad')):
            if not self.units.delta(getattr(self.units,bad),a,b):
                cost+=self.weighted[name].nonmembers(i,j,members)
        cost+=unresolved*w['unresolved_spelling_exposure']+w['harmonic_run_count']+int(functional)*w['functional_role_complexity']
        rate=max(0,len(members)-3)*w['extra_member_complexity']+int(root is None)*w['unknown_root']
        if present:
            if members:rate+=F(len(members-known),len(members))*w['missing_member_fraction']
            if root is not None:rate+=int(root not in known)*w['missing_root']
            if roles is not None:
                for name,t in zip(('absent_third_exposure','absent_altered_fifth_exposure','absent_seventh_exposure'),roles):
                    rate+=int(t is not None and t not in known)*w[name]
        cost+=span*rate
        if members and not self.units.delta(self.units.key_bad,a,b):
            cost+=sum((self.units.delta(self.units.foreign_prefix(t),a,b) for t in members),F())/len(members)*w['key_signature_foreign_member']
        deferred=old.get('root_deferred_presence')
        if deferred is not None:
            first=self.units.first(root,a,b)
            raw=F() if first is None else (first-a)/(self.problem.points[-1]-self.problem.points[0])
            if raw:cost+=self.units.delta(self.units.beats,a,first)*(deferred/raw)*w['root_deferred_presence']
        late=old.get('late_identifying_member_exposure')
        if late is not None:cost+=late*self.units.total_beats*w['late_identifying_member_exposure']
        credit=old.get('conditional_step_ornament_exposure')
        if credit is not None:
            cost+=min(credit*self.units.total_beats,old['nonmember_exposure'])*w['conditional_step_ornament_exposure']
        return cost


# Preserve the measured original inference/finish/provider code, including the
# independent stage99 UnitScorer. Telemetry has no effect on score or candidates.
infer_phases=bind(phases.infer,{'fast':SimpleNamespace(FastSearch=CompiledSearch,VERSION=VERSION)})


def infer(ir,total):return infer_phases(ir,total,phases.Telemetry())


worker=bind(phases.worker,{'infer':infer_phases})

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--worker',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();worker(args.worker,args.output)
