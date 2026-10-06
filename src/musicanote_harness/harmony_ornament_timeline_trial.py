import argparse
from pathlib import Path
import sys
from .harmony_ornament_timeline import augment, VERSION
from .harmony_boundary_assessment_trial import run

BOUNDARY_KEY = 'ornament_timeline'
TOP_KEYS = {'ornament_timeline_version', 'ornament_timeline_preview'}
COUNTS_KEY = 'ornament_timeline_counts'
TITLE = '시간순 장식 후보와 보류·미설명 구간'

def counts(e):
    return {'boundaries': 1, e['status']: 1, 'withheld_patterns': len(e['withheld_pattern_reasons'])}

if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--source', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(); run(a.source, a.output, stage=sys.modules[__name__])
