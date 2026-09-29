"""Post-inference evidence for priority review flags; no source labels feed scoring."""
import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
from .formal_ir import q
from .harmony_joint import f, prepare, candidates
from .harmony_temporal_shadow import provider
from .harmony_context_sensitivity import stability_components
from .harmony_review_cohort import validate_split
from .harmony_review_supplement import verified_annotations, context_excerpt
from .harmony_case_retrieval import load_prepared_package
from .harmony_candidate_explanation import explain_candidate, explain_path

PRIORITY_FLAGS = {'lost_context_stability', 'distributed_proxy_contains_internal_boundary',
                  'short_change_proxy_edges_not_both_supported'}


def boundary_kind(before, after):
    """Compare source categories, not predicted harmony or harmonic truth."""
    if f(before['target']['span']['end']) != f(after['target']['span']['start']):
        return 'noncontiguous_source_records'
    a, b = before.get('raw_fields', {}), after.get('raw_fields', {})
    required = ('globalkey', 'localkey', 'numeral', 'chord_type')
    if any(not r.get(k) for r in (a, b) for k in required):return 'insufficient_source_fields'
    identity = (*required, 'form', 'relativeroot', 'root')
    if any(a.get(k, '') != b.get(k, '') for k in identity):return 'source_harmonic_identity_change'
    if a.get('figbass', '') != b.get('figbass', ''):return 'source_inversion_change'
    if a.get('pedal', '') != b.get('pedal', ''):return 'source_pedal_change'
    if any(a.get(k, '') != b.get(k, '') for k in ('changes', 'added_tones', 'chord')):
        return 'same_identity_surface_detail_change'
    return 'same_identity_annotation_boundary'


