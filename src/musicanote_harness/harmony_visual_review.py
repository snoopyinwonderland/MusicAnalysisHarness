"""Render saved harmony experiments on original notation; never rerun/rerank inference.

Source Roman labels and display-only key-relative projections are separate tracks.
Build local research artifacts, not a production analysis release.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import html
import json
import re
import shutil
from pathlib import Path
from xml.etree import ElementTree as ET

from .engraving import render_musicxml_pages
from .harmony_candidate_explanation import spelling_evidence
from .harmony_joint import f
from .harmony_review_cohort import validate_split

VERSION = 'harmony-visual-review-0.3.0'
ASSETS = Path(__file__).with_name('visual_review_assets')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def overlaps(left, right):
    return f(left['start']) < f(right['end']) and f(left['end']) > f(right['start'])


def key_token(value):
    """Keep lowercase b as B minor; only later b characters denote flats."""
    return value[:1] + value[1:].replace('b', '-')


def source_reference_key(annotation):
    """Resolve imported local-key context for display, never feed it to inference."""
    from music21 import key, roman
    from music21.exceptions21 import Music21Exception
    fields = annotation.get('raw_fields', {})
    global_key, local = fields.get('globalkey'), fields.get('localkey')
    minor = fields.get('localkey_is_minor')
    if not global_key or not local or minor not in ('0', '1'):
        return None
    try:
        root = roman.RomanNumeral(local, key.Key(key_token(global_key))).root().name.replace('-', 'b')
        return root[0].lower()+root[1:] if minor == '1' else root
    except (ValueError, Music21Exception):
        return None


def roman_projection(ir, span, candidate, reference_key, bass_cell=None):
    """Display only, root position, supplied reference key. Not inferred function/inversion."""
    answer = {'text': 'unknown', 'status': 'unavailable', 'reference_key': reference_key,
              'policy': 'display_only_supplied_key_root_position_not_function',
              'used_for_inference': False}
    if not reference_key or candidate.get('root') is None:
        return answer
    evidence = spelling_evidence(ir, span, candidate)
    supported = [r for r in evidence.get('candidates', []) if not r['conflicting_event_refs']]
    if len(supported) != 1:
        answer['reason'] = 'ambiguous_or_unobserved_root_spelling'
        return answer
    from music21 import chord, key, pitch, roman
    from music21.exceptions21 import Music21Exception
    names = supported[0]['expected_members']
    pitches = []
    for name in names:
        p = pitch.Pitch(name.replace('b', '-') + '4')
        while pitches and p.midi <= pitches[-1].midi:
            p.octave += 1
        pitches.append(p)
    try:
        reference = key.Key(key_token(reference_key))
        rn = roman.romanNumeralFromChord(chord.Chord(pitches), reference,
                                        preferSecondaryDominants=False)
        # Omit music21's added figured-bass alterations (e.g. II75#3).
        # This is explicitly root/quality shorthand, not figured bass/inversion.
        suffix = {'major': '', 'minor': '', 'diminished': 'o', 'augmented': '+',
                  'dominant7': '7', 'major7': 'M7', 'minor7': '7',
                  'half-diminished7': 'ø7', 'diminished7': 'o7'}
        quality=candidate['label'].partition(':')[2]
        figure = rn.romanNumeral + suffix[quality]
        if bass_cell is not None:
            ix=bass_cell.get('inversion_index')
            if ix is None:
                answer['reason']=bass_cell.get('status','inversion_unresolved')
                return answer
            seventh=quality.endswith('7')
            figures=('7','65','43','2') if seventh else ('','6','64')
            if not 0<=ix<len(figures):
                answer['reason']='unsupported_inversion';return answer
            sign={'half-diminished7':'ø','diminished7':'o','diminished':'o','augmented':'+','major7':'M'}.get(quality,'')
            figure=rn.romanNumeral+sign+figures[ix]
            answer.update(policy='display_supplied_key_candidate_conditioned_acoustic_inversion',
                          inversion_index=ix,bass_status=bass_cell['status'])
    except (ValueError, Music21Exception) as exc:
        # Rendering must not invent a figure for an unsupported source key/dialect.
        answer['reason'] = type(exc).__name__
        return answer
    answer.update(text=figure, status='conditional_display', root_spelling=supported[0]['root_spelling'])
    return answer


def system_fragments(pages, context_note_ids):
    """Keep original SVG systems + defs; no lossy reconstruction from events."""
    result = []
    for page_index, page in enumerate(pages):
        root = ET.fromstring(page)
        systems = [e for e in root.iter() if 'system' in e.get('class', '').split()]
        selected = [i for i, system in enumerate(systems)
                    if any((e.get('data-id') or e.get('id')) in context_note_ids for e in system.iter())]
        for index in selected:
            fragment = copy.deepcopy(root)
            copies = [e for e in fragment.iter() if 'system' in e.get('class', '').split()]
            parents = {c: p for p in fragment.iter() for c in p}
            for i, system in enumerate(copies):
                if i != index:
                    parents[system].remove(system)
            # Page-level running headers/footers are not part of a context system.
            for e in list(fragment.iter()):
                if set(e.get('class', '').split()) & {'pgHead', 'pgFoot'} and e in parents:
                    parents[e].remove(e)
                # ElementTree's ns1:href is not recognized by the HTML SVG parser.
                href = e.get('{http://www.w3.org/1999/xlink}href')
                if href:
                    e.set('href', href)
                    del e.attrib['{http://www.w3.org/1999/xlink}href']
            # Flatten the percentage-sized inner SVG so a cropped root viewBox
            # cannot recursively change its scale and break note coordinates.
            inner = next((e for e in fragment if 'definition-scale' in e.get('class', '').split()), None)
            if inner is not None:
                for key in ('viewBox', 'color', 'font-family'):
                    if inner.get(key):
                        fragment.set(key, inner.get(key))
                fragment.remove(inner)
                fragment.extend(list(inner))
            result.append({'page': page_index + 1, 'system': index + 1,
                           'svg': ET.tostring(fragment, encoding='unicode')})
    return result


def make_payload(ir, audit, result):
    annotations = audit['verified_source_context']
    keys = {source_reference_key(a) for a in annotations if overlaps(a['target']['span'], audit['target_span'])}
    reference_key = next(iter(keys)) if len(keys) == 1 and None not in keys else None
    tracks = []
    source = []
    for a in annotations:
        source.append({'id': a['annotation_id'], 'span': a['target']['span'],
                       'roman': a['components'].get('chord') or 'unknown',
                       'cadence': a['components'].get('cadence') or '',
                       'label': a['raw_label'], 'kind': 'source',
                       'reference_key': source_reference_key(a),
                       'key_context': a['components'], 'provenance': a['source_locator'],
                       'roman_status': 'imported_not_gold'})
    tracks.append({'id': 'source', 'name': '원자료 주석 · 정답 승인 전', 'segments': source})
    for run in result['runs']:
        comparisons = [('baseline', result.get('track_names', {}).get('baseline', '최초 기준 계산 · joint v0.1'), run['baseline'], None)]
        if 'variants' in run:
            comparisons += [('experiment', result['arm_names'][arm], value, arm) for arm, value in run['variants'].items()]
        else:
            comparisons.append(('experiment', result.get('track_names', {}).get('experiment', '이전 실험 · temporal v0.3'), run['experiment'], None))
        for engine, name, calculated, variant in comparisons:
            segments = []
            for i, s in enumerate(calculated['segments']):
                display = roman_projection(ir, s['span'], s['selected'], reference_key)
                segments.append({'id': f'{engine}-{variant or "default"}-{f(run["margin_quarters"])}-{i}',
                                 'span': s['span'], 'roman': display['text'],
                                 'roman_status': display['status'], 'roman_projection': display,
                                 'label': s['selected']['label'], 'kind': engine,
                                 'selected': s['selected'], 'alternatives': s.get('alternatives', []),
                                 'engine_version': calculated['engine_version']})
            tracks.append({'id': f'{engine}-{variant or "default"}-{f(run["margin_quarters"])}', 'kind': engine, 'variant': variant,
                           'name': name, 'margin': str(f(run['margin_quarters'])),
                           'analysis_span': run['analysis_span'], 'segments': segments})
    return {'version': VERSION, 'case_id': audit['case_id'],
            'title': ir['score'].get('title') or Path(audit['source_xml']).stem,
            'source_file': Path(audit['source_xml']).name,
            'target_span': audit['target_span'], 'context_span': audit['context_excerpt']['context_span'],
            'reference_key': reference_key, 'tracks': tracks,
            'notes': [{k: n[k] for k in ('note_id', 'measure_id', 'global_onset_quarter',
                       'notated_duration_quarter', 'written_pitch', 'tie_role')} for n in ir['note_events']],
            'measures': ir['measures'], 'flags': audit['flags'],
            'stability': result.get('stability_components', audit['stability_components']),
            'cells': audit['target_cell_evidence'], 'source_boundaries': audit['source_boundary_types'],
            'score_sha256': audit['score_sha256'], 'result_sha256': audit['source_result_sha256'],
            'comparison': result.get('comparison_provenance'),
            'ablation': result.get('ablation_provenance'), 'arm_names': result.get('arm_names'),
            'arm_stability': result.get('arm_stability'),
            'gate_diagnostic_version': 'temporal-support-shadow-0.3.0',
            'musical_gold': False, 'production_enabled': False}


def write_page(payload, fragments, destination):
    encoded = json.dumps(payload, ensure_ascii=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    score = ''.join('<section class="score-system"><div class="range-layer"></div>'
                    f'<div class="engraving">{row["svg"]}</div></section>' for row in fragments)
    template = (ASSETS/'review.html').read_text(encoding='utf-8')
    page = template.replace('<!--SCORE-->', score).replace('<!--PAYLOAD-->', encoded)
    Path(destination).write_text(page, encoding='utf-8')


def verified_comparison(previous, previous_hash, replacement, replacement_hash, expected):
    """A new baseline must be the exact saved prior experiment, not a relabelled run."""
    if replacement_hash != expected['result_sha256'] or replacement['previous_result_sha256'] != previous_hash:
        raise ValueError('comparison_result_hash_mismatch')
    for key in ('case_id', 'target_span', 'ir_sha256'):
        if replacement[key] != previous[key] or replacement[key] != expected[key]:
            raise ValueError('comparison_identity_mismatch')
    if len(previous['runs']) != len(replacement['runs']):
        raise ValueError('comparison_run_count_mismatch')
    for before, after in zip(previous['runs'], replacement['runs']):
        if (before['margin_quarters'] != after['margin_quarters'] or before['analysis_span'] != after['analysis_span']
                or before['experiment'] != after['baseline']):
            raise ValueError('comparison_previous_engine_changed')
    return {**replacement, 'comparison_provenance': {
        'previous_result_sha256': previous_hash, 'new_result_sha256': replacement_hash,
        'previous_track': 'saved temporal v0.3', 'new_track': 'multiscale v0.1 shadow',
        'inference_rerun_by_viewer': False}}


def verified_ablation(previous, ablation, actual_hash, expected):
    from .harmony_ablation_review import ARMS, NAMES, replay_matches
    if actual_hash != expected['result_sha256'] or ablation['previous_result_sha256'] != previous['comparison_provenance']['previous_result_sha256']:
        raise ValueError('ablation_hash_mismatch')
    if ablation['multiscale_result_sha256'] != previous['comparison_provenance']['new_result_sha256']:
        raise ValueError('ablation_previous_result_changed')
    for key in ('case_id', 'target_span', 'ir_sha256'):
        if ablation[key] != previous[key] or ablation[key] != expected[key]:
            raise ValueError('ablation_identity_mismatch')
    if len(ablation['runs']) != len(previous['runs']) or ablation['arm_names'] != NAMES:
        raise ValueError('ablation_runs_or_arm_names_changed')
    result = copy.deepcopy(previous)
    for old, new, target in zip(previous['runs'], ablation['runs'], result['runs']):
        if old['margin_quarters'] != new['margin_quarters'] or old['analysis_span'] != new['analysis_span']:
            raise ValueError('ablation_context_changed')
        for arm, switches in ARMS.items():
            if new[arm]['analysis_span'] != new['analysis_span'] or any(new[arm]['policy'][k] != v for k, v in switches.items()):
                raise ValueError('ablation_arm_policy_changed')
        if not replay_matches(old['baseline'], new['none']) or not replay_matches(old['experiment'], new['both']):
            raise ValueError('ablation_replay_failed')
        target['variants'] = {arm: new[arm] for arm in ARMS}
    result.update(arm_names=NAMES, arm_stability=ablation['stability_components'],
                  ablation_provenance={'result_sha256': actual_hash, 'all_replays_verified': True,
                                       'inference_rerun_by_viewer': False})
    return result


def build(manifest, audit_dir, review_dir, output, font_dir, comparison_dir=None, ablation_dir=None):
    out = Path(output)
    if out.exists():
        raise ValueError('output_exists_choose_new_run_directory')
    manifest_path = Path(manifest)
    entries = json.loads(manifest_path.read_text(encoding='utf-8'))['entries']
    validate_split(entries)
    audit_dir, review_dir = Path(audit_dir), Path(review_dir)
    audit_report = json.loads((audit_dir/'report.json').read_text(encoding='utf-8'))
    if digest(manifest_path) != audit_report['manifest_sha256']:
        raise ValueError('manifest_changed')
    plan_path = review_dir/'plan/cases.jsonl'
    if digest(plan_path) != audit_report['queue_sha256']:
        raise ValueError('case_queue_changed')
    comparison_cases = {}
    ablation_cases = {}
    if ablation_dir and not comparison_dir:
        raise ValueError('ablation_requires_verified_previous_comparison')
    if comparison_dir:
        comparison_dir = Path(comparison_dir)
        comparison_report = json.loads((comparison_dir/'report.json').read_text(encoding='utf-8'))
        if (comparison_report['manifest_sha256'] != digest(manifest_path) or
                comparison_report['plan_sha256'] != digest(review_dir/'plan/report.json') or
                comparison_report['queue_sha256'] != digest(plan_path)):
            raise ValueError('comparison_plan_changed')
        comparison_cases = {c['case_id']: c for c in comparison_report['cases']}
    if ablation_dir:
        ablation_dir = Path(ablation_dir)
        ablation_report = json.loads((ablation_dir/'report.json').read_text(encoding='utf-8'))
        if (any(ablation_report[k] != comparison_report[k] for k in ('manifest_sha256', 'plan_sha256', 'queue_sha256')) or
                ablation_report['previous_report_sha256'] != digest(comparison_dir/'report.json')):
            raise ValueError('ablation_plan_changed')
        ablation_cases = {c['case_id']: c for c in ablation_report['cases']}
    queue = {r['case_id']: r for r in map(json.loads, plan_path.read_text(encoding='utf-8').splitlines())}
    packages = {e['package_path']: e for e in entries}
    tasks = []
    # Entire metadata preflight before reading score packages.
    for summary in audit_report['cases']:
        case_id = summary['case_id']
        if not re.fullmatch(r'reviewm_[a-f0-9]+', case_id):
            raise ValueError('invalid_case_id')
        case = queue[case_id]; entry = packages[case['package_path']]
        if case['split'] != 'train' or entry['split'] != 'train':
            raise ValueError('non_train_case')
        for k in ('score_id', 'ir_document_id', 'score_sha256', 'annotation_sha256', 'rights'):
            if case[k] != entry[k]:
                raise ValueError('identity_mismatch:'+k)
        if not entry['rights'].get('internal_research_use'):
            raise ValueError('internal_research_not_allowed')
        tasks.append((case, entry))
    for name in ('Campania.woff', 'Campania.LICENSE.txt'):
        if not (Path(font_dir)/name).is_file():
            raise ValueError('font_and_license_required')
    out.mkdir(parents=True)
    for name in ('review.css', 'review.js'):
        shutil.copyfile(ASSETS/name, out/name)
    for name in ('Campania.woff', 'Campania.LICENSE.txt'):
        shutil.copyfile(Path(font_dir)/name, out/name)
    rows = []
    for case, entry in tasks:
        case_id = case['case_id']; audit_path = audit_dir/(case_id+'.json')
        audit = json.loads(audit_path.read_text(encoding='utf-8'))
        result_path = review_dir/'results'/(case_id+'.json')
        if digest(result_path) != audit['source_result_sha256']:
            raise ValueError('result_changed')
        if digest(entry['score_source_path']) != audit['score_sha256']:
            raise ValueError('score_changed')
        for name, expected in audit['package_hashes'].items():
            if digest(Path(entry['package_path'])/name) != expected:
                raise ValueError('package_changed:'+name)
        ir = json.loads((Path(entry['package_path'])/'canonical_music_ir.json').read_text(encoding='utf-8'))
        result = json.loads(result_path.read_text(encoding='utf-8'))
        if (audit['case_id'] != case_id or result['case_id'] != case_id or
                audit['target_span'] != case['target_span'] or result['target_span'] != case['target_span'] or
                ir['ir_document_id'] != entry['ir_document_id']):
            raise ValueError('case_identity_mismatch')
        if comparison_dir:
            replacement_path = comparison_dir/'results'/(case_id+'.json')
            replacement = json.loads(replacement_path.read_text(encoding='utf-8'))
            result = verified_comparison(result, digest(result_path), replacement,
                                         digest(replacement_path), comparison_cases[case_id])
        if ablation_dir:
            ablation_path = ablation_dir/'results'/(case_id+'.json')
            result = verified_ablation(result, json.loads(ablation_path.read_text(encoding='utf-8')),
                                       digest(ablation_path), ablation_cases[case_id])
        print(json.dumps({'rendering': case_id, 'source': Path(entry['score_source_path']).name}), flush=True)
        pages, mapping = render_musicxml_pages(entry['score_source_path'], ir)
        context_ids = {n['note_id'] for n in audit['context_excerpt']['note_events']}
        fragments = system_fragments(pages, context_ids)
        rendered = set()
        for fragment in fragments:
            for e in ET.fromstring(fragment['svg']).iter():
                if (e.get('data-id') or e.get('id')) in context_ids:
                    rendered.add(e.get('data-id') or e.get('id'))
        if not fragments or context_ids-rendered:
            raise ValueError('incomplete_context_engraving:'+case_id)
        payload = make_payload(ir, audit, result)
        payload['mapping'] = {'context_notes': len(context_ids), 'rendered_context_notes': len(rendered),
                              'full_score_complete': mapping['complete'],
                              'semantic_mismatches': mapping['semantic_mismatches']}
        write_page(payload, fragments, out/(case_id+'.html'))
        (out/(case_id+'.json')).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        rows.append({'case_id': case_id, 'title': payload['title'], 'collection': entry['collection_id'], 'source_file': payload['source_file'],
                     'systems': len(fragments), 'mapping': payload['mapping'],
                     'audit_sha256': digest(audit_path), 'result_sha256': digest(result_path),
                     'comparison': payload['comparison'], 'ablation': payload['ablation']})
    links = ''.join(f'<li><a href="{r["case_id"]}.html">{html.escape(r["collection"])} · {html.escape(r["title"])} · '
                    f'{html.escape(r["source_file"])}</a><p>{r["case_id"]} · {r["systems"]}개 악보 줄</p></li>' for r in rows)
    index = '<!doctype html><html lang="ko"><meta charset="utf-8"><link rel="stylesheet" href="review.css">'
    index += '<title>화성 실험 · 악보 비교 사례</title><main class="gallery"><h1>화성 실험 · 악보 비교</h1>'
    index += f'<p>검토 {len(rows)}사례. 원자료 주석과 두 계산 버전을 원본 악보 위에서 비교합니다.</p>'
    if comparison_dir and not ablation_dir:
        summary = comparison_report['summary']
        index += '<p>이번 계산: 분산·5음 생략 증거 보완 후보. 이전 temporal v0.3과 비교합니다. 최초 joint 기준과의 비교가 아닙니다.</p>'
        index += f'<p>30사례 문맥 안정성 17 → {summary["context_stable_counts"]["experiment"]}. 정답률이 아닙니다. 안정성 저하 사례도 아래에 포함했습니다.</p>'
    if ablation_dir:
        index += '<p>이번 화면은 새 개선안의 승격이 아니라, 두 보완 기능의 효과를 따로 확인하는 실험입니다.</p>'
        index += '<p>상단의 보완 조건 선택으로 보완 없음 / 5음 생략만 / 분산 누적만 / 둘 다를 비교할 수 있습니다. 아래 악보의 회색은 항상 이전 temporal 기준입니다.</p>'
        index += '<ul>'+''.join('<li>'+html.escape(ablation_report['arm_names'][arm])+': '+str(count)+'/30</li>'
                               for arm,count in ablation_report['summary']['context_stable_counts'].items())+'</ul><p>위 수치는 문맥 길이를 바꿔도 결과가 유지되는 사례 수이며 정답률이 아닙니다.</p>'
    index += '<p>해결 완료나 정답 승인을 뜻하지 않습니다. 실험은 현재 서비스의 분석을 바꾸지 않습니다.</p>'
    index += '<p>화성 구간을 클릭하면 해당 음표가 1초 강조됩니다. 오른쪽에서 원래 화음 이름과 판단 근거를 확인하세요.</p><ol>'+links+'</ol></main></html>'
    (out/'index.html').write_text(index, encoding='utf-8')
    report = {'version': VERSION, 'cases': rows, 'manifest_sha256': digest(manifest_path),
              'audit_report_sha256': digest(audit_dir/'report.json'),
              'code_sha256': digest(__file__), 'asset_sha256': {p.name: digest(p) for p in ASSETS.iterdir() if p.is_file()},
              'production_enabled': False, 'inference_rerun': False,
              'roman_policy': 'source_labels_separate_from_display_only_target_local_key_root_position_projection',
              'local_research_only': True}
    (out/'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for flag in ('manifest', 'audit-dir', 'review-dir', 'output', 'font-dir'):
        parser.add_argument('--'+flag, required=True)
    parser.add_argument('--comparison-dir')
    parser.add_argument('--ablation-dir')
    args = parser.parse_args()
    print(json.dumps(build(args.manifest, args.audit_dir, args.review_dir, args.output, args.font_dir, args.comparison_dir, args.ablation_dir), ensure_ascii=False))
