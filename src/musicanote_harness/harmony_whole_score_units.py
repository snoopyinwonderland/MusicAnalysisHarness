"""Research v0.2: local beat costs + explicit supported-candidate domain.

Old coefficient NUMBERS are priors, not a calibrated/frozen model with the
same meanings. All page candidates remain archived; unsupported shapes are
not silently assigned zero missing-role costs in the main selector.
"""
import argparse
from collections import Counter
from fractions import Fraction as F
import gzip
import json
from pathlib import Path
from time import perf_counter
import traceback

from .harmony_whole_score import CellSearch, CONFIG, model_weights
from .harmony_whole_score_diagnosis import evidence, pc
from .harmony_test_a import MODEL_SHA, digest, fraction as f, read_score, write, merge_spans
from .harmony_source_clock import SourceClockGuard
from .harmony_progression_search import _hash
from .harmony_candidate_catalog import propose
from .harmony_candidate_recall import rational as q
from .harmony_evidence_scoring import metric, meter_at, key_alters
from .harmony_temporal_scoring import beat_extent, resolution_features
from .harmony_full_score import Scorer, FEATURES, applicability
from .harmony_functional_scoring import shapes, six_four_surface, PAIR_WEIGHTS
from .harmony_support_balance import roles
from .harmony_scored_decoder import Problem, Edge, feature_cost, transition, TRANSITION_FEATURES

VERSION = 'local-beat-whole-score-supported-domain-0.2.0'
COUNT_FEATURES = frozenset((*TRANSITION_FEATURES, *PAIR_WEIGHTS,
                          'harmonic_run_count', 'functional_role_complexity'))


def supported(sig):
    return bool(shapes(sig) or six_four_surface(sig) is not None)


