"""Mine real wrong competitors for correct Train paths; no fitting or Dev use."""
import argparse
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
import json
from pathlib import Path
from time import perf_counter

from . import harmony_joint_balance_trial as prior
from . import harmony_context_refresh_trial as refresh
from . import harmony_train_protection_search as search

VERSION = 'harmony-train-protection-trial-0.1.0'
ROOT = Path('K:/Music Analysis/output/harmony-joint-balance-2026-10-05-r1')
PINS = {
    'report.json': 'd95ef8ed4d63968c752774db705e1b8472c77e67a5b7cfa09efbd36242929358',
    'post-seal-audit.json': 'a8ca0d6efb86f08d54fa7d1cd5c601e4e1353883f34315da361d2cacb133f51d',
    'training-vectors.json.gz': 'a70a4e6a94a639622afc3255c70f0f6623c829744576e44d5fa3784b0072818c',
}
s, io, load, same_json = prior.s, prior.io, prior.load, prior.same_json
learning, ledger = prior.learning, prior.ledger
WALL_SECONDS = 20


def configuration():
    return dict(search='exact_cheapest_positive_semantic_loss_path',
        score='sealed_stage83_member_role35', target='existing_reference_compatible_train_path',
        protect='all_original_zero_loss_scopes_and_stage83_stage85_correct_scopes',
        retained_union_runs=3, additional_state='monotone_semantic_error_bit',
        positive_loss_is_not_loss_augmented_score=True, same_original_graph_and_raw_cap=True,
        transition_budget=s.fresh.BUDGET, wall_seconds_per_scope=WALL_SECONDS,
        retries=0, partial_winner=False, fit=False, dev=False, production=False,
        original_noop_rows='preserved_inactive_not_counted_as_effective_protection',
        deduplication='new_competitor_semantic_runs_against_existing_positive_pool',
        unknown_policy='whole_unknown_gradient_null_known_partial_cost_preserved')


def context(read):
    report, audit, vectors = [read(ROOT/n, h) for n, h in PINS.items()]
    if (report['complete'] is not True or audit['passed'] is not True
            or audit['report_sha256'] != PINS['report.json']
            or report['current_dev_reconstructed_or_used'] is not False
            or report['operational_weights_changed'] is not False):
        raise ValueError('protection_parent_not_sealed_train')
    for p, h in (report['input_hashes'] | report['artifact_hashes'] | report['code_hashes']).items():
        read(p, h, raw=True)
    ctx = prior.context(read)
    rows, _ = prior.collect(ctx)
    if not same_json(rows, vectors['rows']) or report['cohort'] != [r['sample_id'] for r in ctx['rows']]:
        raise ValueError('protection_parent_vectors_or_cohort_changed')
    ctx['pool'] = rows; ctx['joint_report'] = report
    ctx['joint_records'] = {r['sample_id']: r for r in report['records']}
    return ctx


def inventory(ctx):
    inert = [r for r in ctx['pool'] if s.f(r['loss']) == 0]
    if any(r['negative_ids'] != r['target_ids'] or any(s.f(v) for v in r['score_delta'].values())
           or any(s.f(v) for v in r['gradient_delta'].values() if v is not None) for r in inert):
        raise ValueError('protection_original_zero_rows_not_inert')
    protected = {}
    for row in inert:
        sample = row['sample_id']
        if sample in protected:
            raise ValueError('protection_duplicate_original_scope')
        protected[sample] = ['original_zero_loss']
    for name, records in (('stage83_correct', ctx['previous_records']), ('stage85_correct', ctx['joint_records'])):
        for sample, row in records.items():
            if row['evaluation']['selected_hit'] is True:
                protected.setdefault(sample, []).append(name)
    allowed = {r['sample_id'] for r in ctx['rows'] if r['split'] == 'train'}
    if not set(protected) <= allowed or len(allowed) != len(ctx['rows']):
        raise ValueError('protection_nontrain_or_duplicate_scope')
    return inert, protected


def semantic_key(graph, ids):
    return tuple(search.base.context_features.control.completed_runs(graph, ids))


