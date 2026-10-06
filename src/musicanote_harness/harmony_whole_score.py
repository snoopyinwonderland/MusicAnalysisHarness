"""Research whole-score route: frozen old26 costs, explicit bounded beam.

This is NOT the sealed v1 graph/decoder. Computational pages propose spelling
banks; all original attack/release coordinates survive. A harmonic run and its
start survive pages. No page winner is committed. Beam loss is reported and
only a complete, independently rescored path can become a submission.
"""
from dataclasses import replace
from fractions import Fraction as F
from functools import lru_cache
import argparse
import gzip
import json
from pathlib import Path
from time import perf_counter
import traceback

from .harmony_test_a import MODEL, MODEL_SHA, digest, fraction as f, read_score, write, merge_spans
from .harmony_bounded_recovery import grace_projection, bound_evidence
from .harmony_source_clock import SourceClockGuard
from .harmony_scored_decoder import Problem, Edge, feature_cost, transition
from .harmony_full_score import Scorer, coefficients, applicability
from .harmony_member_timing import Scorer as IndexedScorer, ZERO
from .harmony_temporal_scoring import resolution_features
from .harmony_functional_scoring import six_four_surface
from .harmony_candidate_catalog import propose
from .harmony_candidate_recall import rational as q
from .harmony_progression_search import _hash

VERSION = 'frozen-old26-whole-score-beam-0.1.0'
CONFIG = {'beam_width': 8, 'page_cells': 12, 'operations': 2_000_000,
          'run_memo_entries': 8192, 'pilot_timeout_seconds': 60}


def model_weights():
    if digest(MODEL) != MODEL_SHA:
        raise ValueError('frozen_model_changed')
    model = json.loads(gzip.decompress(MODEL.read_bytes()))
    if model.get('production_deployment') is not False or model.get('source_labels_used_at_inference') is not False:
        raise ValueError('model_use_contract_changed')
    return coefficients({k: f(v) for k, v in model['weights'].items()})


class CellSearch:
    """Globally carried run states, approximate only when beam discards states."""
    def __init__(self, problem, ev, weights, *, beam_width=8, operations=2_000_000,
                 grace_notes=(), history_gate=None):
        if type(beam_width) is not int or beam_width < 1 or type(operations) is not int or operations < 1:
            raise ValueError('invalid_search_budget')
        self.problem, self.ev, self.weights = problem, ev, coefficients(weights)
        self.width, self.budget = beam_width, operations
        self.args = dict(grace_notes=grace_notes, history_gate=history_gate)
        # Existing indexed feature definitions, not substituted musical costs.
        self.index = IndexedScorer(problem, ev, ZERO, build_index=True, **self.args).index
        self.frontier = {(None, None): (F(), ())}
        self.at = self.operations = self.discarded = 0
        self.status = 'pending'
        self.ledger = {}
        self.run_cost = lru_cache(CONFIG['run_memo_entries'])(self._run_cost)
        self.pair_cost = lru_cache(CONFIG['run_memo_entries'])(self._pair_cost)
        self.change_cost = lru_cache(CONFIG['run_memo_entries'])(self._change_cost)

    def _run_cost(self, a, b, sig):
        values, _ = self.index.features(self.problem.points[a], self.problem.points[b], sig)
        values = applicability(values) | {'functional_role_complexity': F(int(six_four_surface(sig) is not None))}
        return feature_cost(values, self.weights)

    def _pair_cost(self, a, b, sig, next_sig):
        # Existing pair evidence depends on arrival, not the future raw edge end.
        values, _ = resolution_features(self.ev, self.problem.points[a], self.problem.points[b],
            self.problem.points[b+1], sig, next_sig)
        return feature_cost(values, self.weights)

    def _change_cost(self, previous, sig, attacks):
        edge = Edge('', 0, 1, F(), F(1), sig, {}, attacks, (), (), {})
        return feature_cost(transition(previous, edge), self.weights)

    def consume(self, edges):
        if self.status != 'pending':
            raise ValueError('terminal_search')
        i = self.at
        if not edges or any(e.start_index != i or e.end_index != i+1 for e in edges):
            raise ValueError('missing_or_nonatomic_cell')
        new = {}
        for e in edges:
            if e.group_id in self.ledger:
                raise ValueError('duplicate_edge')
            self.ledger[e.group_id] = e
            for (a, previous), (cost, ids) in self.frontier.items():
                if self.operations >= self.budget:
                    self.status = 'operation_budget_abstention'
                    return
                self.operations += 1
                start = a if previous == e.signature else i
                if previous == e.signature:
                    value = cost + self.run_cost(a, i+1, previous) - self.run_cost(a, i, previous)
                else:
                    value = cost + self.run_cost(i, i+1, e.signature)
                    if previous is not None:
                        value += self.change_cost(previous, e.signature, e.attack_spellings)
                        value += self.pair_cost(a, i, previous, e.signature)
                value += self.weights['blocker_exposure'] * e.features.get('blocker_exposure', F())
                key, candidate = (start, e.signature), (value, ids+(e.group_id,))
                if key not in new or candidate < new[key]:
                    new[key] = candidate
        ordered = sorted(new.items(), key=lambda kv: kv[1])
        self.discarded += max(0, len(ordered)-self.width)
        self.frontier = dict(ordered[:self.width])
        self.at += 1

    def finish(self):
        info = dict(status=self.status, operations=self.operations, cells_consumed=self.at,
                    beam_width=self.width, states_discarded=self.discarded,
                    exact_optimum_claimed=False, selected=None)
        if self.status != 'pending':
            return info
        if self.at != len(self.problem.points)-1:
            raise ValueError('partial_path_not_submission')
        cost, ids = min(self.frontier.values())
        graph = replace(self.problem, edges=tuple(self.ledger[i] for i in ids))
        original = Scorer(graph, self.ev, self.weights, **self.args)
        actual = original.score_path(ids)
        if actual != cost:
            raise ValueError('indexed_frozen_score_mismatch')
        return info | dict(status='complete', selected=ids, score_cost=str(cost),
                           independently_rescored=True)


