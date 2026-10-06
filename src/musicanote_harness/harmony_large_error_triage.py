"""ALL-Train error anatomy and source-only seventh-release observations.

No decoding, fitting, Dev access or promotion. Frozen winners and stored
training witnesses are compared AFTER selection; targets never enter the new
feature extractor. Preserve every old abstention, source package and cost.
"""
import argparse
from collections import Counter
from fractions import Fraction as F
import json
from pathlib import Path
from time import perf_counter

from . import harmony_exact_beat_train_trial as parent
from . import harmony_member_release as release
from . import harmony_score_balance_ledger as ledger
from .harmony_functional_scoring import six_four_surface
from .harmony_joint_nct_scoring import completed_runs

VERSION = 'harmony-large-train-error-triage-0.1.0'
ROOT = Path('K:/Music Analysis/output/harmony-exact-beat-train-2026-10-06-r1')
PINS = {'report.json': '09d170b697ca3190c850da76a646946eff75b52fd2585ad10ec8435fb67a9cce',
        'post-seal-audit.json': '5770611df3045023f1a56be21d816fa192101e53b38fc37a5982863ea15027ef'}
PRIOR_VALIDATION_SHA = '3355a1f7e13635310c14900f105e98108935f178f1600a003dd56628038efd28'
q, f, io, load = ledger.q, ledger.f, parent.io, parent.load
CODE_FILES = ('src/musicanote_harness/harmony_member_release.py', __file__,
              'tests/test_harmony_member_release.py', 'tests/test_harmony_large_error_triage.py',
              'scripts/validate_harmony_large_error_triage.py')


def compare_runs(winner, target):
    """Exact duration decomposition, not four independent accuracy metrics."""
    totals = Counter(); cells = []
    for a, b, sig in winner:
        for x, y, ref in target:
            start, end = max(a, x), min(b, y)
            if start >= end: continue
            if sig == ref: kind = 'same_signature'
            elif sig[1] == ref[1]: kind = 'same_members_different_root'
            elif sig[0] == ref[0]: kind = 'same_root_different_members'
            else: kind = 'different_root_and_members'
            subtype = None
            if kind == 'same_members_different_root':
                for functional, literal in ((sig, ref), (ref, sig)):
                    surface = six_four_surface(functional)
                    if surface is not None and surface[0] == literal[0]:
                        subtype = 'functional_six_four_vs_literal_surface'
            totals[kind] += end-start
            cells.append(dict(span=dict(start=q(start), end=q(end)), kind=kind, subtype=subtype,
                              winner_signature=sig, target_signature=ref))
    return dict(quarter_totals={k: q(v) for k, v in sorted(totals.items())}, cells=cells,
                target_is_stored_training_witness=True, interpretation_confirmed=False)


def contrast(winner, target, gap):
    available = winner['availability'] and target['availability']
    delta = f(winner['feature'])-f(target['feature']) if available else None
    # A single-contrast threshold is an algebraic diagnostic, NOT a chosen
    # coefficient, a fitted model, or a claim that the global optimum changes.
    threshold = -gap/delta if delta is not None and delta > 0 and gap < 0 else None
    return dict(available_both=available, feature_delta=None if delta is None else q(delta),
        old_winner_minus_target_cost=q(gap),
        single_contrast_equal_cost_weight=None if threshold is None else q(threshold),
        threshold_is_not_fitted_weight=True, fresh_optimum_not_computed=True)


def source_window(ev, span):
    a, b = max(F(), f(span['start'])-4), f(span['end'])+4
    rows = [dict(sounding_event_id=r['id'], source_note_ids=list(r['source_note_ids']),
        span=dict(start=q(r['start']), end=q(r['end'])), pitch=r['pitch_data'],
        explicit_part_voice=r['identity'], source_clock_valid=r['clock_valid'])
        for r in ev.rows if r['start'] < r['end'] and r['start'] < b and a < r['end']]
    return dict(display_context_quarters=4, span=dict(start=q(a), end=q(b)),
                original_spans_not_clipped=True, events=rows,
                diagnostic_excerpt_not_standalone_score=True)


