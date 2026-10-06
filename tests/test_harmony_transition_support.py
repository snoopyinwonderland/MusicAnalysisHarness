from copy import deepcopy
from dataclasses import replace
from fractions import Fraction as F
from types import SimpleNamespace as NS
import unittest

from musicanote_harness import harmony_transition_support as t
from musicanote_harness import harmony_full_score as s
from musicanote_harness.harmony_scored_decoder import Observation
from test_harmony_functional_scoring import C, G, G7, example


def evidence(specs, meters=((0, (4, 4), None),), links=()):
    events = tuple(Observation(i, F(a), F(b), p, ('note_'+i,)) for i, p, a, b, height, voice in specs)
    rows = tuple({'id': e.event_id, 'start': e.start, 'end': e.end, 'pitch': height,
                  'token': e.pitch, 'pitch_data': {'step': e.pitch[0], 'alter': t.q(e.pitch[1]),
                    'octave': (height-e.pitch[1])//12-1, 'midi_pitch': height} if e.pitch and height is not None else {},
                  'identity': ('part', voice) if voice else None,
                  'source_note_ids': e.source_note_ids, 'clock_valid': bool(voice)}
                 for e, (_, _, _, _, height, voice) in zip(events, specs))
    by_id = {r['id']: r for r in rows}
    src = NS(events=events, measures=meters, _measure_times=tuple(F(m[0]) for m in meters),
             _metric_cache={}, source_ir_content_sha256='toy-source')
    return NS(source=src, rows=rows, links=tuple((by_id[a], by_id[b]) for a, b in links),
              _surface_cache={}, _pair_cache={})


def graph(runs, end=2):
    edges = tuple(NS(group_id=str(i), start=F(a), end=F(b), signature=sig)
                  for i, (a, b, sig) in enumerate(runs))
    return NS(edges=edges, points=(F(0), F(end)), max_segments=6), [e.group_id for e in edges]


class TransitionSupportTests(unittest.TestCase):
    def test_distributed_union_not_vertical_gate(self):
        ev = evidence([('c', ('C', 0), 1, F(4, 3), 60, 'v'),
                       ('e', ('E', 0), F(4, 3), F(5, 3), 64, 'v'),
                       ('g', ('G', 0), F(5, 3), 2, 67, 'v')])
        r = t.window(ev, F(1), F(2), G7, C)
        self.assertEqual(r['right_union_member_count'], 3)
        self.assertEqual(r['coverage']['right_two'], t.q(0))
        self.assertEqual(r['coverage']['exclusive_present'], t.q(F(2, 3)))
        self.assertEqual(len(r['events']), 3)

    def test_octave_doubling_is_one_spelled_member(self):
        ev = evidence([('a', ('C', 0), 1, 2, 60, 'a'), ('b', ('C', 0), 1, 2, 72, 'b')])
        r = t.window(ev, F(1), F(2), G7, C)
        self.assertEqual(r['right_union_member_count'], 1)
        self.assertEqual(r['coverage']['right_two'], t.q(0))
        self.assertEqual(r['cells'][0]['lowest_sounding_event_ids'], ['a'])

    def test_motion_credit_without_independent_chord_support_is_observable(self):
        ev = evidence([('b', ('B', 0), 0, 1, 59, 'v'), ('c', ('C', 0), 1, 2, 60, 'v')], links=(('b', 'c'),))
        p, ids = graph(((0, 1, G7), (1, 2, C)))
        r = t.observe_path(p, ev, ids)['transitions'][0]
        self.assertEqual(r['credited_resolution_features']['dominant_family_leading_tone'], t.q(1))
        self.assertEqual(r['right_complete_run']['right_union_member_count'], 1)
        self.assertFalse(r['harmony_change_confirmed']); self.assertFalse(r['nct_confirmed'])

    def test_supported_resolution_and_multiple_paths_do_not_multiply_credit(self):
        ev = evidence([('b', ('B', 0), 0, 1, 59, 'v'), ('c', ('C', 0), 1, 2, 60, 'v'),
                       ('b2', ('B', 0), 0, 1, 71, 'v2'), ('c2', ('C', 0), 1, 2, 72, 'v2'),
                       ('g', ('G', 0), 0, 2, 55, 'bass'), ('e', ('E', 0), 1, 2, 64, 'inner')],
                      links=(('b', 'c'), ('b2', 'c2')))
        p, ids = graph(((0, 1, G7), (1, 2, C)))
        r = t.observe_path(p, ev, ids)['transitions'][0]
        self.assertEqual(r['raw_resolution_features']['dominant_family_leading_tone'], t.q(1))
        self.assertEqual(r['right_complete_run']['coverage']['right_two'], t.q(1))
        self.assertEqual(r['held_common_event_ids'], ['g'])
        self.assertEqual(sum(len(d.get('source_event_pairs', [])) for d in r['resolution_details']), 2)

    def test_held_sound_preserves_complete_source_span_and_is_not_attack(self):
        ev = evidence([('g', ('G', 0), 0, 3, 55, 'bass')])
        r = t.window(ev, F(1), F(2), G, C)['events'][0]
        self.assertEqual(r['source_span'], {'start': t.q(0), 'end': t.q(3)})
        self.assertFalse(r['new_attack_in_window']); self.assertTrue(r['held_across_window_start'])
        self.assertEqual(r['source_note_ids'], ['note_g'])

    def test_unresolved_pitch_is_not_observed_zero(self):
        ev = evidence([('unknown', None, 1, 2, None, None)])
        r = t.window(ev, F(1), F(2), G, C)
        self.assertIsNone(r['right_union_member_count']); self.assertIsNone(r['coverage']['right_two'])
        self.assertFalse(r['cells'][0]['lowest_pitch_available'])
        self.assertEqual(len(r['events']), 1)

    def test_silence_is_known_zero(self):
        r = t.window(evidence([]), F(1), F(2), G, C)
        self.assertEqual(r['right_union_member_count'], 0)
        self.assertEqual(r['coverage']['right_two'], t.q(0)); self.assertEqual(r['coverage']['silence'], t.q(1))

    def test_meter_change_integrated_and_unknown_withheld(self):
        src = evidence([], meters=((0, (4, 4), None), (1, (6, 8), None))).source
        self.assertEqual(t.first_beat_end(src, F(1, 2), F(3)), F(7, 4))
        src = evidence([], meters=((0, (None, 4), None),)).source
        self.assertIsNone(t.first_beat_end(src, F(0), F(2)))
        p, ids = graph(((0, 1, G), (1, 2, C)))
        ev = evidence([], meters=((0, (None, 4), None),))
        r = t.observe_path(p, ev, ids)['transitions'][0]
        self.assertIsNone(r['right_first_beat']); self.assertIsNotNone(r['right_complete_run'])

    def test_completed_run_not_first_raw_edge_is_profiled(self):
        ev = evidence([('c', ('C', 0), 1, 2, 60, 'v')])
        a, ai = graph(((0, 1, G), (1, 2, C)))
        b, bi = graph(((0, 1, G), (1, F(3, 2), C), (F(3, 2), 2, C)))
        self.assertEqual(t.observe_path(a, ev, ai), t.observe_path(b, ev, bi))

    def test_spelling_not_enharmonic_midi_membership(self):
        ev = evidence([('bsharp', ('B', 1), 1, 2, 60, 'v')])
        r = t.window(ev, F(1), F(2), G, C)
        self.assertEqual(r['right_union_member_count'], 0)
        self.assertEqual(r['cells'][0]['lowest_spelled_tokens'], [('B', 1)])

    def test_invalid_or_incomplete_path_rejected(self):
        p, ids = graph(((0, 1, G), (1, 2, C)))
        for bad in ([], ids[:1], ['unknown'], list(reversed(ids))):
            with self.assertRaises(ValueError): t.completed_runs(p, bad)

    def test_profile_is_label_blind_and_leaves_original_score_unchanged(self):
        ir, _, _, p, ev = example(); before = deepcopy(ir)
        ids = [e.group_id for e in p.edges]
        scorer = s.Scorer(p, ev, s.initial_weights(s.fresh.timing.ZERO))
        cost = scorer.score_path(ids); a = t.observe_path(p, ev, ids)
        self.assertEqual(ir, before); self.assertEqual(scorer.score_path(ids), cost)
        ir['annotations'] = ['not_feature_input']; b = t.observe_path(p, ev, ids)
        self.assertEqual(a, b); self.assertFalse(a['source_labels_used'])


if __name__ == '__main__': unittest.main()
