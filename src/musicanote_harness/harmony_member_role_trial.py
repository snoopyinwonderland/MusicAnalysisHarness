"""One two-interaction Train experiment; sealed old33, same graphs/cohort."""
import argparse
from collections import Counter, defaultdict
from copy import deepcopy
from fractions import Fraction as F
import json
from pathlib import Path
from time import perf_counter

from . import harmony_context_refresh_trial as prior
from . import harmony_member_role_scoring as scoring
from . import harmony_member_role_learning as learning

VERSION = 'harmony-member-role-trial-0.1.0'
ROOT = 'K:/Music Analysis/output/harmony-context-refreshed-pool-2026-10-05-r1'
PINS = {
    'report.json': 'ffb9b6bd49a97af745b769f00664dbeac5bd107c902ccf263bd442944d088c67',
    'run-contract.json': '1281ee60fe398547851f62bc689adeb571c411cc534a867fb27eae9d5d806d94',
    'post-seal-audit.json': '8491823e2ce2ac012b6cbad5931a7c6a8b0b095ec66317ed8d4d926e05ef9ce7',
    'model.json.gz': '2b36a64aa933a228d3d71396b3be899be2336afc39e1c217dd4e63ef6fc447dd',
    'training-vectors.json.gz': 'c179514e151b3469895ce4bdabcec190e4a602f1f57438bb5c54d7eb9b623217',
}
s, io, load, same_json = prior.s, prior.io, prior.load, prior.same_json


def context(read):
    report, contract, audit, model, vectors = [read(Path(ROOT)/p, h) for p, h in PINS.items()]
    if report['complete'] is not True or audit['passed'] is not True or audit['report_sha256'] != PINS['report.json']:
        raise ValueError('member_role_parent_not_sealed')
    for p, h in (report['input_hashes'] | report['artifact_hashes'] | report['code_hashes']).items():
        read(p, h, raw=True)
    ctx = prior.context(read)
    if contract['cohort'] != [r['sample_id'] for r in ctx['rows']]:
        raise ValueError('member_role_original_cohort_changed')
    ctx['frozen7'] = prior.learning.model_weights(model, ctx['weights'], ctx['use'], ctx['manifest'], ctx['parent_sha'], prior.PINS['report.json'])
    ctx['role_parent_records'] = {r['sample_id']: r for r in report['records']}
    ctx['role_parent_report'] = report; ctx['role_pool'] = vectors['rows']
    prior.learning.validate_rows(ctx['role_pool'], ctx['use'], ctx['manifest'], ctx['parent_sha'])
    return ctx


def make_scorer(ctx, graph, ev, args, weights=None):
    return scoring.Scorer(s.Scorer(graph, ev, ctx['weights'], **args), ctx['frozen7'],
        scoring.ZERO if weights is None else weights, **args)


def verify_projection(sc, ids, receipt):
    count = prior.parent.verify_projection(sc, ids, receipt)
    runs = scoring.parent.sealed.context_features.control.completed_runs(sc.problem, ids)
    for i, p in enumerate(receipt['member_role']['transitions'], 1):
        v = sc.role_index.observe(runs, i)
        if (v['availability'] != p['availability']
                or {k: s.q(x) for k, x in v['observed_feature_sums'].items()} != p['observed_feature_sums']
                or {k: None if x is None else s.q(x) for k, x in v['features'].items()} != p['features']):
            raise ValueError('member_role_scalar_detailed_mismatch')
    return count


