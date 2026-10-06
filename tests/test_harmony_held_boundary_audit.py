from copy import deepcopy
import unittest
from test_harmony_boundary_figures import pair_fixture,C,F
from test_harmony_segment_contrast import fixture
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_continuous_survey import plan as survey_plan,analyze
from musicanote_harness.harmony_segment_contrast import build
from musicanote_harness.harmony_held_boundary_audit import plan,invalidate_condition
from musicanote_harness.harmony_boundary_figures import observe


def held():
    r=pair_fixture([('F4',0,2),('E4',2,3)],F,C)
    extra=deepcopy(r['events'][0]);extra.update(sounding_event_id='other_voice',span={'start':q(1),'end':q(2)})
    r['events'].append(extra);r['boundaries']=[]
    return r


class HeldBoundaryAuditTests(unittest.TestCase):
    def test_other_voice_attack_inside_held_sound_is_added(self):
        r=held();old=deepcopy(r);p=plan(r)
        self.assertEqual(r,old);self.assertEqual(len(p['cuts']),1)
        self.assertEqual(p['cuts'][0]['boundary'],q(1));self.assertFalse(p['cuts'][0]['already_tested'])
        self.assertEqual(p['cuts'][0]['attack_event_refs'],['other_voice'])

    def test_duplicate_attacks_one_cut(self):
        r=held();s=deepcopy(r['events'][-1]);s['sounding_event_id']='other2';r['events'].append(s)
        self.assertEqual(len(plan(r)['cuts']),1)
        self.assertEqual(len(plan(r)['cuts'][0]['attack_event_refs']),2)

    def test_existing_boundary_not_added_twice(self):
        r=held();r['boundaries']=[{'boundary':q(1)}]
        self.assertTrue(plan(r)['cuts'][0]['already_tested'])

    def test_reattack_or_release_not_a_held_crossing(self):
        r=held();r['events'][-1]['span']['start']=q(2)
        self.assertFalse(plan(r)['cuts'])

    def test_partial_sound_outside_observation_not_silently_completed(self):
        r=held();r['events'][0]['span']['start']=q(-1)
        self.assertFalse(plan(r)['cuts'])

    def test_unready_remains_unready(self):
        self.assertEqual(plan({'status':'baseline_abstention'})['cuts'],[])

    def test_planning_does_not_use_candidate_labels_or_pitch(self):
        r=held();expected=plan(r)
        for s in r['events']:s.pop('pitch',None)
        self.assertEqual(plan(r),expected)

    def test_explicit_default_cuts_equal_old_contract_except_selection_tag(self):
        ir=fixture();p=survey_plan(ir,{'start':q(0),'end':q(3)})['samples'][0];b=analyze(ir,p)
        old=build(ir,b);new=build(ir,b,boundary_offsets=p['attack_group_onsets'][1:])
        new.pop('boundary_selection');self.assertEqual(old,new)

    def test_non_observed_duplicate_and_external_cuts_rejected(self):
        ir=fixture();p=survey_plan(ir,{'start':q(0),'end':q(3)})['samples'][0];b=analyze(ir,p)
        for cuts in ([q(0)],[q(1),q(1)],[q(100)],[q('1/3')]):
            with self.assertRaises(ValueError):build(ir,b,boundary_offsets=cuts)

    def test_candidate_abstention_removes_only_its_support(self):
        r=pair_fixture([('F4',0,2),('E4',2,3)],F,C);before=deepcopy(r)
        self.assertTrue(observe(r,0)['patterns'])
        for side in ('left','right'):
            mutated=invalidate_condition(r,0,side,0,'counterfactual_untrusted')
            self.assertFalse(observe(mutated,0)['patterns'])
        self.assertEqual(r,before)
