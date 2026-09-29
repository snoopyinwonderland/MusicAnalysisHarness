"""Replay frozen paired/real cases and publish non-selected boundary alternatives."""
import argparse
from fractions import Fraction as F
import html
import json
from pathlib import Path
import re
import shutil

from .harmony_arpeggio_benchmark import digest, write, metrics
from .harmony_joint import f
from .harmony_boundary_ownership import review, VERSION


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def verify(path, sha):
    if digest(path) != sha:
        raise ValueError('snapshot_hash_mismatch:'+str(path))


def path_text(segments, beat_type=4):
    unit = F(4, beat_type)
    def pos(v):
        value = 1+f(v)/unit
        return str(float(value)).rstrip('0').rstrip('.') if value.denominator in (1, 2, 4) else str(value)
    return ' → '.join(f"{pos(s['span']['start'])}–{pos(s['span']['end'])}박 직전: {s['selected']['label']}" for s in segments)


def build(source, output):
    if output.exists():
        raise ValueError('output_exists_choose_new_revision')
    baseline_report = load(source/'report.json')
    # Re-evaluation uses exactly the archived engine cost function.
    for name, sha in baseline_report['contract']['code_sha256'].items():
        verify(Path(__file__).parent/name, sha)
    output.mkdir(parents=True)
    contract = {'version': VERSION, 'baseline_report_sha256': digest(source/'report.json'),
                'source_path': str(source.resolve()), 'selected_paths_modified': False,
                'production_modified': False, 'annotation_labels_used_for_inference': False,
                'code_sha256': {p.name: digest(p) for p in Path(__file__).parent.glob('*.py')}}
    write(output/'run-contract.json', contract)
    summaries = []; markup = []
    for row in baseline_report['cases']:
        cid = row['case_id']; folder = source/cid; out = output/cid; out.mkdir()
        verify(folder/'score.musicxml', row['source_sha256'])
        verify(folder/'canonical_music_ir.json', row['ir_sha256'])
        for name in ('score.musicxml', 'canonical_music_ir.json', 'fixture.json', 'results.json'):
            shutil.copyfile(folder/name, out/name)
        ir = load(folder/'canonical_music_ir.json')
        baseline = load(folder/'results.json')['runs']['current']
        result = review(ir, baseline)
        # Expectations are consulted only AFTER the proposal generator returns.
        case = load(folder/'fixture.json')
        evaluated = [metrics(case['expected'], {'segments': a['alternative_segments']}) for a in result['alternatives']]
        summary = {'case_id': cid, 'transform': row['transform'], 'change': row['change'],
                   'source_sha256': row['source_sha256'], 'ir_sha256': row['ir_sha256'],
                   'baseline_results_sha256': digest(folder/'results.json'),
                   'alternative_count': len(result['alternatives']),
                   'baseline_exact': row['metrics']['current']['exact_intention_match'],
                   'intention_in_alternatives': any(m['exact_intention_match'] for m in evaluated),
                   'alternative_metrics': evaluated}
        write(out/'ownership-review.json', {'summary': summary, 'review': result}); summaries.append(summary)
        if row['transform'] == 'base' and result['alternatives']:
            # Re-engrave the unchanged XML tightly: the earlier full-page SVG
            # leaves one short measure tiny on a narrow review panel.
            import verovio
            toolkit = verovio.toolkit()
            toolkit.setOptions({'inputFrom': 'musicxml', 'breaks': 'none', 'adjustPageWidth': True,
                                'adjustPageHeight': True, 'scale': 50, 'header': 'none', 'footer': 'none'})
            if not toolkit.loadFile(str(folder/'score.musicxml')):
                raise ValueError('review_render_failed')
            svg = toolkit.renderToSVG(1)
            size = re.search(r'<svg width="([0-9.]+)px" height="([0-9.]+)px"', svg)
            if size:
                svg = svg.replace('<svg ', f'<svg viewBox="0 0 {size[1]} {size[2]}" ', 1)
            (out/'score.svg').write_text(svg, encoding='utf-8')
            for i, a in enumerate(result['alternatives']):
                card = cid+'-'+str(i)
                aa, bb = f(a['proposed_boundary']), f(a['current_boundary'])
                ordered = sorted(case['events'], key=lambda e: (e['voice'], f(e['start'])))
                ids = [f'fixture_note_{n}' for n,e in enumerate(ordered)
                       if f(e['start']) < bb and f(e['start'])+f(e['duration']) > aa]
                selectors = ','.join(f'#{card} [id="{nid}"], #{card} [id="{nid}"] *' for nid in ids)
                style = '<style>'+selectors+'{fill:#1466b8!important;stroke:#1466b8!important;color:#1466b8!important}</style>'
                title = {'ascending': '상행 분산화음', 'overlapping': '음이 겹쳐 울리는 분산화음',
                         'delayed_quality': '구성음이 늦게 등장하는 분산화음'}.get(row['texture'], cid)
                content = f'<section id="{card}"><h2>{html.escape(title)}</h2>'+style+svg
                content += '<p>파란 음표: 앞 화음에 포함되어 있지만 뒤 화음의 시작으로도 볼 수 있는 공통음입니다.</p>'
                content += '<table><tr><th>기존 자동 선택</th><td>'+html.escape(path_text(baseline['segments']))+'</td></tr>'
                content += '<tr><th>추가 검토 대안 · 미적용</th><td>'+html.escape(path_text(a['alternative_segments']))+'</td></tr></table>'
                content += f'<p>계산 비용 차이: {a["cost_delta"]:.6f} (0이면 기존 계산식의 동점; 정답 확정 아님)</p>'
                content += '<p>반대 해석: 이 음은 앞 화음에도 속합니다. 선행음·페달 가능성을 배제하지 않았습니다.'
                if 'quality_arrives_more_than_one_denominator_beat_later' in a['counterevidence']:
                    content += ' 특히 뒤 구성음의 도착이 한 박보다 늦어 시작 구간은 모호합니다.'
                content += f'</p><a href="{cid}/ownership-review.json">음표 ID·근거·전체 후보</a> · <a href="{cid}/score.musicxml">원 악보</a></section>'
                markup.append(content)
    real_source = source/'real-cases'; real_rows = []
    real_report = load(real_source/'report.json')
    contract['real_report_sha256'] = digest(real_source/'report.json')
    for row in real_report['cases']:
        cid = row['case_id']; folder = real_source/cid; out = output/'real-cases'/cid; out.mkdir(parents=True)
        provenance = load(folder/'case-provenance.json')
        case, entry, plan = (provenance[k] for k in ('case', 'manifest_entry', 'frozen_plan'))
        if any(r['split'] != 'train' for r in (case, entry, plan)) or not entry['rights']['internal_research_use']:
            raise ValueError('not_eligible_frozen_train_case')
        source_name = Path(entry['score_source_path']).name
        verify(folder/'canonical_music_ir.json', plan['ir_sha256'])
        verify(folder/source_name, entry['score_sha256'])
        for name in ('canonical_music_ir.json', source_name, 'case-provenance.json', 'results.json'):
            shutil.copyfile(folder/name, out/name)
        ir = load(folder/'canonical_music_ir.json'); original = load(folder/'results.json'); runs = []
        for r in original['runs']:
            for arm in ('baseline', 'experiment'):
                answer = review(ir, r[arm])
                runs.append({'margin_quarters': r['margin_quarters'], 'analysis_span': r['analysis_span'],
                             'frozen_arm': arm, 'review': answer})
        rr = {'case_id': cid, 'collection': row['collection'], 'stratum': row['stratum'],
              'alternative_count': sum(len(r['review']['alternatives']) for r in runs),
              'contexts_with_alternatives': sum(bool(r['review']['alternatives']) for r in runs),
              'baseline_results_sha256': digest(folder/'results.json')}
        write(out/'ownership-review.json', {'summary': rr, 'runs': runs}); real_rows.append(rr)
        print(cid, rr['alternative_count'], flush=True)
    summary = {'synthetic_inputs': len(summaries),
               'baseline_exact': sum(r['baseline_exact'] for r in summaries),
               'cases_with_alternatives': sum(r['alternative_count']>0 for r in summaries),
               'missed_intentions_available_as_alternatives': sum(not r['baseline_exact'] and r['intention_in_alternatives'] for r in summaries),
               'hold_cases_with_alternatives': sum(not r['change'] and r['alternative_count']>0 for r in summaries),
               'real_cases': len(real_rows), 'real_cases_with_alternatives': sum(r['alternative_count']>0 for r in real_rows),
               'real_alternatives': sum(r['alternative_count'] for r in real_rows),
               'selected_path_accuracy_improvement_claimed': False}
    write(output/'run-contract.json', contract)
    write(output/'report.json', {'contract': contract, 'summary': summary, 'synthetic': summaries, 'real': real_rows})
    real_html = '<h2>실제 악보 고정 10사례 / 40조건</h2><p>직전 on/off와 두 문맥 결과를 그대로 보존했습니다. 후보 발생은 정확도 향상이 아닙니다.</p><ul>'
    for r in real_rows:
        real_html += f'<li>{html.escape(r["collection"])} · {r["case_id"]}: 후보 {r["alternative_count"]}개 · <a href="real-cases/{r["case_id"]}/ownership-review.json">근거 보기</a></li>'
    real_html += '</ul>'
    page = '<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>공통음의 화음 소속 — 경계 대안 검토</title>'
    page += '<style>body{font:16px system-ui;max-width:1180px;margin:32px auto;padding:0 20px;background:#f4f7fb;color:#182c40}section{background:white;border:1px solid #cad6e2;border-radius:12px;margin:24px 0;padding:22px}section>svg{width:100%;height:auto}h2{font-size:20px}p,li{line-height:1.7}table{width:100%;border-collapse:collapse}th,td{padding:12px;text-align:left;border-bottom:1px solid #ddd}th{width:180px}@media(max-width:600px){th{width:105px}th,td{padding:8px}section{padding:14px}}</style>'
    page += '<h1>공통음으로 시작하는 분산화음: 두 경계 비교</h1><p>기존 자동 선택을 바꾸지 않고, 뒤 화음의 구성음으로 앞선 시작점을 재검토했습니다. 파란 음표를 보면서 두 해석을 비교해 주세요. 구간은 시작 포함·끝 제외이며 5박 직전은 이 4/4 예제의 끝입니다.</p>'
    page += '<p>major = 장3화음 · dominant7 = 장단7화음 · diminished = 감3화음. 로마자 기능·조성을 확정한 표기가 아닙니다.</p>'
    page += f'<p>기존 의도 일치 {summary["baseline_exact"]}/84는 그대로입니다. 놓쳤던 {summary["missed_intentions_available_as_alternatives"]}개 변형 입력의 의도를 <strong>대안으로</strong> 찾았습니다. 이조·음가 변형은 독립적인 새 곡이 아닙니다. 운영 악보 뷰어에는 적용하지 않았습니다.</p>'
    page += ''.join(markup)+real_html+'<p><a href="report.json">전체 보고서</a></p></html>'
    (output/'index.html').write_text(page, encoding='utf-8')
    write(output/'gallery-manifest.json', {'renderer_sha256': digest(Path(__file__)), 'index_sha256': digest(output/'index.html')})
    print(json.dumps(summary), flush=True)
    return summary


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args(); build(args.source, args.output)
