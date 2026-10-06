import unittest
from copy import deepcopy
from test_harmony_progression_multivoice import fixture
from musicanote_harness.harmony_candidate_relation_survey import plan,run
from musicanote_harness.formal_ir import q


class SurveyTests(unittest.TestCase):
    def test_all_pairs_not_first_reading(self):
        r,p,ir=fixture(return_ir=True)
        # Every edge has C7 then F: the first-reading path alone has no C7 -> F.
        a=run(r,ir)
        self.assertEqual(len(a['plan']['pairs']),1)
        self.assertEqual(a['plan']['pairs'][0]['target']['reading'],1)
        self.assertEqual(a['summary'],{'witness_exists':1})

    def test_duplicate_origins_preserved(self):
        r,p,ir=fixture(return_ir=True)
        target=r['edges'][p[1]['edge']]['readings'];other=deepcopy(target[1]);other['candidate_ref']='other-origin';target.append(other)
        a=run(r,ir);self.assertEqual(len(a['results']),2)
        self.assertEqual({x['target_candidate_ref'] for x in a['results']},{'1','other-origin'})

    def test_blocked_pair_retained(self):
        r,p,ir=fixture(return_ir=True);r['edges'][p[0]['edge']]['readings'][0]['abstention_reasons']=['blocked']
        self.assertEqual(run(r,ir)['summary'],{'blocked_context':1})

    def test_budget_does_not_pick_subset(self):
        r,p,ir=fixture(return_ir=True);r['edges'][p[1]['edge']]['readings'].append(deepcopy(r['edges'][p[1]['edge']]['readings'][1]))
        a=run(r,ir,1);self.assertEqual(a['status'],'pair_budget_abstention_no_pruning');self.assertEqual(a['results'],[])

    def test_display_labels_do_not_change_plan(self):
        r,p,ir=fixture(return_ir=True);before=plan(r)
        for e in r['edges']:
            for reading in e['readings']:reading['display_label']='not a harmonic label'
        self.assertEqual(plan(r),before)

    def test_input_preserved(self):
        r,p,ir=fixture(return_ir=True);saved=deepcopy((r,ir));run(r,ir);self.assertEqual((r,ir),saved)

    def test_wrong_ir_rejected(self):
        r,p,ir=fixture(return_ir=True);ir=deepcopy(ir);ir['sounding_events'][0]['pitch']['midi_pitch']+=1
        with self.assertRaises(ValueError):run(r,ir)

    def test_zero_timing_preserved_as_unsupported(self):
        r,p,ir=fixture(return_ir=True)
        s=deepcopy(ir['sounding_events'][0]);s['sounding_event_id']='zero'
        s['span']={'start':q('1/2'),'end':q('1/2')}
        ir['sounding_events'].append(s);r['events']=list(ir['sounding_events'])
        a=run(r,ir)
        self.assertEqual(a['summary'],{'nonpositive_sound_duration_unsupported':1})
        self.assertEqual(a['results'][0]['unsupported_event_refs'],['zero'])


if __name__=='__main__':unittest.main()
