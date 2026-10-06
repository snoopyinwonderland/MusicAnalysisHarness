"""Post-hoc fixed-path diagnosis, never an inference or gold-label adapter.

Replays sealed paths. A PC-only baseline may be projected to a unique
source-spelled template for COUNTERFACTUAL scoring, not injected in a decoder.
Lower counterfactual cost cannot distinguish candidate omission from beam loss.
"""
from collections import Counter
from fractions import Fraction as F
import gzip
import json
from pathlib import Path

from .harmony_bounded_recovery import grace_projection, bound_evidence
from .harmony_candidate_recall import rational as q
from .harmony_full_score import Scorer
from .harmony_functional_scoring import shapes
from .harmony_progression_search import _hash
from .harmony_scored_decoder import Problem, Edge, feature_cost
from .harmony_test_a import fraction as f
from .harmony_whole_score import geometry, model_weights
from .seventh_context import chord, QUALITIES

VERSION = 'sealed-whole-score-path-diagnosis-0.1.0'
NATURAL = dict(zip('CDEFGAB', (0, 2, 4, 5, 7, 9, 11)))


def signature(raw):
    return (None if raw[0] is None else tuple(raw[0]), tuple(map(tuple, raw[1])))


def pc(token):
    return (NATURAL[token[0]] + token[1]) % 12


def evidence(ir, total):
    """Exactly the sealed consumer projection and repeat-history policy."""
    view, grace = grace_projection(ir)
    points, pages = geometry(view, total)
    _, ev, _ = bound_evidence(view, {'start': q(0), 'end': q(total)}, grace)
    barriers = []
    for m in view['measures']:
        bar = m.get('repeat_barline') or {}
        if any(bar.get(k) for k in ('repeat_direction', 'ending_number')):
            barriers.append(f(m['global_start_quarter']) +
                (F() if bar.get('location') == 'left' else f(m['actual_duration_quarter'])))
    crosses = lambda a, b: any(a < t <= b for t in barriers)
    ev.links = tuple((p, n) for p, n in ev.links if not crosses(p['start'], n['start']))
    ev.source.neighbors = {eid: pair for eid, pair in ev.source.neighbors.items()
                          if not crosses(pair[0]['start'], pair[1]['start'])}
    args = dict(grace_notes=grace['grace_note_events'], history_gate=lambda a, b: not crosses(a, b))
    return ev, points, pages, args


def graph(ev, points, path):
    if len(path) != len(points)-1:
        raise ValueError('incomplete_replay_path')
    total_note_time = sum((e.end-e.start for e in ev.source.events), F())
    edges = []
    for i, row in enumerate(path):
        a, b = points[i:i+2]
        if (f(row['start']), f(row['end'])) != (a, b):
            raise ValueError('changed_atomic_geometry')
        active = [e for e in ev.source.events if e.start < b and a < e.end]
        refs = tuple(sorted(e.event_id for e in active))
        if tuple(sorted(row['source_event_ids'])) != refs:
            raise ValueError('changed_source_event_refs')
        exposure = sum((min(e.end,b)-max(e.start,a) for e in active), F())
        blocked = tuple(row['blockers'])
        edges.append(Edge(f'replay_{i}', i, i+1, a, b, signature(row['signature']),
            {'blocker_exposure': exposure/total_note_time if blocked else F()},
            frozenset(e.pitch for e in active if e.start == a and e.pitch is not None),
            refs, blocked, {}))
    return Problem(points, tuple(edges), len(edges), total_note_time, 'ready')


def runs(problem):
    result = []
    for e in problem.edges:
        if result and result[-1][2] == e.signature:
            result[-1] = (result[-1][0], e.end, e.signature)
        else:
            result.append((e.start, e.end, e.signature))
    return result


def fixed_receipt(problem, ev, args, weights):
    sc = Scorer(problem, ev, weights, **args)
    ids = tuple(e.group_id for e in problem.edges)
    values, available = sc.path_features(ids)
    cost = sc.score_path(ids)
    if cost != feature_cost(values, weights):
        raise ValueError('receipt_cost_mismatch')
    unavailable = Counter()
    shapes_count = Counter()
    for a,b,sig in runs(problem):
        base, _ = sc.source_scorer.base_run(problem, ev.source, a,b,sig)
        member, _ = sc.source_scorer.member_features(problem, ev.source, a,b,sig)
        unavailable.update(k for k,v in (base|member).items() if v is None)
        shapes_count['ordinary_triads_or_sevenths' if shapes(sig) else 'other_shape'] += 1
    return dict(cost=str(cost), run_count=len(runs(problem)),
        feature_values={k:str(v) for k,v in values.items()},
        term_costs={k:str(v*weights[k]) for k,v in values.items()},
        aggregate_availability=available, unavailable_runs=dict(unavailable), shape_runs=dict(shapes_count),
        unknown_cost_policy='old_policy_omits_unknown_not_observed_zero')