class BeatIndex:
    """Cell-local note weighting; unrelated thick texture cannot dilute a cell.

    Beat coordinates are exact; no notated time is changed. Silence contributes
    no note-fit exposure, but elapsed beat priors remain explicit.
    """
    def __init__(self, ev, points):
        self.source, self.points = ev.source, points
        self.position = {t:i for i,t in enumerate(points)}
        self.beats = [F()]
        self.exposure, self.metric_exposure, self.durable, self.lowest, self.foreign = {},{},{},{},{}
        self.unknown = [F()]
        self.metric_bad, self.durable_bad, self.bass_bad, self.key_bad = [F()],[F()],[F()],[F()]
        self.key_cells = []
        tokens = {e.pitch for e in ev.source.events if e.pitch is not None}
        for table in (self.exposure,self.metric_exposure,self.durable,self.lowest,self.foreign):
            table.update({t:[F()] for t in tokens})
        for a,b in zip(points,points[1:]):
            dt = beat_extent(ev.source,a,b)
            if dt is None:raise ValueError('meter_unavailable_no_quarter_fallback')
            active = [e for e in ev.source.events if e.start < b and a < e.end]
            n=len(active); exposure=Counter(); met=Counter(); dur=Counter(); bass=Counter()
            mb=db=bb=False
            known=[]
            for e in active:
                strength,unit=metric(ev.source,e.start)
                mb |= strength is None; db |= unit is None
                if e.pitch is None:continue
                exposure[e.pitch] += dt/n
                if strength is not None:met[e.pitch] += dt*strength/n
                if unit is not None and e.end-e.start >= unit:dur[e.pitch] += dt/n
                row=ev.source.rows.get(e.event_id)
                if row is None or row.get('pitch') is None:bb=True
                else:known.append((row['pitch'],e.pitch))
            if active and not bb and len(known)==n:
                height=min(p for p,t in known)
                lowest=[t for p,t in known if p==height]
                for t in lowest:bass[t] += dt/len(lowest)
            elif active:bb=True
            grid=meter_at(ev.source,a)
            alters=key_alters(grid[2]) if grid else None
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

    def delta(self, prefix,a,b):
        return prefix[self.position[b]]-prefix[self.position[a]]

    def foreign_prefix(self, token):
        # Candidate members need not occur in the score. Absence is evidence,
        # not an invalid key lookup; preserve unknown-key handling separately.
        if token not in self.foreign:
            prefix=[F()]
            for dt,alters in self.key_cells:
                prefix.append(prefix[-1]+(dt*int(alters[token[0]]!=token[1])
                    if alters is not None else F()))
            self.foreign[token]=prefix
        return self.foreign[token]

    def convert(self, old,a,b,sig):
        # The remaining bounded ornament/late-entry observations retain their
        # old definitions. Their rate is expanded to beat-cost units explicitly.
        result={k:None if v is None else v*(1 if k in COUNT_FEATURES else self.total_beats)
                for k,v in old.items()}
        members=set(sig[1]);root=sig[0]
        span=self.delta(self.beats,a,b)
        known={t for t,p in self.exposure.items() if self.delta(p,a,b)>0}
        unresolved=self.delta(self.unknown,a,b)
        present=bool(known) and not unresolved
        total=lambda table:sum((self.delta(p,a,b) for t,p in table.items() if t not in members),F())
        result.update(nonmember_exposure=total(self.exposure), unresolved_spelling_exposure=unresolved,
            missing_member_fraction=span*F(len(members-known),len(members)) if present and members else None,
            missing_root=span*int(root not in known) if present and root is not None else None,
            extra_member_complexity=span*max(0,len(members)-3), unknown_root=span*int(root is None),
            metric_nonmember_exposure=None if self.delta(self.metric_bad,a,b) else total(self.metric_exposure),
            durable_nonmember_exposure=None if self.delta(self.durable_bad,a,b) else total(self.durable),
            lowest_nonmember_exposure=None if self.delta(self.bass_bad,a,b) else total(self.lowest),
            key_signature_foreign_member=None if self.delta(self.key_bad,a,b) or not members else
                sum((self.delta(self.foreign_prefix(t),a,b) for t in members),F())/len(members))
        r=roles(sig)
        for name,t in zip(('absent_third_exposure','absent_altered_fifth_exposure','absent_seventh_exposure'),
                          r or (None,None,None)):
            result[name]=span*int(t is not None and t not in known) if present and r is not None else None
        # Preserve the old conditional context attenuation without retroactive
        # sound. Convert first-root delay from quarter ratio to actual beats.
        if old.get('root_deferred_presence') is not None:
            first=next((t for t in self.points[self.position[a]:self.position[b]]
                        if root in self.exposure and self.delta(self.exposure[root],t,
                            self.points[self.position[t]+1])>0),None)
            raw=F() if first is None else (first-a)/(self.points[-1]-self.points[0])
            factor=old['root_deferred_presence']/raw if raw else F()
            result['root_deferred_presence']=self.delta(self.beats,a,first)*factor if first is not None else F()
        credit=result.get('conditional_step_ornament_exposure')
        if credit is not None:
            result['conditional_step_ornament_exposure']=min(credit,result['nonmember_exposure'])
        return result


class UnitScorer:
    """Independent direct old-feature extraction + new unit aggregation."""
    def __init__(self,problem,ev,weights,args):
        self.problem,self.ev,self.weights=problem,ev,weights
        self.old=Scorer(problem,ev,weights,**args)
        self.units=BeatIndex(ev,problem.points)

    def path_features(self,ids):
        by_id={e.group_id:e for e in self.problem.edges}
        self.old.path_features(ids)  # completeness/referential contract
        values=dict.fromkeys(FEATURES,F());available=dict.fromkeys(FEATURES,True)
        def add(v):
            for k,x in v.items():
                if x is None:available[k]=False
                else:values[k]+=x
        runs=[]
        for gid in ids:
            e=by_id[gid];values['blocker_exposure']+=e.features.get('blocker_exposure',F())
            if runs and runs[-1][2]==e.signature:runs[-1]=(runs[-1][0],e.end,e.signature)
            else:
                if runs:
                    a,b,sig=runs[-1]
                    add(transition(sig,e))
                    add(resolution_features(self.ev,a,b,e.end,sig,e.signature)[0])
                runs.append((e.start,e.end,e.signature))
        for a,b,sig in runs:
            base,_=self.old.source_scorer.base_run(self.problem,self.ev.source,a,b,sig)
            member,_=self.old.source_scorer.member_features(self.problem,self.ev.source,a,b,sig)
            old=applicability(base)|member|{'functional_role_complexity':F(int(six_four_surface(sig) is not None))}
            add(self.units.convert(old,a,b,sig))
        return values,available,len(runs)


