from copy import deepcopy
import unittest
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_joint import f
from musicanote_harness.harmony_open_candidates import window
from musicanote_harness.harmony_hold_change_contrast import compare, profile
from test_harmony_change_gate import fixture, run
from test_harmony_reattack_figures import fixture as repeated


class HoldChangeContrastTests(unittest.TestCase):
    def test_all_alternatives_preserved(self):
        ir=fixture();gate=run(ir);r=compare(ir,gate)
        self.assertEqual(len(r['change_readings']),len(gate['change_proposals']))
        self.assertEqual(len(r['comparisons']),len(r['hold_readings'])*len(r['change_readings']))
        self.assertIsNone(r['selected']);self.assertFalse(r['ranking_performed'])
    def test_same_time_coverage(self):
        ir=fixture();r=compare(ir,run(ir))
        for v in r['hold_readings']+r['change_readings']:
            self.assertEqual(v['profile']['total_note_time_quarters'],q(12))
            self.assertEqual(sum(map(f,v['profile']['note_time_quarters'].values())),12)
    def test_complete_change_zero_unexplained_not_winner(self):
        ir=fixture();r=compare(ir,run(ir));v=next(x for x in r['change_readings'] if x['proposal']['source_label']=='C:major' and x['proposal']['target_label']=='G:major')
        self.assertEqual(v['profile']['note_time_quarters']['unexplained'],q(0))
        self.assertTrue(all(c['preferred'] is None for c in r['comparisons']))
    def test_repeated_hold_explanations(self):
        ir=repeated();r=compare(ir,run(ir));v=next(h for h in r['hold_readings'] if h['candidate']['label']=='C:major')
        self.assertEqual(v['profile']['note_time_quarters']['conditional_nct'],q(1))
        self.assertTrue(v['candidate']['residual_event_refs'])
    def test_absence_of_change_not_hold_confirmation(self):
        ir=repeated();r=compare(ir,run(ir));self.assertEqual(r['change_readings'],[])
        self.assertEqual(r['comparisons'],[]);self.assertIsNone(r['selected'])
    def test_no_mutation_and_annotation_independent(self):
        ir=fixture();g=run(ir);old=(deepcopy(ir),deepcopy(g));r=compare(ir,g)
        self.assertEqual((ir,g),old);ir['annotations']=['V7'];self.assertEqual(compare(ir,g),r)
    def test_mismatched_boundary_rejected(self):
        ir=fixture();g=run(ir);g['boundary']=q(1)
        with self.assertRaises(ValueError):compare(ir,g)
    def test_gapped_partition_rejected(self):
        ir=fixture();w=window(ir,{'start':q(0),'end':q(4)})
        with self.assertRaises(ValueError):profile(w,[{'span':{'start':q(1),'end':q(4)},'candidate':w['candidates'][0],'roles':{}}])
    def test_deltas_sum_to_zero(self):
        ir=fixture();r=compare(ir,run(ir))
        for c in r['comparisons']:self.assertEqual(sum(map(f,c['change_minus_hold_note_time'].values())),0)
    def test_held_sound_counted_by_duration_not_twice(self):
        ir=repeated();w=window(ir,{'start':q(0),'end':q(4)});c=next(c for c in w['candidates'] if c['label']=='C:major')
        p=profile(w,[{'span':{'start':q(0),'end':q(2)},'candidate':c,'roles':{}},
                     {'span':{'start':q(2),'end':q(4)},'candidate':c,'roles':{}}])
        sid=next(s['sounding_event_id'] for s in ir['sounding_events'] if s['pitch']['spelling']=='C3')
        self.assertEqual(sum(f(x['duration']) for x in p['event_readings'][sid]),4)
