from copy import deepcopy
from fractions import Fraction as F
import unittest
from test_harmony_reading_voice_context import score,chord
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_path_explanation import explain


def fixture(extra=()):
    pitches=['C4','E4','G4','C4','E4','G4','B4','E4']
    ir=score([('C3',0,1,'bass')]+[(p,1+F(i,4),1+F(i+1,4),'lead') for i,p in enumerate(pitches)]+[('E3',3,4,'bass')]+list(extra))
    def seg(a,b,c):return {'span':{'start':q(a),'end':q(b)},'candidate':c}
    candidate={'evidence_id':'test','span':{'start':q(1),'end':q(3)},'boundary':q(2),'beat_unit_quarter':q(1),
        'merged_seventh':[{'segments':[seg(1,3,chord(0,'major7'))],'local_cost':1}],
        'split_triads':[{'segments':[seg(1,2,chord(0,'major')),seg(2,3,chord(4,'minor'))],'local_cost':2}]}
    return ir,candidate,{'start':q(0),'end':q(4)}


class PathExplanationTests(unittest.TestCase):
    def test_only_identical_frozen_duplicates_collapsed(self):
        from musicanote_harness.harmony_path_explanation_trial import unique_records
        rows=[{'id':'x','span':[1,2]},{'id':'x','span':[1,2]}]
        self.assertEqual(len(unique_records(rows,'id')),1)
    def test_conflicting_duplicate_not_silently_overwritten(self):
        from musicanote_harness.harmony_path_explanation_trial import unique_records
        with self.assertRaises(ValueError):unique_records([{'id':'x','span':[1,2]},{'id':'x','span':[1,3]}],'id')
    def test_equivalent_membership_does_not_choose_harmony(self):
        r=explain(*fixture());self.assertEqual(r['pairs'][0]['status'],'same_observed_membership_not_equivalent_harmony')
        self.assertIsNone(r['selected']);self.assertIsNone(r['pairs'][0]['ranking_weight'])
    def test_seventh_inside_first_triad_not_deleted_as_nct(self):
        r=explain(*fixture([('B3',1,2,'other')]));p=r['pairs'][0]
        self.assertEqual(p['status'],'different_explanation_not_winner')
        self.assertEqual(p['diagnostic_pc_quarter_exposure']['core']['merged_only_member'],q(1))
        self.assertIsNone(p['selected'])
    def test_pedal_crossing_change_keeps_original_duration(self):
        r=explain(*fixture([('C2',0,4,'pedal')]));self.assertEqual(r['event_units']['s10']['original_span'],{'start':q(0),'end':q(4)})
        p=r['pairs'][0];self.assertEqual(p['diagnostic_pc_quarter_exposure']['after']['merged_only_member'],q(1))
    def test_unison_doubling_not_double_exposure(self):
        first=explain(*fixture([('B3',1,2,'other')]))['pairs'][0]
        second=explain(*fixture([('B3',1,2,'other'),('B2',1,2,'bass2')]))['pairs'][0]
        self.assertEqual(first['diagnostic_pc_quarter_exposure'],second['diagnostic_pc_quarter_exposure'])
    def test_empty_time_cell_preserved(self):
        ir,c,ctx=fixture();ir['sounding_events'][0]['span']['end']=q(F(1,2));r=explain(ir,c,ctx)
        self.assertTrue(any(not cell['event_refs'] and cell['span']=={'start':q(F(1,2)),'end':q(1)} for cell in r['cells']))
    def test_enharmonic_member_is_unresolved(self):
        r=explain(*fixture([('F-4',3,4,'other')]));self.assertEqual(r['pairs'][0]['status'],'spelling_unresolved')
    def test_incomplete_path_rejected(self):
        ir,c,ctx=fixture();c['split_triads'][0]['segments'][1]['span']['start']=q(F(9,4))
        with self.assertRaises(ValueError):explain(ir,c,ctx)
    def test_context_truncation_not_absence(self):
        ir,c,_=fixture();r=explain(ir,c,{'start':q(1),'end':q(3)})
        self.assertEqual(r['pairs'][0]['status'],'context_unresolved')
    def test_half_open_release_attack(self):
        r=explain(*fixture());cell=next(c for c in r['cells'] if c['span']['start']==q(2))
        self.assertNotIn('s4',cell['event_refs']);self.assertIn('s5',cell['event_refs'])
    def test_annotation_independence_and_inputs_unchanged(self):
        args=fixture();old=deepcopy(args);r=explain(*args);self.assertEqual(args,old)
        args[0]['annotations']=['V7'];self.assertEqual(explain(*args),r)
    def test_edges_flagged_as_assumptions(self):
        r=explain(*fixture())
        for p in r['paths']:
            for cell,e in zip(r['cells'],p['cells']):self.assertEqual(e['outside_extension_assumption'],cell['region']!='core')
    def test_bad_pitch_does_not_supply_membership(self):
        ir,c,ctx=fixture();ir['sounding_events'][0]['pitch']['alter']=q(F(1,2))
        self.assertEqual(explain(ir,c,ctx)['pairs'][0]['status'],'spelling_unresolved')