def geometry(view, total):
    points = sorted({F(), total} |
        {f(s['span'][k]) for s in view['sounding_events'] for k in ('start', 'end') if 0 < f(s['span'][k]) < total} |
        {f(m['global_start_quarter']) for m in view['measures'] if 0 < f(m['global_start_quarter']) < total})
    # Pages remain within physical measures; meter changes/repeats are not lost.
    ends = {f(m['global_start_quarter'])+f(m['actual_duration_quarter']) for m in view['measures']}
    pages, lo = [], 0
    for hi in range(1, len(points)):
        if hi-lo >= CONFIG['page_cells'] or points[hi] in ends or hi == len(points)-1:
            pages.append((lo, hi)); lo = hi
    return tuple(points), pages


def infer(ir, total):
    original_sha = _hash(ir)
    clock = SourceClockGuard(ir)
    gate = clock.scope({'start': q(F()), 'end': q(total)})
    if not gate['accepted']:
        return [], dict(status='source_clock_abstention', source_clock_gate=gate)
    view, grace = grace_projection(ir)
    points, pages = geometry(view, total)
    span = {'start': q(F()), 'end': q(total)}
    _, ev, _ = bound_evidence(view, span, grace)
    total_note_time = sum((e.end-e.start for e in ev.source.events), F())
    if not total_note_time:
        return [], dict(status='no_positive_sounding_exposure')
    barriers = []
    for m in view['measures']:
        bar = m.get('repeat_barline') or {}
        if any(bar.get(k) for k in ('repeat_direction', 'ending_number')):
            barriers.append(f(m['global_start_quarter']) + (F() if bar.get('location') == 'left' else f(m['actual_duration_quarter'])))
    crosses = lambda a, b: any(a < t <= b for t in barriers)
    original_links = len(ev.links)
    ev.links = tuple((p, n) for p, n in ev.links if not crosses(p['start'], n['start']))
    ev.source.neighbors = {eid: pair for eid, pair in ev.source.neighbors.items()
                           if not crosses(pair[0]['start'], pair[1]['start'])}
    history = lambda a, b: not crosses(a, b)
    graph = Problem(points, (), len(points)-1, total_note_time, 'ready')
    search = CellSearch(graph, ev, model_weights(), beam_width=CONFIG['beam_width'],
        operations=CONFIG['operations'], grace_notes=grace['grace_note_events'], history_gate=history)
    page_info, previous_bank = [], {}
    sig_ids = {}
    for lo, hi in pages:
        page_span = {'start': q(points[lo]), 'end': q(points[hi])}
        catalog = propose(view, page_span, page_span)
        bank = {}
        for c in catalog['candidates']:
            for alt in c['spelling_alternatives']:
                sig = (None if alt['root_spelling'] is None else tuple(alt['root_spelling']),
                       tuple(sorted(map(tuple, alt['members']))))
                # Conservative union when several providers offer a spelling.
                # Provider abstention is not silently declared resolved.
                bank[sig] = bank.get(sig, frozenset()) | frozenset(c['abstention_reasons'])
        # A sparse/empty page can carry an already proposed spelling; no pitch
        # or performed timing is invented. No source note is dropped.
        if not bank:
            bank = previous_bank.copy()
        if not bank:
            return [], dict(status='no_context_candidates', cells_consumed=search.at)
        previous_bank = bank.copy()
        page_info.append(dict(start=str(points[lo]), end=str(points[hi]), signatures=len(bank),
                              catalog_sha256=_hash(catalog)))
        for i in range(lo, hi):
            choices = dict(bank)
            for _, sig in search.frontier:
                if sig is not None and sig not in choices:
                    choices[sig] = frozenset(catalog['providers']['base']['abstention_reasons'])
            active = [e for e in ev.source.events if e.start < points[i+1] and points[i] < e.end]
            attacks = frozenset(e.pitch for e in active if e.start == points[i] and e.pitch is not None)
            edges = []
            exposure = sum((min(e.end, points[i+1])-max(e.start, points[i]) for e in active), F())
            for sig in sorted(choices, key=repr):
                sig_ids.setdefault(sig, _hash(sig)[:20])
                gid = f'whole_{i:06d}_{sig_ids[sig]}'
                blockers = tuple(sorted(choices[sig]))
                features = {'blocker_exposure': exposure/total_note_time if blockers else F()}
                edges.append(Edge(gid, i, i+1, points[i], points[i+1], sig, features, attacks,
                    tuple(sorted(e.event_id for e in active)), blockers, {'proposal_page': len(page_info)-1}))
            search.consume(edges)
            if search.status != 'pending':
                break
        if search.status != 'pending':
            break
    result = search.finish()
    details = {k: v for k, v in result.items() if k != 'selected'}
    details.update(version=VERSION, model_sha256=MODEL_SHA, config=CONFIG, page_inventory=page_info,
        source_labels_used=False, core_modified=False, calibrated_confidence=False,
        candidate_policy='page_union_spelling_bank_on_original_atomic_grid_plus_live_continuations',
        graph_changed_from_v1=True, weights_changed=False, local_winner_stitching=False,
        provider_blockers_preserved=True, repeat_voice_links_withheld=original_links-len(ev.links),
        source_ir_sha256=original_sha,
        repeat_policy='notated_order_unfolding_disabled_voice_links_across_repeat_withheld')
    if _hash(ir) != original_sha:
        raise ValueError('canonical_core_mutated')
    if result['status'] != 'complete':
        return [], details
    details['selected_path'] = [dict(start=str(search.ledger[gid].start), end=str(search.ledger[gid].end),
        signature=search.ledger[gid].signature, source_event_ids=search.ledger[gid].source_event_ids,
        blockers=search.ledger[gid].blockers, proposal_page=search.ledger[gid].adapter['proposal_page'])
        for gid in result['selected']]
    output = []
    notes = {s['sounding_event_id']: s for s in ir['sounding_events']}
    natural = dict(zip('CDEFGAB', (0, 2, 4, 5, 7, 9, 11)))
    pc = lambda token: (natural[token[0]]+token[1]) % 12
    for gid in result['selected']:
        e = search.ledger[gid]
        if e.signature[0] is None or not e.source_event_ids:
            continue  # augmented tonic coordinate / silence isn't a tertian root
        members = sorted({pc(t) for t in e.signature[1]})
        active = [notes[sid]['pitch'].get('midi_pitch') for sid in e.source_event_ids]
        bass = min(p for p in active if p is not None) % 12 if any(p is not None for p in active) else None
        output.append(dict(start=str(e.start), end=str(e.end), root_pc=pc(e.signature[0]), pcs=members,
                           bass_pc=bass if bass in members else None))
    return merge_spans(output), details


def worker(source, output):
    t = perf_counter()
    try:
        sha = digest(source)
        ir, total, removed = read_score(source)
        parsed = perf_counter()-t
        spans, info = infer(ir, total)
        if digest(source) != sha:
            raise ValueError('source_changed')
        Path(output).with_suffix('.ir.json.gz').write_bytes(gzip.compress(
            json.dumps(ir, ensure_ascii=False, separators=(',', ':')).encode('utf-8'), mtime=0))
        result = dict(source_file=str(source), source_sha256=sha, score_duration=str(total),
            parse_seconds=parsed, seconds=perf_counter()-t, harmony_elements_removed=removed,
            spans=spans, **info)
    except Exception as exc:
        result = dict(status='error', error=f'{type(exc).__name__}: {exc}',
                      traceback=traceback.format_exc(), seconds=perf_counter()-t, spans=[])
    write(output, result)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--worker', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    worker(args.worker, args.output)
