import unittest
from fractions import Fraction as F
from test_harmony_joint import fixture
from musicanote_harness.harmony_joint import prepare, analyze_joint
from musicanote_harness.harmony_boundary_gate import gate, analyze

C={'label':'C:major','root':0,'pcs':[0,4,7]}
G={'label':'G:dominant7','root':7,'pcs':[7,11,2,5]}


class GateTests(unittest.TestCase):
    def test_complete_new_chord_discount(self):
        rows,_=prepare(fixture([(p,1,F(3,2),str(i)) for i,p in enumerate([55,59,62,65])]))
        r=gate(rows,F(1),F(3,2),F(1),C,G)
        self.assertTrue(r['eligible']);self.assertEqual(r['charge'],.075)
        self.assertEqual(len(r['evidence_refs']),4)

    def test_unknown_voice_and_brief_attack_abstain(self):
        for voice,end in [(None,F(3,2)),('v',F(9,8))]:
            rows,_=prepare(fixture([(p,1,end,voice) for p in [55,59,62,65]]))
            self.assertFalse(gate(rows,F(1),F(3,2),F(1),C,G)['eligible'])

    def test_same_chord_and_initial_no_discount(self):
        rows,_=prepare(fixture([(p,0,1,str(i)) for i,p in enumerate([48,52,55])]))
        for prev in (None,C):self.assertFalse(gate(rows,F(0),F(1),F(1),prev,C)['eligible'])

    def test_arpeggio_and_neighbor_not_split(self):
        for specs in [[(60,0,1,'v'),(64,1,2,'v'),(67,2,3,'v'),(64,3,4,'v')],
                      [(48,0,4,'b'),(64,0,4,'i'),(67,0,1,'v'),(69,1,F(5,4),'v'),(67,F(5,4),4,'v')]]:
            self.assertEqual(len(analyze(fixture(specs))['segments']),1)

    def test_default_engine_unchanged_by_noop_policy(self):
        ir=fixture([(p,0,4,str(i)) for i,p in enumerate([48,52,55])])
        self.assertEqual(analyze_joint(ir),analyze_joint(ir,segment_policy=lambda *args:None))

    def test_annotation_independence(self):
        ir=fixture([(p,0,4,str(i)) for i,p in enumerate([48,52,55])])
        self.assertEqual(analyze(ir),analyze({**ir,'annotations':['V'],'phrases':[1]}))

    def test_transposition_preserves_gate(self):
        for shift in (0,1,5,11):
            rows,_=prepare(fixture([(p+shift,1,F(3,2),str(i)) for i,p in enumerate([55,59,62,65])]))
            def moved(c):return {**c,'root':(c['root']+shift)%12,'pcs':[(p+shift)%12 for p in c['pcs']]}
            self.assertTrue(gate(rows,F(1),F(3,2),F(1),moved(C),moved(G))['eligible'])

    def test_sustained_seventh_and_long_span_not_discounted(self):
        ir=fixture([(p,0,4,str(i)) for i,p in enumerate([55,59,62,65])])
        out=analyze(ir)
        self.assertEqual(len(out['segments']),1)
        self.assertEqual(out['segments'][0]['selected']['label'],'G:dominant7')
        rows,_=prepare(ir)
        self.assertFalse(gate(rows,F(0),F(4),F(1),C,G)['eligible'])
