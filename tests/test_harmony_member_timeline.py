import unittest
from copy import deepcopy
from test_harmony_open_candidates import score,run,get
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_member_timeline import observe


def analyze(ir,a=1,b=3,root=0,quality='major',roots=None):
    c=get(run(ir,0,4),root,quality)
    return observe(ir,{'start':q(a),'end':q(b)},c,roots if roots is not None else c['root_hypotheses'],{'start':q(0),'end':q(4)})


class MemberTimelineTests(unittest.TestCase):
    def test_arpeggio_completion_not_backdated(self):
        r=analyze(score([('C4',1,1.5,'v'),('E4',1.5,2,'v'),('G4',2,3,'v')]))
        self.assertEqual(r['pooled_members_first_complete_at'],q(2));self.assertFalse(r['simultaneously_complete_cells'])
    def test_vertical_complete(self):
        r=analyze(score([('C4',1,3,'a'),('E4',1,3,'b'),('G4',1,3,'c')]))
        self.assertEqual(r['pooled_members_first_complete_at'],q(1));self.assertTrue(r['simultaneously_complete_cells'])
    def test_future_note_does_not_fill_missing(self):
        r=analyze(score([('C4',1,3,'a'),('E4',1,3,'b'),('G4',3,4,'c')]))
        self.assertIn('G',r['missing_inside']);self.assertIsNone(r['pooled_members_first_complete_at'])
        self.assertTrue(next(m for m in r['members'] if m['spelling']=='G')['missing_inside_but_seen_outside'])
    def test_held_sound_original_onset_preserved(self):
        r=analyze(score([('C4',0,4,'a'),('E4',1,3,'b'),('G4',1,3,'c')]))
        c=next(m for m in r['members'] if m['spelling']=='C');self.assertEqual(c['held_across_start'],c['held_across_end'])
        self.assertEqual(r['event_units'][c['held_across_start'][0]]['original_span']['start'],q(0))
    def test_reattack_not_held(self):
        r=analyze(score([('C4',0,1,'a'),('C4',1,3,'a'),('C4',3,4,'a'),('E4',1,3,'b'),('G4',1,3,'c')]))
        c=next(m for m in r['members'] if m['spelling']=='C');self.assertFalse(c['held_across_start']);self.assertFalse(c['held_across_end'])
        self.assertNotEqual(c['refs_by_region']['before'],c['refs_by_region']['after'])
    def test_enharmonic_not_accepted(self):
        ir=score([('C4',1,3,'a'),('F-4',1,3,'b'),('G4',1,3,'c')]);roots=[{'expected_members':['C','E','G']}]
        r=analyze(ir,roots=roots);self.assertIn('E',r['missing_inside'])
    def test_unknown_root_not_invented(self):
        r=analyze(score([('C4',1,3,'a'),('E4',1,3,'b'),('G4',1,3,'c')]),roots=[])
        self.assertIn('root_spelling_unobserved_or_ambiguous',r['abstention_reasons'])
    def test_silence_kept(self):
        r=analyze(score([('C4',1,1.5,'a'),('E4',2,2.5,'a'),('G4',2.5,3,'a')]))
        self.assertTrue(r['windows']['inside']['all_voice_silence'])
    def test_truncated_context_not_complete(self):
        r=analyze(score([('C4',0,4,'a'),('E4',0,4,'b'),('G4',0,4,'c')]),a=0)
        self.assertIn('requested_context_truncated',r['abstention_reasons'])
    def test_repeat_barrier_recorded(self):
        ir=score([('C4',0,4,'a'),('E4',0,4,'b'),('G4',0,4,'c')]);ir['measures'][0]['repeat_barline']={'location':'left','repeat_direction':'forward'}
        ir['measures'][0]['global_start_quarter']=q(2)
        r=analyze(ir);self.assertIn('repeat_or_ending_barrier',r['abstention_reasons'])
    def test_immutable_and_annotation_independent(self):
        ir=score([('C4',0,4,'a'),('E4',0,4,'b'),('G4',0,4,'c')]);old=deepcopy(ir);r=analyze(ir)
        self.assertEqual(ir,old);ir['annotations']=['I'];self.assertEqual(analyze(ir),r)
    def test_invalid_context_rejected(self):
        ir=score([('C4',0,4,'a'),('E4',0,4,'b')]);c=get(run(ir),0,'major')
        with self.assertRaises(ValueError):observe(ir,{'start':q(1),'end':q(3)},c,c['root_hypotheses'],{'start':q(2),'end':q(4)})