def vector(entry, sample, negative, target, loss, source_sha, weights):
    if (negative['source_labels_used'] is not False or target['source_labels_used'] is not False
            or negative['target_path_created_using_labels'] is not False
            or target['target_path_created_using_labels'] is not True or s.f(loss['total']) <= 0):
        raise ValueError('protection_contrast_requires_wrong_and_label_free_features')
    diff = ledger.compare(negative, target, weights); terms = diff['terms']
    ids, targets = list(negative['existing_path_ids']), list(target['existing_path_ids'])
    row = dict(entry=deepcopy(entry), sample_id=sample,
        contrast_id='protect_'+learning.use.content_hash([sample, ids, targets])[:24],
        negative_ids=ids, target_ids=targets, loss=loss['total'],
        source_arm='stage87_train_only_cheapest_wrong_not_prediction',
        source_ir_content_sha256=source_sha,
        score_delta={k: terms[k]['scored_partial_delta'] for k in learning.FEATURES},
        gradient_delta={k: terms[k]['value_delta'] for k in learning.FEATURES},
        available={k: terms[k]['known_both'] for k in learning.FEATURES},
        features_use_source_labels=False, target_created_using_training_reference=True,
        negative_selection_used_training_labels=True, analysis_export_allowed=False)
    if learning.gap(row, weights) != s.f(diff['left_minus_right_cost']):
        raise ValueError('protection_vector_gap_changed')
    return row, diff


def diagnostic(row, weights):
    gap = learning.gap(row, weights); violation = s.f(row['loss'])-gap
    box = learning.bounds(weights)
    # Upper bound only on jointly-known trainable dimensions; unknowns stay fixed.
    attainable = gap
    for k in learning.TRAINABLE:
        if row['available'][k]:
            g = s.f(row['gradient_delta'][k]); low, high = box[k]
            attainable += max((low-weights[k])*g, (high-weights[k])*g)
    return dict(gap=s.q(gap), required_margin=row['loss'], violation=s.q(violation),
        margin_satisfied=violation <= 0, wrong_cheaper_than_stored_target=gap < 0,
        known_nonzero_trainable_gradient=any(row['available'][k]
            and s.f(row['gradient_delta'][k]) for k in learning.TRAINABLE),
        maximum_gap_under_same_trust_box_known_gradient=s.q(attainable),
        individual_margin_possible_under_same_trust_box=attainable >= s.f(row['loss']),
        individual_feasibility_is_not_joint_fit_or_accuracy=True)


