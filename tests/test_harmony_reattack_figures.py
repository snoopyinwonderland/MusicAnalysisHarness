from copy import deepcopy
import unittest
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_open_candidates import window
from musicanote_harness.harmony_reattack_figures import assess
from test_harmony_open_candidates import score


def fixture(melody=None):
    return score([('C3',0,4,'a'),('E3',0,4,'b'),('G3',0,4,'c')] +
                 (melody or [('C4',0,1,'d'),('D4',1,1.5,'d'),('D4',1.5,2,'d'),('E4',2,4,'d')]))


def run(ir, end=4):
    w = window(ir, {'start':q(0), 'end':q(end)})
    return assess(ir,w)


def compatible(r, label='C:major'):
    return [v for v in r['records'] if any(e['label']==label and e['conditional_role']
            for e in v['candidate_explanations'])]


class ReattackFigureTests(unittest.TestCase):
    def test_repeated_middle_passing(self):
        ir=fixture();r=run(ir);rows=compatible(r)
        self.assertEqual(len(rows),1);self.assertEqual(len(rows[0]['middle_refs']),2)
        w=window(ir,{'start':q(0),'end':q(4)})
        self.assertFalse(any(e['conditional_role'] for x in w['conditional_figures']['records'] for e in x['path_explanations']))
    def test_lossless_attacks_and_duration(self):
        ir=fixture();r=run(ir);byid={s['sounding_event_id']:s for s in ir['sounding_events']}
        for g in r['groups']:
            self.assertFalse(g['is_tie_chain'])
            for a in g['attacks']:
                self.assertEqual(a['span'],byid[a['event_ref']]['span'])
                self.assertEqual(a['source_note_ids'],byid[a['event_ref']]['source_note_ids'])
    def test_repeated_neighbor(self):
        r=run(fixture([('C4',0,1,'d'),('D4',1,1.5,'d'),('D4',1.5,2,'d'),('C4',2,4,'d')]))
        self.assertEqual(compatible(r)[0]['geometry'],'neighbor_geometry')
    def test_gap_is_not_bridged(self):
        self.assertFalse(compatible(run(fixture([('C4',0,1,'d'),('D4',1,1.25,'d'),('D4',1.5,2,'d'),('E4',2,4,'d')]))))
    def test_overlap_is_not_bridged(self):
        self.assertFalse(compatible(run(fixture([('C4',0,1,'d'),('D4',1,2,'d'),('D4',1.5,2,'d'),('E4',2,4,'d')]))))
    def test_enharmonic_reattack_not_merged(self):
        r=run(fixture([('C4',0,1,'d'),('D#4',1,1.5,'d'),('E-4',1.5,2,'d'),('E4',2,4,'d')]))
        self.assertFalse(any(g['attack_count']>1 for g in r['groups']))
    def test_outside_resolution_not_borrowed(self):
        self.assertFalse(compatible(run(fixture(),3)))
    def test_missing_meter_blocks_role(self):
        ir=fixture();ir['measures'][0]['time_signature'].pop('beats')
        self.assertFalse(compatible(run(ir)))
    def test_repeat_barrier_blocks_role(self):
        ir=fixture();m=deepcopy(ir['measures'][0]);m['global_start_quarter']=q(2)
        m['actual_duration_quarter']=q(2);m['repeat_barline']={'location':'left','repeat_direction':'forward'}
        ir['measures'][0]['actual_duration_quarter']=q(2);ir['measures'].append(m)
        r=run(ir);self.assertIn('repeat_barrier',r['abstention_reasons']);self.assertFalse(compatible(r))
    def test_different_voice_not_connected(self):
        self.assertFalse(compatible(run(fixture([('C4',0,1,'d'),('D4',1,1.5,'d'),('D4',1.5,2,'e'),('E4',2,4,'d')]))))
    def test_plain_triple_not_duplicated(self):
        self.assertEqual(run(fixture([('C4',0,1,'d'),('D4',1,2,'d'),('E4',2,4,'d')]))['records'],[])
    def test_no_mutation_or_annotation_input(self):
        ir=fixture();old=deepcopy(ir);r=run(ir);self.assertEqual(ir,old)
        ir['annotations']=['ii6'];self.assertEqual(run(ir),r)
        self.assertIsNone(r['selected'])
    def test_candidate_member_alternative_retained(self):
        r=run(fixture([('C4',0,1,'d'),('D4',1,1.5,'d'),('D4',1.5,2,'d'),('C4',2,4,'d')]))
        self.assertTrue(any(e['status']=='all_events_are_candidate_members' for v in r['records'] for e in v['candidate_explanations']))
