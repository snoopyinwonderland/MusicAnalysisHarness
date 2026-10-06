import unittest
from copy import deepcopy
from test_harmony_progression_multivoice import fixture
from musicanote_harness.harmony_progression_polyphony import analyze


def shared():
    r,p,ir=fixture(return_ir=True)
    for n in ir['note_events']:n['voice_id']='shared'
    return r,p,ir


class PolyphonyTests(unittest.TestCase):
    def test_complete_four_note_partial_matchings(self):
        r,p,ir=shared();a=analyze(r,p,'none',ir)
        self.assertEqual(a['possible_combinations'],209)
        self.assertEqual(len(a['assignments']),209)
        self.assertTrue(a['assignments_with_any_direct_support'])
        self.assertLess(len(a['assignments_with_any_direct_support']),209)
        self.assertIsNone(a['selected_assignment'])
        self.assertFalse(a['counts_are_confidence'])

    def test_all_events_preserved_once_in_every_assignment(self):
        r,p,ir=shared();a=analyze(r,p,'none',ir)
        expected=sorted(s['sounding_event_id'] for s in r['events'])
        for row in a['assignments']:
            self.assertEqual(sorted(s for t in row['tracks'] for s in t),expected)

    def test_no_link_alternative_retained(self):
        r,p,ir=shared();a=analyze(r,p,'none',ir)
        empty=next(x for x in a['assignments'] if not x['links'])
        self.assertEqual(empty['resolution']['relations'][0]['status'],'shape_relation_only')

    def test_budget_abstains_without_best_subset(self):
        r,p,ir=shared();a=analyze(r,p,'none',ir,max_combinations=208)
        self.assertEqual(a['status'],'global_budget_abstention_no_pruning')
        self.assertEqual(a['assignments'],[])

    def test_unlocated_voice_abstains(self):
        r,p,ir=shared();ir['note_events'][0]['voice_id']=None
        self.assertEqual(analyze(r,p,'none',ir)['status'],'unlocated_sounds_no_partial_selection')

    def test_explicit_lanes_not_crossed(self):
        r,p,ir=fixture(return_ir=True);a=analyze(r,p,'none',ir)
        self.assertEqual(a['possible_combinations'],16)

    def test_inputs_unchanged(self):
        r,p,ir=shared();saved=deepcopy((r,ir));analyze(r,p,'none',ir)
        self.assertEqual((r,ir),saved)

    def test_invalid_budget_rejected(self):
        r,p,ir=shared()
        with self.assertRaises(ValueError):analyze(r,p,'none',ir,0)


if __name__=='__main__':unittest.main()
