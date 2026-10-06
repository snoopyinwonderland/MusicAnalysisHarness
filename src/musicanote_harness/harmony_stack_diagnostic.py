"""Optional watchdog output; preserve the sealed bootstrap and score workers.

The synthetic probes load no score, music21, model or labels. Disabling timed
stack dumps does not disable fatal handlers, deadlines or phase telemetry.
"""
import argparse
import faulthandler
from fractions import Fraction
import hashlib
from pathlib import Path
from time import perf_counter, sleep
from types import SimpleNamespace

from .harmony_execution import atomic_json, child
from .harmony_owned_score_worker import bind, load_worker

VERSION = 'harmony-stack-diagnostic-0.1.0'
PROBE_SECONDS = 6.5


def diagnostic_facade(periodic, handler=faulthandler):
    if type(periodic) is not bool:
        raise ValueError('periodic_policy_must_be_boolean')
    return SimpleNamespace(
        enable=handler.enable,
        dump_traceback_later=(handler.dump_traceback_later if periodic
                              else lambda *args, **kwargs: None),
        cancel_dump_traceback_later=(handler.cancel_dump_traceback_later if periodic
                                     else lambda: None))


def bind_bootstrap(periodic=False, loader=load_worker, handler=faulthandler):
    return bind(child, {
        'faulthandler': diagnostic_facade(periodic, handler),
        'importlib': SimpleNamespace(import_module=loader)})


def run(output, nonce, action, source, *, periodic=False):
    if action not in ('intervals', 'compiled'):
        raise ValueError('unrecognized_score_action')
    atomic_json(output/'diagnostic-policy.json', dict(
        version=VERSION, periodic_snapshots=periodic,
        fatal_handler_enabled=True, original_bootstrap_bytecode_preserved=True))
    bind_bootstrap(periodic)(output, nonce, action, source, windows_label=False)


def kernel():
    return sum(((value*3 + Fraction(1, 7))/(value+1)
                for value in (Fraction(i, i+1) for i in range(1, 65))), Fraction())


def workload(kind, seconds=PROBE_SECONDS):
    if kind not in ('cpu', 'sleep') or seconds <= 0:
        raise ValueError('invalid_synthetic_workload')
    expected = kernel()
    last = expected
    iterations = 0
    started = perf_counter()
    if kind == 'sleep':
        sleep(seconds)
    else:
        while perf_counter()-started < seconds:
            last = kernel()
            iterations += 1
    if last != expected:
        raise ArithmeticError('synthetic_fraction_kernel_changed')
    return dict(kind=kind, target_seconds=seconds,
        workload_seconds=perf_counter()-started, iterations=iterations,
        kernel_result=str(last), kernel_sha256=hashlib.sha256(str(last).encode()).hexdigest(),
        kernel_verified=True, no_music_analysis=True)


def probe(output, nonce, kind, *, periodic):
    # Exercise the SAME bootstrap under two private diagnostic dependencies.
    # Its synthetic source label is never opened as a score or any other file.
    def worker(source, result):
        atomic_json(result, dict(status='complete', scope='synthetic_stdlib_only',
                                **workload(kind)))

    def loader(name):
        if name != 'musicanote_harness.harmony_whole_score_intervals':
            raise ValueError('unexpected_probe_import')
        return SimpleNamespace(worker=worker)

    atomic_json(output/'diagnostic-policy.json', dict(
        version=VERSION, periodic_snapshots=periodic, kind=kind,
        fatal_handler_enabled=True, no_music_analysis=True))
    bind_bootstrap(periodic, loader)(output, nonce, 'intervals',
        Path('synthetic-stdlib-'+kind), windows_label=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--child', type=Path, required=True)
    parser.add_argument('--nonce', required=True)
    parser.add_argument('--action', choices=('cpu', 'sleep', 'intervals', 'compiled'), required=True)
    parser.add_argument('--source', type=Path)
    parser.add_argument('--periodic-snapshots', action='store_true')
    args = parser.parse_args()
    if args.action in ('cpu', 'sleep'):
        if args.source is not None:
            parser.error('synthetic probes must not receive a score')
        probe(args.child.resolve(), args.nonce, args.action, periodic=args.periodic_snapshots)
    else:
        if args.source is None:
            parser.error('score action requires --source')
        run(args.child.resolve(), args.nonce, args.action, args.source,
            periodic=args.periodic_snapshots)
