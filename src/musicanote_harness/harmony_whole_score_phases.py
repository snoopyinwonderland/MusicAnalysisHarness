"""Bounded, score-preserving phase diagnostics with durable timeout progress.

Private dependencies/instances only. No partial prediction is a submission.
Times are wall time, inclusive when nested; they must not be summed blindly.
"""
import argparse
from collections import Counter
from contextlib import contextmanager
import gzip
import json
from pathlib import Path
from time import perf_counter
import traceback

from . import harmony_whole_score_fast as fast
from . import harmony_whole_score_units as original
from .harmony_window_workspace import WindowWorkspace, bind
from .harmony_test_a import digest, read_score, write

VERSION = 'whole-score-phase-diagnostics-0.1.0'


class Telemetry:
    def __init__(self, path=None):
        self.path = path
        self.started = perf_counter()
        self.seconds, self.calls = Counter(), Counter()
        self.stack, self.progress = [], {}

    def checkpoint(self, **progress):
        self.progress.update(progress)
        if self.path is not None:
            write(self.path, self.receipt())

    def receipt(self):
        now = perf_counter()
        return dict(version=VERSION, elapsed_seconds=now-self.started,
            completed_seconds=dict(self.seconds), calls=dict(self.calls),
            active=[dict(phase=p, elapsed_seconds=now-t) for p,t in self.stack],
            progress=self.progress, times_inclusive_when_nested=True,
            partial_prediction_submitted=False)

    @contextmanager
    def phase(self, name, *, persist=False):
        t = perf_counter()
        self.stack.append((name,t))
        if persist: self.checkpoint()
        try:
            yield
        finally:
            self.seconds[name] += perf_counter()-t
            self.calls[name] += 1
            self.stack.pop()
            if persist: self.checkpoint()

    def wrap(self, name, fn, *, persist=False):
        def measured(*args, **kwargs):
            with self.phase(name, persist=persist):
                return fn(*args, **kwargs)
        return measured


def infer(ir, total, telemetry):
    leases=[]
    def propose(view, span, context_span=None):
        with telemetry.phase('candidate_catalog', persist=True):
            if not leases: leases.append(WindowWorkspace(view,max_entries=4))
            workspace=leases[0]
            if view is not workspace.ir: raise ValueError('workspace_foreign_source')
            result=workspace._catalog(view,span,context_span)
        telemetry.checkpoint(pages=telemetry.calls['candidate_catalog'])
        return result

    class TimedScorer(original.UnitScorer):
        def __init__(self,*args):
            init=bind(original.UnitScorer.__init__,{
                'BeatIndex':telemetry.wrap('direct_beat_index',original.BeatIndex,persist=True),
                'Scorer':telemetry.wrap('direct_context_init',original.Scorer,persist=True)})
            init(self,*args)
            self.old.path_features=telemetry.wrap('legacy_full_features',self.old.path_features,persist=True)
        def path_features(self,ids):
            with telemetry.phase('direct_path_features',persist=True):
                return super().path_features(ids)

    class TimedSearch(fast.FastSearch):
        def __init__(self,*args,**kwargs):
            with telemetry.phase('search_index',persist=True):
                super().__init__(*args,**kwargs)
            telemetry.checkpoint(total_cells=len(self.problem.points)-1,events=len(self.ev.source.events))
        def consume(self,edges):
            with telemetry.phase('search_consume'):
                super().consume(edges)
            if self.at%32==0 or self.at==len(self.problem.points)-1:
                telemetry.checkpoint(cells_consumed=self.at,operations=self.operations)
        def finish(self):
            telemetry.checkpoint(cells_consumed=self.at,operations=self.operations)
            with telemetry.phase('finish',persist=True):
                return bind(original.UnitSearch.finish,{'UnitScorer':TimedScorer})(self)

    dependencies={'UnitSearch':TimedSearch,'propose':propose,
        'evidence':telemetry.wrap('source_evidence',original.evidence,persist=True)}
    with telemetry.phase('infer',persist=True):
        spans,details,catalogs=bind(original.infer,dependencies)(ir,total)
        details.update(version=fast.VERSION,optimization_changes_score_semantics=False,
            optimization_changes_candidates=False,optimization_changes_beam=False,
            window_reuse=leases[0].receipt() if leases else None)
    return spans,details,catalogs


def worker(source,output):
    telemetry=Telemetry(Path(output).with_suffix('.phases.json'))
    telemetry.checkpoint(source_file=str(source))
    try:
        with telemetry.phase('parse',persist=True):
            sha=digest(source);ir,total,removed=read_score(source)
        spans,info,catalogs=infer(ir,total,telemetry)
        if sha!=digest(source):raise ValueError('source_changed')
        for suffix,obj in (('.ir.json.gz',ir),('.catalogs.json.gz',catalogs)):
            with telemetry.phase('serialize'+suffix,persist=True):
                data=json.dumps(obj,ensure_ascii=False,separators=(',',':')).encode('utf-8')
            with telemetry.phase('compress'+suffix,persist=True):
                compressed=gzip.compress(data,mtime=0)
            with telemetry.phase('write'+suffix,persist=True):
                Path(output).with_suffix(suffix).write_bytes(compressed)
        result=dict(source_file=str(source),source_sha256=sha,score_duration=str(total),
            parse_seconds=telemetry.seconds['parse'],seconds=perf_counter()-telemetry.started,
            harmony_elements_removed=removed,spans=spans,**info)
    except Exception as exc:
        result=dict(status='error',error=f'{type(exc).__name__}: {exc}',traceback=traceback.format_exc(),spans=[])
    telemetry.checkpoint(status=result['status'])
    write(output,result)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--worker',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();worker(args.worker,args.output)
