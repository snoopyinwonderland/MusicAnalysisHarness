"""Original stage103 bootstrap; private atomic-result writer for both arms.

No global module mutation, musical/provider dependency replacement or OS-label
bypass. This module itself must remain stdlib-only before bootstrap_enter.
"""
import argparse
import importlib
from pathlib import Path
from types import FunctionType, SimpleNamespace

from .harmony_execution import atomic_json, child

VERSION = 'owned-whole-score-execution-0.1.0'


def bind(original, replacements):
    if not isinstance(original, FunctionType) or not set(replacements) <= (
            set(original.__code__.co_names) & set(original.__globals__)):
        raise ValueError('unrecognized_private_writer_binding')
    result = FunctionType(original.__code__, original.__globals__ | replacements,
                          original.__name__, original.__defaults__, original.__closure__)
    result.__kwdefaults__ = original.__kwdefaults__
    return result


def atomic_worker(module):
    # Both original workers bind phases.worker privately. Replace its final
    # writer too, so a timeout during publication cannot destroy previous JSON.
    phase_worker = bind(module.phases.worker, {'write': atomic_json})
    replacements = {'phases': SimpleNamespace(worker=phase_worker)}
    if 'write' in module.worker.__code__.co_names:
        replacements['write'] = atomic_json
    return bind(module.worker, replacements)


def load_worker(name):
    if name not in ('musicanote_harness.harmony_whole_score_intervals',
                    'musicanote_harness.harmony_phase_checkpoint'):
        raise ValueError('unrecognized_owned_worker_module')
    module = importlib.import_module(name)
    return SimpleNamespace(worker=atomic_worker(module))


def run(output, nonce, action, source):
    bootstrap = bind(child, {'importlib': SimpleNamespace(import_module=load_worker)})
    bootstrap(output, nonce, action, source, windows_label=False)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--child', type=Path, required=True)
    ap.add_argument('--nonce', required=True)
    ap.add_argument('--action', choices=('intervals', 'compiled'), required=True)
    ap.add_argument('--source', type=Path, required=True)
    args = ap.parse_args()
    run(args.child.resolve(), args.nonce, args.action, args.source)
