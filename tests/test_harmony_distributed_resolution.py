import unittest
from copy import deepcopy
from test_harmony_open_candidates import score
from test_harmony_progression_multivoice import fixture as old_fixture
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_joint import f
from musicanote_harness.harmony_progression_context import plan
from musicanote_harness.harmony_distributed_resolution import analyze, joint_paths
from musicanote_harness.harmony_candidate_relation_survey import local_query


def fixture(specs=None):
    # Sequential source members; held E resolves late to F, Bb resolves to A.
    specs = specs or [('C3', 0, 1, 'bass'), ('G4', 0, '1/2', 'fifth'),
                      ('E4', '1/2', 2, 'lead'), ('B-4', '1/2', 1, 'seventh'),
                      ('F3', 1, 3, 'bass'), ('F4', 2, 3, 'lead'),
                      ('A4', 1, 3, 'seventh'), ('C5', 2, 3, 'fifth')]
    ir = score(specs)
    template, _, _ = old_fixture(return_ir=True)
    r = {**template, 'events': ir['sounding_events'], 'assignments': [{'assignment_id': 'none', 'links': []}]}
    p = plan(r['events'], {'start': q(0), 'end': q(3)})
    r['plan'] = p
    r['edges'] = []
    for edge in p['intervals']:
        readings = deepcopy(template['edges'][0]['readings'])
        for reading in readings:
            reading['span'] = deepcopy(edge['span'])
            reading['event_states'] = {s['sounding_event_id']: 'member' if [s['pitch']['step'], s['pitch']['alter']] in reading['members']
                                      else 'nonmember_not_confirmed_nct' for s in r['events']
                                      if f(s['span']['start']) < f(edge['span']['end']) and f(s['span']['end']) > f(edge['span']['start'])}
        r['edges'].append({**edge, 'readings': readings})
    r['cells'] = [{'span': {'start': a, 'end': b}, 'event_refs': [s['sounding_event_id'] for s in r['events']
                   if f(s['span']['start']) < f(b) and f(s['span']['end']) > f(a)]} for a, b in zip(p['points'], p['points'][1:])]
    path = [{'edge': next(i for i, e in enumerate(r['edges']) if e['span'] == {'start': q(a), 'end': q(b)}), 'reading': reading}
            for a, b, reading in [(0, 1, 0), (1, 3, 1)]]
    return r, path, ir


def result(data, **kwargs):
    r, p, ir = data
    return analyze(r, p, 'none', ir, **kwargs)['temporal_queries'][0]


