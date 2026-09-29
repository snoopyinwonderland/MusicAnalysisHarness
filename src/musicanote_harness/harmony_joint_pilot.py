"""Small real-score diagnostic of the joint harmonic span prototype."""
import json
from pathlib import Path
from time import perf_counter
from .harmony_joint import analyze_joint, f
from .formal_ir import q
from .harmony_unfolded import analyze_unfolded


def main():
    source = Path('output/dcml-batch-2026-09-24/pairs')
    output = Path('output/harmony-joint-pilot-2026-09-26')
    output.mkdir(parents=True, exist_ok=True)
    results = []
    for collection in ('beethoven-quartets','chopin-mazurkas','corelli'):
        path = sorted((source/collection).rglob('canonical_music_ir.json'))[0]
        original = json.loads(path.read_text(encoding='utf-8'))
        ir = {**original, 'sounding_events': [
            {**s, 'span': {**s['span'], 'end': q(min(f(s['span']['end']),16))}}
            for s in original['sounding_events'] if f(s['span']['start']) < 16],
            'measures': [{**m, 'actual_duration_quarter': q(min(f(m['actual_duration_quarter']),16-f(m['global_start_quarter'])))}
                         for m in original['measures'] if f(m['global_start_quarter']) < 16]}
        t = perf_counter()
        joint = analyze_joint(ir)
        elapsed = perf_counter()-t
        baseline = analyze_unfolded(ir)
        name = collection+'-'+path.parent.name
        (output/(name+'.json')).write_text(json.dumps(joint,ensure_ascii=False,indent=2),encoding='utf-8')
        results.append({'score': name, 'ir_source': str(path.resolve()), 'range_quarters': [0,16],
                        'sounds': len(ir['sounding_events']), 'seconds': round(elapsed,3),
                        'baseline_segments': len(baseline['segments']), 'joint_segments': len(joint['segments']),
                        'conditional_nct_count': sum(len(s['selected']['nct']) for s in joint['segments']),
                        'selected_labels': [s['selected']['label'] for s in joint['segments']]})
    report = {'policy':'blind real-score runtime diagnostic; not accuracy evaluation', 'results':results,
              'production_enabled':False, 'holdout_used':False}
    (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