class UnitSearch(CellSearch):
    def __init__(self,problem,ev,weights,**kwargs):
        super().__init__(problem,ev,weights,**kwargs)
        self.units=BeatIndex(ev,problem.points)

    def _run_cost(self,a,b,sig):
        old,_=self.index.features(self.problem.points[a],self.problem.points[b],sig)
        old=applicability(old)|{'functional_role_complexity':F(int(six_four_surface(sig) is not None))}
        return feature_cost(self.units.convert(old,self.problem.points[a],self.problem.points[b],sig),self.weights)

    def finish(self):
        info=dict(status=self.status,operations=self.operations,cells_consumed=self.at,
            beam_width=self.width,states_discarded=self.discarded,exact_optimum_claimed=False,selected=None)
        if self.status!='pending':return info
        if self.at!=len(self.problem.points)-1:raise ValueError('partial_path_not_submission')
        cost,ids=min(self.frontier.values())
        from dataclasses import replace
        graph=replace(self.problem,edges=tuple(self.ledger[i] for i in ids))
        direct=UnitScorer(graph,self.ev,self.weights,self.args)
        values,available,runs=direct.path_features(ids)
        if cost!=feature_cost(values,self.weights):raise ValueError('unit_score_direct_mismatch')
        return info|dict(status='complete',selected=ids,score_cost=str(cost),
            mean_cost_per_beat=str(cost/self.units.total_beats),total_beats=str(self.units.total_beats),
            independently_rescored=True,actual_harmonic_runs=runs,
            feature_values={k:str(v) for k,v in values.items()},feature_availability=available)