def collect(ctx, read, save=None):
    groups = defaultdict(list)
    for r in ctx['role_pool']:
        groups[r['sample_id']].append(r)
    vectors, proofs = [], []; counts = Counter(); transitions = 0
    for row in ctx['rows']:
        saved, entry, graph, ev, clock, args = prior.old.prior.prepare_sample(ctx, row, read)
        sc = make_scorer(ctx, graph, ev, args); receipts = {}; local_vectors = []
        for old in groups[row['sample_id']]:
            sides = []
            for target, key in ((False, 'negative_ids'), (True, 'target_ids')):
                ids = tuple(old[key]); rkey = ids, target
                if rkey not in receipts:
                    receipts[rkey] = sc.path_receipt(ids, target=target)
                    transitions += verify_projection(sc, ids, receipts[rkey])
                sides.append(receipts[rkey])
            negative, target = sides
            gap = s.f(negative['parent_score_cost'])-s.f(target['parent_score_cost'])
            if gap != prior.learning.gap(old, ctx['frozen7']):
                raise ValueError('member_role_frozen33_cost_changed')
            available = {k: negative['member_role']['availability'][k] and target['member_role']['availability'][k] for k in scoring.FEATURES}
            delta = {k: s.f(negative['member_role']['scored_available_feature_sums'][k])-s.f(target['member_role']['scored_available_feature_sums'][k]) for k in scoring.FEATURES}
            new = {k: deepcopy(old[k]) for k in ('entry', 'sample_id', 'contrast_id', 'negative_ids', 'target_ids', 'loss', 'source_arm', 'source_ir_content_sha256')}
            new |= {'frozen33_gap': s.q(gap), 'score_delta': {k: s.q(v) for k, v in delta.items()},
                'gradient_delta': {k: s.q(delta[k]) if available[k] else None for k in scoring.FEATURES},
                'available': available, 'features_use_source_labels': False,
                'target_created_using_training_reference': True, 'no_new_negative_or_target_search': True}
            vectors.append(new); local_vectors.append(new)
            counts['contrasts'] += 1
            counts['known_nonzero_new_gradient'] += any(available[k] and delta[k] for k in scoring.FEATURES)
            counts['both_new_axes_available'] += all(available.values())
            counts['zero_loss_protection_retained'] += s.f(old['loss']) == 0
        packet = {k: saved[k] for k in prior.SOURCE_FIELDS} | {'vectors': local_vectors,
            'path_receipts': [{'ids': list(ids), 'target': target, 'receipt': value} for (ids, target), value in receipts.items()],
            'source_labels_used_for_features': False, 'human_validated': False}
        if save:
            p, h = save(Path('vectors')/(row['sample_id']+'.json.gz'), packet, True)
            proofs.append({'sample_id': row['sample_id'], 'artifact': p, 'sha256': h})
        else:
            proofs.append(packet)
        prior.clear(ev, clock)
    vectors.sort(key=lambda r: (r['entry']['work_family_id'], r['sample_id'], r['contrast_id']))
    learning.validate_rows(vectors, ctx['use'], ctx['manifest'], ctx['parent_sha'])
    return vectors, dict(counts), proofs, transitions


