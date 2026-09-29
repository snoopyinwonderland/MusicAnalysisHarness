import unittest
from test_harmony_joint import fixture
from musicanote_harness.harmony_ambiguity_context import inspect


class ContextTests(unittest.TestCase):
    def test_tie_not_selected_from_neighbor(self):
        ir=fixture([(58,0,1,'b'),(62,0,1,'v'),(65,1,2,'v')])
        r=inspect(ir,0,1)
        self.assertEqual(r['status'],'ambiguous');self.assertIsNone(r['selected_hypothesis'])
        self.assertIn('Bb:major',[c['label'] for c in r['hypotheses']])
        self.assertTrue(any(o['region']=='after' and o['pitch']==65 for o in r['context_observations']))

    def test_unambiguous_pitch_set_not_claimed_verified(self):
        r=inspect(fixture([(60,0,1,'b'),(64,0,1,'v'),(67,0,1,'w')]),0,1)
        self.assertEqual(r['status'],'single_local_candidate')
        self.assertIsNone(r['selected_hypothesis'])

    def test_polyphonic_voice_link_abstains(self):
        r=inspect(fixture([(58,0,1,'b'),(62,0,1,'v'),(65,1,2,'v'),(69,1,2,'v')]),0,1)
        self.assertEqual(r['boundary_voice_links'],[])

    def test_outside_context_and_labels_do_not_change_report(self):
        specs=[(58,0,1,'b'),(62,0,1,'v')]
        a=inspect(fixture(specs),0,1)
        b=inspect({**fixture(specs+[(65,8,9,'v')]),'annotations':['I']},0,1)
        self.assertEqual(a,b)

    def test_rest_and_bad_span(self):
        self.assertEqual(inspect(fixture([]),0,1)['status'],'insufficient_evidence')
        with self.assertRaises(ValueError):inspect(fixture([]),1,0)