def infer(ir,total):
    original=_hash(ir)
    gate=SourceClockGuard(ir).scope({'start':q(0),'end':q(total)})
    if not gate['accepted']:return [],dict(status='source_clock_abstention',source_clock_gate=gate),[]
    ev,points,pages,args=evidence(ir,total)
    from .harmony_bounded_recovery import grace_projection
    view,_=grace_projection(ir)
    graph=Problem(points,(),len(points)-1,sum((e.end-e.start for e in ev.source.events),F()),'ready')
    if not graph.total_note_time:return [],dict(status='no_positive_sounding_exposure'),[]
    search=UnitSearch(graph,ev,model_weights(),beam_width=CONFIG['beam_width'],
        operations=CONFIG['operations'],**args)
    catalogs=[];inventory=[];previous={}
    for lo,hi in pages:
        span={'start':q(points[lo]),'end':q(points[hi])}
        catalog=propose(view,span,span);catalogs.append(catalog)
        bank={};held=0
        for c in catalog['candidates']:
            for alt in c['spelling_alternatives']:
                sig=(None if alt['root_spelling'] is None else tuple(alt['root_spelling']),
                     tuple(sorted(map(tuple,alt['members']))))
                if not supported(sig):held+=1;continue
                bank[sig]=bank.get(sig,frozenset())|frozenset(c['abstention_reasons'])
        native_count=len(bank)
        if not bank:bank=previous.copy()
        inventory.append(dict(start=str(points[lo]),end=str(points[hi]),supported_signatures=native_count,
            analysis_only_alternatives=held,catalog_sha256=_hash(catalog),carried_bank=not native_count))
        if not bank:return [],dict(status='no_supported_context_candidates',pages=inventory),catalogs
        previous=bank.copy()
        for i in range(lo,hi):
            choices=dict(bank)
            for _,sig in search.frontier:
                if sig is not None and sig not in choices:
                    choices[sig]=frozenset(catalog['providers']['base']['abstention_reasons'])
            a,b=points[i:i+2]
            active=[e for e in ev.source.events if e.start<b and a<e.end]
            attack=frozenset(e.pitch for e in active if e.start==a and e.pitch is not None)
            edges=[]
            for sig in sorted(choices,key=repr):
                blockers=tuple(sorted(choices[sig]))
                blocked=search.units.delta(search.units.beats,a,b) if blockers and active else F()
                edges.append(Edge(f'unit_{i:06d}_{_hash(sig)[:20]}',i,i+1,a,b,sig,
                    {'blocker_exposure':blocked},attack,tuple(sorted(e.event_id for e in active)),blockers,
                    {'proposal_page':len(inventory)-1}))
            search.consume(edges)
            if search.status!='pending':break
        if search.status!='pending':break
    result=search.finish();details={k:v for k,v in result.items() if k!='selected'}
    details.update(version=VERSION,coefficient_origin_sha256=MODEL_SHA,coefficient_numbers_changed=False,
        score_semantics_changed=True,calibrated_confidence=False,config=CONFIG,page_inventory=inventory,
        source_labels_used=False,core_modified=False,source_ir_sha256=original,
        candidate_domain='ordinary_tertian_triads_sevenths_and_functional_six_four_surface',
        unsupported_candidates='archived_analysis_only_not_absent_or_invalid_chords',
        candidate_graph_changed=True,local_winner_stitching=False,production_enabled=False,
        limitations=['Remaining bounded NCT/entry features reuse old definitions; not a complete local-role scorer.',
                    'Unknown features remain unavailable. No confirmed NCT/local key/cadence.',
                    'Candidate lifetime is still soft run evidence; no complete persistence/expiry model.'])
    if _hash(ir)!=original:raise ValueError('canonical_core_mutated')
    if result['selected'] is None:return [],details,catalogs
    path=[search.ledger[gid] for gid in result['selected']]
    details['selected_path']=[dict(start=str(e.start),end=str(e.end),signature=e.signature,
        source_event_ids=e.source_event_ids,blockers=e.blockers,proposal_page=e.adapter['proposal_page']) for e in path]
    notes={s['sounding_event_id']:s for s in ir['sounding_events']};output=[]
    for e in path:
        if not e.source_event_ids or e.signature[0] is None:continue
        members=sorted({pc(t) for t in e.signature[1]})
        pitches=[notes[s]['pitch'].get('midi_pitch') for s in e.source_event_ids]
        bass=min(p for p in pitches if p is not None)%12 if any(p is not None for p in pitches) else None
        output.append(dict(start=str(e.start),end=str(e.end),root_pc=pc(e.signature[0]),pcs=members,
            bass_pc=bass if bass in members else None))
    return merge_spans(output),details,catalogs


def worker(source,output):
    t=perf_counter()
    try:
        sha=digest(source);ir,total,removed=read_score(source);parsed=perf_counter()-t
        spans,info,catalogs=infer(ir,total)
        if sha!=digest(source):raise ValueError('source_changed')
        for suffix,obj in (('.ir.json.gz',ir),('.catalogs.json.gz',catalogs)):
            Path(output).with_suffix(suffix).write_bytes(gzip.compress(
                json.dumps(obj,ensure_ascii=False,separators=(',',':')).encode('utf-8'),mtime=0))
        result=dict(source_file=str(source),source_sha256=sha,score_duration=str(total),
            parse_seconds=parsed,seconds=perf_counter()-t,harmony_elements_removed=removed,spans=spans,**info)
    except Exception as exc:
        result=dict(status='error',error=f'{type(exc).__name__}: {exc}',traceback=traceback.format_exc(),
            seconds=perf_counter()-t,spans=[])
    write(output,result)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--worker',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True);args=ap.parse_args();worker(args.worker,args.output)
