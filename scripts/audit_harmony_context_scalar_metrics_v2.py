"""Correct tuple/list path counters without changing sealed search artifacts.

The raw audit independently replayed the source/receipts/score/metrics. Only
two post-search change counters are wrong: pre-JSON tuple versus stored list.
No decoder, source, weight, selected path, evaluation or old artifact write.
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path
from musicanote_harness import harmony_context_scalar_trial as t

VERSION = 'harmony-context-scalar-counter-audit-0.2.0'
EXPECTED_REPORT = 'd9a27279ce46407968c354a5e9a36a18bd7e1dfe1eb314a7870f50ef66d38297'
FIELDS = ('selected_ids', 'prior_selected_ids', 'original_baseline_ids')
ALLOWED = {('against_same_model_stage80', 'changes', 'path_changed_with_complete_selection'),
           ('against_frozen_old26', 'changes', 'path_changed_with_complete_selection')}


def canonical_records(records):
    result = []
    for row in records:
        copy = dict(row)
        for key in FIELDS:
            path = copy[key]
            if path is not None:
                if type(path) not in (list, tuple) or not path or any(type(i) is not str or not i for i in path):
                    raise ValueError('invalid_scalar_counter_path')
                path = tuple(path)
            copy[key] = path
        result.append(copy)
    return result


def differences(a, b, path=()):
    if isinstance(a, dict) and isinstance(b, dict):
        return [item for key in sorted(a.keys() | b.keys())
                for item in differences(a.get(key), b.get(key), path+(key,))]
    return [] if a == b else [(path, a, b)]


def run(root):
    root = Path(root); dest = root/'post-seal-metric-correction-v2.json'
    if dest.exists(): raise ValueError('output_exists_no_overwrite')
    if t.io.digest(root/'report.json') != EXPECTED_REPORT: raise ValueError('scalar_counter_parent_report_changed')
    report, audit = t.load(root/'report.json'), t.load(root/'post-seal-audit.json')
    if (audit['passed'] is not True or audit['report_sha256'] != EXPECTED_REPORT
            or audit['new_search_fit_or_dev'] is not False or report['model_sha256'] != t.PINS['model.json.gz']):
        raise ValueError('scalar_counter_detailed_audit_not_passed')
    pins = report['input_hashes'] | report['artifact_hashes'] | report['code_hashes']
    pins |= {str((root/'report.json').resolve()): EXPECTED_REPORT,
             str((root/'post-seal-audit.json').resolve()): t.io.digest(root/'post-seal-audit.json'),
             str(Path(__file__).resolve()): t.io.digest(Path(__file__)),
             str(Path('tests/test_harmony_context_scalar_metrics_v2.py').resolve()):
                 t.io.digest(Path('tests/test_harmony_context_scalar_metrics_v2.py'))}
    for p, h in pins.items():
        if t.io.digest(p) != h: raise ValueError('scalar_counter_sealed_input_changed:'+p)
    rows = canonical_records(report['records']); corrected = t.summaries(rows)
    changed = differences(report['tables'], corrected)
    if {p for p, _, _ in changed} != ALLOWED: raise ValueError('scalar_counter_unexpected_other_metric_change')
    for row in rows:
        case = t.load(row['artifact']); old = t.load(case['prior_case_ref'])
        a = t.s.fresh.path_ids(case['result']['selected']) if case['result']['selected'] else None
        b = t.s.fresh.path_ids(old['result']['selected']) if old['result']['selected'] else None
        if a != row['selected_ids'] or b != row['prior_selected_ids']:
            raise ValueError('scalar_counter_source_path_changed')
    result = {'version': VERSION, 'passed': True, 'parent_report_sha256': EXPECTED_REPORT,
        'detailed_audit_sha256': t.io.digest(root/'post-seal-audit.json'),
        'code_pins': {p: h for p, h in pins.items() if p.endswith('scalar_metrics_v2.py')},
        'corrected_tables': corrected,
        'corrections': [{'path': '.'.join(p), 'stored': a, 'corrected': b} for p, a, b in changed],
        'reason': 'pre_serialization_selected_tuple_vs_stored_baseline_list_identity_only',
        'checked_scope_paths': len(rows), 'sha_checks': len(pins),
        'selected_paths_costs_source_and_all_agreement_metrics_unchanged': True,
        'new_search_fit_or_dev': False, 'production_modified': False, 'old_artifacts_overwritten': False}
    t.io.write(dest, result); return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--root', required=True)
    result = run(p.parse_args().root)
    print(json.dumps({k: v for k, v in result.items() if k != 'corrected_tables'}, indent=2), flush=True)
