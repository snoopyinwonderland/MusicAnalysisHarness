"""Supplemental audit of Stage93; do not overwrite its failed v1 reload.

Canonical JSON equality treats a serialized list and its original tuple as
the same data. Independently recompute stored feature arithmetic and trace
every receipt sound/note ID to the full original IR. No new selection or fit.
"""
import argparse
import json
from pathlib import Path
from fractions import Fraction as F
from . import harmony_large_error_triage as t

VERSION = 'harmony-large-error-supplemental-audit-0.1.0'
REPORT_SHA = '1527e7b0a513455243e0aba1d4ff05c705b4c2b79cd2209b095f22952e082f63'


def check_summary(cases, stored):
    if not t.parent.train.same_json(t.summary(cases), stored):
        raise ValueError('large_error_semantic_summary_changed')


def check_feature(profile):
    values = []; available = True
    for r in profile['observations']:
        value = None if r['feature'] is None else t.f(r['feature'])
        if r['availability'] is not (value is not None): raise ValueError('release_availability_mismatch')
        if value is not None:
            if r['reason'] == 'triad_supported_tail_with_one_beat_allowance':
                expected = max(F(), t.f(r['tail_beats'])-t.f(r['allowance_beats']))/t.f(r['normalization_scope_beats'])
            else: expected = F()
            if value != expected: raise ValueError('release_feature_arithmetic_changed')
            values.append(value)
        else: available = False
        if r['source_labels_used'] is not False or r['score_changed'] is not False:
            raise ValueError('release_source_only_contract_changed')
    known = sum(values, F())
    if (t.f(profile['known_partial_sum']) != known or profile['availability'] is not available
            or profile['feature'] != (t.q(known) if available else None)):
        raise ValueError('release_path_sum_changed')


def check_source(profile, ir):
    sounds = {r['sounding_event_id']: r for r in ir['sounding_events']}
    notes = {r['note_id'] for r in ir['note_events']}
    for r in profile['observations']:
        for ident, ids in r['source_note_ids'].items():
            if ident not in sounds or ids != sounds[ident]['source_note_ids'] or not set(ids) <= notes:
                raise ValueError('release_source_reference_changed')
        if not set(r['seventh_event_ids']+r['tail_support_event_ids']) <= set(r['source_event_ids']):
            raise ValueError('release_witness_not_in_observation')
        if r['last_seventh_release'] is not None:
            expected = min(t.f(r['span']['end']), max(t.f(sounds[i]['span']['end']) for i in r['seventh_event_ids']))
            if t.f(r['last_seventh_release']) != expected: raise ValueError('release_sounding_end_changed')


def run(root, output):
    root, output = Path(root), Path(output)
    if output.exists(): raise ValueError('output_exists_no_overwrite')
    if t.io.digest(root/'report.json') != REPORT_SHA: raise ValueError('large_error_report_changed')
    report = t.load(root/'report.json')
    paths = report['input_hashes'] | report['artifact_hashes'] | report['code_hashes']
    for p, sha in paths.items():
        if t.io.digest(p) != sha: raise ValueError('large_error_audit_pin_changed:'+p)
    cases = [t.load(r['artifact']) for r in report['records']]; check_summary(cases, report['summary'])
    cache = {}; profiles = observations = 0
    for case in cases:
        path = case['full_source_paths']['working_ir_path']
        if path not in cache: cache[path] = t.load(path)
        for name in ('target_source_feature', 'winner_source_feature'):
            profile = case[name]
            if profile is None: continue
            check_feature(profile); check_source(profile, cache[path])
            profiles += 1; observations += len(profile['observations'])
    audit = dict(version=VERSION, passed=True, report_sha256=REPORT_SHA,
        original_v1_reload_failure_preserved=True, reason='tuple_list_only_after_lossless_JSON_serialization',
        original_report_code_and_source_unchanged=True,
        unique_pins_verified=len(paths), records=len(cases), full_ir_packages=len(cache),
        feature_path_profiles=profiles, feature_run_observations=observations,
        exact_feature_arithmetic_and_source_references_checked=True,
        musical_feature_accuracy_validated=False, fresh_selection_or_fit=False,
        summary_semantically_identical=True,
        code_pins={str(Path(p).resolve()): t.io.digest(p) for p in (__file__,
            'tests/test_harmony_large_error_audit_v2.py', 'scripts/validate_harmony_large_error_audit_v2.py')})
    t.io.write(output, audit); return audit


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--root', required=True)
    p.add_argument('--output', required=True); a = p.parse_args(); print(json.dumps(run(a.root, a.output), indent=2))
