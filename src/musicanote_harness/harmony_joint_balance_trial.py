"""Bounded joint calibration and fresh ordinary Train selection, research only."""
import argparse
from collections import Counter
from copy import deepcopy
from pathlib import Path
from time import perf_counter
import json

from . import harmony_member_role_trial as prior
from . import harmony_joint_balance_learning as learning
from . import harmony_score_balance_ledger as ledger

VERSION = 'harmony-joint-score-balance-trial-0.1.0'
ROOT = Path('K:/Music Analysis/output/harmony-score-balance-2026-10-05-r1')
PINS = {'report.json': '11d86b722a55501b12fad5276e07bf433a669ced935e4148e432f6f6dc8d1173',
        'post-seal-audit.json': 'd981e52e741108f74e5ce5544fa610f6be387b355b37e808bf597360f69da748',
        'train-contrasts.json.gz': '868e220dcca4c970b039065e5b8bef66a500e0cb22027c9f9a99fadfafd24385'}
ROLE_ROOT = Path('K:/Music Analysis/output/harmony-member-role-interactions-2026-10-05-r2')
ROLE_PINS = {'report.json': '641806ea8fbfc94c135446a4134a57ff607e4fc581aad35b2274463102ccd340',
             'model.json.gz': '3f2c10e7899b3e66696be82bc64e41530829cb48c23707c456dcc3231033d346',
             'training-vectors.json.gz': '02c9a9938513dc4188b84af9b55df3965ce7d712c81d2851ca1931c5fe6da999'}
s, io, load, same_json = prior.s, prior.io, prior.load, prior.same_json


def context(read):
    report, audit, contrasts = [read(ROOT/n, h) for n, h in PINS.items()]
    if report['complete'] is not True or audit['passed'] is not True or audit['report_sha256'] != PINS['report.json']:
        raise ValueError('joint_balance_parent_not_sealed')
    for p, h in (report['input_hashes'] | report['artifact_hashes'] | report['code_hashes']).items(): read(p, h, raw=True)
    ctx = prior.context(read)
    role_report, model, pool = [read(ROLE_ROOT/n, h) for n, h in ROLE_PINS.items()]
    prior.learning.model_weights(model, ctx['weights'], ctx['frozen7'], ctx['use'], ctx['manifest'],
                                 ctx['parent_sha'], prior.PINS['training-vectors.json.gz'])
    if role_report['cohort'] != [r['sample_id'] for r in ctx['rows']] or report['new_fit_or_search'] is not False:
        raise ValueError('joint_balance_cohort_changed')
    ctx['initial35'] = ledger.coefficients(model); ctx['previous_records'] = {r['sample_id']: r for r in role_report['records']}
    ctx['contrast_rows'] = contrasts['rows']; ctx['role_vectors'] = {(r['sample_id'], r['contrast_id']): r for r in pool['rows']}
    ctx['balance_report'] = report; ctx['member_role_report'] = role_report
    return ctx


def collect(ctx):
    rows = []; counts = Counter()
    for item in ctx['contrast_rows']:
        old = ctx['role_vectors'][item['sample_id'], item['contrast_id']]; terms = item['comparison']['terms']
        row = {k: deepcopy(old[k]) for k in ('entry', 'sample_id', 'contrast_id', 'negative_ids', 'target_ids',
                                            'loss', 'source_arm', 'source_ir_content_sha256')}
        row |= {'score_delta': {k: terms[k]['scored_partial_delta'] for k in learning.FEATURES},
                'gradient_delta': {k: terms[k]['value_delta'] for k in learning.FEATURES},
                'available': {k: terms[k]['known_both'] for k in learning.FEATURES},
                'features_use_source_labels': False, 'target_created_using_training_reference': True}
        if row['loss'] != item['loss'] or learning.gap(row, ctx['initial35']) != s.f(item['comparison']['left_minus_right_cost']):
            raise ValueError('joint_balance_initial_gap_changed')
        rows.append(row); counts['contrasts'] += 1; counts['zero_loss_protections'] += s.f(row['loss']) == 0
        counts['known_nonzero_trainable_gradient'] += any(row['available'][k] and s.f(row['score_delta'][k]) for k in learning.TRAINABLE)
    learning.validate_rows(rows, ctx['use'], ctx['manifest'], ctx['parent_sha'])
    rows.sort(key=lambda r: (r['entry']['work_family_id'], r['sample_id'], r['contrast_id']))
    return rows, dict(counts)


