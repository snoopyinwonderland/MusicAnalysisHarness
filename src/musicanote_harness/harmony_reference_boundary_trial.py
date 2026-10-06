"""Audit all frozen boundaries against separate archival DCML records, train only."""
import argparse
from collections import Counter
import html
import shutil
from pathlib import Path
from .harmony_arpeggio_benchmark import write, digest
from .harmony_shared_tone_trial import load
from .harmony_case_retrieval import load_prepared_package
from .harmony_review_supplement import verified_annotations
from .harmony_reference_boundary import classify, diagnose, VERSION


def time_axis(ir):
    keys = ('sequential_measure_index', 'global_start_quarter',
            'actual_duration_quarter', 'nominal_duration_quarter', 'time_signature')
    return [{k: m[k] for k in keys} for m in ir['measures']]


def run(source, output, review_base):
    if output.exists():
        raise ValueError('choose_new_output')
    previous = load(source/'report.json')
    output.mkdir(parents=True)
    contract = {'version': VERSION, 'source_report_sha256': digest(source/'report.json'),
                'selection': 'every previously frozen boundary; no label-based inclusion',
                'labels_visible_to_diagnostic_only': True, 'blind_accuracy_measured': False,
                'production_modified': False, 'training_eligible': False,
                'code_hashes': {p.name: digest(p) for p in Path(__file__).parent.glob('*.py')}}
    write(output/'run-contract.json', contract)
    records = []; scores = []
    for old in previous['real']:
        cid = old['case_id']; src = source/'real-cases'/cid
        snapshot = src/'source-snapshot'; provenance = load(snapshot/'case-provenance.json')
        entry = provenance['manifest_entry']; folder = Path(entry['package_path'])
        if entry['split'] != 'train' or not entry['rights']['internal_research_use']:
            raise ValueError('train_internal_research_only')
        for name, value in old['source_hashes'].items():
            if digest(snapshot/name) != value: raise ValueError('snapshot_changed')
        if digest(Path(entry['score_source_path'])) != entry['score_sha256']:
            raise ValueError('source_score_changed')
        filenames = ('canonical_music_ir.json', 'imported_annotations.jsonl', 'alignment_records.jsonl')
        hashes = {name: digest(folder/name) for name in filenames}
        package = load_prepared_package(folder); revised = load(snapshot/'candidate_revision_ir.json')
        if package['ir']['ir_document_id'] != entry['ir_document_id']:
            raise ValueError('original_revision_mismatch')
        if time_axis(package['ir']) != time_axis(revised):
            raise ValueError('written_time_axis_changed')
        valid, skipped = verified_annotations(package, entry)
        ids = {a['annotation_id'] for a in valid}
        # Validate source-asset identity without rereading any private books or sending data.
        for a in package['annotations']:
            if a['source_asset_sha256'] != entry['annotation_sha256']:
                raise ValueError('annotation_identity_mismatch')
        assets = {a['source_locator']['path'] for a in package['annotations']}
        for path in assets:
            if digest(Path(path)) != entry['annotation_sha256']: raise ValueError('annotation_source_changed')
        input_hashes = {}
        for sample, meta in enumerate(load(src/'manifest.json')):
            path = src/'samples'/f'{sample}.json'; input_hashes[str(path)] = digest(path)
            result = load(path)
            for bi, b in enumerate(result['boundaries']):
                ref = classify(result['span'], b['boundary'], package['annotations'], ids)
                diagnostic = diagnose(result, bi, ref)
                records.append({'case_id': cid, 'title': old['title'], 'sample': sample, 'boundary': bi,
                    'display': meta['display'], 'span': result['span'], 'cut': b['boundary'],
                    'sample_sha256': input_hashes[str(path)], 'reference': ref, 'diagnostic': diagnostic,
                    'review_url': review_base.rstrip('/')+'/real-cases/'+cid+'/whole-score.html?sample='+str(sample),
                    'source_ir_document_id': entry['ir_document_id'], 'analysis_ir_document_id': revised['ir_document_id'],
                    'alignment_policy': 'equal written measure grid; spans only; old event IDs never reused',
                    'musical_gold': False})
        for path, value in input_hashes.items():
            if digest(Path(path)) != value: raise ValueError('analyzer_input_mutated')
        if hashes != {name: digest(folder/name) for name in filenames}: raise ValueError('package_mutated')
        scores.append({'case_id': cid, 'package_path': str(folder), 'hashes': hashes,
                       'alignment_skips': dict(skipped), 'time_axis_equal': True,
                       'printed_number_changes': [
                           {'index': a['sequential_measure_index'], 'old': a['printed_measure_number'],
                            'new': b['printed_measure_number']}
                           for a,b in zip(package['ir']['measures'], revised['measures'])
                           if a['printed_measure_number'] != b['printed_measure_number']]})
    summary = {'boundaries': len(records),
        'reference_status': dict(Counter(r['reference']['status'] for r in records)),
        'source_classes': dict(Counter(r['reference']['source_class'] for r in records if r['reference']['source_class'])),
        'diagnostic_status': dict(Counter(r['diagnostic']['status'] for r in records)),
        'unsupported_features': dict(Counter(k for r in records for k in r['reference'].get('unsupported_features', [])))}
    report = {'version': VERSION, 'summary': summary, 'scores': scores, 'records': records,
              'accuracy_measured': False, 'production_modified': False, 'source_conditioned_diagnostic': True}
    write(output/'report.json', report)
    for name in ('Campania.woff', 'Campania.LICENSE.txt'):
        shutil.copyfile(source/name, output/name)
    names = {'multiple_reference_changes_within_side': '한쪽 구간 안에 주석 변화 있음',
             'unsupported_reference_chord': '참조 변환 미지원',
             'reference_not_evaluable': '현재 두 화음 비교로 평가 불가',
             'source_hold': '주석상 유지', 'source_member_change': '구성음 변화',
             'source_same_members_semantic_change': '동일 구성음·전위/의미 변화', None: '미분류',
             'pedal': '페달음'}
    rows = []
    for r in records:
        ref = r['reference']
        labels = ' → '.join('<span class="roman">'+html.escape(a['raw_fields'].get('chord',''))+'</span>'
                           for a in ref['source_annotations'])
        ds = r['diagnostic']; changes = [str(c['split_minus_hold_unexplained']['numerator'])+'/'+
                str(c['split_minus_hold_unexplained']['denominator']) for c in ds['comparisons']]
        cells = (r['title'], r['display'], r['boundary'], names.get(ref['source_class'],ref['source_class']),
             names.get(ref['status'],ref['status'])+(' ('+', '.join(names.get(x,x) for x in ref['unsupported_features'])+')' if ref.get('unsupported_features') else ''),
             names.get(ds['status'],ds['status']), ', '.join(changes))
        rows.append('<tr>'+''.join('<td>'+html.escape(str(x))+'</td>' for x in cells[:3])+
            '<td>'+labels+'</td>'+''.join('<td>'+html.escape(str(x))+'</td>' for x in cells[3:])+
            '<td><a href="'+html.escape(r['review_url'], quote=True)+'">전체 악보</a></td></tr>')
    (output/'index.html').write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><title>화음 유지·교체 참조 진단</title>'
        '<style>@font-face{font-family:Campania;src:url(Campania.woff)}.roman{font-family:Campania;font-size:21px}body{font:15px system-ui;margin:24px}table{border-collapse:collapse}td,th{padding:9px;border:1px solid #bbb}th{position:sticky;top:0;background:#eee}</style>'
        '<h1>화음 유지·교체 참조 진단</h1><p>원자료 주석에 조건을 맞춘 train 진단입니다. 자동 탐지 정답률이나 검수된 정답이 아닙니다. '
        '여러 변화·주석 공백·미지원은 제외 사유를 보존합니다. Δ는 분할−유지의 미설명 음가이며 음수만으로 분할을 채택하지 않습니다. '
        '전체 악보 링크는 표본만 선택합니다. 화음과 경계는 이 표의 원주석 및 report.json의 후보 인덱스를 참고해 선택해야 합니다.</p>'
        '<p>검사 경계 '+str(len(records))+'개 · 현 계약에서 수치 비교 가능한 경계 '+str(sum(r['diagnostic']['status']=='ready' for r in records))+
        '개. 0개는 정답률 0%라는 뜻이 아닙니다.</p><p><a href="report.json">원표기·전후 주석·제외 사유 전체 JSON</a></p><table><thead><tr>'+''.join('<th>'+x+'</th>' for x in
            ('악보','구간','경계 인덱스','원주석','주석 분류','참조 상태','후보 대조 상태','Δ 미설명 quarter','악보'))+
        '</tr></thead><tbody>'+''.join(rows)+'</tbody></table></html>', encoding='utf-8')
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--source', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True); p.add_argument('--review-base', required=True)
    a = p.parse_args(); print(run(a.source, a.output, a.review_base)['summary'])
