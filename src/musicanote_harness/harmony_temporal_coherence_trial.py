"""Apply ordered coherence evidence to all frozen held-boundary cases."""
import argparse
from collections import Counter
from pathlib import Path
import sys
from .harmony_temporal_coherence import augment, VERSION
from .harmony_boundary_assessment_trial import run

BOUNDARY_KEY = 'temporal_coherence'
TOP_KEYS = {'temporal_coherence_version', 'temporal_coherence_preview'}
COUNTS_KEY = 'coherence_counts'
TITLE = '분산화음과 화성 교체의 시간 순서 대조'


def counts(evidence):
    c = Counter({'boundaries': 1, evidence['status']: 1})
    for p in evidence.get('profiles', {}).values():
        c['profiles'] += 1
        c['member_only_profiles'] += p['all_sounding_pitches_are_members']
        c['complete_union_with_nonmembers'] += p['complete_union_contains_nonmembers']
        c['complete_union_crossing_silence'] += p['complete_union_crosses_silence']
        c['complete_union_profiles'] += p['first_complete_union_time'] is not None
    return c


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--source', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(); run(a.source, a.output, stage=sys.modules[__name__])
