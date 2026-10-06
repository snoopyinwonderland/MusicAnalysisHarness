"""Replay frozen cases with explicit abstention, retaining all previous output."""
import argparse
from collections import Counter
from pathlib import Path
import shutil
from .harmony_arpeggio_benchmark import write, digest
from .harmony_shared_tone_trial import load
from .harmony_boundary_assessment import augment, VERSION


def run(source, output, *, stage=None):
    # Optional additive stage reuses frozen-source/rights/preservation checks.
    version = stage.VERSION if stage else VERSION
    processor = stage.augment if stage else augment
    boundary_key = stage.BOUNDARY_KEY if stage else 'boundary_assessment'
    top_keys = stage.TOP_KEYS if stage else {'boundary_assessment_version'}
    if output.exists(): raise ValueError('choose_new_output')
    output.mkdir(parents=True)
    previous = load(source / 'report.json')
    report = {'version': version, 'real': [], 'source_labels_used': False,
              'accuracy_measured': False, 'production_modified': False,
              'previous_hypotheses_unchanged': True}
    for name in ('catalog_resolution.css', 'Campania.woff', 'Campania.LICENSE.txt', 'index.html'):
        shutil.copyfile(source / name, output / name)
    asset = Path(__file__).parent / 'visual_review_assets' / 'segment_contrast.js'
    shutil.copyfile(asset, output / asset.name)
    write(output / 'run-contract.json', {'version': version, 'source_report_sha256': digest(source / 'report.json'),
        'code_hashes': {p.name: digest(p) for p in Path(__file__).parent.glob('*.py')},
        'ui_sha256': digest(asset), 'selection': 'All frozen samples, cuts and candidates; no label selection',
        'rights': 'local research only'})
    for row in previous['real']:
        src = source / 'real-cases' / row['case_id']; dst = output / 'real-cases' / row['case_id']
        snap = src / 'source-snapshot'; prov = load(snap / 'case-provenance.json')['manifest_entry']
        assert prov['split'] == 'train' and prov['rights']['internal_research_use']
        for name, value in row['source_hashes'].items(): assert digest(snap / name) == value
        assert digest(src / 'plan.json') == row['original_plan_sha256']
        assert digest(src / 'held-cut-plan.json') == row['held_cut_plan_sha256']
        dst.mkdir(parents=True); (dst / 'samples').mkdir()
        shutil.copytree(snap, dst / 'source-snapshot')
        for name in ('plan.json', 'held-cut-plan.json', 'manifest.json', 'counterfactual-checks.json', 'whole-score.html'):
            shutil.copyfile(src / name, dst / name)
        page = dst / 'whole-score.html'
        page.write_text(page.read_text(encoding='utf8').replace(' · 경계의 실제 음·베이스·박절 근거',
            ' · 계류음 보류와 지연 구성음 대조'), encoding='utf8')
        if stage:
            page.write_text(page.read_text(encoding='utf8').replace('계류음 보류와 지연 구성음 대조', stage.TITLE).replace('분산화음과 화성 교체의 시간 순서 대조', stage.TITLE).replace('시간순 장식 후보와 보류·미설명 구간', stage.TITLE), encoding='utf8')
        hashes = {p.name: digest(p) for p in (src / 'samples').glob('*.json')}; counts = Counter()
        for i in range(row['samples']):
            baseline = load(src / 'samples' / f'{i}.json'); out = processor(baseline)
            restored = {k: v for k, v in out.items() if k not in top_keys}
            restored['boundaries'] = [{k: v for k, v in b.items() if k != boundary_key} for b in out['boundaries']]
            assert restored == baseline
            for b in out['boundaries']:
                if stage:
                    counts.update(stage.counts(b[boundary_key]))
                    continue
                e = b['boundary_assessment']; counts['boundaries'] += 1
                counts[e['status']] += 1
                for a in e.get('support_assessments', {}).values(): counts[a['status']] += 1
                counts['suspension_abstentions'] += len(e['patterns'])
                for p in e['patterns']:
                    counts['with_member_competitors'] += any(p['competing_member_reading_indices'].values())
                    counts['noncontiguous_resolution'] += 'resolution_not_contiguous' in p['abstention_reasons']
            write(dst / 'samples' / f'{i}.json', out)
        assert hashes == {p.name: digest(p) for p in (src / 'samples').glob('*.json')}
        write(dst / 'baseline-sample-hashes.json', hashes)
        result = {**row, (stage.COUNTS_KEY if stage else 'assessment_counts'): dict(counts)}
        report['real'].append(result); print(row['title'], dict(counts), flush=True)
    write(output / 'report.json', report)
    page = output / 'index.html'
    page.write_text(page.read_text(encoding='utf8').replace('경계의 실제 음·베이스·박절 근거',
        '계류음 보류와 지연 구성음 대조'), encoding='utf8')
    if stage:
        page.write_text(page.read_text(encoding='utf8').replace('계류음 보류와 지연 구성음 대조', stage.TITLE).replace('분산화음과 화성 교체의 시간 순서 대조', stage.TITLE).replace('시간순 장식 후보와 보류·미설명 구간', stage.TITLE), encoding='utf8')
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--source', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(); run(a.source, a.output)
