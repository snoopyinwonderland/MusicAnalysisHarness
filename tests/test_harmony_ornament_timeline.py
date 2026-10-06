from copy import deepcopy
import unittest
from test_harmony_boundary_figures import pair_fixture, C, F
from test_harmony_segment_contrast import full_assignment
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_boundary_figures import augment as figures
from musicanote_harness.harmony_ornament_timeline import compare, augment

def fixture(suspension=False):
    return figures(pair_fixture([('F4',0,2),('E4',2,3)] if suspension else [('C4',0,1),('D4',1,2),('E4',2,3)],F if suspension else C,C))

class OrnamentTimelineTests(unittest.TestCase):
    def test_passing_is_conditional_not_confirmed(self):
        r=fixture(); c=compare(r,0,0,0,0,full_assignment(r))
        self.assertEqual(c['split']['note_time']['conditional_nonmember'],q(1))
        self.assertFalse(c['split']['confirmed_nct']);self.assertIsNone(c['preferred'])
    def test_suspension_withheld_even_without_assessment(self):
        r=fixture(True);c=compare(r,0,0,0,0,full_assignment(r))
        self.assertEqual(c['split']['note_time']['withheld_nonmember'],q(1))
        self.assertEqual(c['split']['note_time']['conditional_nonmember'],q(0))
        self.assertEqual(c['split']['total_note_time'],q(3))
    def test_unlinked_has_no_invented_explanation(self):
        r=fixture();a=next(a['assignment_id'] for a in r['assignments'] if not a['links'])
        self.assertEqual(compare(r,0,0,0,0,a)['split']['note_time']['unexplained_nonmember'],q(1))
    def test_source_fields_preserved(self):
        r=fixture();saved=deepcopy(r);out=augment(r);out.pop('ornament_timeline_version')
        for b in out['boundaries']:b.pop('ornament_timeline')
        self.assertEqual(out,r);self.assertEqual(r,saved)
    def test_sustain_only_withheld_after_boundary(self):
        r=fixture(True);c=compare(r,0,0,0,0,full_assignment(r))
        self.assertEqual([x['state'] for x in c['split']['cells']],['member','withheld_nonmember','member'])
    def test_blocked_reading_cannot_use_stale_pattern(self):
        r=fixture();r['boundaries'][0]['right']['readings'][0]['condition']['abstention_reasons']=['blocked']
        c=compare(r,0,0,0,0,full_assignment(r));self.assertFalse(c['active_pattern_refs'])
    def test_independent_local_explanation_retained(self):
        r=fixture(True);aid=full_assignment(r);b=r['boundaries'][0]
        sid=b['boundary_figures']['patterns'][0]['affected_event_ref']
        a=next(a for a in b['right']['readings'][0]['condition']['assignments'] if a['assignment_ref']==aid)
        a['conditionally_explained_nonmember_refs']=[sid]
        c=compare(r,0,0,0,0,aid)
        self.assertEqual(c['split']['note_time']['conditional_nonmember'],q(1))
        self.assertTrue(any(x['withheld_pattern_refs'] and x['local_conditional_support'] for x in c['split']['items']))
    def test_same_cell_two_voices_not_double_wall_time(self):
        r=figures(pair_fixture([('C4',0,1),('D4',1,2),('E4',2,3),('G3',0,3)],C,C))
        c=compare(r,0,0,0,0,full_assignment(r))
        self.assertEqual(c['split']['total_note_time'],q(6))
        self.assertEqual(c['split']['wall_time']['conditional_nonmember'],q(1))

if __name__=='__main__':unittest.main()