def run(output):
    output = Path(output)
    if output.exists():
        raise ValueError('output_exists_no_overwrite')
    begun = perf_counter(); inputs, artifacts = {}, {}
    def read(p, expected=None, compressed=False, raw=False):
        p = Path(p); name = str(p.resolve()); h = io.digest(p)
        if (expected is not None and expected != h) or (name in inputs and inputs[name] != h):
            raise ValueError('protection_input_changed:'+name)
        inputs[name] = h
        return None if raw else load(p)
    ctx = context(read); inert, protected = inventory(ctx)
    code = {str(p.resolve()): io.digest(p) for p in Path(__file__).parent.glob('*.py')}
    for n in ('tests/test_harmony_train_protection_search.py', 'tests/test_harmony_train_protection_trial.py',
              'scripts/validate_harmony_train_protection.py', 'scripts/audit_harmony_train_protection.py'):
        p = Path(n); code[str(p.resolve())] = io.digest(p)
    output.mkdir(parents=True); (output/'cases').mkdir()
    def save(p, value, compressed=False):
        p = output/p; (io.write_packet if compressed else io.write)(p, value)
        name = str(p.resolve()); artifacts[name] = io.digest(p); return name, artifacts[name]
    contract = dict(version=VERSION, configuration=configuration(),
        cohort=[r['sample_id'] for r in ctx['rows']], protected_scopes=protected,
        original_inert_contrasts=len(inert), parent_train_report_sha256=PINS['report.json'],
        frozen_model_sha256=prior.ROLE_PINS['model.json.gz'],
        frozen_weights={k: s.q(v) for k, v in ctx['initial35'].items()}, code_pins=code,
        use_contract_sha256=learning.use.content_hash(ctx['use']),
        purpose='local_noncommercial_research', fit_performed=False,
        current_dev_reconstructed_or_used=False, operational_weights_changed=False,
        production_modified=False, historical_parent_containers_include_exposed_dev=True)
    save(Path('run-contract.json'), contract)
    save(Path('inactive-original-noops.json.gz'), {'rows': inert, 'history_preserved': True}, True)
    active = [deepcopy(r) for r in ctx['pool'] if s.f(r['loss']) > 0]
    learning.validate_rows(active, ctx['use'], ctx['manifest'], ctx['parent_sha'])
    counts = Counter(); records = []; sources = set(); edges = projections = 0
    for row in ctx['rows']:
        sample = row['sample_id']
        if sample not in protected:
            records.append({k: row[k] for k in refresh.FIELDS} | {
                'attempted': False, 'status': 'not_a_protection_scope_no_new_search', 'reasons': []})
            counts['unattempted_original_scopes_preserved'] += 1; continue
        saved, entry, graph, ev, clock, args = prior.prior.prior.old.prior.prepare_sample(ctx, row, read)
        sc = prior.Scorer(graph, ev, ctx['initial35'], **args)
        target_ids = next((r['target_ids'] for r in inert if r['sample_id'] == sample),
            ctx['joint_packets'][sample]['arms']['epoch3_target']['path_ids'])
        loss = refresh.loss_object(graph, ctx['refs'][sample])
        target_loss = refresh.loss_for_ids(graph, loss, target_ids)
        if s.f(target_loss['total']) != 0:
            raise ValueError('protection_stored_target_not_reference_compatible')
        target = sc.path_receipt(target_ids, target=True)
        projections += prior.prior.verify_projection(sc, target_ids, target)
        result = search.decode(sc, loss, wall_seconds=WALL_SECONDS)
        competitor, comparison, metrics, duplicate = None, None, None, None
        if result['path_ids'] is not None:
            ids = result['path_ids']; negative = result['receipt']
            projections += prior.prior.verify_projection(sc, ids, negative)
            competitor, comparison = vector(entry, sample, negative, target,
                result['training_loss'], saved['source_ir_content_sha256'], ctx['initial35'])
            if semantic_key(graph, ids) == semantic_key(graph, target_ids):
                raise ValueError('protection_semantically_identical_competitor')
            metrics = diagnostic(competitor, ctx['initial35'])
            key = semantic_key(graph, ids), semantic_key(graph, target_ids)
            duplicate = next((r['contrast_id'] for r in active if r['sample_id'] == sample
                and (semantic_key(graph, r['negative_ids']), semantic_key(graph, r['target_ids'])) == key), None)
            if duplicate is None:
                active.append(competitor); counts['new_positive_protection_rows'] += 1
            else:
                counts['linked_existing_positive_rows_not_reweighted'] += 1
            counts['positive_wrong_competitors'] += 1
            for name in ('margin_satisfied', 'wrong_cheaper_than_stored_target',
                         'known_nonzero_trainable_gradient', 'individual_margin_possible_under_same_trust_box'):
                counts[name] += bool(metrics[name])
        counts['attempted_protection_scopes'] += 1; counts[result['status']] += 1
        packet = {k: saved[k] for k in refresh.SOURCE_FIELDS} | dict(
            reasons=protected[sample], target_ids=target_ids, target_receipt=target,
            target_loss=target_loss, result=result, vector=competitor, comparison=comparison,
            diagnostic=metrics, duplicate_existing_contrast_id=duplicate,
            human_validated=False, full_source_not_clipped=True, source_labels_used_for_features=False)
        p, h = save(Path('cases')/(sample+'.json.gz'), packet, True)
        records.append({k: row[k] for k in refresh.FIELDS} | dict(attempted=True,
            artifact=p, sha256=h, status=result['status'], reasons=protected[sample],
            diagnostic=metrics, duplicate_existing_contrast_id=duplicate))
        sources.add(ev.source.source_ir_content_sha256); edges += len(graph.edges)
        refresh.clear(ev, clock)
        print(f'[Train protection {counts["attempted_protection_scopes"]}/{len(protected)}] '
              f'{sample}: {result["status"]}', flush=True)
    active.sort(key=lambda r: (r['entry']['work_family_id'], r['sample_id'], r['contrast_id']))
    learning.validate_rows(active, ctx['use'], ctx['manifest'], ctx['parent_sha'])
    save(Path('training-vectors.json.gz'), dict(rows=active, counts=dict(counts),
        original_positive_rows_retained=len(ctx['pool'])-len(inert), inactive_original_noops=len(inert)), True)
    for p, h in (inputs | artifacts | code).items():
        if io.digest(p) != h:
            raise ValueError('protection_final_seal_changed:'+p)
    report = contract | dict(complete=True, counts=dict(counts), active_contrasts=len(active),
        original_positive_rows_retained=len(ctx['pool'])-len(inert), records=records,
        full_source_packages=len(sources), original_edges=edges,
        scalar_detailed_transitions_compared=projections,
        input_hashes=inputs, artifact_hashes=artifacts, code_hashes=code,
        elapsed_seconds=perf_counter()-begun, music_accuracy_improvement_claimed=False,
        excluded_parent_scopes_preserved=ctx['joint_report']['excluded_parent_scopes_preserved'])
    io.write(output/'report.json', report)
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--output', required=True)
    r = run(p.parse_args().output)
    print(json.dumps({k: r[k] for k in ('complete', 'counts', 'active_contrasts',
        'full_source_packages', 'original_edges', 'elapsed_seconds')}, indent=2), flush=True)
