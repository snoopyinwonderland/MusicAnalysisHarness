from copy import deepcopy
import unittest
from test_harmony_open_candidates import score
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_augmented_candidates import propose
from musicanote_harness.harmony_open_candidates import window


def fixture(extra=()):
    return score([(p, 0, 1, str(i)) for i, p in enumerate(('A-3', 'C4', 'F#4') + tuple(extra))])


def run(ir, end=1, context=1):
    return propose(ir, {'start': q(0), 'end': q(end)}, {'start': q(0), 'end': q(context)})


def cmajor(result, family):
    return next(c for c in result['augmented_sixth_candidates']
                if c['tonic_coordinate'] == ['C', 0] and c['family'] == family)


class AugmentedCandidateTests(unittest.TestCase):
    def test_all_shapes(self):
        for family, extra in [('It', ()), ('Ger', ('E-4',)), ('Fr', ('D4',)), ('Ger43', ('D#4',))]:
            with self.subTest(family=family):
                c = cmajor(run(fixture(extra)), family)
                self.assertTrue(c['pooled_complete']); self.assertTrue(c['simultaneous_complete'])
                self.assertFalse(c['extra_spellings']); self.assertIsNone(c['mode']); self.assertIsNone(c['root'])

    def test_no_resolution_required(self):
        c = cmajor(run(fixture()), 'It')
        self.assertEqual(c['context_evidence']['joint_geometry'], [])
        self.assertIsNone(c['function'])

    def test_actual_resolution(self):
        ir = score([('A-3',0,1,'a'),('G3',1,2,'a'),('F#4',0,1,'b'),('G4',1,2,'b'),('C4',0,1,'c')])
        self.assertEqual(len(cmajor(run(ir, context=2),'It')['context_evidence']['joint_geometry']),1)

    def test_dominant_respelling_not_german(self):
        ir = score([(p,0,1,str(i)) for i,p in enumerate(('A-3','C4','E-4','G-4'))])
        r = run(ir)
        self.assertFalse(any(c['tonic_coordinate']==['C',0] for c in r['augmented_sixth_candidates']))
        self.assertTrue(any(c['root']==8 and c['label'].endswith(':dominant7') for c in r['base_window']['candidates']))

    def test_enharmonic_pc_competitor_retained(self):
        r=run(fixture(('E-4',)))
        self.assertTrue(any(c['root']==8 and c['label'].endswith(':dominant7') for c in r['base_window']['candidates']))
        self.assertTrue(cmajor(r,'Ger')['pooled_complete'])

    def test_arpeggio_not_simultaneous(self):
        ir=score([('A-3',0,1,'v'),('C4',1,2,'v'),('F#4',2,3,'v')])
        c=cmajor(run(ir,3,3),'It')
        self.assertTrue(c['pooled_complete']);self.assertFalse(c['simultaneous_complete'])

    def test_missing_members_retained(self):
        c=cmajor(run(fixture()),'Ger');self.assertEqual(c['missing_spellings'],[['E',-1]])

    def test_actual_bass_not_assumed_flat6(self):
        ir=score([('C3',0,1,'a'),('A-3',0,1,'b'),('F#4',0,1,'c')])
        self.assertEqual(cmajor(run(ir),'It')['cells'][0]['bass_member_roles'],['tonic'])

    def test_residual_not_deleted(self):
        c=cmajor(run(fixture(('B4',))),'It');self.assertEqual(c['extra_spellings'],[['B',0]])
        self.assertIn('nonmember_not_confirmed_nct',c['event_states'].values())

    def test_base_unchanged_annotation_blind(self):
        ir=fixture();saved=deepcopy(ir);r=run(ir)
        self.assertEqual(ir,saved);self.assertEqual(r['base_window'],window(ir,r['span']))
        ir['annotations']=['Ger6'];ir['localkey']='wrong';self.assertEqual(run(ir),r)

    def test_transpose(self):
        ir=score([(p,0,1,str(i)) for i,p in enumerate(('B-3','D4','G#4'))])
        c=next(c for c in run(ir)['augmented_sixth_candidates'] if c['family']=='It' and c['tonic_coordinate']==['D',0])
        self.assertTrue(c['pooled_complete'])

    def test_barrier_blocks_context_not_shape(self):
        ir=fixture();ir['measures'][0]['time_signature']['beats']=None
        c=cmajor(run(ir),'It');self.assertIsNone(c['context_evidence']);self.assertTrue(c['abstention_reasons'])

    def test_unsupported_spelling_abstains(self):
        ir=fixture();ir['sounding_events'][0]['pitch']['alter']=q(0.5)
        self.assertEqual(run(ir)['augmented_sixth_candidates'],[])

    def test_context_bounds(self):
        with self.assertRaises(ValueError):run(fixture(),2,1)
