"""Read-only source/parser timing discrepancies. Never repair a source implicitly."""
import argparse
from collections import defaultdict
from fractions import Fraction
import json
from pathlib import Path
from .source_sequence_audit import xml_rows, parser_rows
from .dcml_import import parse_score_without_imported_harmony
from .harmony_visual_review import digest


def grid_disagreements(measures):
    by_index=defaultdict(dict)
    for (part,index),value in measures.items():
        by_index[index][part]=value
    parts={part for part,_ in measures}
    result=[]
    for index,rows in sorted(by_index.items()):
        signatures={tuple(sorted(row.items())) for row in rows.values()}
        if len(signatures)>1 or set(rows)!=parts:
            starts=[Fraction(r['start']) for r in rows.values()]
            durations=[Fraction(r['duration']) for r in rows.values()]
            result.append({'physical_measure':index,'parts':rows,
                'onset_spread_quarters':str(max(starts)-min(starts)),
                'duration_spread_quarters':str(max(durations)-min(durations))})
    return result


def inspect(source):
    before=digest(source)
    raw,measures=xml_rows(source)
    score,_,mapping=parse_score_without_imported_harmony(source)
    parsed=parser_rows(score,mapping)
    # A local token/order match is diagnostic only; global time disagreement blocks reuse.
    rg=defaultdict(list); pg=defaultdict(list); ambiguous=0
    for r in raw: rg[r['part'],r['measure_index'],r['staff'],r['voice']].append(r)
    for p in parsed:
        keys=[k for k in rg if k[:3]==(p['part'],p['measure_index'],p['staff']) and (p['voice'] is None or k[3]==p['voice'])]
        if len(keys)!=1: ambiguous+=1
        else: pg[keys[0]].append(p)
    mismatches=[]
    for k,rows in pg.items():
        if [p['token'] for p in rows] != [r['token'] for r in rg[k]]: continue
        for p,r in zip(rows,rg[k]):
            if Fraction(p['global_onset'])!=Fraction(r['global_onset']):
                mismatches.append({'source':r,'parser':p,
                    'delta_quarters':str(Fraction(p['global_onset'])-Fraction(r['global_onset']))})
    assert before==digest(source)
    return {'source':str(source),'sha256':before,'input_unchanged':True,
        'part_grid_disagreements':grid_disagreements(measures),
        'source_parser_global_time_mismatches':mismatches,'ambiguous_lane_events':ambiguous,
        'policy':'diagnostic_only_no_rounding_or_source_edit',
        'next_contract':'Distinguish shared measure anchoring, duration rounding and real irregular measures before a versioned time migration.'}


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('source',type=Path);ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args()
    if args.output.exists():raise ValueError('output_exists')
    data=inspect(args.source);args.output.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'grid_disagreements':len(data['part_grid_disagreements']),
        'parser_time_mismatches':len(data['source_parser_global_time_mismatches']),
        'first_grid_disagreement':data['part_grid_disagreements'][:1],
        'first_parser_mismatch':data['source_parser_global_time_mismatches'][:1]},ensure_ascii=True))
