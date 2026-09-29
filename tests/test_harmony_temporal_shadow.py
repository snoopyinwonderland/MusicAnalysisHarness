import unittest
from fractions import Fraction
from test_harmony_joint import fixture
from musicanote_harness.harmony_temporal_shadow import analyze, provider, bass_path
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_joint import prepare, candidates


class TemporalTests(unittest.TestCase):
    def test_half_beat_arpeggio_and_neighbor(self):
        for specs in [[(60,0,1,'v'),(64,1,2,'v'),(67,2,3,'v'),(64,3,4,'v')],
                      [(48,0,4,'b'),(64,0,4,'i'),(67,0,1,'v'),(69,1,Fraction(5,4),'v'),(67,Fraction(5,4),4,'v')]]:
            self.assertEqual(len(analyze(fixture(specs),cell_divisions=2)['segments']),1)

    def test_half_beat_short_seventh(self):
        ir=fixture([(p,a,b,str(i)) for a,b,ps in [(0,1,[48,52,55]),(1,Fraction(3,2),[55,59,62,65]),(Fraction(3,2),4,[48,52,55])] for i,p in enumerate(ps)])
        self.assertIn('G:dominant7',[s['selected']['label'] for s in analyze(ir,cell_divisions=2)['segments']])

    def test_bass_factor_changes_not_single_inversion(self):
        ir=fixture([(48,0,1,'b'),(52,1,2,'b'),(55,0,2,'t'),(60,0,2,'s')])
        rows,_=prepare(ir)
        segment={'span':{'start':q(0),'end':q(2)},'selected':{'root':0,'label':'C:major'}}
        result=bass_path(rows,segment)
        self.assertEqual([x['inversion_index_under_template'] for x in result],[0,1])
        self.assertEqual(result[1]['event_refs'],['s1'])

    def test_bass_outside_candidate_and_silence(self):
        rows,_=prepare(fixture([(49,0,1,'b')]))
        segment={'span':{'start':q(0),'end':q(2)},'selected':{'root':0,'label':'C:major'}}
        result=bass_path(rows,segment)
        self.assertIsNone(result[0]['inversion_index_under_template'])
        self.assertIsNone(result[1]['lowest_midi'])
        self.assertEqual(result[1]['event_refs'],[])

    def test_invalid_resolution(self):
        with self.assertRaises(ValueError):provider(cell_divisions=0)

    def test_unsupported_local_candidate_is_scored_not_ignored(self):
        ir=fixture([(p,a,b,str(i)) for a,b,ps in [(0,1,[48,52,55]),(1,2,[49,53,56])] for i,p in enumerate(ps)])
        rows,neighbors=prepare(ir)
        args=(rows,neighbors,Fraction(0),Fraction(2),Fraction(1))
        old={c['label']:c for c in provider(False)(*args,limit=None)}
        new={c['label']:c for c in provider(True)(*args,limit=None)}
        self.assertGreater(new['C:major']['temporal_regret'],old['C:major']['temporal_regret'])
        local=candidates(rows,neighbors,Fraction(1),Fraction(2),Fraction(1),limit=None,min_shared_pcs=0)
        unsupported=next(c for c in local if c['label']=='C:major')
        self.assertEqual(unsupported['coverage'],0)
        self.assertGreater(unsupported['cost'],.9)

    def test_short_complete_change_survives(self):
        ir=fixture([(p,a,b,str(i)) for a,b,ps in [(0,1,[48,52,55]),(1,Fraction(3,2),[55,59,62,65]),(Fraction(3,2),4,[48,52,55])] for i,p in enumerate(ps)])
        result=analyze(ir)
        self.assertIn('G:dominant7',[s['selected']['label'] for s in result['segments']])

    def test_neighbor_does_not_force_split(self):
        ir=fixture([(48,0,4,'b'),(64,0,4,'i'),(67,0,1,'v'),
                    (69,1,Fraction(5,4),'v'),(67,Fraction(5,4),4,'v')])
        self.assertEqual(len(analyze(ir)['segments']),1)

    def test_empty(self):
        self.assertEqual(analyze({'sounding_events':[]})['segments'],[])

    def test_arpeggio_not_split(self):
        ir=fixture([(60,0,1,'v'),(64,1,2,'v'),(67,2,3,'v'),(64,3,4,'v')])
        self.assertEqual(len(analyze(ir)['segments']),1)

    def test_sustained_seventh_not_removed(self):
        ir=fixture([(55,0,4,'b'),(59,0,4,'a'),(62,0,4,'t'),(65,0,4,'s')])
        out=analyze(ir)
        self.assertEqual(len(out['segments']),1)
        self.assertEqual(out['segments'][0]['selected']['label'],'G:dominant7')

    def test_clear_change_kept(self):
        ir=fixture([(p,a,b,str(i)) for a,b,ps in [(0,2,[48,52,55]),(2,4,[55,59,62])] for i,p in enumerate(ps)])
        self.assertEqual(len(analyze(ir)['segments']),2)

    def test_labels_ignored_and_deterministic(self):
        ir=fixture([(60,0,4,'a'),(64,0,4,'b'),(67,0,4,'c')])
        self.assertEqual(analyze(ir),analyze({**ir,'annotations':['V'],'phrases':[1]}))