def annotate(result, weights):
    if 'member_role_contract' in result: result['member_role_contract']['old26_and_old7_frozen'] = False
    result['joint_balance_contract'] = {'version': VERSION, 'all_35_weights_frozen_during_selection': True,
        'trainable_during_fit': list(learning.TRAINABLE), 'fixed_during_fit': list(learning.FIXED),
        'source_features_and_graph_unchanged': True, 'source_labels_used': False, 'production_modified': False}
    if result['selected']:
        result['selected']['proposal_id'] = 'joint_balance_'+learning.use.content_hash(
            [s.fresh.path_ids(result['selected']), {k: s.q(v) for k, v in weights.items()}])[:24]
    return result


class Scorer(prior.scoring.Scorer):
    def __init__(self, graph, ev, weights, **args):
        weights = learning.coefficients(weights); self.joint_weights = weights
        super().__init__(s.Scorer(graph, ev, {k: weights[k] for k in ledger.old.FEATURES}, **args),
                         {k: weights[k] for k in ledger.context.FEATURES},
                         {k: weights[k] for k in ledger.role.FEATURES}, **args)

    def decode(self, **kwargs): return annotate(super().decode(**kwargs), self.joint_weights)


def run(output):
    output = Path(output)
    if output.exists(): raise ValueError('output_exists_no_overwrite')
    tick = perf_counter(); inputs, artifacts = {}, {}
    def read(p, expected=None, compressed=False, raw=False):
        p = Path(p); name = str(p.resolve()); h = io.digest(p)
        if (expected is not None and h != expected) or (name in inputs and inputs[name] != h):
            raise ValueError('joint_balance_input_changed:'+name)
        inputs[name] = h; return None if raw else load(p)
    ctx = context(read)
    code = {str(p.resolve()): io.digest(p) for p in Path(__file__).parent.glob('*.py')}
    for name in ('tests/test_harmony_joint_balance_learning.py', 'tests/test_harmony_joint_balance_trial.py',
                 'scripts/validate_harmony_joint_balance.py', 'scripts/audit_harmony_joint_balance.py'):
        p = Path(name); code[str(p.resolve())] = io.digest(p)
    output.mkdir(parents=True); (output/'cases').mkdir()
    def save(p, value, compressed=False):
        p = output/p; (io.write_packet if compressed else io.write)(p, value)
        name = str(p.resolve()); artifacts[name] = io.digest(p); return name, artifacts[name]
    contract = {'version': VERSION, 'configuration': learning.configuration(),
        'cohort': [r['sample_id'] for r in ctx['rows']], 'parent_report_sha256': PINS['report.json'],
        'initial_model_sha256': ROLE_PINS['model.json.gz'], 'wall_seconds_per_fresh_scope': prior.prior.old.WALL_SECONDS,
        'transition_budget': s.fresh.BUDGET, 'same_candidate_graph_and_raw_cap': True,
        'source_labels_used_for_prediction': False, 'current_dev_reconstructed_or_used': False,
        'production_modified': False, 'purpose': 'local_noncommercial_research', 'code_pins': code,
        'feature_rules_prespecified_no_work_conditions': True, 'pool_complete': False}
    save(Path('run-contract.json'), contract)
    rows, counts = collect(ctx); save(Path('training-vectors.json.gz'), {'rows': rows, 'counts': counts}, True)
    model = learning.fit(rows, ctx['initial35'], ctx['use'], ctx['manifest'], ctx['parent_sha'], PINS['report.json'])
    if model['margin_sum_before'] != ctx['balance_report']['margin_violation_sum']:
        raise ValueError('joint_balance_parent_margin_changed')
    save(Path('model.json.gz'), model, True); model_sha = io.digest(output/'model.json.gz')
    weights = learning.model_weights(model, ctx['initial35'], ctx['use'], ctx['manifest'], ctx['parent_sha'], PINS['report.json'])
    save(Path('model-freeze.json'), {'model_sha256': model_sha, 'postfit_selection_started': False,
         'all_35_weights_frozen_during_selection': True, 'dev_used': False})
    print('[joint balance frozen] '+json.dumps({'counts': counts, 'updates': len(model['updates']),
          'before': model['margin_sum_before'], 'after': model['margin_sum_after']}, ensure_ascii=False), flush=True)
    records = []; sources = set(); edges = projections = 0
    for i, row in enumerate(ctx['rows'], 1):
        sample = row['sample_id']; saved, entry, graph, ev, clock, args = prior.prior.old.prior.prepare_sample(ctx, row, read)
        sc = Scorer(graph, ev, weights, **args)
        result = annotate(prior.prior.parent.select(sc, model['model_id']), weights)
        result['frozen_model_ref'] = {'model_id': model['model_id'], 'model_sha256': model_sha,
            'fit_performed_before_selection': True, 'fit_performed_this_selection': False,
            'all_35_weights_frozen': True, 'existing_26_frozen_during_fit': False,
            'source_labels_used_for_selection': False, 'operational_promotion': False}
        selected = result['selected']; ids = s.fresh.path_ids(selected) if selected else None
        previous = ctx['previous_records'][sample]; baseline = ctx['stage80_records'][sample]
        chains = {'fresh': ids, 'previous_member_role': previous['selected_ids'], 'frozen_old26': baseline['baseline_ids'],
                  'stored_target': ctx['joint_packets'][sample]['arms']['epoch3_target']['path_ids']}
        receipts = {}
        for name, path in chains.items():
            if path is None: continue
            receipt = sc.path_receipt(path, target=name == 'stored_target')
            projections += prior.verify_projection(sc, path, receipt)
            ledger.flatten(receipt, weights)
            if name == 'fresh' and not same_json(receipt, selected['context_score']): raise ValueError('joint_balance_fresh_cost_changed')
            receipts[name] = receipt
        ref = ctx['refs'][sample]
        evaluation = prior.prior.old.evaluate(prior.prior.old.native_reference(ref),
            prior.prior.old.native_prediction(selected, ref['sample_span']), ref['sample_span'], selected=selected is not None)
        packet = {k: saved[k] for k in prior.prior.SOURCE_FIELDS} | {'result': result, 'evaluation': evaluation,
            'model_sha256': model_sha, 'post_search_cost_receipts': receipts,
            'previous_case_ref': previous['artifact'], 'previous_case_sha256': previous['sha256'],
            'source_labels_used_for_inference': False, 'full_source_not_clipped': True, 'human_validated': False}
        p, h = save(Path('cases')/(sample+'.json.gz'), packet, True)
        records.append({k: row[k] for k in prior.prior.FIELDS} | {'artifact': p, 'sha256': h, 'status': result['status'],
            'selected_ids': ids, 'previous_ids': previous['selected_ids'], 'baseline_ids': baseline['baseline_ids'],
            'evaluation': evaluation, 'previous_evaluation': previous['evaluation'], 'baseline_evaluation': baseline['baseline_evaluation'],
            'elapsed_seconds': result['resource_guard']['elapsed_seconds']})
        sources.add(ev.source.source_ir_content_sha256); edges += len(graph.edges); prior.prior.clear(ev, clock)
        print(f'[joint balance Train {i}/{len(ctx["rows"])}] {sample}: {result["status"]}, hit={evaluation["selected_hit"]}', flush=True)
    for p, h in (inputs | artifacts | code).items():
        if io.digest(p) != h: raise ValueError('joint_balance_final_seal_changed:'+p)
    report = contract | {'complete': True, 'fit_performed': True, 'model_sha256': model_sha,
        'training_contrasts': len(rows), 'vector_counts': counts, 'fresh_ordinary_attempts': len(records),
        'full_source_packages': len(sources), 'original_edges': edges, 'scalar_detailed_transitions_compared': projections,
        'tables': prior.prior.comparisons(records), 'records': records, 'input_hashes': inputs,
        'artifact_hashes': artifacts, 'code_hashes': code, 'operational_weights_changed': False,
        'independent_accuracy_claimed': False, 'elapsed_seconds': perf_counter()-tick,
        'excluded_parent_scopes_preserved': ctx['member_role_report']['excluded_parent_scopes_preserved'],
        'historical_parent_containers_include_exposed_dev': True}
    io.write(output/'report.json', report); return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--output', required=True)
    result = run(p.parse_args().output)
    print(json.dumps({k: result[k] for k in ('complete', 'vector_counts', 'tables', 'elapsed_seconds')}, indent=2), flush=True)