def spelling_options(ev, root_pc, pcs):
    """No key guessing: observed root spellings plus exact tertian templates."""
    roots = {e.pitch for e in ev.source.events if e.pitch is not None and pc(e.pitch) == root_pc}
    options = set()
    for root in roots:
        for quality in QUALITIES:
            members = tuple(sorted(map(tuple, chord(root,quality)['members'])))
            if {pc(p) for p in members} == set(pcs):
                options.add((root,members))
    return sorted(options, key=repr)


def project_baseline(path, spans, ev):
    """Strict diagnostic projection; reject ambiguous spelling/timing.

    Silent cells keep the sealed signature. Unknown active cells are not filled.
    Original blockers remain. Candidate-policy reachability is NOT assumed.
    """
    projected, issues = [], []
    cache = {}
    silent = 0
    for i,row in enumerate(path):
        a,b = f(row['start']), f(row['end'])
        intervals = [s for s in spans if f(s['start']) < b and a < f(s['end'])]
        if not row['source_event_ids']:
            projected.append(dict(row)); silent += 1; continue
        labels = {(s['root_pc'], tuple(sorted(s['pcs']))) for s in intervals}
        covered = sum((min(b,f(s['end']))-max(a,f(s['start'])) for s in intervals), F())
        if covered != b-a or len(labels) != 1:
            issues.append(dict(cell=i,start=str(a),end=str(b),issue='gap_or_label_change_inside_atomic_cell'))
            continue
        label = next(iter(labels))
        if label not in cache: cache[label] = spelling_options(ev,*label)
        options = cache[label]
        if len(options) != 1:
            issues.append(dict(cell=i,start=str(a),end=str(b),issue='nonunique_or_unsupported_source_spelling',options=len(options)))
            continue
        projected.append(dict(row,signature=options[0]))
    return (None if issues else projected), dict(issues=issues, silent_cells_preserved=silent,
        graph_reachability='unverified_counterfactual_not_original_decoder_path',
        source_spelling_policy='unique_observed_root_and_exact_tertian_template')


def local_support(problem, ev, pages):
    """Observations only: pooling or absence does not prove a harmonic boundary."""
    output = []
    for a,b,sig in runs(problem):
        rows = []
        for lo,hi in pages:
            x,y=max(a,problem.points[lo]),min(b,problem.points[hi])
            if x >= y:continue
            observed={e.pitch for e in ev.source.events if e.start < y and x < e.end and e.pitch is not None}
            rows.append(dict(start=str(x),end=str(y),root_observed=sig[0] in observed,
                observed_member_count=len(set(sig[1])&observed),
                missing_spellings=sorted(set(sig[1])-observed)))
        output.append(dict(start=str(a),end=str(b),signature=sig, pages=rows,
            absence_forces_boundary=False, pooled_presence_confirms_harmony=False))
    return output


def diagnose(job_file, baseline_file):
    job_file, baseline_file = Path(job_file), Path(baseline_file)
    job=json.loads(job_file.read_text(encoding='utf-8'))
    baseline=json.loads(baseline_file.read_text(encoding='utf-8'))
    if job['status'] != 'complete' or baseline['status'] != 'complete':
        raise ValueError('completed_paired_paths_required')
    ir=json.loads(gzip.decompress(job_file.with_suffix('.ir.json.gz').read_bytes()))
    if _hash(ir) != job['source_ir_sha256']:
        raise ValueError('saved_ir_changed')
    if job['source_sha256'] != baseline['source_sha256'] or job['score_duration'] != baseline['score_duration']:
        raise ValueError('paired_sources_differ')
    before=_hash(ir)
    ev,points,pages,args=evidence(ir,f(job['score_duration']))
    weights=model_weights()
    problem=graph(ev,points,job['selected_path'])
    selected=fixed_receipt(problem,ev,args,weights)
    if f(selected['cost']) != f(job['score_cost']):
        raise ValueError('sealed_selected_cost_changed')
    projected, projection=project_baseline(job['selected_path'],baseline['spans'],ev)
    other=None if projected is None else fixed_receipt(graph(ev,points,projected),ev,args,weights)
    if _hash(ir) != before:raise ValueError('source_mutated')
    return dict(version=VERSION,title=job['title'], source_ir_sha256=before,
        selected=selected, baseline_counterfactual=other, projection=projection,
        counterfactual_lower_cost=None if other is None else f(other['cost'])<f(selected['cost']),
        local_support=local_support(problem,ev,pages), source_labels_used=False,
        new_inference=False, weights_changed=False, production_enabled=False,
        diagnosis_limit='lower_counterfactual_cost_does_not_separate_candidate_loss_from_beam_loss')
