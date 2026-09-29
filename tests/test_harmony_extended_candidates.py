from copy import deepcopy
from fractions import Fraction as F
import unittest
from test_harmony_open_candidates import score
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_extended_candidates import propose
from musicanote_harness.harmony_open_candidates import window


def fixture(pitches):return score([(p,0,1,str(i)) for i,p in enumerate(pitches)])
def run(ir,end=1,context=1):return propose(ir,{'start':q(0),'end':q(end)},{'start':q(0),'end':q(context)})
def selected(r,roles,root=('C',0)):
    return next(c for c in r['extended_candidates'] if c['root_coordinate']==list(root) and set(c['added_roles'])==set(roles))
CORE=['C3','E3','G3','B-3']


class ExtendedCandidatesTests(unittest.TestCase):
    def test_five_added_classes(self):
        for p,role in [('D-4','minor_ninth'),('D4','major_ninth'),('F4','fourth_or_eleventh'),
                       ('A-4','minor_sixth_or_thirteenth'),('A4','major_sixth_or_thirteenth')]:
            c=selected(run(fixture(CORE+[p])),[role])
            self.assertTrue(c['pooled_complete']);self.assertTrue(c['simultaneous_complete']);self.assertIsNone(c['function'])

    def test_base_candidates_and_input_unchanged(self):
        ir=fixture(CORE+['D4']);before=deepcopy(ir);r=run(ir)
        self.assertEqual(ir,before);self.assertEqual(r['base_window'],window(ir,r['span']))
        ir['annotations']=['wrong'];ir['localkey']='F#';self.assertEqual(run(ir),r)

    def test_rootless_competes_with_half_diminished(self):
        r=run(fixture(['E3','G3','B-3','D4']));c=selected(r,['major_ninth'])
        self.assertFalse(c['root_observed']);self.assertEqual(c['missing_core_roles'],['root'])
        self.assertTrue(any(c['root']==4 and c['label'].endswith(':half-diminished7') for c in r['base_window']['candidates']))

    def test_missing_fifth(self):
        c=selected(run(fixture(['C3','E3','B-3','D4'])),['major_ninth'])
        self.assertEqual(c['missing_core_roles'],['fifth'])

    def test_fourth_without_third(self):
        c=selected(run(fixture(['C3','G3','B-3','F4'])),['fourth_or_eleventh'])
        self.assertEqual(c['missing_core_roles'],['third']);self.assertFalse(c['pooled_complete'])

    def test_no_third_or_root_no_candidate(self):
        r=run(fixture(['G3','B-3','D4']))
        self.assertFalse(any(c['root_coordinate']==['C',0] for c in r['extended_candidates']))

    def test_add9_triad_not_forced_dominant9(self):
        r=run(fixture(['C3','E3','G3','D4']))
        self.assertFalse(any(c['root_coordinate']==['C',0] for c in r['extended_candidates']))

    def test_enharmonic_not_rewritten_as_minor_ninth(self):
        r=run(fixture(CORE+['C#4']))
        self.assertFalse(any(c['root_coordinate']==['C',0] and 'minor_ninth' in c['added_roles'] for c in r['extended_candidates']))

    def test_thirteenth_does_not_invent_ninth_or_eleventh(self):
        c=selected(run(fixture(CORE+['A4'])),['major_sixth_or_thirteenth'])
        self.assertEqual(len(c['member_spellings']),5);self.assertFalse(c['missing_spellings'])

    def test_subsets_preserve_ornament_alternative(self):
        r=run(fixture(CORE+['D4','A4']))
        c=selected(r,['major_ninth']);self.assertIn(['A',0],c['extra_spellings'])
        self.assertFalse(selected(r,['major_ninth','major_sixth_or_thirteenth'])['extra_spellings'])

    def test_conflicting_extensions_not_combined(self):
        r=run(fixture(CORE+['D-4','D4']))
        selected(r,['minor_ninth']);selected(r,['major_ninth'])
        self.assertFalse(any({'minor_ninth','major_ninth'}<=set(c['added_roles']) for c in r['extended_candidates']))

    def test_actual_bass(self):
        c=selected(run(fixture(['E2','C3','G3','B-3','D4'])),['major_ninth'])
        self.assertEqual(c['cells'][0]['bass_member_roles'],['third']);self.assertIsNone(c['inversion'])

    def test_arpeggio_pool_not_simultaneous(self):
        ir=score([(p,i,i+1,'v') for i,p in enumerate(CORE+['D4'])])
        c=selected(run(ir,5,5),['major_ninth']);self.assertTrue(c['pooled_complete']);self.assertFalse(c['simultaneous_complete'])

    def test_descent_not_nct_verdict(self):
        ir=score([(p,0,3,str(i)) for i,p in enumerate(CORE)]+[('D4',0,1,'lead'),('C4',1,2,'lead'),('B-3',2,3,'lead')])
        r=run(ir,1,3);c=selected(r,['major_ninth']);ref=next(x for x in r['references'] if x['reference_id']==c['reference_id'])
        p=next(p for p in ref['context_evidence']['paths'] if p['role']=='major_ninth')
        self.assertTrue(p['root_then_seventh_geometry']);self.assertIsNone(p['nct_label'])

    def test_simple_second_not_claimed_actual_ninth(self):
        r=run(fixture(['C4','E4','G4','B-4','D4']));c=selected(r,['major_ninth'])
        ref=next(x for x in r['references'] if x['reference_id']==c['reference_id'])
        p=next(p for p in ref['context_evidence']['paths'] if p['role']=='major_ninth')
        self.assertEqual(p['simultaneous_root_intervals'][0]['interval']['generic'],2)

    def test_transpose(self):
        c=selected(run(fixture(['D3','F#3','A3','C4','E4'])),['major_ninth'],('D',0))
        self.assertTrue(c['pooled_complete'])

    def test_scaling(self):
        a=run(fixture(CORE+['D4']))
        ir=score([(p,0,F(1,2),str(i)) for i,p in enumerate(CORE+['D4'])])
        b=run(ir,F(1,2),F(1,2))
        self.assertEqual([(c['root_coordinate'],c['added_roles']) for c in a['extended_candidates']],
                         [(c['root_coordinate'],c['added_roles']) for c in b['extended_candidates']])

    def test_unknown_meter_blocks_context_only(self):
        ir=fixture(CORE+['D4']);ir['measures'][0]['time_signature']['beats']=None;r=run(ir)
        selected(r,['major_ninth']);self.assertTrue(all(x['context_evidence'] is None for x in r['references']))

    def test_grace_abstains(self):
        ir=fixture(CORE+['D4']);ir['note_events'][0]['grace']={'is_grace':True};ir['note_events'][0]['global_onset_quarter']=q(0)
        self.assertEqual(run(ir)['extended_candidates'],[])

    def test_unsupported_spelling_abstains(self):
        ir=fixture(CORE+['D4']);ir['sounding_events'][0]['pitch']['alter']=q(F(1,2))
        self.assertEqual(run(ir)['extended_candidates'],[])

    def test_context_bounds(self):
        with self.assertRaises(ValueError):run(fixture(CORE+['D4']),2,1)

    def test_incomplete_candidate_has_actual_simultaneous_support(self):
        c=selected(run(fixture(['C3','E3','B-3','D4'])),['major_ninth'])
        self.assertFalse(c['simultaneous_complete']);self.assertTrue(c['proposal_support_simultaneous'])

    def test_pooled_replacement_not_simultaneous_support(self):
        ir=score([('C3',0,1,'a'),('B-3',1,2,'a'),('F4',2,3,'a')])
        c=selected(run(ir,3,3),['fourth_or_eleventh'])
        self.assertFalse(c['proposal_support_simultaneous']);self.assertEqual(c['identity_gate'],'root_seventh_replacement_shape')
