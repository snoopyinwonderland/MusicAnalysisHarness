from copy import deepcopy
import unittest
from test_harmony_open_candidates import score,run,get
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_voice_figures import octave_links,double_neighbors


def octaves(specs=None):
    return score(specs or [('D4',0,1,'v'),('D5',0,1,'v'),('E-4',1,2,'v'),('E-5',1,2,'v')])


def read(ir):return octave_links(ir,{'start':q(0),'end':q(4)})


def neighbor(middle=('G4','B-4'),gap=False):
    return score([('A-3',0,4,'bass'),('C4',0,4,'inner'),('E-4',0,4,'other'),
        ('A-4',0,.5 if gap else 1,'v'),(middle[0],1,2,'v'),(middle[1],2,3,'v'),('A-4',3,4,'v')])


def dn(ir):return double_neighbors(ir,run(ir))


class VoiceFigureTests(unittest.TestCase):
    def test_synchronous_octaves(self):
        r=read(octaves());self.assertEqual(len(r['links']),2)
        self.assertEqual(len({l['dependency_group'] for l in r['links']}),1)
        self.assertTrue(all(not l['contrapuntal_voice_identity_confirmed'] for l in r['links']))
    def test_unequal_counts_abstain(self):
        self.assertFalse(read(octaves([('D4',0,1,'v'),('D5',0,1,'v'),('E-4',1,2,'v')]))['links'])
    def test_mixed_chord_abstains(self):
        self.assertFalse(read(octaves([('D4',0,1,'v'),('F4',0,1,'v'),('E-4',1,2,'v'),('G4',1,2,'v')]))['links'])
    def test_leap_abstains(self):
        self.assertFalse(read(octaves([('D4',0,1,'v'),('D5',0,1,'v'),('F4',1,2,'v'),('F5',1,2,'v')]))['links'])
    def test_overlapping_inner_note_blocks(self):
        ir=octaves([('D4',0,1,'v'),('D5',0,1,'v'),('E-4',1,2,'v'),('E-5',1,2,'v'),('A4',0,2,'v')])
        self.assertFalse(read(ir)['links'])
    def test_asynchronous_octaves_block(self):
        self.assertFalse(read(octaves([('D4',0,1,'v'),('D5',0,.5,'v'),('E-4',1,2,'v'),('E-5',1,2,'v')]))['links'])
    def test_grace_not_removed(self):
        ir=octaves();ir['note_events'][0]['grace']={'is_grace':True};self.assertFalse(read(ir)['links'])
    def test_context_end_respected(self):
        self.assertFalse(octave_links(octaves(),{'start':q(0),'end':q(1)})['links'])
    def test_double_neighbor(self):
        ir=neighbor();r=dn(ir);self.assertEqual(r['conditional_count'],1)
        c=get(run(ir),8,'major');e=next(e for e in r['records'][0]['candidate_explanations'] if e['candidate_ref']==c['candidate_id'])
        self.assertEqual(e['conditional_role'],'double_neighbor');self.assertFalse(e['confirmed_nct'])
    def test_reverse_neighbor_order(self):self.assertEqual(dn(neighbor(('B-4','G4')))['conditional_count'],1)
    def test_gap_not_bridged(self):
        r=dn(neighbor(gap=True));self.assertEqual(len(r['records']),1);self.assertEqual(r['conditional_count'],0)
        self.assertIn('gap_or_overlap_inside_figure',r['records'][0]['abstention_reasons'])
    def test_same_side_is_not_double_neighbor(self):self.assertEqual(dn(neighbor(('G4','G4')))['records'],[])
    def test_nonstep_not_neighbor(self):self.assertEqual(dn(neighbor(('F4','C5')))['records'],[])
    def test_does_not_mutate_or_read_annotations(self):
        ir=neighbor();old=deepcopy(ir);r=dn(ir);self.assertEqual(ir,old);ir['annotations']=['ct'];self.assertEqual(dn(ir),r)
    def test_barrier_blocks_role(self):
        ir=neighbor();w=run(ir);w['abstention_reasons']=['repeat_barrier'];self.assertEqual(double_neighbors(ir,w)['conditional_count'],0)
    def test_polyphony_blocks_role(self):
        ir=neighbor();ir['note_events'][0]['voice_id']=ir['note_events'][-1]['voice_id'];self.assertEqual(dn(ir)['conditional_count'],0)
    def test_suffix_without_anchor_is_not_full_role(self):
        ir=score([('A-3',0,4,'bass'),('C4',0,4,'inner'),('E-4',0,4,'other'),('G5',1,2,'v'),('B-5',2,3,'v'),('A-5',3,4,'v')])
        r=dn(ir);self.assertEqual(r['conditional_count'],0);self.assertEqual(len(r['records']),1)
        self.assertFalse(r['records'][0]['preparation_anchor_observed'])
        self.assertTrue(any(e['status']=='incomplete_double_neighbor_hypothesis' for e in r['records'][0]['candidate_explanations']))
    def test_full_form_does_not_duplicate_suffix(self):self.assertEqual(len(dn(neighbor())['records']),1)
