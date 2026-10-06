"""Bounded prefix CPU diagnosis, not a partial whole-score submission."""
import argparse
import cProfile
import json
from pathlib import Path
import pstats
import sys
from time import perf_counter

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from musicanote_harness import harmony_whole_score_units as units
from musicanote_harness.harmony_test_a import read_score,digest,write
from musicanote_harness.harmony_window_workspace import bind


class PrefixDone(Exception):pass


def run(output):
    if output.exists():raise ValueError('output_exists_no_overwrite')
    cohort=json.loads((ROOT/'output/harmony-whole-score-units-2026-10-06-r1/freeze.json').read_text(encoding='utf-8'))
    source=Path(next(e['source_file'] for e in cohort['selected'] if e['index']==156))
    source_sha=digest(source);ir,total,_=read_score(source)
    counters={};limit=32
    class TraceSearch(units.UnitSearch):
        def __init__(self,*args,**kwargs):
            super().__init__(*args,**kwargs);counters['whole_cells']=len(self.problem.points)-1
        def consume(self,edges):
            super().consume(edges);counters.update(cells=self.at,operations=self.operations)
            if self.at>=limit:raise PrefixDone()
    call=bind(units.infer,{'UnitSearch':TraceSearch})
    profiler=cProfile.Profile();t=perf_counter();profiler.enable()
    try:call(ir,total)
    except PrefixDone:pass
    finally:profiler.disable()
    if counters.get('cells')!=limit:raise ValueError('profile_prefix_incomplete')
    if digest(source)!=source_sha:raise ValueError('source_changed')
    output.mkdir(parents=True)
    profiler.dump_stats(str(output/'prefix.prof'))
    stats=pstats.Stats(profiler)
    rows=[dict(file=file,line=line,function=name,primitive_calls=cc,calls=nc,
        self_seconds=tt,cumulative_seconds=ct) for (file,line,name),(cc,nc,tt,ct,_) in stats.stats.items()]
    rows.sort(key=lambda r:r['cumulative_seconds'],reverse=True)
    write(output/'profile.json',dict(source_file=str(source),source_sha256=source_sha,
        version=units.VERSION,prefix_cells=limit,whole_score_scope_preserved=True,
        whole_score_inference_completed=False,partial_predictions_submitted=False,
        source_labels_used=False,seconds=perf_counter()-t,counts=counters,functions=rows))
    print(json.dumps(dict(seconds=perf_counter()-t,counts=counters,top=rows[:20]),ensure_ascii=False),flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True)
    run(ap.parse_args().output.resolve())