def inspect_sample(row, archived, graph, ev, args, weights):
    receipts = archived['post_search_cost_receipts']
    target = receipts['historical_stored_target']
    target_ids = tuple(target['existing_path_ids'])
    target_runs = completed_runs(graph, target_ids)
    target_observation = release.observe_path(graph, ev, target_ids, history_gate=args.get('history_gate'))
    selected = archived['result']['selected']
    common = dict(sample_id=row['sample_id'], split=row['split'], pair_id=row['pair_id'],
        work_family_id=row['work_family_id'], sample_span=row['sample_span'],
        historical_case_ref=row['artifact'], historical_case_sha256=row['sha256'],
        original_status=archived['result']['status'], original_evaluation=row['evaluation'],
        full_source_paths=archived['full_source_paths'], source_provenance=archived['source_provenance'],
        source_clock_gate=archived['source_clock_gate'], source_ir_content_sha256=archived['source_ir_content_sha256'],
        original_scope_artifact=archived['original_scope_artifact'],
        original_scope_sha256=archived['original_scope_sha256'], original_edge_count=len(graph.edges),
        target_path_ids=target_ids, target_source_feature=target_observation,
        target_created_using_training_labels=True,
        source_window=source_window(ev, row['sample_span']),
        human_validated=False, score_changed=False, source_labels_used_for_features=False)
    if selected is None:
        return common | dict(winner_path_ids=None, winner_source_feature=None,
                             path_comparison=None, cost_comparison=None, feature_contrast=None)
    winner = receipts['fresh']; ids = tuple(winner['existing_path_ids'])
    observed = release.observe_path(graph, ev, ids, history_gate=args.get('history_gate'))
    compared = ledger.compare(winner, target, weights)
    runs = completed_runs(graph, ids)
    # Scope truncation is not automatically the explanation of the root error.
    no_successor = [dict(span=dict(start=q(a), end=q(b)), signature=sig,
        reason='functional_hypothesis_at_scope_end_has_no_selected_successor')
        for a, b, sig in target_runs if b == graph.points[-1] and six_four_surface(sig) is not None]
    return common | dict(winner_path_ids=ids, winner_source_feature=observed,
        path_comparison=compare_runs(runs, target_runs), cost_comparison=compared,
        feature_contrast=contrast(observed, target_observation, f(compared['left_minus_right_cost'])),
        functional_terminal_context_limits=no_successor)


def summary(cases):
    counts = Counter(); quarters = Counter(); feature = Counter(); ranking = []
    for case in cases:
        counts['records'] += 1
        if case['winner_path_ids'] is None:
            counts['compute_abstentions'] += 1; continue
        counts['completed'] += 1
        hit = case['original_evaluation']['selected_hit']
        counts['reference_correct' if hit is True else 'reference_wrong' if hit is False else 'reference_partial'] += 1
        loss = F()
        for k, v in case['path_comparison']['quarter_totals'].items():
            quarters[k] += f(v)
            if k != 'same_signature': loss += f(v)
        c = case['feature_contrast']
        group = 'correct' if hit is True else 'wrong' if hit is False else 'partial'
        feature[group+'_available' if c['available_both'] else group+'_unavailable'] += 1
        if c['available_both']:
            delta = f(c['feature_delta'])
            feature[group+('_positive_delta' if delta > 0 else '_negative_delta' if delta < 0 else '_zero_delta')] += 1
        if hit is False:
            ranking.append(dict(sample_id=case['sample_id'], pair_id=case['pair_id'],
                                loss_quarters=q(loss), feature_contrast=c,
                                terminal_functional_context_limits=case['functional_terminal_context_limits']))
    ranking.sort(key=lambda x: (-f(x['loss_quarters']), x['sample_id']))
    return dict(counts=dict(counts), completed_winner_vs_target_quarters={k: q(v) for k, v in sorted(quarters.items())},
        feature_contrast_counts=dict(feature), largest_completed_errors=ranking,
        training_witness_comparison_not_independent_accuracy=True,
        new_accuracy_measurement=False, candidate_recall_remeasured=False)