def run(output):
    output = Path(output)
    if output.exists():
        raise ValueError('output_exists_no_overwrite')
    tick = perf_counter(); inputs, artifacts = {}, {}
    def read(p, expected=None, compressed=False, raw=False):
        p = Path(p); name = str(p.resolve()); h = io.digest(p)
        if (expected is not None and h != expected) or (name in inputs and inputs[name] != h):
            raise ValueError('member_role_input_changed:'+name)
        inputs[name] = h; return None if raw else load(p)
    ctx = context(read)
    code = {str(p.resolve()): io.digest(p) for p in Path(__file__).parent.glob('*.py')}
    for p in ('tests/test_harmony_member_role_scoring.py', 'tests/test_harmony_member_role_learning.py',
              'scripts/validate_harmony_member_roles.py', 'scripts/audit_harmony_member_roles.py'):
        code[str(Path(p).resolve())] = io.digest(p)
    output.mkdir(parents=True); (output/'cases').mkdir(); (output/'vectors').mkdir()
    def save(p, value, compressed=False):
        p = output/p; (io.write_packet if compressed else io.write)(p, value)
        name = str(p.resolve()); artifacts[name] = io.digest(p); return name, artifacts[name]
    contract = {'version': VERSION, 'feature_version': scoring.VERSION, 'configuration': learning.configuration(),
        'cohort': [r['sample_id'] for r in ctx['rows']], 'parent_report_sha256': PINS['report.json'],
        'pool_sha256': PINS['training-vectors.json.gz'], 'old26_and_old7_frozen': True,
        'wall_seconds_per_fresh_scope': prior.old.WALL_SECONDS, 'transition_budget': s.fresh.BUDGET,
        'same_candidate_graph_and_raw_cap': True, 'source_labels_used_for_prediction': False,
        'current_dev_reconstructed_or_used': False, 'production_modified': False,
        'purpose': 'local_noncommercial_research', 'code_pins': code,
        'feature_rules_prespecified_no_work_conditions': True, 'pool_complete': False}
    save(Path('run-contract.json'), contract)
    vectors, counts, proofs, projections = collect(ctx, read, save)
    save(Path('training-vectors.json.gz'), {'rows': vectors, 'counts': counts, 'proofs': proofs}, True)
    model = learning.fit(vectors, ctx['weights'], ctx['frozen7'], ctx['use'], ctx['manifest'], ctx['parent_sha'], PINS['training-vectors.json.gz'])
    save(Path('model.json.gz'), model, True); model_sha = io.digest(output/'model.json.gz')
    weights = learning.model_weights(model, ctx['weights'], ctx['frozen7'], ctx['use'], ctx['manifest'], ctx['parent_sha'], PINS['training-vectors.json.gz'])
    save(Path('model-freeze.json'), {'model_sha256': model_sha, 'postfit_selection_started': False,
        'old26_and_old7_frozen': True, 'dev_used': False})
    print('[member-role frozen] '+json.dumps({'counts': counts, 'weights': model['weights']}, ensure_ascii=False), flush=True)
    records = []; sources = set(); edges = 0
    for i, row in enumerate(ctx['rows'], 1):
        sample = row['sample_id']; saved, entry, graph, ev, clock, args = prior.old.prior.prepare_sample(ctx, row, read)
        sc = make_scorer(ctx, graph, ev, args, weights)
        result = prior.parent.select(sc, model['model_id'])
        result['frozen_model_ref'] = {'model_id': model['model_id'], 'model_sha256': model_sha,
            'old26_and_old7_frozen': True, 'fit_performed_before_selection': True,
            'source_labels_used_for_selection': False, 'operational_promotion': False}
        selected = result['selected']; ids = s.fresh.path_ids(selected) if selected else None
        previous = ctx['role_parent_records'][sample]; baseline = ctx['stage80_records'][sample]
        chains = {'fresh': ids, 'previous_context': previous['selected_ids'], 'frozen_old26': baseline['baseline_ids'],
            'stored_target': ctx['joint_packets'][sample]['arms']['epoch3_target']['path_ids']}
        receipts = {}
        for name, path in chains.items():
            if path is None:
                continue
            receipt = sc.path_receipt(path, target=name == 'stored_target'); projections += verify_projection(sc, path, receipt)
            if name == 'fresh' and not same_json(receipt, selected['context_score']):
                raise ValueError('member_role_fresh_cost_changed')
            receipts[name] = receipt
        ref = ctx['refs'][sample]
        evaluation = prior.old.evaluate(prior.old.native_reference(ref), prior.old.native_prediction(selected, ref['sample_span']), ref['sample_span'], selected=selected is not None)
        packet = {k: saved[k] for k in prior.SOURCE_FIELDS} | {'result': result, 'evaluation': evaluation,
            'model_sha256': model_sha, 'post_search_cost_receipts': receipts,
            'previous_case_ref': previous['artifact'], 'previous_case_sha256': previous['sha256'],
            'source_labels_used_for_inference': False, 'full_source_not_clipped': True, 'human_validated': False}
        p, h = save(Path('cases')/(sample+'.json.gz'), packet, True)
        records.append({k: row[k] for k in prior.FIELDS} | {'artifact': p, 'sha256': h, 'status': result['status'],
            'selected_ids': ids, 'previous_ids': previous['selected_ids'], 'baseline_ids': baseline['baseline_ids'],
            'evaluation': evaluation, 'previous_evaluation': previous['evaluation'], 'baseline_evaluation': baseline['baseline_evaluation'],
            'elapsed_seconds': result['resource_guard']['elapsed_seconds']})
        sources.add(ev.source.source_ir_content_sha256); edges += len(graph.edges); prior.clear(ev, clock)
        print(f'[member-role Train {i}/{len(ctx["rows"])}] {sample}: {result["status"]}, hit={evaluation["selected_hit"]}', flush=True)
    for p, h in (inputs | artifacts | code).items():
        if io.digest(p) != h:
            raise ValueError('member_role_final_seal_changed:'+p)
    report = contract | {'complete': True, 'fit_performed': True, 'model_sha256': model_sha,
        'training_contrasts': len(vectors), 'vector_counts': counts, 'fresh_ordinary_attempts': len(records),
        'full_source_packages': len(sources), 'original_edges': edges, 'scalar_detailed_transitions_compared': projections,
        'tables': prior.comparisons(records), 'records': records, 'input_hashes': inputs,
        'artifact_hashes': artifacts, 'code_hashes': code, 'operational_weights_changed': False,
        'independent_accuracy_claimed': False, 'elapsed_seconds': perf_counter()-tick,
        'excluded_parent_scopes_preserved': ctx['role_parent_report']['excluded_parent_scopes_preserved'],
        'historical_parent_containers_include_exposed_dev': True}
    io.write(output/'report.json', report); return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--output', required=True)
    r = run(p.parse_args().output)
    print(json.dumps({k: r[k] for k in ('complete', 'training_contrasts', 'vector_counts', 'tables', 'elapsed_seconds')}, indent=2), flush=True)
