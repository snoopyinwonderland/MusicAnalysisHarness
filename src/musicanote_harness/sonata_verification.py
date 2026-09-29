"""Explicit development-score verification, separate from production and holdout.

Score names select inputs only. All timing, mapping and sampling rules are generic.
Source harmony labels never enter the two inference calls.
"""
import argparse
from collections import Counter
from copy import deepcopy
from fractions import Fraction
import html
import json
from pathlib import Path
import shutil
import time
from xml.etree import ElementTree as ET

from .dcml_import import prepare_dcml, write_dcml_package, parse_score_without_imported_harmony
from .source_sequence_audit import parser_rows, xml_rows, match_sequences
from .source_identity_revision import revise, validate_revision, alignment_membership
from .source_note_mapping_audit import compare, xml_inventory, write
from .harmony_visual_review import digest, system_fragments, write_page, roman_projection, source_reference_key, ASSETS
from .harmony_joint import f
from .formal_ir import q
from .harmony_multiscale_shadow import analyze, VERSION as ENGINE_VERSION
from .harmony_bass import display_groups

VERSION = 'sonata-verification-0.1.0'


def observation_rows(ir, source):
    score, _, mapping = parse_score_without_imported_harmony(source)
    parsed = parser_rows(score, mapping)
    original, _ = xml_rows(source)
    matches, rejected = match_sequences(parsed, original)
    refs = {r['source_ref_id']: r for r in ir['source_references']}
    events = {refs[n['source_ref_id']]['local_fingerprint']: n
              for n in ir['note_events'] + ir['rest_events']}
    if len(events) != len(parsed) or set(events) != {p['fingerprint'] for p in parsed}:
        raise ValueError('event_identity_not_reproduced')
    if rejected or len(matches) != len(original):
        raise ValueError('source_sequence_incomplete:' + str(Counter(r['reason'] for r in rejected)))
    return [{'event_id': events[p['fingerprint']].get('note_id', events[p['fingerprint']].get('rest_id')),
             'source_ref_id': events[p['fingerprint']]['source_ref_id'],
             'fingerprint': p['fingerprint'], 'kind': p['kind'], 'parser': p, 'original': r}
            for p, r in matches]


