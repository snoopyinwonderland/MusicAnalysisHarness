"""Read-only explanations of existing heuristic costs and observed pitch spelling.

No reranking, source-label input, Roman-numeral inference, or Core mutation.
"""
import argparse
import hashlib
import json
from fractions import Fraction
from pathlib import Path

from .formal_ir import q
from .harmony_joint import f, prepare, candidates, nct
from .harmony_surface import TEMPLATES
from .harmony_temporal_shadow import provider
from .harmony_cost_diagnostic import transition
from .harmony_review_cohort import validate_split

VERSION = 'harmony-candidate-explanation-0.1.0'
NATURAL = dict(zip('CDEFGAB', (0, 2, 4, 5, 7, 9, 11)))


def spelling_evidence(ir, span, candidate):
    """Conditional tertian spelling supported by observed roots, not local key."""
    root = candidate['root']
    intervals = dict(TEMPLATES).get(candidate['label'].partition(':')[2])
    if root is None or intervals is None:
        return {'status': 'not_applicable', 'candidates': []}
    a, b = f(span['start']), f(span['end'])
    observed = []
    unsupported = []
    for s in ir['sounding_events']:
        if f(s['span']['start']) >= b or f(s['span']['end']) <= a:
            continue
        p = s['pitch']; step = p.get('step'); alter = p.get('alter'); midi = p.get('midi_pitch')
        if step not in NATURAL or not isinstance(alter, dict) or midi is None:
            unsupported.append(s['sounding_event_id']); continue
        alteration = f(alter)
        if alteration.denominator != 1 or (NATURAL[step]+alteration) % 12 != midi % 12:
            unsupported.append(s['sounding_event_id']); continue
        observed.append((step, int(alteration), midi % 12, s['sounding_event_id']))
    roots = sorted({(step, alter) for step, alter, pc, _ in observed if pc == root})
    answers = []
    for step, alter in roots:
        expected = []
        for i, interval in enumerate(intervals):
            letter = 'CDEFGAB'[('CDEFGAB'.index(step)+2*i) % 7]
            pc = (root+interval) % 12
            acc = (pc-NATURAL[letter]+6) % 12-6
            expected.append((letter, acc, pc))
        support = []; conflict = []
        for letter, acc, pc, ref in observed:
            if pc in candidate['pcs']:
                (support if (letter, acc, pc) in expected else conflict).append(ref)
        def name(letter, acc):return letter+('#'*acc if acc > 0 else 'b'*(-acc))
        answers.append({'root_spelling': name(step, alter),
                        'conditional_label': name(step, alter)+':'+candidate['label'].partition(':')[2],
                        'expected_members': [name(letter, acc) for letter, acc, _ in expected],
                        'supported_event_refs': support, 'conflicting_event_refs': conflict,
                        'missing_member_pcs': [pc for _, _, pc in expected if not any(v[2] == pc for v in observed)]})
    # Absence of a sounded root is not evidence for an invented enharmonic root.
    return {'status': 'conditional_spelling_not_function' if roots else 'root_spelling_unobserved',
            'pc_label_unchanged': candidate['label'], 'candidates': answers,
            'unsupported_pitch_event_refs': unsupported, 'used_for_ranking': False}


def explain_candidate(ir, span, candidate, beat):
    a, b = f(span['start']), f(span['end'])
    if a < 0 or b <= a or beat <= 0:
        raise ValueError('invalid_span_or_beat')
    rows, neighbors = prepare(ir)
    active = [r for r in rows if r['start'] < b and r['end'] > a]
    if candidate['root'] is None:
        return {'label': candidate['label'], 'status': 'rest_or_unknown_no_template_explanation'}
    total = sum((min(r['end'], b)-max(r['start'], a) for r in active), Fraction(0))
    if not total:
        raise ValueError('pitched_candidate_without_sound')
    pcs = set(candidate['pcs']); notes = []
    for r in active:
        overlap = min(r['end'], b)-max(r['start'], a)
        member = r['pitch'] % 12 in pcs
        hypothesis = None if member else nct(r, pcs, a, b, neighbors, beat)
        residual = 0 if member else (1-hypothesis['strength'] if hypothesis else 1)
        notes.append({'sounding_event_id': r['id'], 'spelling': r['spelling'], 'midi_pitch': r['pitch'],
                      'original_span': {'start': q(r['start']), 'end': q(r['end'])},
                      'overlap_quarters': q(overlap), 'pc_template_member': member,
                      'conditional_nct': hypothesis, 'unexplained_cost': .7*float(overlap/total)*residual})
    at_start = [r for r in active if r['start'] <= a < r['end']]
    bass = min(r['pitch'] for r in at_start or active)
    observed = {r['pitch'] % 12 for r in active}
    parts = {'unexplained_notes': sum(n['unexplained_cost'] for n in notes),
             'missing_template_members': .3*(1-len(pcs & observed)/len(pcs)),
             'bass_not_root': .04*(bass % 12 != candidate['root'])}
    pooled = sum(parts.values())
    expected = candidate.get('pooled_cost', candidate['cost'])
    if abs(pooled-expected) > 1e-9:
        raise ValueError('candidate_cost_reconstruction_mismatch')
    return {'label': candidate['label'], 'span': span, 'pooled_cost_parts': parts,
            'pooled_cost': pooled, 'temporal_regret': candidate.get('temporal_regret', 0),
            'total_candidate_cost': candidate['cost'], 'summed_voice_duration_quarters': q(total),
            'bass_midi': bass, 'notes': notes, 'spelling_evidence': spelling_evidence(ir, span, candidate),
            'limits': ['PC membership is not a confirmed musical role',
                       'Bass penalty is a scoring preference, not an inversion error',
                       'Duplicate/doubled voices each contribute duration weight']}


