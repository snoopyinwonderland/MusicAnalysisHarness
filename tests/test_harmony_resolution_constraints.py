import unittest
from copy import deepcopy
from test_harmony_progression_polyphony import shared
from test_harmony_progression_multivoice import fixture
from musicanote_harness.harmony_progression_polyphony import analyze as exhaustive
from musicanote_harness.harmony_resolution_constraints import analyze,compatible_witness


class ConstraintTests(unittest.TestCase):
    def test_matches_exhaustive_positive(self):
        r,p,ir=shared();old=exhaustive(r,p,'none',ir);new=analyze(r,p,'none',ir)
        self.assertEqual(bool(old['assignments_with_any_direct_support']),new['queries'][0]['status']=='witness_exists')
        self.assertEqual(len(new['local_link_candidates']),16)
        self.assertEqual(len(new['queries'][0]['links']),2)
        self.assertFalse(new['queries'][0]['witness_is_preferred'])

    def test_matches_exhaustive_negative(self):
        r,p,ir=fixture(wrong=True,return_ir=True)
        for n in ir['note_events']:n['voice_id']='shared'
        old=exhaustive(r,p,'none',ir);new=analyze(r,p,'none',ir)
        self.assertFalse(old['assignments_with_any_direct_support'])
        self.assertEqual(new['queries'][0]['status'],'direct_identity_prerequisite_missing')

    def test_complete_target_but_wrong_motion_matches_exhaustive(self):
        r,p,ir=shared()
        s=ir['sounding_events'][6]
        s['pitch'].update(octave=5,midi_pitch=81,spelling='A5')
        # The fixture shares these canonical event objects with the path container.
        old=exhaustive(r,p,'none',ir);new=analyze(r,p,'none',ir)
        self.assertFalse(old['assignments_with_any_direct_support'])
        self.assertEqual(new['queries'][0]['status'],'no_compatible_witness')

    def test_global_enumeration_limit_not_required(self):
        r,p,ir=shared()
        self.assertEqual(exhaustive(r,p,'none',ir,1)['status'],'global_budget_abstention_no_pruning')
        self.assertEqual(analyze(r,p,'none',ir)['queries'][0]['status'],'witness_exists')

    def test_merge_conflict_not_independent_votes(self):
        a=compatible_witness({'leading':[['a','z']],'seventh':[['b','z']]})
        self.assertEqual(a['status'],'no_compatible_witness')

    def test_branch_conflict_rejected(self):
        self.assertEqual(compatible_witness({'one':[['a','b']],'two':[['a','c']]})['status'],'no_compatible_witness')

    def test_budget_not_negative_proof(self):
        self.assertEqual(compatible_witness({'one':[['a','b']],'two':[['c','d']]},1)['status'],'query_budget_abstention')

    def test_graph_limit_no_partial_answer(self):
        r,p,ir=shared();a=analyze(r,p,'none',ir,edge_budget=1)
        self.assertEqual(a['status'],'edge_budget_abstention');self.assertEqual(a['queries'],[])

    def test_missing_lane_abstains(self):
        r,p,ir=shared();ir['note_events'][0]['voice_id']=None
        self.assertEqual(analyze(r,p,'none',ir)['status'],'unlocated_sounds_abstention')

    def test_lane_identity_preserved(self):
        r,p,ir=fixture(return_ir=True);a=analyze(r,p,'none',ir)
        self.assertEqual(len(a['local_link_candidates']),4)

    def test_input_unchanged(self):
        r,p,ir=shared();saved=deepcopy((r,ir));analyze(r,p,'none',ir);self.assertEqual((r,ir),saved)


if __name__=='__main__':unittest.main()
