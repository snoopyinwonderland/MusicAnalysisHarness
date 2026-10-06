"""Fresh ordinary Train winners, not a loss-augmented or gold inference API.

Reuse the sealed run-aware decoder and original candidate points/edge cap.
Old Train graphs lack some measure boundaries required by the prefix index;
direct original-source features avoid inventing points or changing the score.
"""
from fractions import Fraction as F

from . import harmony_member_timing as timing
from .harmony_temporal_scoring import bind
from .harmony_structured_learning import compatible_problem, content_hash
from .harmony_margin_learning import training_loss, path_loss
from .harmony_scored_decoder import feature_cost

VERSION = 'harmony-fresh-train-negatives-0.1.0'
ARMS = ('support_calibrated', 'timing_calibrated')
BUDGET = 2_000_000
BOUNDARY_WEIGHT = F(1, 4)
q, f = timing.support.q, timing.support.f


def direct_scorer(problem, ev, weights, **args):
    """No index/grid mutation; the original reconstruction checks the winner."""
    scorer = timing.Scorer(problem, ev, weights, build_index=False, **args)
    class DirectOriginalEvents:
        def __init__(self, graph, source): self.graph, self.source = graph, source
        def features(self, a, b, sig):
            base, receipts = scorer.base_run(self.graph, self.source, a, b, sig)
            extra, details = scorer.member_features(self.graph, self.source, a, b, sig)
            return base | extra, receipts + details
    scorer.chosen = bind(scorer.chosen, {'RunIndex': DirectOriginalEvents})
    return scorer


def path_ids(selected):
    return tuple(s['semantic_group_ref'] for s in selected['segments'])


def reachable_target(problem, cells):
    """Oracle representation ceiling ONLY, not a prediction or accuracy."""
    gold, reason = compatible_problem(problem, cells)
    if reason: return None, {'reachable': None, 'reason': reason, 'minimum_raw_edges': None}
    minimum = [None] * len(gold.points); minimum[0] = 0
    outgoing = [[] for _ in gold.points]
    for e in gold.edges: outgoing[e.start_index].append(e)
    for i, count in enumerate(minimum):
        if count is None: continue
        for e in outgoing[i]:
            value = count + 1
            if minimum[e.end_index] is None or value < minimum[e.end_index]: minimum[e.end_index] = value
    n = minimum[-1]
    reason = ('no_compatible_path_in_original_graph' if n is None else
              'raw_segment_cap_blocks_reference' if n > gold.max_segments else None)
    return gold, {'reachable': reason is None, 'reason': reason, 'minimum_raw_edges': n,
        'compatible_edges': len(gold.edges), 'original_edges': len(problem.edges),
        'max_raw_edges': problem.max_segments, 'gold_candidates_injected': False}


def target_choice(gold, ev, weights, **args):
    """TRAIN ONLY latent compatible target; must never be displayed as analysis."""
    result = direct_scorer(gold, ev, weights, **args).decode(transition_budget=BUDGET)
    if result['selected'] is not None:
        result['selected'].update(source_labels_used_for_selection=True,
            training_reference_labels_used=True, target_only=True)
    return result


def path_receipt(scorer, ids, *, target=False):
    features, available = scorer.path_features(ids)
    return {'existing_path_ids': ids, 'base_cost': q(scorer.base_cost(ids)),
        'cost': q(scorer.score_path(ids)), 'features': {k: q(v) for k, v in features.items()},
        'availability': available, 'source_labels_used_to_create_this_path': target,
        'source_support': [d for a, b, sig in timing.support.completed_runs(scorer.problem, ids)
            for d in scorer.member_features(scorer.problem, scorer.ev.source, a, b, sig)[1]]}


def contrast(sample, entry, graph, ev, cells, negative, target, weights, **args):
    """Keep unavailable features and positive-loss collisions, never hide them."""
    nids, tids = path_ids(negative), path_ids(target)
    gold, ceiling = reachable_target(graph, cells)
    if not ceiling['reachable']: raise ValueError('fresh_target_not_reachable')
    if not set(tids) <= {e.group_id for e in gold.edges}: raise ValueError('fresh_target_not_compatible')
    loss = training_loss(graph, cells, BOUNDARY_WEIGHT)
    nloss = path_loss(graph, {'selected': negative}, loss)
    tloss = path_loss(graph, {'selected': target}, loss)
    if f(tloss['total']) != 0: raise ValueError('fresh_target_has_positive_loss')
    if f(nloss['total']) <= 0: raise ValueError('fresh_negative_requires_positive_loss')
    scorer = direct_scorer(graph, ev, weights, **args)
    nf, na = scorer.path_features(nids); tf, ta = scorer.path_features(tids)
    delta = {k: nf[k]-tf[k] for k in timing.FEATURES}
    base_gap = scorer.base_cost(nids)-scorer.base_cost(tids)
    scored_gap = scorer.score_path(nids)-scorer.score_path(tids)
    if base_gap + feature_cost(delta, weights) != scored_gap: raise ValueError('fresh_contrast_score_gap_mismatch')
    if (q(scorer.score_path(nids)) != negative['score_cost']
            or q(scorer.score_path(tids)) != target['score_cost']): raise ValueError('fresh_selection_cost_mismatch')
    return {'contrast_id': content_hash([sample, nids, tids]), 'sample_id': sample, 'entry': entry,
        'negative_ids': nids, 'target_ids': tids, 'loss_details': nloss, 'loss': nloss['total'],
        'feature_delta': {k: q(v) for k, v in delta.items()},
        'feature_available': {k: na[k] and ta[k] for k in timing.FEATURES},
        'negative_features': {k: q(v) for k, v in nf.items()},
        'target_features': {k: q(v) for k, v in tf.items()},
        'base_cost_gap': q(base_gap), 'current_score_gap': q(scored_gap),
        'positive_loss_feature_collision': not any(delta.values()),
        'negative_kind': 'ordinary_current_joint_winner_not_loss_augmented',
        'source_labels_used_for_negative_selection': False, 'training_reference_labels_used_for_target': True,
        'train_feature_backend': 'direct_original_events_no_graph_point_insertion'}