def explain_path(result, verify=True):
    previous = None; segments = []
    for s in result['segments']:
        candidate = s['selected']; duration = float((f(s['span']['end'])-f(s['span']['start']))/f(s['beat_unit_quarter']))
        change, resolution = transition(previous, candidate)
        parts = {'pooled_fit': duration*candidate.get('pooled_cost', candidate['cost']),
                 'temporal_regret': duration*candidate.get('temporal_regret', 0),
                 'boundary_contrast': duration*candidate.get('boundary_contrast_cost', 0),
                 'segment_charge': s.get('segment_policy', {}).get('charge', .15),
                 'label_change': change, 'resolution_discount': resolution}
        segments.append({'span': s['span'], 'label': candidate['label'], 'cost_parts': parts})
        previous = candidate
    total = sum(sum(s['cost_parts'].values()) for s in segments)
    if verify and abs(total-result['path_cost']) > 1e-8:
        raise ValueError('path_cost_reconstruction_mismatch')
    return {'segments': segments, 'reconstructed_path_cost': total,
            'limits': ['Cost of selected path only; not proof of global optimality or musical correctness']}


def score_fixed_path(ir, result, use_temporal):
    """Compare the same paths under the same objective, without a new search."""
    rows, neighbors = prepare(ir)
    choose = provider(cell_divisions=2, measures=ir.get('measures', [])) if use_temporal else candidates
    segments = []
    for s in result['segments']:
        alternatives = choose(rows, neighbors, f(s['span']['start']), f(s['span']['end']),
                              f(s['beat_unit_quarter']), limit=None)
        c = next((c for c in alternatives if c['label'] == s['selected']['label']), None)
        if c is None:raise ValueError('fixed_path_candidate_no_longer_proposed')
        segments.append({**s, 'selected': c})
    return explain_path({'segments': segments}, verify=False)


