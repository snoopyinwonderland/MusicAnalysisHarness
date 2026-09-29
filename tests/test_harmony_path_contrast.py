from copy import deepcopy
from fractions import Fraction as F
import unittest
from test_harmony_reading_voice_context import score, chord
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_candidate_explanation import spelling_evidence
from musicanote_harness.harmony_path_contrast import compare


def fixture(extra=()):
    ir=score([('E4',0,1,'lead'),('G#3',F(5,4),F(3,2),'lead'),('D3',F(3,2),F(7,4),'lead'),('B3',F(7,4),2,'lead')]+list(extra))
    span={'start':q(0),'end':q(3)};es=[]
    for root,quality in [(4,'dominant7'),(8,'half-diminished7')]:
        c=chord(root,quality);sp=spelling_evidence(ir,span,c)
        es.append({'candidate':c,'span':deepcopy(span),'provenance':[{'candidate_ref':'test','reading_type':'conditional','reading_index':len(es)}],
            'status':'conditional_explanation_only','spelling_evidence':sp,'coherent_root_spellings':[r['root_spelling'] for r in sp['candidates']],
            'compatible_patterns':['chord_member_unfolding_compatible'],'conditional_ornaments':[]})
    path={'path_id':'p','group_id':'g','source_refs':['s0','s3'],'arrival_event_refs':['s1','s2','s3'],
          'conditional_explanations':es,'abstention_reasons':[],'initial_gap':{'start':q(1),'end':q(F(5,4))},'prior_review_reasons':['intervening_attacks_need_path_explanation']}
    return ir,{'records':[path]}


class PathContrastTest(unittest.TestCase):
    def test_control_xml_displays_sharps(self):
        from musicanote_harness.harmony_path_contrast_trial import fixture as control, control_xml
        from xml.etree import ElementTree as ET
        root=ET.fromstring(control_xml(control('held_Fsharp')))
        altered=[n for n in root.findall('.//note') if n.findtext('pitch/alter')=='1']
        self.assertEqual(len(altered),2)
        self.assertTrue(all(n.findtext('accidental')=='sharp' for n in altered))
    def test_control_xml_preserves_flat_spelling(self):
        from musicanote_harness.harmony_path_contrast_trial import fixture as control, control_xml
        from xml.etree import ElementTree as ET
        root=ET.fromstring(control_xml(control('enharmonic')))
        self.assertTrue(any(n.findtext('pitch/step')=='F' and n.findtext('accidental')=='flat' for n in root.findall('.//note')))
    def test_shared_unfolding_not_two_votes(self):
        ir,p=fixture();r=compare(ir,p);pair=r['records'][0]['pairs'][0]
        self.assertEqual(pair['status'],'no_observed_membership_difference')
        self.assertEqual(len(pair['shared_pattern_refs']),1);self.assertIsNone(pair['selected']);self.assertIsNone(pair['ranking_weight'])
    def test_held_other_voice_distinguishes_membership_not_truth(self):
        ir,p=fixture([('E5',1,2,'upper')]);r=compare(ir,p)['records'][0];pair=r['pairs'][0]
        self.assertEqual(pair['status'],'observed_membership_difference_not_winner')
        self.assertIn('s4',pair['event_buckets']['left_member_only']+pair['event_buckets']['right_member_only'])
        self.assertTrue(next(x for x in r['all_voice_events'] if x['event_ref']=='s4')['held_at_start'])
    def test_opposing_tones_preserve_both_sides(self):
        ir,p=fixture([('E5',1,2,'upper'),('F#4',1,2,'inner')]);pair=compare(ir,p)['records'][0]['pairs'][0]
        self.assertEqual(len(pair['event_buckets']['left_member_only']),1);self.assertEqual(len(pair['event_buckets']['right_member_only']),1)
    def test_unobserved_member_not_disproof(self):
        ir,p=fixture();r=compare(ir,p)['records'][0]
        self.assertTrue(all(c['unobserved_member_pcs'] for c in r['conditions']))
        self.assertEqual(r['pairs'][0]['status'],'no_observed_membership_difference')
    def test_same_onset_doubling_not_double_occupancy(self):
        ir,p=fixture([('E5',1,2,'upper'),('E6',1,2,'inner')]);r=compare(ir,p)['records'][0]
        self.assertEqual(r['pitch_class_occupancy_quarters']['4'],q(F(3,4)))
    def test_half_open_window(self):
        ir,p=fixture([('E5',0,F(5,4),'upper'),('F#4',2,3,'inner')]);r=compare(ir,p)['records'][0]
        self.assertEqual(len(r['all_voice_events']),3)
    def test_partial_context_not_counted_as_failure(self):
        ir,p=fixture();p['records'][0]['conditional_explanations'][0]['span']['start']=q(F(3,2));r=compare(ir,p)['records'][0]
        self.assertEqual(r['pairs'],[]);self.assertEqual(len(r['excluded_conditions']),1)
    def test_duplicate_windows_do_not_multiply_pairs(self):
        ir,p=fixture();base=compare(ir,p)
        p['records'][0]['conditional_explanations']*=3
        self.assertEqual(compare(ir,p),base)
    def test_overlapping_paths_reuse_units(self):
        ir,p=fixture();p['records'].append({**deepcopy(p['records'][0]),'path_id':'another'})
        r=compare(ir,p);self.assertEqual(len(r['event_units']),3)
    def test_enharmonic_conflict_does_not_become_support(self):
        ir,p=fixture([('F-5',1,2,'upper')]);r=compare(ir,p)['records'][0]['pairs'][0]
        self.assertEqual(r['status'],'spelling_unresolved');self.assertIn('s4',r['event_buckets']['spelling_unresolved'])
    def test_prior_voice_abstention_remains(self):
        ir,p=fixture([('E5',1,2,'upper')]);p['records'][0]['abstention_reasons']=['arrival_polyphony_or_sustained_overlap']
        self.assertEqual(compare(ir,p)['records'][0]['pairs'][0]['status'],'context_or_voice_unresolved')
    def test_inputs_and_labels_unchanged(self):
        ir,p=fixture();old=deepcopy((ir,p));a=compare(ir,p);self.assertEqual((ir,p),old)
        self.assertEqual(a,compare({**ir,'annotations':['V7'],'phrases':[1,2]},p))
