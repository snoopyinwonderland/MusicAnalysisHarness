"""Rebuild source-linked Train contrasts and masks, without fitting/searching."""
import argparse
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
from musicanote_harness import harmony_train_protection_trial as t


def run(root):
    root = Path(root); dest = root/'post-seal-audit.json'
    if dest.exists():
        raise ValueError('output_exists_no_overwrite')
    report, contract = t.load(root/'report.json'), t.load(root/'run-contract.json')
    pins = report['input_hashes'] | report['artifact_hashes'] | report['code_hashes']; reads = set()
    def check():
        for p, h in pins.items():
            if t.io.digest(p) != h:
                raise ValueError('protection_audit_seal_changed:'+p)
    def read(p, expected=None, compressed=False, raw=False):
        name = str(Path(p).resolve()); h = t.io.digest(p)
        if pins.get(name) != h or (expected is not None and h != expected):
            raise ValueError('protection_audit_unsealed_input:'+name)
        reads.add(name)
        return None if raw else t.load(p)
    check(); ctx = t.context(read); inert, protected = t.inventory(ctx)
    weights = ctx['initial35']
    if (report['complete'] is not True or report['configuration'] != t.configuration()
            or not all(t.same_json(contract[k], report[k]) for k in contract)
            or report['cohort'] != [r['sample_id'] for r in ctx['rows']]
            or report['protected_scopes'] != protected
            or report['frozen_weights'] != {k: t.s.q(v) for k, v in weights.items()}
            or report['frozen_model_sha256'] != t.prior.ROLE_PINS['model.json.gz']
            or any(report[k] is not False for k in ('fit_performed', 'current_dev_reconstructed_or_used',
                'operational_weights_changed', 'production_modified', 'music_accuracy_improvement_claimed'))
            or len(report['records']) != len(ctx['rows'])):
        raise ValueError('protection_audit_contract_or_cohort_changed')
    if not t.same_json(read(root/'inactive-original-noops.json.gz')['rows'], inert):
        raise ValueError('protection_audit_inert_history_changed')
    active = [deepcopy(r) for r in ctx['pool'] if t.s.f(r['loss']) > 0]
    counts = Counter(); sources = set(); edges = costs = projections = 0
    for row, record in zip(ctx['rows'], report['records']):
        sample = row['sample_id']
        if any(not t.same_json(row[k], record[k]) for k in t.refresh.FIELDS):
            raise ValueError('protection_audit_original_record_changed')
        if sample not in protected:
            if record['attempted'] is not False or record['status'] != 'not_a_protection_scope_no_new_search':
                raise ValueError('protection_audit_unattempted_scope_changed')
            counts['unattempted_original_scopes_preserved'] += 1
            continue
        if record['attempted'] is not True or record['reasons'] != protected[sample]:
            raise ValueError('protection_audit_protection_scope_missing')
        packet = read(record['artifact'], record['sha256'])
        saved, entry, graph, ev, clock, args = t.prior.prior.prior.old.prior.prepare_sample(ctx, row, read)
        if not all(t.same_json(packet[k], saved[k]) for k in t.refresh.SOURCE_FIELDS):
            raise ValueError('protection_audit_original_source_changed')
        sc = t.prior.Scorer(graph, ev, weights, **args)
        ids = next((r['target_ids'] for r in inert if r['sample_id'] == sample),
            ctx['joint_packets'][sample]['arms']['epoch3_target']['path_ids'])
        loss = t.refresh.loss_object(graph, ctx['refs'][sample])
        target_loss = t.refresh.loss_for_ids(graph, loss, ids)
        target = sc.path_receipt(ids, target=True); costs += 1
        projections += t.prior.prior.verify_projection(sc, ids, target)
        if (t.s.f(target_loss['total']) != 0 or not t.same_json(packet['target_ids'], ids)
                or not t.same_json(packet['target_receipt'], target) or packet['target_loss'] != target_loss
                or packet['source_labels_used_for_features'] is not False or packet['human_validated'] is not False):
            raise ValueError('protection_audit_target_or_feature_contract_changed')
        result = packet['result']; guard = result['resource_guard']
        if (result['training_reference_labels_used_for_constraint'] is not True
                or result['analysis_export_allowed'] is not False or result['prediction'] is not False
                or result['loss_used_as_score'] is not False or result['partial_winner_returned'] is not False
                or guard['raw_segment_cap'] != graph.max_segments
                or guard['transition_budget'] != t.s.fresh.BUDGET or guard['wall_seconds'] != t.WALL_SECONDS
                or result['transitions'] > t.s.fresh.BUDGET or result['transitions'] < 0):
            raise ValueError('protection_audit_miner_contract_changed')
        diagnostic = duplicate = None
        if result['path_ids'] is not None:
            negative_ids = result['path_ids']; negative = sc.path_receipt(negative_ids); costs += 1
            projections += t.prior.prior.verify_projection(sc, negative_ids, negative)
            negative_loss = t.refresh.loss_for_ids(graph, loss, negative_ids)
            vector, comparison = t.vector(entry, sample, negative, target, negative_loss,
                saved['source_ir_content_sha256'], weights)
            if (result['status'] != 'selected_train_only_wrong_competitor'
                    or result['exact_optimum_among_positive_loss_paths'] is not True
                    or not t.same_json(negative, result['receipt']) or negative['cost'] != result['ordinary_cost']
                    or negative_loss != result['training_loss'] or t.s.f(negative_loss['total']) <= 0
                    or t.semantic_key(graph, negative_ids) == t.semantic_key(graph, ids)
                    or not t.same_json(vector, packet['vector']) or comparison != packet['comparison']):
                raise ValueError('protection_audit_wrong_path_cost_loss_or_vector_changed')
            diagnostic = t.diagnostic(vector, weights)
            key = t.semantic_key(graph, negative_ids), t.semantic_key(graph, ids)
            duplicate = next((r['contrast_id'] for r in active if r['sample_id'] == sample
                and (t.semantic_key(graph, r['negative_ids']), t.semantic_key(graph, r['target_ids'])) == key), None)
            if duplicate is None:
                active.append(vector); counts['new_positive_protection_rows'] += 1
            else:
                counts['linked_existing_positive_rows_not_reweighted'] += 1
            counts['positive_wrong_competitors'] += 1
            for name in ('margin_satisfied', 'wrong_cheaper_than_stored_target',
                         'known_nonzero_trainable_gradient', 'individual_margin_possible_under_same_trust_box'):
                counts[name] += bool(diagnostic[name])
        else:
            exact = result['status'] == 'no_positive_loss_path_under_original_cap'
            if (result['status'] not in ('protection_wall_budget_abstention', 'transition_budget_abstention',
                    'no_positive_loss_path_under_original_cap')
                    or result['exact_optimum_among_positive_loss_paths'] is not exact
                    or result['receipt'] is not None or packet['vector'] is not None
                    or packet['comparison'] is not None):
                raise ValueError('protection_audit_abstention_changed')
        if (packet['diagnostic'] != diagnostic or record['diagnostic'] != diagnostic
                or packet['duplicate_existing_contrast_id'] != duplicate
                or record['duplicate_existing_contrast_id'] != duplicate or record['status'] != result['status']):
            raise ValueError('protection_audit_case_summary_changed')
        counts['attempted_protection_scopes'] += 1; counts[result['status']] += 1
        sources.add(ev.source.source_ir_content_sha256); edges += len(graph.edges)
        t.refresh.clear(ev, clock)
        print(f'[protection audit {counts["attempted_protection_scopes"]}/{len(protected)}]', flush=True)
    active.sort(key=lambda r: (r['entry']['work_family_id'], r['sample_id'], r['contrast_id']))
    vectors = read(root/'training-vectors.json.gz')
    t.learning.validate_rows(active, ctx['use'], ctx['manifest'], ctx['parent_sha'])
    if (not t.same_json(active, vectors['rows']) or dict(counts) != vectors['counts']
            or dict(counts) != report['counts'] or len(active) != report['active_contrasts']
            or len(sources) != report['full_source_packages'] or edges != report['original_edges']
            or projections != report['scalar_detailed_transitions_compared']
            or report['excluded_parent_scopes_preserved'] != ctx['joint_report']['excluded_parent_scopes_preserved']):
        raise ValueError('protection_audit_aggregate_changed')
    check()
    result = dict(passed=True, version=t.VERSION, report_sha256=t.io.digest(root/'report.json'),
        sha_checks=len(pins), sealed_inputs_reloaded=len(reads), attempted_scopes=len(protected),
        full_source_packages=len(sources), original_edges=edges, inactive_original_noops=len(inert),
        active_training_contrasts=len(active), independent_detailed_costs_replayed=costs,
        scalar_detailed_transitions_replayed=projections,
        new_search_or_fit_or_dev=False, original_core_operational_weights_and_parent_artifacts_unchanged=True)
    t.io.write(dest, result)
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--root', required=True)
    print(json.dumps(run(p.parse_args().root), indent=2), flush=True)