def build(manifest, comparison_dir, output):
    source = Path(comparison_dir)
    raw = Path(manifest).read_bytes(); entries = json.loads(raw)['entries']; validate_split(entries)
    bypackage = {e['package_path']: e for e in entries}
    if len(bypackage) != len(entries):raise ValueError('duplicate_manifest_package')
    plan_raw = (source/'report.json').read_bytes(); plan = json.loads(plan_raw)
    if plan['manifest_sha256'] != hashlib.sha256(raw).hexdigest():
        raise ValueError('manifest_changed')
    queue_raw = (source/'cases.jsonl').read_bytes()
    queue_rows = list(map(json.loads, queue_raw.decode('utf-8').splitlines()))
    queue = {r['case_id']: r for r in queue_rows}
    if len(queue) != len(queue_rows):raise ValueError('duplicate_queue_case')
    selected = [i for i in plan['plan'] if i['comparison']['label_sequence_changed']]
    for item in selected:
        case = queue[item['case_id']]; entry = bypackage[case['package_path']]
        if any(r['split'] != 'train' for r in (item, case, entry)):
            raise ValueError('non_train_case')
        for key in ('score_id', 'ir_document_id', 'work_family_id', 'score_sha256', 'annotation_sha256', 'rights'):
            if case[key] != entry[key]:raise ValueError('identity_mismatch:'+key)
        if item['target_span'] != case['target_span']:raise ValueError('target_changed')
    out = Path(output); out.mkdir(parents=True, exist_ok=True); summaries = []
    for item in selected:
        case = queue[item['case_id']]; entry = bypackage[case['package_path']]
        data = (Path(case['package_path'])/'canonical_music_ir.json').read_bytes()
        if hashlib.sha256(data).hexdigest() != item['ir_sha256']:raise ValueError('live_ir_hash_mismatch')
        if hashlib.sha256(Path(entry['score_source_path']).read_bytes()).hexdigest() != entry['score_sha256']:
            raise ValueError('live_score_hash_mismatch')
        ir = json.loads(data)
        if ir['ir_document_id'] != entry['ir_document_id'] or ir['score']['score_id'] != entry['score_id']:
            raise ValueError('live_ir_identity_mismatch')
        detail_raw = (source/(item['case_id']+'.json')).read_bytes(); detail = json.loads(detail_raw)
        if any(detail[k] != item[k] for k in ('case_id', 'target_span', 'ir_sha256', 'absolute_window')):
            raise ValueError('source_detail_mismatch')
        target = item['target_span']; a, b = f(target['start']), f(target['end'])
        measures = sorted(ir.get('measures', []), key=lambda m: f(m['global_start_quarter']))
        m = next((m for m in reversed(measures) if f(m['global_start_quarter']) <= a), None)
        beat = Fraction(4, m['time_signature']['beat_type']) if m else Fraction(1)
        rows, neighbors = prepare(ir)
        choose = provider(cell_divisions=2, measures=measures)
        choices = choose(rows, neighbors, a, b, beat, limit=None)
        chosen_labels = {s['selected']['label'] for engine in ('baseline', 'experiment') for s in detail[engine]['segments']
                         if f(s['span']['start']) < b and f(s['span']['end']) > a}
        target_choices = [c for i,c in enumerate(choices) if i < 5 or c['label'] in chosen_labels]
        paths = {}; inferred = {}
        for engine in ('baseline', 'experiment'):
            paths[engine] = explain_path(detail[engine])
            inferred[engine] = [explain_candidate(ir, s['span'], s['selected'], f(s['beat_unit_quarter']))
                                for s in detail[engine]['segments']
                                if f(s['span']['start']) < b and f(s['span']['end']) > a]
        span_checks = []
        spans = sorted({(f(s['span']['start']), f(s['span']['end']), f(s['beat_unit_quarter']))
                        for engine in ('baseline', 'experiment') for s in detail[engine]['segments']
                        if f(s['span']['start']) < b and f(s['span']['end']) > a})
        for x, y, unit in spans:
            span_choices = choose(rows, neighbors, x, y, unit, limit=None)
            span_checks.append({'span': {'start': q(x), 'end': q(y)},
                                'candidates': [explain_candidate(ir, {'start': q(x), 'end': q(y)}, c, unit)
                                               for i,c in enumerate(span_choices) if i < 3 or c['label'] in chosen_labels],
                                'labels_not_proposed': sorted(chosen_labels-{c['label'] for c in span_choices})})
        record = {'case_id': item['case_id'], 'collection': item['collection'], 'target_span': target,
                  'ir_sha256': item['ir_sha256'], 'source_detail_sha256': hashlib.sha256(detail_raw).hexdigest(),
                  'selected_paths': paths, 'selected_inferred_spans': inferred,
                  'fixed_path_cross_objectives': {
                      objective: {engine: score_fixed_path(ir, detail[engine], objective == 'temporal')
                                  for engine in ('baseline', 'experiment')}
                      for objective in ('pooled', 'temporal')},
                  'same_inferred_span_comparisons': span_checks,
                  'same_target_candidates': [explain_candidate(ir, target, c, beat) for c in target_choices],
                  'labels_not_proposed_on_target': sorted(chosen_labels-{c['label'] for c in choices}),
                  'policy': 'Target-only candidate audit is not a new inferred segmentation; no source labels input'}
        (out/(item['case_id']+'.json')).write_text(json.dumps(record, indent=2), encoding='utf-8')
        summaries.append({'case_id': item['case_id'], 'collection': item['collection'],
                          'target_top_labels': [c['label'] for c in choices[:3]],
                          'path_costs_verified': True})
    result = {'version': VERSION, 'manifest_sha256': hashlib.sha256(raw).hexdigest(),
              'source_plan_sha256': hashlib.sha256(plan_raw).hexdigest(),
              'source_queue_sha256': hashlib.sha256(queue_raw).hexdigest(), 'cases': summaries,
              'production_enabled': False, 'accuracy_measured': False, 'reserved_contents_read': False}
    (out/'report.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2)); return result


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--manifest', required=True); p.add_argument('--comparison-dir', required=True)
    p.add_argument('--output', required=True)
    args = p.parse_args(); build(args.manifest, args.comparison_dir, args.output)