def sample_windows(ir, width=4, repair_proof=None):
    """Predeclare first/middle/last physical measures, independent of annotations."""
    measures = ir['measures']
    if width < 1 or not measures:
        raise ValueError('invalid_window_width_or_empty_score')
    starts = sorted({0, max(0, len(measures)//2-width//2), max(0, len(measures)-width)})
    repair_starts=set()
    for edit in (repair_proof or {}).get('edits', []):
        physical=edit['physical_measure']
        if not 1 <= physical <= len(measures):
            raise ValueError('repair_measure_out_of_range')
        repair_starts.add(min(max(0, physical-2), max(0,len(measures)-width)))
    starts=sorted(set(starts)|repair_starts)
    result = []
    for index in starts:
        subset = measures[index:index+width]
        result.append({'physical_start': index+1, 'physical_end': index+len(subset),
            'repair_context': index in repair_starts,
            'printed_start': subset[0]['printed_measure_number'], 'printed_end': subset[-1]['printed_measure_number'],
            'span': {'start': subset[0]['global_start_quarter'],
                     'end': q(f(subset[-1]['global_start_quarter'])+f(subset[-1]['actual_duration_quarter']))}})
    return result


def projected_track(ir, result, annotations, kind, name, with_bass=False):
    from .harmony_applied_context import applied_projection
    segments = []
    for i, s in enumerate(result['segments']):
        keys = {source_reference_key(a) for a in annotations if a.get('target', {}).get('span')
                and f(a['target']['span']['start']) < f(s['span']['end'])
                and f(a['target']['span']['end']) > f(s['span']['start'])}
        reference = next(iter(keys)) if len(keys) == 1 else None
        display = roman_projection(ir, s['span'], s['selected'], reference)
        base={'id': f'{kind}-{i}', 'span': s['span'], 'roman': display['text'],
            'roman_status': display['status'], 'roman_projection': display, 'reference_key': reference,
            'label': s['selected']['label'], 'kind': kind, 'selected': s['selected'],
              'alternatives': s['alternatives'], 'engine_version': result['engine_version']}
        groups=display_groups(s) if with_bass else []
        if not groups:segments.append(base)
        for j,group in enumerate(groups):
            cell=group['cells'][0]
            shown=roman_projection(ir,s['span'],s['selected'],reference,cell)
            contexts=[h for h in s.get('applied_context_hypotheses',[]) if h['hypothesis_id'] in cell.get('applied_context_refs',[])]
            applied=next((p for h in contexts if (p:=applied_projection(h,reference,cell['inversion_index']))),None)
            literal=shown
            if applied:shown=applied
            upper=roman_projection(ir,s['span'],s['selected'],reference,cell['upper_if_pedal_excluded']) if cell['pedal_hypothesis'] else None
            segments.append({**base,'id':f'{kind}-{i}-bass-{j}','span':group['span'],
                'roman':shown['text'],'roman_status':shown['status'],'roman_projection':shown,
                'literal_roman_projection':literal,'applied_context_hypotheses':contexts,'applied_display':bool(applied),
                'boundary_contrast_at_start':s.get('boundary_contrast_at_start',[]) if group['span']['start']==s['span']['start'] else [],
                'parent_harmony_span':s['span'],'bass_cells':group['cells'],
                'pedal_hypothesis':cell['pedal_hypothesis'],'upper_if_pedal_excluded':upper})
    return {'id': kind, 'kind': kind, 'name': name, 'margin': '0', 'segments': segments}


def verified_pages(source, ir):
    """Render only verified explicit IDs; never positional fallback after engraving."""
    import verovio
    checks = compare(ir, xml_inventory(source))
    if any(c['status'] != 'exact' for c in checks.values()):
        raise ValueError('raw_xml_comparison_failed')
    refs = {r['source_ref_id']: r for r in ir['source_references']}
    by_path = {refs[n['source_ref_id']]['source_xpath']: n['note_id'] for n in ir['note_events']}
    root = ET.parse(source).getroot()
    for el in root.iter():
        el.tag = el.tag.rsplit('}', 1)[-1]
    for pi, part in enumerate(root.findall('part'), 1):
        for mi, measure in enumerate(part.findall('measure'), 1):
            # Existing source Roman labels must not appear as an unlabelled fourth track.
            for harmony in list(measure.findall('harmony')):
                measure.remove(harmony)
            for ni, note in enumerate(measure.findall('note'), 1):
                note.attrib.pop('id', None)
                note.attrib.pop('{http://www.w3.org/XML/1998/namespace}id', None)
                nid = by_path.get(f'/score-partwise/part[{pi}]/measure[{mi}]/note[{ni}]')
                if nid:
                    note.set('id', nid)
    toolkit = verovio.toolkit()
    toolkit.setOptions({'inputFrom': 'musicxml', 'pageWidth': 1800, 'pageHeight': 2500,
        'adjustPageHeight': True, 'scale': 35, 'breaks': 'auto', 'svgHtml5': True, 'removeIds': False})
    if not toolkit.loadData(ET.tostring(root, encoding='unicode')):
        raise ValueError('engraving_load_failed')
    pages = [toolkit.renderToSVG(i) for i in range(1, toolkit.getPageCount()+1)]
    rendered = Counter((e.get('data-id') or e.get('id')) for page in pages
                       for e in ET.fromstring(page).iter() if 'note' in e.get('class', '').split())
    expected = {n['note_id'] for n in ir['note_events']}
    missing = expected-set(rendered)
    duplicates = [nid for nid in expected if rendered[nid] > 1]
    if missing or duplicates:
        raise ValueError(f'engraving_identity_incomplete:missing={len(missing)},duplicates={len(duplicates)}')
    return pages, {'complete': True, 'policy': 'verified_source_xpath_direct_id_only',
                   'rendered_canonical_id_count': len(expected), 'semantic_mismatches': []}


def load_package(folder):
    return {'ir': json.loads((folder/'canonical_music_ir.json').read_text(encoding='utf-8')),
        'annotations': [json.loads(x) for x in (folder/'imported_annotations.jsonl').read_text(encoding='utf-8').splitlines()],
        'alignments': [json.loads(x) for x in (folder/'alignment_records.jsonl').read_text(encoding='utf-8').splitlines()],
        'report': json.loads((folder/'preparation_report.json').read_text(encoding='utf-8'))}


def prepare(source_root, stem, folder, source_override=None):
    source = source_override or source_root/'MS3'/f'{stem}.musicxml'
    paths = {'score': source, **{name: source_root/name/f'{stem}.{name}.tsv' for name in ('measures','harmonies','notes')}}
    before = {k: digest(v) for k,v in paths.items()}
    imported = folder/'import'
    if (imported/'preparation_report.json').exists():
        package = load_package(imported)
        if package['report']['source_sha256'] != before:
            raise ValueError('cached_source_hash_changed')
    else:
        package = prepare_dcml(paths['score'], paths['measures'], paths['harmonies'], paths['notes'])
        write_dcml_package(package, imported)
    observations = observation_rows(package['ir'], source)
    corrected, migration = revise(package['ir'], observations, source)
    validation = validate_revision(package['ir'], corrected)
    independent = compare(corrected, xml_inventory(source))
    if any(c['status'] != 'exact' for c in independent.values()):
        raise ValueError('independent_note_check_failed')
    write(folder/'observations.json', observations)
    write(folder/'canonical_music_ir.json', corrected)
    write(folder/'migration.json', migration)
    # Preserve eligibility. An old ambiguous annotation is NOT automatically promoted.
    annotations = deepcopy(package['annotations']); alignments = deepcopy(package['alignments'])
    for a in annotations + alignments:
        if a.get('target'):
            a['target']['ir_document_id'] = corrected['ir_document_id']
    for a in alignments:
        a['ir_document_id'] = corrected['ir_document_id']
        members = alignment_membership(corrected['sounding_events'], a['target']) if a.get('target') and a['mapping_status'] in ('exact','verified_transform') else ([],[])
        a['sounding_event_ids'], a['attacked_sounding_event_ids'] = members
    write(folder/'annotations.json', annotations)
    write(folder/'alignments.json', alignments)
    if before != {k:digest(v) for k,v in paths.items()}:
        raise ValueError('source_modified')
    return package['ir'], corrected, annotations, alignments, {'source':str(source),'hashes':before,
        'validation':validation, 'xml_exact_notes':len(independent), 'notes':len(corrected['note_events']),
        'rests':len(corrected['rest_events']), 'annotations':len(annotations),
        'alignment_statuses':dict(Counter(a['mapping_status'] for a in alignments)),
        'cadence_rows':sum(bool(a['components']['cadence']) for a in annotations),
        'phraseend_rows':sum(bool(a['components']['phraseend']) for a in annotations),
        'sound_count_before':len(package['ir']['sounding_events']), 'sound_count_after':len(corrected['sounding_events'])}


def build(source_root, stems, output, font_dir, manifest, normalized_root=None):
    output.mkdir(parents=True, exist_ok=True)
    # Existing held-out works stay reserved, even when explicitly selected for browsing.
    entries = json.loads(manifest.read_text(encoding='utf-8'))['entries']
    hashes = {p.name:digest(p) for p in Path(__file__).parent.glob('*.py')}
    normalization={}
    if normalized_root:
        for stem in stems:
            derived=normalized_root/f'{stem}.musicxml'
            proof=json.loads(derived.with_suffix('.repair.json').read_text(encoding='utf-8'))
            original=source_root/'MS3'/f'{stem}.musicxml'
            if proof['source_sha256']!=digest(original) or proof['normalized_sha256']!=digest(derived):
                raise ValueError('normalization_provenance_mismatch')
            normalization[stem]=proof
    contract = {'version':VERSION,'engine_version':ENGINE_VERSION,'code_hashes':hashes,
        'source_normalization':normalization,
        'stems':stems,'source_root':str(source_root),'manifest_sha256':digest(manifest),
        'scope':'full_score_input_validation_sample_windows_and_optional_repair_context',
        'selection':'first_middle_last_and_manifest_repair_locations_no_harmony_annotation_selection',
        'source_labels_used_for_inference':False,'production_modified':False,
        'split':'explicit_development_review_not_independent_test',
        'limitations':['No inferred local key, secondary function or cadence',
            'Phrase engine is not run here; source phraseend is not a predicted boundary',
            'Window edges are computational cuts, not predicted phrase/harmony boundaries']}
    contract_path=output/'run-contract.json'
    if contract_path.exists() and json.loads(contract_path.read_text(encoding='utf-8')) != contract:
        raise ValueError('contract_changed_use_new_output')
    write(contract_path,contract)
    for name in ('review.css','review.js'):
        shutil.copyfile(ASSETS/name,output/name)
    for name in ('Campania.woff','Campania.LICENSE.txt'):
        shutil.copyfile(font_dir/name,output/name)
    summaries=[]
    for stem in stems:
        folder=output/stem; folder.mkdir(exist_ok=True)
        source=source_root/'MS3'/f'{stem}.musicxml'
        split_rows=[e for e in entries if Path(e['score_source_path']).resolve()==source.resolve()]
        if any(e.get('split') in ('dev','holdout') for e in split_rows):
            summaries.append({'score':stem,'status':'reserved_split_not_run'}); continue
        began=time.monotonic()
        try:
            if normalized_root: source=normalized_root/f'{stem}.musicxml'
            old,ir,annotations,alignments,summary=prepare(source_root,stem,folder,source)
            if stem in normalization: summary['source_normalization']=normalization[stem]
            windows=sample_windows(ir,repair_proof=normalization.get(stem))
            write(folder/'predeclared_windows.json',windows)
            eligible={a['annotation_id'] for a in alignments if a['mapping_status'] in ('exact','verified_transform')}
            verified=[a for a in annotations if a['annotation_id'] in eligible and a.get('target') and 'span' in a['target']]
            pages,mapping=verified_pages(source,ir)
            cases=[]
            for i,window in enumerate(windows):
                cache=folder/f'window-{i+1}.json'
                if cache.exists():
                    runs=json.loads(cache.read_text(encoding='utf-8'))
                    if runs['ir_sha256']!=digest(folder/'canonical_music_ir.json'):
                        raise ValueError('cached_ir_changed')
                else:
                    print(stem,'window',i+1,'analyzing',flush=True)
                    # Same engine and window: isolate input revision from algorithm changes.
                    baseline=analyze(old,analysis_span=window['span'])
                    experiment=analyze(ir,analysis_span=window['span'])
                    runs={'window':window,'baseline':baseline,'experiment':experiment,
                          'ir_sha256':digest(folder/'canonical_music_ir.json')}
                    write(cache,runs)
                source_segments=[{'id':a['annotation_id'],'span':a['target']['span'],
                    'roman':a['components']['chord'] or 'unknown','cadence':a['components']['cadence'],
                    'label':a['raw_label'],'kind':'source','reference_key':source_reference_key(a),
                    'key_context':a['components'],'source_pedal':a.get('raw_fields',{}).get('pedal'),
                    'provenance':a['source_locator'],'roman_status':'imported_not_gold'}
                    for a in verified]
                normalized=stem in normalization
                tracks=[{'id':'source','name':'원자료 화성·종지 주석','segments':source_segments},
                    projected_track(old,runs['baseline'],verified,'baseline','시간 교정 사본 · 기존 IR' if normalized else '교정 전 IR · 같은 엔진'),
                    projected_track(ir,runs['experiment'],verified,'experiment','이번 계산 · 실제 베이스 기준 조건부 전위',with_bass=True)]
                ids={n['note_id'] for n in ir['note_events'] if f(window['span']['start'])<=f(n['global_onset_quarter'])<f(window['span']['end'])}
                fragments=system_fragments(pages,ids)
                filename=f'{stem}-window-{i+1}.html'
                payload={'case_id':f'{stem}-window-{i+1}','title':f'Beethoven {stem} · m.{window["printed_start"]}–{window["printed_end"]}',
                    'source_file':source.name,'target_span':window['span'],'context_span':window['span'],
                    'reference_key':None,'tracks':tracks,'notes':ir['note_events'],'measures':ir['measures'],
                    'mapping':mapping,'score_sha256':summary['hashes']['score'],'result_sha256':digest(cache),
                    'stability':{'experiment':{}},'cells':[],'production_enabled':False,
                    'verification_review':True,'bass_review':True,'review_questions':[
                        '보라색은 선택된 화음과 실제 최저음에 따른 조건부 전위입니다. 전위 표시의 분할은 새 화음 경계가 아닙니다. 회색은 근음·종류만 표시합니다.',
                        '페달 후보는 반복 베이스와 화음 변화에서 자동 제안합니다. 클릭하면 페달을 제외했을 때의 전위 대안을 확인할 수 있습니다. 원자료 페달 주석은 별도 표시입니다.',
                        ('두 계산 모두 시간 교정 사본을 사용합니다. 회색/보라색 차이는 음표 연결 IR 개선이며, 원본 XML과 시간 교정 사본 비교가 아닙니다.' if normalized else '회색/보라색은 동일 엔진의 교정 전후 IR 계산입니다. 변화가 없어도 실패가 아닙니다.'),
                        '조성은 원주석에서 빌린 표시 기준입니다. 전위는 선택 화음에 조건부이며 Secondary 기능은 아직 판정하지 않습니다.',
                        '초록색 종지는 원자료 주석입니다. 자동 종지·프레이즈 분석은 아직 비교하지 않았습니다.',
                        ('시간 교정 위치와 앞뒤 마디를 포함한 표본입니다.' if window['repair_context'] else '처음·중간·끝 4마디 표본입니다.')+' 악장 전체 화성 분석/정답률 검증 완료가 아닙니다.',
                        '분산 지지·비화성음 가설은 보라색 구간을 눌러 확인하세요. 구간 밖 화음/NCT 문맥에는 제한이 있습니다.']}
                write_page(payload,fragments,output/filename)
                before=[(s['span'],s['selected']['label']) for s in runs['baseline']['segments']]
                after=[(s['span'],s['selected']['label']) for s in runs['experiment']['segments']]
                cases.append({'page':filename,'window':window,'changed_labels_or_spans':before!=after,
                    'baseline_segments':len(before),'corrected_segments':len(after),
                    'distributed_evidence_count':sum(e.get('reason')=='supplemental_distributed_window' for s in runs['experiment']['segments'] for e in s['selected'].get('temporal_evidence',[]))})
            summaries.append({'score':stem,'status':'sample_review_ready',**summary,'cases':cases,'seconds':round(time.monotonic()-began,2)})
        except (ValueError,KeyError,FileNotFoundError) as exc:
            summaries.append({'score':stem,'status':'blocked','reason':str(exc),'seconds':round(time.monotonic()-began,2)})
        write(output/'report.json',{'contract':contract,'scores':summaries})
        print(stem,summaries[-1]['status'],summaries[-1].get('reason',''),flush=True)
        rows=[]
        for s in summaries:
            links=' · '.join(f'<a href="{c["page"]}">{"시간 교정 구간 · " if c["window"].get("repair_context") else ""}m.{html.escape(str(c["window"]["printed_start"]))}–{html.escape(str(c["window"]["printed_end"]))}</a>' for c in s.get('cases',[]))
            rows.append(f'<li><strong>{html.escape(s["score"])}</strong> {links or html.escape(s.get("reason",s["status"]))}</li>')
        notice='<p>시간 교정 사본으로 만든 검토 페이지입니다. 원본 파일은 변경하지 않았습니다. 두 자동 계산은 모두 같은 시간 교정 사본을 사용하며, 음표 연결 IR 개선 전후만 비교합니다. 시간 교정 위치도 별도 표본으로 포함했습니다.</p>' if normalization else ''
        (output/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>베토벤 소나타 검증</title><link rel="stylesheet" href="review.css"><main class="gallery"><h1>베토벤 소나타 검증</h1><p>08 = Op.13 비창 · 01 = Op.2 No.1</p>'+notice+'<p>원자료 주석 / 기존 IR 계산 / 음표 연결 개선 IR 계산. 악장별 처음·중간·끝 4마디 표본. 전곡 입력 검증과 전곡 화성 정확도 검증은 다릅니다. 종지는 원주석만 표시하며 프레이즈 엔진은 미실행입니다.</p><ul>'+''.join(rows)+'</ul><a href="report.json">검증 기록</a></main>',encoding='utf-8')
    return summaries


if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--source-root',type=Path,required=True)
    ap.add_argument('--scores',nargs='+',required=True); ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--font-dir',type=Path,required=True); ap.add_argument('--manifest',type=Path,required=True)
    ap.add_argument('--normalized-root',type=Path)
    args=ap.parse_args(); build(args.source_root,args.scores,args.output,args.font_dir,args.manifest,args.normalized_root)