def run(output, validation):
    output = Path(output)
    if output.exists(): raise ValueError('output_exists_no_overwrite')
    begun = perf_counter(); inputs = {}; artifacts = {}
    def read(path, expected=None, compressed=False, raw=False):
        p = Path(path); key = str(p.resolve()); sha = inputs.get(key) or io.digest(p)
        if expected is not None and sha != expected: raise ValueError('large_error_input_changed:'+key)
        inputs[key] = sha
        return None if raw else load(p)
    checked = read(validation)
    if (checked['passed'] is not True or checked['previous_validation_sha256'] != PRIOR_VALIDATION_SHA
            or not {'test_harmony_member_release','test_harmony_large_error_triage'} <= set(checked['test_modules'])):
        raise ValueError('large_error_validation_not_passed')
    previous, audit = [read(ROOT/n, sha) for n, sha in PINS.items()]
    if previous['complete'] is not True or audit['passed'] is not True or audit['report_sha256'] != PINS['report.json']:
        raise ValueError('large_error_parent_not_sealed')
    for p, sha in (previous['input_hashes'] | previous['artifact_hashes'] | previous['code_hashes']).items():
        read(p, sha, raw=True)
    ctx = parent.context(read)
    if previous['cohort'] != [r['sample_id'] for r in ctx['rows']]: raise ValueError('large_error_cohort_changed')
    old_rows = {r['sample_id']: r for r in previous['records']}
    code = {str(Path(p).resolve()): io.digest(p) for p in CODE_FILES}
    output.mkdir(parents=True); (output/'cases').mkdir()
    contract = dict(version=VERSION, cohort=previous['cohort'], feature_version=release.VERSION,
        parent_report_sha256=PINS['report.json'], model_sha256=previous['model_sha256'],
        new_search=False, fit_performed=False, current_dev_read=False, production_modified=False,
        old_candidates_costs_and_abstentions_preserved=True, source_labels_used_for_features=False,
        target_used_only_for_post_selection_train_diagnosis=True,
        feature_weight_not_selected=True, no_work_specific_rules=True, code_pins=code)
    io.write(output/'run-contract.json', contract)
    cases = []; records = []; sources = set()
    for i, row in enumerate(ctx['rows'], 1):
        old_row = old_rows[row['sample_id']]; archived = read(old_row['artifact'], old_row['sha256'])
        saved, entry, graph, ev, clock, args = parent.prepare(ctx, row, read)
        parent.assert_source(saved, archived)
        case = inspect_sample(old_row, archived, graph, ev, args, ctx['beat_weights'])
        path = output/'cases'/(row['sample_id']+'.json.gz'); io.write_packet(path, case)
        key = str(path.resolve()); artifacts[key] = io.digest(path)
        records.append(dict(sample_id=row['sample_id'], artifact=key, sha256=artifacts[key]))
        cases.append(case); sources.add(case['source_ir_content_sha256']); parent.train.refresh.clear(ev, clock)
        if i % 20 == 0 or i == len(ctx['rows']): print(f'[large error source observations {i}/{len(ctx["rows"])}]', flush=True)
    for p, sha in (inputs | artifacts | code).items():
        if io.digest(p) != sha: raise ValueError('large_error_final_seal_changed:'+p)
    result = contract | dict(complete=True, records=records, summary=summary(cases),
        full_source_packages=len(sources), input_hashes=inputs, artifact_hashes=artifacts,
        code_hashes=code, elapsed_seconds=perf_counter()-begun,
        next_required='extend_train_feature_contract_then_calibrate_and_fresh_decode_before_dev_or_adoption')
    io.write(output/'report.json', result)
    # Seal verification plus serialized observation checks; independent musical
    # validation and fresh decoding are deliberately NOT claimed by this audit.
    reloaded = [load(r['artifact']) for r in records]
    if summary(reloaded) != result['summary']: raise ValueError('large_error_reload_summary_changed')
    io.write(output/'post-seal-audit.json', dict(passed=True, report_sha256=io.digest(output/'report.json'),
        source_input_hashes_checked=len(inputs), case_artifacts_checked=len(records), code_pins_checked=len(code),
        serialized_summary_replayed=True, source_feature_accuracy_validated=False,
        new_search=False, fit_performed=False))
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--output', required=True)
    p.add_argument('--validation', required=True); a = p.parse_args(); r = run(a.output, a.validation)
    print(json.dumps(dict(complete=r['complete'], summary=r['summary'], elapsed_seconds=r['elapsed_seconds']), indent=2))
