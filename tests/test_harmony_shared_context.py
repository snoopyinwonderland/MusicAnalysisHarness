from copy import deepcopy
import unittest
from test_harmony_boundary_figures import pair_fixture, C, F, G
from test_harmony_segment_contrast import full_assignment
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_shared_context import augment, compare, catalog

def fixture(notes=None,left=C,right=C,cut=1,end=3):
    return pair_fixture(notes or [('C4',0,1),('D4',1,2),('E4',2,3)],left,right,cut=cut,end=end)

class SharedContextTests(unittest.TestCase):
    def test_same_chord_cut_does_not_lose_passing(self):
        r=fixture();c=compare(r,0,0,0,0,full_assignment(r))
        self.assertTrue(c['same_harmony_invariant_passed'])
        self.assertEqual(c['hold']['note_time']['conditional_nonmember'],q(1))
        self.assertEqual(c['hold']['cells'],c['split']['cells'])
    def test_cut_inside_middle_sound(self):
        r=fixture(cut=1.5);c=compare(r,0,0,0,0,full_assignment(r))
        self.assertTrue(c['same_harmony_invariant_passed'])
        self.assertEqual(c['split']['note_time']['conditional_nonmember'],q(1))
    def test_geometry_wholly_on_one_side_retained(self):
        r=fixture([('C4',0,1),('D4',1,2),('E4',2,3),('G4',3,4)],cut=3,end=4)
        c=compare(r,0,0,0,0,full_assignment(r));self.assertEqual(c['split']['note_time']['conditional_nonmember'],q(1))
    def test_no_link_symmetric_unexplained(self):
        r=fixture();aid=next(a['assignment_id'] for a in r['assignments'] if not a['links'])
        c=compare(r,0,0,0,0,aid);self.assertTrue(c['same_harmony_invariant_passed'])
        self.assertEqual(c['hold']['note_time']['unexplained_nonmember'],q(1))
    def test_neighbor_symmetric(self):
        r=fixture([('C4',0,1),('D4',1,2),('C4',2,3)])
        self.assertTrue(compare(r,0,0,0,0,full_assignment(r))['same_harmony_invariant_passed'])
    def test_changed_membership_can_remove_geometry(self):
        r=fixture(right=G);c=compare(r,0,0,0,0,full_assignment(r))
        self.assertFalse(c['same_harmony_invariant_applicable'])
        self.assertEqual(c['hold']['note_time']['conditional_nonmember'],q(1))
        self.assertEqual(c['split']['note_time']['conditional_nonmember'],q(0))
    def test_suspension_kept_withheld_on_split(self):
        r=fixture([('F4',0,2),('E4',2,3)],F,C)
        c=compare(r,0,0,0,0,full_assignment(r));self.assertEqual(c['split']['note_time']['withheld_nonmember'],q(1))
        self.assertEqual(c['hold']['note_time']['withheld_nonmember'],q(0))
    def test_anticipation_held_same_grammar(self):
        r=fixture([('F4',0,2)],C,F,end=2)
        c=compare(r,0,0,0,0,full_assignment(r));self.assertEqual(c['split']['note_time']['conditional_nonmember'],q(1))
    def test_legacy_local_explanation_not_leaked(self):
        r=fixture();aid=next(a['assignment_id'] for a in r['assignments'] if not a['links'])
        sid=r['events'][1]['sounding_event_id']
        for a in r['hold_readings'][0]['condition']['assignments']:a['conditionally_explained_nonmember_refs']=[sid]
        c=compare(r,0,0,0,0,aid);self.assertEqual(c['hold']['note_time']['conditional_nonmember'],q(0))
    def test_candidate_blocker_respected(self):
        r=fixture();r['boundaries'][0]['right']['readings'][0]['condition']['abstention_reasons']=['blocked']
        c=compare(r,0,0,0,0,full_assignment(r));self.assertFalse(c['same_harmony_invariant_applicable'])
        self.assertEqual(c['split']['note_time']['conditional_nonmember'],q(0))
    def test_no_external_endpoint_invented(self):
        r=fixture();r['events'][0]['span']['start']=q(-1)
        self.assertFalse(catalog(r,0)['patterns'])
    def test_invalid_track_partition_rejected(self):
        r=fixture();r['assignments'][0]['tracks']=[]
        with self.assertRaises(ValueError):catalog(r,0)
    def test_original_json_unchanged(self):
        r=fixture();saved=deepcopy(r);out=augment(r);out.pop('shared_context_version')
        for b in out['boundaries']:b.pop('shared_context')
        self.assertEqual(r,saved);self.assertEqual(out,r)
    def test_title_does_not_affect_rules(self):
        r=fixture();before=catalog(r,0);r['title']='other work';self.assertEqual(before,catalog(r,0))

if __name__=='__main__':unittest.main()
