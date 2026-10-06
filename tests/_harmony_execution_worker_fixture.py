"""Stdlib-only fixture; writes evidence before optionally waiting past deadline."""
import argparse
import json
import os
from pathlib import Path
import time

ap = argparse.ArgumentParser()
ap.add_argument('--output', type=Path, required=True)
ap.add_argument('--nonce', required=True)
ap.add_argument('--mode', required=True)
args = ap.parse_args()
sequence = 0


def emit(event):
    global sequence
    value = dict(nonce=args.nonce, sequence=sequence, event=event,
                 clock_ns=time.perf_counter_ns(), pid=os.getpid(), parent_pid=os.getppid())
    with (args.output/'events.jsonl').open('a', encoding='utf-8') as handle:
        handle.write(json.dumps(value)+'\n')
    sequence += 1


emit('bootstrap_enter')
emit('module_load_begin')
emit('module_loaded')
emit('worker_begin')
if args.mode == 'malformed':
    (args.output/'worker.json').write_bytes(b'{"status": "complete"')
else:
    value = dict(status='complete' if args.mode != 'partial_wait' else 'partial',
                 fixture=True, notes_preserved=[60, 62, 64])
    (args.output/'worker.json').write_text(json.dumps(value), encoding='utf-8')
emit('worker_returned')
if args.mode == 'foreign':
    with (args.output/'events.jsonl').open('a', encoding='utf-8') as handle:
        handle.write(json.dumps(dict(nonce='foreign', sequence=sequence))+'\n')
if args.mode in ('complete_wait', 'partial_wait'):
    time.sleep(30)

