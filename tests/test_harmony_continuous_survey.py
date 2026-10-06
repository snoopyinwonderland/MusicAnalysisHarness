from copy import deepcopy
import unittest
from unittest.mock import patch
from test_harmony_open_candidates import score
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_continuous_survey import plan,analyze


def fixture():return score([('G4',0,1,'v'),('A4',1,2,'v'),('B4',2,3,'v'),
    ('C5',3,4,'v'),('G3',0,4,'b'),('D4',0,4,'f')])


class ContinuousSurveyTests(unittest.TestCase):
    def test_all_adjacent_three_groups_not_only_successes(self):
        p=plan(fixture(),{'start':q(0),'end':q(4)})
        self.assertEqual(len(p['samples']),2)
        self.assertEqual(p['samples'][0]['attack_group_onsets'],[q(0),q(1),q(2)])
        self.assertEqual(p['samples'][1]['attack_group_onsets'],[q(1),q(2),q(3)])
        self.assertFalse(p['independent_samples'])

    def test_simultaneous_pitches_are_one_group(self):
        ir=score([('G4',0,1,'v'),('D5',0,1,'v'),('A4',1,2,'v'),('B4',2,3,'v')])
        p=plan(ir,{'start':q(0),'end':q(4)})
        self.assertEqual(len(p['samples']),1);self.assertEqual(len(p['samples'][0]['seed_event_refs']),4)

    def test_labels_phrase_and_title_do_not_select_samples(self):
        ir=fixture();span={'start':q(0),'end':q(4)};a=plan(ir,span)
        ir['annotations']=['V7/V'];ir['phrases']=[0,999];ir['title']='different'
        self.assertEqual(a,plan(ir,span))

    def test_sustained_note_beyond_scope_abstains_without_cutting(self):
        ir=score([('G4',0,6,'v'),('A4',1,2,'v'),('B4',2,3,'v')])
        s=plan(ir,{'start':q(0),'end':q(4)})['samples'][0]
        self.assertEqual(s['span']['end'],q(6));self.assertTrue(s['abstention_reasons'])
        self.assertEqual(analyze(ir,s)['status'],'sample_scope_abstention')

    def test_same_note_time_all_spelled_candidates(self):
        ir=fixture();s=plan(ir,{'start':q(0),'end':q(4)})['samples'][0];r=analyze(ir,s)
        self.assertEqual(r['status'],'evaluated');self.assertTrue(r['conditions'])
        self.assertTrue(all(c['all_note_time']==q(3) for c in r['conditions']))
        self.assertTrue(any(c['patterns'] for c in r['conditions']))

    def test_other_parts_supply_harmonic_evidence_not_voice_assignment(self):
        ir=fixture();s=plan(ir,{'start':q(0),'end':q(4)})['samples'][0];r=analyze(ir,s)
        self.assertEqual(len(r['voices']['events']),3)
        self.assertEqual(len(r['catalog']['providers']['base']['event_units']),5)

    def test_gap_samples_kept_no_pattern_shortcut(self):
        ir=score([('G4',0,1,'v'),('A4',1.5,2,'v'),('B4',2,3,'v'),('G3',0,3,'b'),('D4',0,3,'f')])
        samples=plan(ir,{'start':q(0),'end':q(4)})['samples'];self.assertEqual(len(samples),1)
        r=analyze(ir,samples[0]);self.assertFalse(any(c['patterns'] for c in r['conditions']))

    def test_enharmonic_rewrite_does_not_change_sample_selection(self):
        ir=fixture();a=plan(ir,{'start':q(0),'end':q(4)})
        ir['sounding_events'][1]['pitch'].update(step='G',alter=q(2),spelling='G##4')
        self.assertEqual(a,plan(ir,{'start':q(0),'end':q(4)}))

    def test_repeat_barrier_preserved(self):
        ir=fixture();m=ir['measures'][0];m['actual_duration_quarter']=q(1)
        m['repeat_barline']={'location':'right','repeat_direction':'backward'}
        s=plan(ir,{'start':q(0),'end':q(4)})['samples'][0]
        self.assertEqual(analyze(ir,s)['status'],'context_abstention')

    def test_input_immutable_and_no_harmony_selection(self):
        ir=fixture();before=deepcopy(ir);s=plan(ir,{'start':q(0),'end':q(4)})['samples'][0]
        r=analyze(ir,s);self.assertEqual(ir,before);self.assertIsNone(r['selected'])
        self.assertTrue(all(c['selected'] is None for c in r['conditions']))

    def test_no_supported_spelling_is_not_deleted(self):
        ir=fixture();s=plan(ir,{'start':q(0),'end':q(4)})['samples'][0];r=analyze(ir,s)
        expected={c['candidate_id'] for c in r['catalog']['candidates']}
        seen={c['candidate_ref'] for c in r['conditions']}|set(r['candidates_without_spelling_refs'])
        self.assertEqual(expected,seen)

    def test_condition_budget_abstains_without_pruning(self):
        ir=fixture();s=plan(ir,{'start':q(0),'end':q(4)})['samples'][0]
        with patch('musicanote_harness.harmony_continuous_survey.MAX_CONDITION_ASSIGNMENTS',0):
            r=analyze(ir,s)
        self.assertEqual(r['status'],'condition_budget_abstention_no_pruning')
        self.assertGreater(r['condition_assignment_count'],0)
        self.assertFalse(r['conditions']);self.assertTrue(r['catalog']['candidates'])
        self.assertIsNone(r['selected'])

    def test_incomplete_voice_enumeration_never_enters_explainer(self):
        ir=fixture();s=plan(ir,{'start':q(0),'end':q(4)})['samples'][0]
        with patch('musicanote_harness.harmony_continuous_survey.observe',return_value={'enumeration_complete':False}), patch('musicanote_harness.harmony_continuous_survey.explain') as explainer:
            r=analyze(ir,s)
        self.assertEqual(r['status'],'voice_enumeration_abstention')
        self.assertFalse(r['conditions']);explainer.assert_not_called()

    def test_missing_lane_reported_not_silently_dropped(self):
        ir=fixture();ir['sounding_events'][0]['source_note_ids']=['missing']
        p=plan(ir,{'start':q(0),'end':q(4)})
        self.assertEqual(p['skipped_sounds'],[{'event_ref':ir['sounding_events'][0]['sounding_event_id'],'reason':'missing_lane_identity'}])
