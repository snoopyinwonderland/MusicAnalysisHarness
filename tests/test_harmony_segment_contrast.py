from copy import deepcopy
from fractions import Fraction
import unittest
from unittest.mock import patch
from test_harmony_open_candidates import score
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_joint import f
from musicanote_harness.harmony_continuous_survey import plan,analyze
from musicanote_harness.harmony_segment_contrast import build,compare,profile


def fixture():return score([('G4',0,1,'v'),('A4',1,2,'v'),('B4',2,3,'v'),('G3',0,3,'bass'),('D4',0,3,'inner')])
def run(ir):
    s=next(s for s in plan(ir,{'start':q(0),'end':q(3)})['samples'] if len(s['seed_event_refs'])==3)
    return build(ir,analyze(ir,s))
def full_assignment(r):return max(r['assignments'],key=lambda a:len(a['links']))['assignment_id']
def index(rows,label):return next(i for i,r in enumerate(rows) if r['display_label']==label)


class SegmentContrastTests(unittest.TestCase):
    def test_two_frozen_attack_cuts_not_annotation_boundaries(self):
        ir=fixture();a=run(ir);ir['annotations']=['force V'];ir['title']='another';self.assertEqual(a,run(ir))
        self.assertEqual([r['boundary'] for r in a['boundaries']],[q(1),q(2)])
        self.assertTrue(all(not r['boundary_confirmed'] for r in a['boundaries']))

    def test_all_part_time_equal_with_sustained_sounds(self):
        r=run(fixture());c=compare(r,0,0,0,0,full_assignment(r))
        self.assertEqual(c['hold']['total_note_time'],q(9));self.assertEqual(c['split']['total_note_time'],q(9))
        self.assertEqual(sum(map(f,c['split_minus_hold'].values())),0)
        bass=next(s['sounding_event_id'] for s in r['events'] if s['pitch']['spelling']=='G3')
        self.assertEqual(sum((f(x['span']['end'])-f(x['span']['start']) for x in c['split']['items'] if x['event_ref']==bass),Fraction()),3)

    def test_same_global_assignment_not_local_cherry_picking(self):
        r=run(fixture());h=index(r['hold_readings'],'G:major');b=r['boundaries'][0]
        l=index(b['left']['readings'],'G:major');rr=index(b['right']['readings'],'G:major')
        linked=compare(r,0,h,l,rr,full_assignment(r))
        no_link=next(a['assignment_id'] for a in r['assignments'] if not a['links'])
        isolated=compare(r,0,h,l,rr,no_link)
        self.assertEqual(linked['hold']['note_time']['conditional_nonmember'],q(1))
        self.assertEqual(isolated['hold']['note_time']['conditional_nonmember'],q(0))
        self.assertEqual(linked['hold']['assignment_ref'],linked['split']['assignment_ref'])

    def test_same_chord_cut_does_not_prove_change(self):
        r=run(fixture());b=r['boundaries'][0]
        c=compare(r,0,index(r['hold_readings'],'G:major'),index(b['left']['readings'],'G:major'),index(b['right']['readings'],'G:major'),full_assignment(r))
        self.assertTrue(c['same_member_spelling_sets']);self.assertFalse(c['harmonic_change_confirmed'])
        self.assertEqual(c['split']['note_time']['conditional_nonmember'],q(0))
        self.assertIn('cross-boundary',c['warning']);self.assertIsNone(c['preferred'])

    def test_unknown_assignment_rejected(self):
        with self.assertRaisesRegex(ValueError,'unknown_assignment'):compare(run(fixture()),0,0,0,0,'missing')

    def test_bad_partition_rejected(self):
        r=run(fixture());bad=deepcopy(r['hold_readings'][0]);bad['span']['start']=q(1)
        with self.assertRaisesRegex(ValueError,'invalid_partition'):profile(r['boundaries'][0]['cells'],r['span'],[bad],full_assignment(r))

    def test_missing_evidence_rejected(self):
        r=run(fixture());r['hold_readings'][0]['event_states'].clear()
        with self.assertRaisesRegex(ValueError,'missing_event_state'):compare(r,0,0,0,0,full_assignment(r))

    def test_blocked_condition_cannot_explain_away_notes(self):
        r=run(fixture());h=index(r['hold_readings'],'G:major')
        r['hold_readings'][h]['condition']['abstention_reasons']=['grace_timing']
        c=compare(r,0,h,0,0,full_assignment(r));self.assertEqual(c['hold']['note_time']['conditional_nonmember'],q(0))

    def test_budget_preserves_catalog_without_pruned_comparison(self):
        with patch('musicanote_harness.harmony_segment_contrast.MAX_SIDE_CONDITION_ASSIGNMENTS',0):r=run(fixture())
        self.assertTrue(r['boundaries'][0]['left']['catalog']['candidates'])
        self.assertEqual(r['boundaries'][0]['virtual_comparison_count'],0)
        with self.assertRaisesRegex(ValueError,'boundary_not_ready'):compare(r,0,0,0,0,full_assignment(r))

    def test_baseline_abstention_propagates(self):
        r=build({}, {'sample':{'span':{'start':q(0),'end':q(1)}},'status':'voice_enumeration_abstention'})
        self.assertEqual(r['status'],'baseline_abstention');self.assertEqual(r['boundaries'],[])

    def test_empty_spelled_factor_is_not_a_comparison(self):
        ir=fixture();sample=plan(ir,{'start':q(0),'end':q(3)})['samples'][0];baseline=analyze(ir,sample)
        baseline['conditions']=[]
        r=build(ir,baseline)
        self.assertTrue(all(b['status']=='no_spelled_comparison' for b in r['boundaries']))
        self.assertTrue(all('hold' in b['empty_reading_factors'] for b in r['boundaries']))
        with self.assertRaisesRegex(ValueError,'boundary_not_ready'):compare(r,0,0,0,0,full_assignment(r))

    def test_factorized_product_is_complete_not_top_k(self):
        r=run(fixture())
        for b in r['boundaries']:
            self.assertEqual(b['virtual_comparison_count'],len(r['hold_readings'])*len(b['left']['readings'])*len(b['right']['readings'])*len(r['assignments']))
            for side in ('left','right'):
                self.assertEqual(len(b[side]['readings']),sum(len(c['spelling_alternatives']) for c in b[side]['catalog']['candidates']))

    def test_inputs_unchanged_and_no_winner(self):
        ir=fixture();s=plan(ir,{'start':q(0),'end':q(3)})['samples'][0];base=analyze(ir,s);before=deepcopy((ir,base))
        r=build(ir,base);self.assertEqual((ir,base),before);self.assertIsNone(r['selected']);self.assertFalse(r['ranking_performed'])