def cell_support(ir, span):
    """Audit the current half-denominator-beat gate; no proposed gate change."""
    rows, neighbors = prepare(ir)
    grids = sorted({(f(m['global_start_quarter']), Fraction(4, m['time_signature']['beat_type'])) for m in ir.get('measures', [])})
    a, b = f(span['start']), f(span['end']); result = []; x = a
    while x < b:
        origin, beat = next(((t,u) for t,u in reversed(grids) if t <= x), (Fraction(0),Fraction(1)))
        unit = beat/2; stop = next((t for t,u in grids if t > x), b)
        y = min(b, stop, origin+((x-origin)//unit+1)*unit)
        active = [r for r in rows if r['start'] < y and r['end'] > x]
        pcs = sorted({r['pitch'] % 12 for r in active})
        local = candidates(rows, neighbors, x, y, beat, limit=None, min_shared_pcs=0)
        usable = len(pcs) >= 3 and local[0]['root'] is not None and local[0].get('coverage', 0) == 1
        result.append({'span': {'start':q(x),'end':q(y)}, 'observed_pcs': pcs,
                       'events': [{'id':r['id'],'spelling':r['spelling'],'voice_id':r['voice'],
                                   'original_span':{'start':q(r['start']),'end':q(r['end'])}} for r in active],
                       'used_by_current_temporal_gate': usable,
                       'abstention_reason': None if usable else ('fewer_than_three_pcs' if len(pcs)<3 else 'best_template_incomplete'),
                       'top_candidates': local[:3]})
        x = y
    return result


def build(manifest, review_dir, output, additional_cases=()):
    raw = Path(manifest).read_bytes(); entries = json.loads(raw)['entries']; validate_split(entries)
    packages = {e['package_path']:e for e in entries}
    if len(packages)!=len(entries):raise ValueError('duplicate_manifest_package')
    source = Path(review_dir)
    review_raw = (source/'report.json').read_bytes(); review = json.loads(review_raw)
    plan_raw = (source/'plan/report.json').read_bytes(); plan = json.loads(plan_raw)
    if plan['manifest_sha256']!=hashlib.sha256(raw).hexdigest():raise ValueError('manifest_changed')
    queue_raw = (source/'plan/cases.jsonl').read_bytes()
    queue_rows = list(map(json.loads,queue_raw.decode('utf-8').splitlines()))
    queue = {r['case_id']:r for r in queue_rows}; planned = {r['case_id']:r for r in plan['plan']}
    if len(queue)!=len(queue_rows):raise ValueError('duplicate_case')
    selected = [r for r in review['aggregate']['review_queue'] if PRIORITY_FLAGS.intersection(r['flags'])]
    # Diagnostic selection only, never a condition in the harmony scorer.
    for case_id in additional_cases:
        if case_id not in planned:
            raise ValueError('additional_case_not_in_frozen_plan')
        if not any(r['case_id'] == case_id for r in selected):
            selected.append({'case_id': case_id, 'flags': ['additional_comparison_review']})
    # All selected source identities are checked before reading package contents.
    for r in selected:
        case=queue[r['case_id']]; e=packages[case['package_path']]; item=planned[r['case_id']]
        if any(v['split']!='train' for v in (case,e,item)):raise ValueError('non_train_case')
        for k in ('score_id','ir_document_id','work_family_id','score_sha256','annotation_sha256','rights'):
            if case[k]!=e[k]:raise ValueError('identity_mismatch:'+k)
        if case['target_span']!=item['target_span']:raise ValueError('target_changed')
    out=Path(output);out.mkdir(parents=True,exist_ok=True);summaries=[]
    for r in selected:
        case=queue[r['case_id']];e=packages[case['package_path']];item=planned[r['case_id']]
        package=Path(case['package_path'])
        hashes={name:hashlib.sha256((package/name).read_bytes()).hexdigest() for name in
                ('canonical_music_ir.json','imported_annotations.jsonl','alignment_records.jsonl')}
        if hashes['canonical_music_ir.json']!=item['ir_sha256']:raise ValueError('live_ir_hash_mismatch')
        if hashlib.sha256(Path(e['score_source_path']).read_bytes()).hexdigest()!=e['score_sha256']:raise ValueError('live_score_hash_mismatch')
        p=load_prepared_package(package);ir=p['ir']
        if ir['ir_document_id']!=e['ir_document_id'] or ir['score']['score_id']!=e['score_id']:raise ValueError('ir_identity_mismatch')
        annotations,skips=verified_annotations(p,e)
        target=case['target_span'];a,b=f(target['start']),f(target['end'])
        source_context=[v for v in annotations if f(v['target']['span']['start'])<b+2 and f(v['target']['span']['end'])>max(0,a-2)]
        boundaries=[]
        for before,after in zip(source_context,source_context[1:]):
            boundaries.append({'at':after['target']['span']['start'],'kind':boundary_kind(before,after),
                               'annotation_refs':[before['annotation_id'],after['annotation_id']],
                               'labels':[before['raw_label'],after['raw_label']], 'status':'source_proxy_not_gold'})
        result_raw=(source/'results'/(r['case_id']+'.json')).read_bytes();result=json.loads(result_raw)
        if result['case_id']!=r['case_id'] or result['target_span']!=target or result['ir_sha256']!=item['ir_sha256']:
            raise ValueError('result_identity_mismatch')
        cells=cell_support(ir,target)
        rows,neighbors=prepare(ir);choose=provider(cell_divisions=2,measures=ir.get('measures',[]))
        measures=sorted(ir.get('measures',[]),key=lambda m:f(m['global_start_quarter']))
        m=next((m for m in reversed(measures) if f(m['global_start_quarter'])<=a),None)
        beat=Fraction(4,m['time_signature']['beat_type']) if m else Fraction(1)
        target_candidates=choose(rows,neighbors,a,b,beat,limit=5)
        runs=[]
        for run in result['runs']:
            explanations={engine:[explain_candidate(ir,s['span'],s['selected'],f(s['beat_unit_quarter']))
                                  for s in run[engine]['segments'] if f(s['span']['start'])<b and f(s['span']['end'])>a]
                          for engine in ('baseline','experiment')}
            runs.append({'margin_quarters':run['margin_quarters'], 'selected_target_spans':explanations,
                         'path_costs':{engine:explain_path(run[engine]) for engine in ('baseline','experiment')}})
        summary={'case_id':r['case_id'],'flags':r['flags'],'target_span':target,
                 'stability_components':{k:stability_components(result['runs'],k,target,2) for k in ('baseline','experiment')},
                 'target_cells':len(cells),'usable_target_cells':sum(c['used_by_current_temporal_gate'] for c in cells),
                 'target_candidate_labels':[c['label'] for c in target_candidates],
                 'source_boundaries_at_target_edges':[v for v in boundaries if f(v['at']) in (a,b)]}
        record={**summary,'package_hashes':hashes,'source_result_sha256':hashlib.sha256(result_raw).hexdigest(),
                'source_xml':e['score_source_path'],'score_sha256':e['score_sha256'],
                'context_excerpt':context_excerpt(ir,target),'verified_source_context':source_context,
                'source_boundary_types':boundaries,'unverified_annotation_skips':dict(skips),
                'target_cell_evidence':cells,'target_candidate_explanations':[explain_candidate(ir,target,c,beat) for c in target_candidates],
                'runs':runs,'source_labels_used_for_inference':False,'musical_gold':False,'training_eligible':False}
        (out/(r['case_id']+'.json')).write_text(json.dumps(record,indent=2),encoding='utf-8');summaries.append(summary)
    report={'version':'harmony-failure-context-audit-0.1.0','manifest_sha256':hashlib.sha256(raw).hexdigest(),
            'review_sha256':hashlib.sha256(review_raw).hexdigest(),'plan_sha256':hashlib.sha256(plan_raw).hexdigest(),
            'queue_sha256':hashlib.sha256(queue_raw).hexdigest(),'cases':summaries,'production_enabled':False,
            'accuracy_measured':False,'reserved_contents_read':False,
            'limits':['Source-boundary categories are descriptive, not mandatory inferred chord boundaries',
                      'Cell eligibility describes the existing gate; no new weighting or musical rule applied',
                      'XML engraving source retained by path/hash; excerpt is not a full Canonical IR']}
    (out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2));return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--review-dir',required=True);p.add_argument('--output',required=True)
    p.add_argument('--additional-case', action='append', default=[])
    a=p.parse_args();build(a.manifest,a.review_dir,a.output,a.additional_case)
