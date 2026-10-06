import unittest
from copy import deepcopy
from unittest.mock import patch
from test_harmony_progression_context import make,path
from test_harmony_progression_context import provider
from test_harmony_shared_context import fixture
from musicanote_harness.harmony_progression_context import build
from musicanote_harness.harmony_progression_bass import cell_role,analyze
from musicanote_harness.harmony_progression_evidence import lowest


def role(pitch,members=None,root=('C',0),blockers=()):
    r,_=make([(pitch,0,3)]); events=r['events']
    reading={'root_spelling':list(root) if root else None,'root_provenance':'fixture',
             'members':members or [['C',0],['E',0],['G',0]],'abstention_reasons':list(blockers)}
    return cell_role(reading,lowest(events),{s['sounding_event_id']:s for s in events})


class BassTests(unittest.TestCase):
    def test_provider_alternative_root_preserved_not_label(self):
        def rooted(ir,span,context):
            c=provider(ir,span,context)
            c['candidates'][0]['spelling_alternatives'][0]['root_spelling']=['C',0]
            return c
        with patch('musicanote_harness.harmony_progression_context.propose',side_effect=rooted), \
             patch('musicanote_harness.harmony_progression_context.label',return_value='misleading-label'):
            r=build({},fixture())
        self.assertEqual(r['edges'][0]['readings'][0]['root_spelling'],['C',0])
        self.assertIsNone(r['edges'][0]['readings'][1]['root_spelling'])

    def test_triad_inversions(self):
        for p,i in [('C3',0),('E3',1),('G3',2)]:
            self.assertEqual(role(p)['inversion_candidate'],i)
            self.assertFalse(role(p)['inversion_confirmed'])

    def test_seventh_third_inversion(self):
        self.assertEqual(role('B3',[['C',0],['E',0],['G',0],['B',0]])['inversion_candidate'],3)

    def test_augmented_sixth_root_not_invented(self):
        self.assertEqual(role('C3',root=None)['status'],'root_unavailable')

    def test_extended_degree_not_ordinary_inversion(self):
        self.assertIsNone(role('D3',[['C',0],['E',0],['G',0],['B',0],['D',0]])['inversion_candidate'])

    def test_nonmember_not_automatically_pedal(self):
        self.assertEqual(role('D3')['status'],'nonmember_bass_role_unresolved')

    def test_blocked_candidate_not_promoted(self):
        self.assertEqual(role('E3',blockers=['unsupported'])['status'],'candidate_blocked')

    def test_enharmonic_bass_not_member(self):
        self.assertEqual(role('F-3')['status'],'nonmember_bass_role_unresolved')

    def test_legacy_root_unknown(self):
        r,aid=make();a=analyze(r,path(r,[(0,3,0)]),aid)
        self.assertEqual(a['bass_roles'][0]['status'],'root_unavailable')

    def test_same_chord_no_pedal(self):
        r,aid=make([('C3',0,3)])
        self.assertEqual(analyze(r,path(r,[(0,1,0)]),aid)['sustained_bass_candidates'],[])

    def test_preserves_input(self):
        r,aid=make();saved=deepcopy(r);analyze(r,path(r,[(0,3,0)]),aid)
        self.assertEqual(saved,r)

    def test_sustained_member_nonmember_member_shape(self):
        r,aid=make([('C3',0,3),('C4',0,1),('D4',1,2),('E4',2,3)])
        a=analyze(r,path(r,[(0,1,0),(1,2,2),(2,3,0)]),aid)
        self.assertEqual(len(a['sustained_bass_candidates']),1)
        pedal=a['sustained_bass_candidates'][0]
        self.assertEqual(pedal['status'],'anchored_sustained_bass_shape')
        self.assertFalse(pedal['pedal_confirmed'])

    def test_no_return_anchor_stays_unresolved(self):
        r,aid=make([('C3',0,3),('C4',0,1),('D4',1,2),('E4',2,3)])
        a=analyze(r,path(r,[(0,1,0),(1,3,2)]),aid)
        self.assertEqual(a['sustained_bass_candidates'][0]['status'],'sustained_bass_role_unresolved')


if __name__=='__main__':unittest.main()
