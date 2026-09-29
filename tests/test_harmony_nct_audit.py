import unittest
from fractions import Fraction as F
from test_harmony_joint import fixture
from musicanote_harness.harmony_nct_audit import audit


class NctAuditTests(unittest.TestCase):
    def test_contiguous_passing_kept(self):
        r=audit(fixture([(48,0,3,'b'),(67,0,3,'t'),(60,0,1,'v'),(62,1,F(3,2),'v'),(64,F(3,2),3,'v')]),0,3)
        c=next(c for c in r['modes']['conservative'] if c['label']=='C:major')
        self.assertEqual(len(c['nct']),1)
        self.assertTrue(all(not c['nct'] for c in r['modes']['no_discount']))

    def test_overlapping_sequence_discount_rejected(self):
        r=audit(fixture([(48,0,3,'b'),(67,0,3,'t'),(60,0,F(5,4),'v'),(62,1,F(3,2),'v'),(64,F(3,2),3,'v')]),0,3)
        self.assertTrue(any('not_contiguous' in h['reasons'] for h in r['discount_checks']))

    def test_sustained_seventh_not_removed(self):
        r=audit(fixture([(p,0,4,str(i)) for i,p in enumerate([55,59,62,65])]),0,4)
        for mode in r['modes'].values():self.assertEqual(mode[0]['label'],'G:dominant7')

    def test_external_context_flagged(self):
        r=audit(fixture([(48,0,3,'b'),(67,0,3,'t'),(60,0,1,'v'),(62,1,F(3,2),'v'),(64,F(3,2),3,'v')]),1,2)
        self.assertTrue(any('outside_candidate_span' in h['reasons'] for h in r['discount_checks']))

    def test_annotations_ignored(self):
        ir=fixture([(60,0,2,'v'),(64,0,2,'w'),(67,0,2,'z')])
        self.assertEqual(audit(ir,0,2),audit({**ir,'annotations':['V']},0,2))

    def test_incomplete_triad_tie_is_exposed(self):
        r=audit(fixture([(58,0,1,'b'),(62,0,1,'v')]),0,1)
        tied=r['ambiguity']['legacy']['tied_best']
        labels={c['label'] for c in tied}
        self.assertTrue({'Bb:major','Bb:augmented'}<=labels)
        self.assertTrue(all(c['missing_pitch_classes'] for c in tied))
