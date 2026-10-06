"""Exact NCT overlap lookup and static-input Voice context performance adapter.

No new role labels, weights, candidates, search budgets or score semantics.
The unmodified stage99 full direct scorer still audits every completed winner.
"""
import argparse
from bisect import bisect_left
from functools import lru_cache
import json
from pathlib import Path
from types import SimpleNamespace

from . import harmony_whole_score_phases as phases
from .harmony_whole_score_compiled import CompiledSearch
from .harmony_context_input import read_score
from .harmony_phase_checkpoint import AtomicTelemetry
from .harmony_test_a import write
from .harmony_window_workspace import bind

VERSION = 'local-beat-whole-score-supported-domain-0.2.3-intervals'


class PatternIntervals:
    """Exact half-open overlap, retaining original pattern order and duplicates.

    For source-grid queries, integer order statistics and a max-end tree skip
    intervals which provably cannot meet the original two inequalities. No
    rounding. Non-grid input or missing endpoints uses the original predicate.
    """
    def __init__(self, patterns, points):
        self.patterns = tuple(patterns)
        self.position = {t: i for i, t in enumerate(points)}
        self.indexed = all(row[0].start in self.position and row[0].end in self.position
                           for row in self.patterns)
        rows = sorted((self.position[row[0].start], i, self.position[row[0].end])
                      for i, row in enumerate(self.patterns)) if self.indexed else []
        self.starts = tuple(row[0] for row in rows)
        self.original = tuple(row[1] for row in rows)
        self.size = 1 << max(0, (len(rows) - 1).bit_length())
        self.ends = [-1] * (2 * self.size)
        for i, row in enumerate(rows):
            self.ends[self.size + i] = row[2]
        for i in range(self.size - 1, 0, -1):
            self.ends[i] = max(self.ends[2 * i], self.ends[2 * i + 1])

    def query(self, a, b):
        if not self.indexed or a not in self.position or b not in self.position:
            return tuple(row for row in self.patterns if row[0].start < b and a < row[0].end)
        ai, bi = self.position[a], self.position[b]
        limit = bisect_left(self.starts, bi)
        stack, found = [(1, 0, self.size)], []
        while stack:
            node, lo, hi = stack.pop()
            if lo >= limit or self.ends[node] <= ai:
                continue
            if hi - lo == 1:
                found.append(self.original[lo])
            else:
                mid = (lo + hi) // 2
                stack.extend(((2 * node, lo, mid), (2 * node + 1, mid, hi)))
        return tuple(self.patterns[i] for i in sorted(found))


class IntervalSearch(CompiledSearch):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pattern_index = PatternIntervals(self.index.patterns, self.problem.points)
        self.index.domain = lru_cache(8192)(self.pattern_index.query)


infer_phases = bind(phases.infer, {
    'fast': SimpleNamespace(FastSearch=IntervalSearch, VERSION=VERSION)})


def infer(ir, total):
    return infer_phases(ir, total, AtomicTelemetry())


def worker(source, output):
    receipt = {}
    run = bind(phases.worker, {'infer': infer_phases, 'Telemetry': AtomicTelemetry,
        'read_score': lambda path: read_score(path, receipt=receipt)})
    run(source, output)
    result = json.loads(Path(output).read_text(encoding='utf-8'))
    result['input_lookup'] = receipt
    write(output, result)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--worker', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    worker(args.worker, args.output)
