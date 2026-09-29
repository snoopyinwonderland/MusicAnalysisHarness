from copy import deepcopy
from fractions import Fraction as F
import unittest

from test_harmony_path_contrast import fixture
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_path_contrast import compare
from musicanote_harness.harmony_temporal_context import observe


def run(extra=(), contexts=None):
    ir, paths = fixture(extra)
    cs = contexts if contexts is not None else [{'start': q(0), 'end': q(4)}]
    return ir, observe(ir, compare(ir, paths), cs)


class TemporalContextTests(unittest.TestCase):
    def test_released_is_not_held(self):
        _, r = run(); boundary = r['records'][0]['boundaries'][0]
        self.assertIn('s0', boundary['released_before'])
        self.assertNotIn('s0', boundary['held_across'])
        self.assertEqual(r['event_units']['s0']['original_span']['end'], q(1))

    def test_exact_release_excluded_from_arrival(self):
        _, r = run([('E5', F(1,2), F(5,4), 'upper')]); row = r['records'][0]
        self.assertIn('s4', row['boundaries'][0]['released_at'])
        self.assertNotIn('s4', row['windows']['arrival']['event_refs'])

    def test_exact_attack_belongs_to_following_window(self):
        _, r = run([('F#4',2,3,'upper')]); row = r['records'][0]
        self.assertIn('s4', row['boundaries'][1]['attacked_at'])
        self.assertNotIn('s4', row['windows']['arrival']['event_refs'])
        self.assertIn('s4', row['windows']['after']['event_refs'])

    def test_tied_sound_id_spans_boundary(self):
        ir,p = fixture([('E5',1,3,'upper')]); ir['sounding_events'][-1]['source_note_ids'].append('continuation')
        ir['note_events'].append({**ir['note_events'][-1], 'note_id':'continuation'})
        row = observe(ir, compare(ir,p), [{'start':q(0),'end':q(4)}])['records'][0]
        self.assertTrue(all('s4' in b['held_across'] for b in row['boundaries']))
        self.assertFalse(any(b['same_spelled_pitch_reattack_pairs'] for b in row['boundaries']))

    def test_reattack_preserves_gap(self):
        _,r = run([('E4',2,F(5,2),'lead')]); b = r['records'][0]['boundaries'][1]
        p = next(p for p in b['same_spelled_pitch_reattack_pairs'] if p['event_refs']==['s0','s4'])
        self.assertEqual(p['gap_quarters'],q(1)); self.assertFalse(p['continuous_sound'])

    def test_different_lane_not_reattack_connection(self):
        _,r = run([('E4',2,3,'other')]); self.assertFalse(r['records'][0]['boundaries'][1]['same_spelled_pitch_reattack_pairs'])

    def test_enharmonic_repetition_not_same_spelling(self):
        _,r = run([('F-4',2,3,'lead')]); row=r['records'][0]
        self.assertFalse(row['boundaries'][1]['same_spelled_pitch_reattack_pairs'])
        self.assertEqual(row['pairs'][0]['status'],'spelling_unresolved')

    def test_exclusive_switch_is_not_chord_change(self):
        _,r = run([('F#4',2,3,'other')]); p=r['records'][0]['pairs'][0]
        self.assertEqual(p['status'],'exclusive_membership_switch_not_harmonic_change')
        self.assertIsNone(p['selected']);self.assertTrue(p['outside_membership_is_counterfactual'])
        self.assertTrue(all(h['selected'] is None for h in p['hypotheses']))

    def test_rest_and_notated_silence_preserved(self):
        ir,p=fixture();ir['rest_events']=[{'rest_id':'rest','global_onset_quarter':q(1),'notated_duration_quarter':q(F(1,4))}]
        row=observe(ir,compare(ir,p),[{'start':q(0),'end':q(4)}])['records'][0]
        self.assertEqual(row['windows']['before']['rest_refs'],['rest'])
        self.assertEqual(row['windows']['before']['all_voice_notated_silence'],[{'start':q(1),'end':q(F(5,4))}])

    def test_context_cutoff_is_not_absence(self):
        _,r=run(contexts=[{'start':q(F(5,4)),'end':q(2)}]); row=r['records'][0]
        self.assertFalse(row['windows']['before']['available'])
        self.assertFalse(row['windows']['before']['complete_requested_window'])
        self.assertEqual(row['pairs'][0]['status'],'context_unresolved')

    def test_contexts_are_not_stitched(self):
        _,r=run(contexts=[{'start':q(0),'end':q(2)},{'start':q(1),'end':q(4)}]); row=r['records'][0]
        self.assertIn('one_denominator_beat_context_truncated',row['abstention_reasons'])

    def test_meter_change_blocks_interpretation(self):
        ir,p=fixture();ir['measures'].append({**ir['measures'][0],'global_start_quarter':q(2),'time_signature':{'beats':3,'beat_type':8}})
        row=observe(ir,compare(ir,p),[{'start':q(0),'end':q(4)}])['records'][0]
        self.assertIn('meter_change',row['abstention_reasons'])

    def test_repeat_barrier_blocks_interpretation(self):
        ir,p=fixture();ir['measures'][0]['actual_duration_quarter']=q(2);ir['measures'][0]['repeat_barline']={'location':'right','repeat_direction':'backward'}
        row=observe(ir,compare(ir,p),[{'start':q(0),'end':q(4)}])['records'][0]
        self.assertIn('repeat_or_ending_barrier',row['abstention_reasons'])

    def test_meter_change_before_arrival_also_blocks(self):
        ir,p=fixture();ir['measures'][0]['time_signature']={'beats':3,'beat_type':8}
        ir['measures'].append({**ir['measures'][0],'global_start_quarter':q(1),'time_signature':{'beats':4,'beat_type':4}})
        row=observe(ir,compare(ir,p),[{'start':q(0),'end':q(4)}])['records'][0]
        self.assertIn('meter_change_or_unknown_before_arrival',row['abstention_reasons'])

    def test_adjacent_same_pitch_attack_is_not_tie(self):
        _,r=run([('B3',2,3,'lead')]); b=r['records'][0]['boundaries'][1]
        self.assertEqual(b['same_spelled_pitch_reattack_pairs'][0]['gap_quarters'],q(0))
        self.assertEqual(b['held_across'],[])

    def test_same_voice_name_other_part_is_not_same_lane(self):
        ir,p=fixture([('E4',2,3,'lead')]);ir['note_events'][-1]['part_id']='part2'
        row=observe(ir,compare(ir,p),[{'start':q(0),'end':q(4)}])['records'][0]
        self.assertEqual(row['boundaries'][1]['same_spelled_pitch_reattack_pairs'],[])

    def test_grace_is_not_silent_evidence(self):
        ir,p=fixture();ir['note_events'].append({'note_id':'grace','grace':{'is_grace':True},'global_onset_quarter':q(2)})
        row=observe(ir,compare(ir,p),[{'start':q(0),'end':q(4)}])['records'][0]
        self.assertEqual(row['grace_refs'],['grace']);self.assertEqual(row['pairs'][0]['status'],'context_unresolved')

    def test_duplicate_paths_share_original_units(self):
        ir,p=fixture();c=compare(ir,p);c['records']*=2;r=observe(ir,c,[{'start':q(0),'end':q(4)}])
        self.assertEqual(len(r['event_units']),4)

    def test_missing_context_no_scan(self):
        _,r=run(contexts=[]);self.assertEqual(r['event_units'],{})
        self.assertEqual(r['records'][0]['status'],'meter_or_frozen_context_unavailable')

    def test_annotation_independence_immutability_and_determinism(self):
        ir,p=fixture();c=compare(ir,p);old=deepcopy((ir,c));ctx=[{'start':q(0),'end':q(4)}]
        r=observe(ir,c,ctx);self.assertEqual((ir,c),old)
        self.assertEqual(r,observe({**ir,'annotations':['V7'],'phrases':[1]},c,ctx))
        self.assertEqual(r,observe(ir,c,ctx))