class DistributedTests(unittest.TestCase):
    def test_sequential_members_and_late_arrival(self):
        a = result(fixture())
        self.assertEqual(a['status'], 'temporal_resolution_possible')
        self.assertTrue(a['has_delayed_arrival'])
        self.assertFalse(a['function_confirmed'])
        self.assertFalse(a['witness_is_preferred'])

    def test_staggered_target_identity_without_onset_third(self):
        specs = [('C3',0,1,'b'), ('E4',0,1,'l'), ('G4',0,1,'g'), ('B-4',0,2,'s'),
                 ('F3',1,3,'b'), ('F4',1,3,'l'), ('C5',1,2,'g'), ('A4',2,3,'s')]
        data = fixture(specs); r,p,ir = data
        a = analyze(r,p,'none',ir)
        self.assertEqual(a['queries'][0]['status'], 'direct_identity_prerequisite_missing')
        self.assertEqual(a['temporal_queries'][0]['status'], 'temporal_resolution_possible')

    def test_same_pitch_reattacks_preserve_chain(self):
        specs = [('C3',0,1,'b'), ('E4',0,1,'l'), ('E4',1,2,'l'), ('G4',0,1,'g'), ('B-4',0,1,'s'),
                 ('F3',1,3,'b'), ('F4',2,3,'l'), ('C5',1,3,'g'), ('A4',1,3,'s')]
        a = result(fixture(specs))
        self.assertEqual(a['status'], 'temporal_resolution_possible')
        self.assertEqual(max(len(o['links']) for o in a['witness']),2)

    def test_unexplained_source_tone_prevents_wide_union(self):
        specs = [('C3',0,1,'b'), ('E4',0,1,'l'), ('G4',0,1,'g'), ('B-4',0,1,'s'), ('D4','1/2',1,'extra'),
                 ('F3',1,3,'b'), ('F4',1,3,'l'), ('C5',1,3,'g'), ('A4',1,3,'s')]
        a = result(fixture(specs))
        self.assertIn('source_nonmember_requires_separate_nct_evidence',a['reasons'])

    def test_new_foreign_target_note_not_excused_by_other_resolution(self):
        # A fresh E in an unrelated voice is not the carried resolving E.
        specs=[('C3',0,1,'b'),('G4',0,'1/2','g'),('E4','1/2',2,'l'),('B-4','1/2',1,'s'),
               ('F3',1,3,'b'),('F4',2,3,'l'),('A4',1,3,'s'),('C5',2,3,'g'),('E4','3/2',2,'unrelated')]
        self.assertEqual(result(fixture(specs))['status'],'no_joint_temporal_witness')

    def test_voice_rest_cannot_be_bridged(self):
        specs=[('C3',0,1,'b'),('E4',0,'3/2','l'),('G4',0,1,'g'),('B-4',0,1,'s'),
               ('F3',1,3,'b'),('F4',2,3,'l'),('A4',1,3,'s'),('C5',1,3,'g')]
        self.assertEqual(result(fixture(specs))['status'],'no_joint_temporal_witness')

    def test_whole_ensemble_silence_abstains(self):
        specs=[('C3',0,'1/2','b'),('E4',0,'1/2','l'),('G4',0,'1/2','g'),('B-4',0,'1/2','s'),
               ('F3',1,3,'b'),('F4',1,3,'l'),('A4',1,3,'s'),('C5',1,3,'g')]
        self.assertIn('silence_breaks_temporal_support',result(fixture(specs))['reasons'])

    def test_wrong_octave_motion_not_resolution(self):
        specs=[('C3',0,1,'b'),('E4',0,2,'l'),('G4',0,1,'g'),('B-4',0,1,'s'),
               ('F3',1,3,'b'),('F5',2,3,'l'),('A4',1,3,'s'),('C5',1,3,'g')]
        self.assertEqual(result(fixture(specs))['status'],'no_joint_temporal_witness')

    def test_path_budget_is_abstention(self):
        self.assertEqual(result(fixture(),path_budget=1)['status'],'path_budget_abstention')

    def test_blocker_preserved(self):
        data=fixture();r,p,ir=data
        r['edges'][p[0]['edge']]['readings'][0]['abstention_reasons']=['blocked']
        self.assertEqual(result(data)['status'],'blocked_context')

    def test_ir_mismatch_rejected(self):
        r,p,ir=fixture();ir=deepcopy(ir);ir['sounding_events'][0]['pitch']['midi_pitch']+=1
        with self.assertRaisesRegex(ValueError,'identity_mismatch'):analyze(r,p,'none',ir)

    def test_direct_answer_and_inputs_unchanged(self):
        r,p,ir=fixture();saved=deepcopy((r,ir))
        a=analyze(r,p,'none',ir)
        from musicanote_harness.harmony_resolution_constraints import analyze as direct
        self.assertEqual(a['queries'],direct(r,p,'none',ir)['queries'])
        self.assertEqual((r,ir),saved)

    def test_joint_chain_merge_conflict(self):
        def opt(edges):return {'links':edges,'carried_event_refs':[]}
        a=joint_paths({'one':[opt([['a','b'],['b','c']])],'two':[opt([['x','b']])]},set(),100)
        self.assertEqual(a['status'],'no_joint_temporal_witness')

    def test_survey_opt_in_preserves_candidate_refs(self):
        r,p,ir=fixture();pair={'source':p[0],'target':p[1],'family':'V7','target_quality':'M'}
        a=local_query(r,pair,ir,temporal=True)
        self.assertEqual(a['temporal_query']['status'],'temporal_resolution_possible')
        self.assertEqual(a['source_candidate_ref'],'0')

    def test_transposed_delayed_relation_same_rule(self):
        r,p,ir=old_fixture(return_ir=True,transpose=True,delayed=True)
        self.assertEqual(result((r,p,ir))['status'],'temporal_resolution_possible')

    def test_absent_member_not_invented(self):
        specs=[('C3',0,1,'b'),('E4',0,2,'l'),('B-4',0,1,'s'),
               ('F3',1,3,'b'),('F4',2,3,'l'),('A4',1,3,'s'),('C5',1,3,'g')]
        a=result(fixture(specs))
        self.assertEqual(a['status'],'temporal_identity_abstention')
        self.assertEqual(a['source_profile']['missing_members'],[['G',0]])

    def test_joint_budget_is_not_negative_proof(self):
        def opt(x,y):return {'links':[[x,y]],'carried_event_refs':[]}
        a=joint_paths({'one':[opt('a','b')],'two':[opt('c','d')]},set(),1)
        self.assertEqual(a['status'],'query_budget_abstention')

    def test_zero_timing_still_preserved_by_survey(self):
        r,p,ir=fixture()
        extra=deepcopy(ir['sounding_events'][0]);extra['sounding_event_id']='zero'
        extra['span']={'start':q('1/2'),'end':q('1/2')}
        ir['sounding_events'].append(extra)
        pair={'source':p[0],'target':p[1],'family':'V7','target_quality':'M'}
        a=local_query(r,pair,ir,temporal=True)
        self.assertEqual(a['status'],'nonpositive_sound_duration_unsupported')
        self.assertEqual(a['unsupported_event_refs'],['zero'])


if __name__=='__main__': unittest.main()
