"""Post-run repair: atomic phase checkpoints, no change to harmony inference.

The stage101 comparison is preserved. This writer has NOT been used for a
second whole-score run. It prevents termination during a write from destroying
the last complete sidecar; it does not improve harmonic or runtime metrics.
"""
import argparse
import os
from pathlib import Path

from . import harmony_whole_score_phases as phases
from .harmony_window_workspace import bind
from .harmony_test_a import write

VERSION='atomic-phase-checkpoint-0.1.0'


class AtomicTelemetry(phases.Telemetry):
    def checkpoint(self,**progress):
        self.progress.update(progress)
        if self.path is not None:
            pending=self.path.with_name(self.path.name+'.pending')
            write(pending,self.receipt()|dict(checkpoint_writer=VERSION))
            # Same-directory replace publishes only a complete JSON file. If
            # writing/replacing fails, the previous checkpoint remains intact.
            os.replace(pending,self.path)


def worker(source,output,*,implementation='control'):
    dependencies={'Telemetry':AtomicTelemetry}
    if implementation=='compiled':
        from .harmony_whole_score_compiled import infer_phases
        dependencies['infer']=infer_phases
    elif implementation!='control':raise ValueError('unknown_implementation')
    return bind(phases.worker,dependencies)(source,output)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--worker',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--implementation',choices=('control','compiled'),default='control')
    args=ap.parse_args();worker(args.worker,args.output,implementation=args.implementation)
