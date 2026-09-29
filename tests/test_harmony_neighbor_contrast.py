from copy import deepcopy
import unittest
from test_harmony_voice_figures import neighbor
from test_harmony_open_candidates import score,run
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_joint import f
from musicanote_harness.harmony_voice_figures import double_neighbors
from musicanote_harness.harmony_neighbor_contrast import compare,profile,minimum_changes


def build(ir):
    w=run(ir);w['double_neighbor_evidence']=double_neighbors(ir,w)
    return w


def held(result):return next(c for c in result['records'][0]['fixed_harmony_readings'] if c['label']=='Ab:major')
def residual(p,group='other'):return f(p['groups'][group].get('nonmember_not_confirmed_nct',{}).get('duration_quarters',q(0)))


class NeighborContrastTests(unittest.TestCase):
    def test_held_triad_background_is_preserved(self):
        ir=neighbor();r=compare(ir,build(ir));h=held(r)
        self.assertEqual(residual(h['profile']),0);self.assertEqual(residual(h['profile'],'figure'),2)
        self.assertIsNone(r['selected']);self.assertTrue(h['constant_harmony_is_assumption'])
    def test_real_chord_change_remains_an_alternative(self):
        ir=score([('C3',0,1,'b'),('E-4',0,1,'i'),('G4',0,1,'j'),('G5',0,1,'v'),
                  ('E-3',1,2,'b'),('G4',1,2,'i'),('B-4',1,2,'j'),('B-5',1,2,'v'),
                  ('A-3',2,4,'b'),('C4',2,4,'i'),('E-4',2,4,'j'),('A-5',2,4,'v')])
        r=compare(ir,build(ir));h=held(r);self.assertGreater(residual(h['profile']),0)
        stage=r['records'][0]['member_stages'][0]
        cm=next(c for c in stage['member_alternatives'] if c['label']=='C:minor')
        self.assertEqual(residual(cm['profile']),0);self.assertEqual(cm['origin'],'local_observation_candidate')
    def test_suffix_does_not_infer_preparation(self):
        ir=score([('A-3',0,4,'b'),('C4',0,4,'i'),('E-4',0,4,'j'),('G5',1,2,'v'),('B-5',2,3,'v'),('A-5',3,4,'v')])
        r=compare(ir,build(ir))['records'][0]
        self.assertFalse(r['preparation_anchor_observed']);self.assertFalse(r['preparation_inferred'])
        self.assertTrue(held({'records':[r]})['surrounding_profiles'])
    def test_rest_not_overridden(self):
        ir=neighbor(gap=True);self.assertEqual(compare(ir,build(ir))['records'],[])
    def test_input_and_annotations_independent(self):
        ir=neighbor();w=build(ir);old=deepcopy(w);r=compare(ir,w);self.assertEqual(w,old)
        ir['annotations']=['ct'];self.assertEqual(compare(ir,w),r)
    def test_profiles_use_clipped_duration(self):
        ir=neighbor();w=build(ir);c=next(c for c in w['candidates'] if c['label']=='Ab:major')
        p=profile(w['event_units'],c,{'start':q(1),'end':q(2)},set(w['double_neighbor_evidence']['records'][0]['event_refs']))
        self.assertEqual(f(p['groups']['other']['member']['duration_quarters']),3)
        self.assertEqual(residual(p,'figure'),1)
    def test_lattice_change_count_is_not_selection(self):
        stage=lambda labels:{'member_alternatives':[{'label':v} for v in labels]}
        self.assertEqual(minimum_changes([stage(['a','b']),stage(['b']),stage(['c'])]),1)
        self.assertEqual(minimum_changes([stage(['a']),stage(['a'])]),0)
        self.assertIsNone(minimum_changes([stage([])]))
    def test_all_references_exist(self):
        ir=neighbor();w=build(ir);r=compare(ir,w)
        for record in r['records']:
            for stage in record['member_stages']:
                self.assertIn(stage['focus_event_ref'],w['event_units'])
                for c in stage['member_alternatives']:
                    self.assertTrue(set(c['profile']['event_refs'])<=set(w['event_refs']))
    def test_sparse_local_arrival_is_carried_hypothesis(self):
        ir=score([('A-3',0,1,'b'),('C4',0,1,'i'),('E-4',0,1,'j'),('G5',0,1,'v'),('B-5',1,2,'v'),('A-5',2,4,'v')])
        r=compare(ir,build(ir))['records'][0]
        last=r['member_stages'][-1]['member_alternatives']
        self.assertTrue(last);self.assertTrue(all(c['origin']=='parent_window_hypothesis' for c in last))
        self.assertTrue(all(c['profile']['missing_member_pcs'] for c in last))
    def test_barrier_blocks_contrast(self):
        ir=neighbor();w=build(ir)
        for fig in w['double_neighbor_evidence']['records']:fig['abstention_reasons'].append('repeat_barrier')
        self.assertEqual(compare(ir,w)['records'],[])
    def test_no_other_notes_is_not_positive_background_evidence(self):
        ir=neighbor();w=build(ir);c=w['candidates'][0]
        p=profile(w['event_units'],c,w['span'],set(w['event_refs']))
        self.assertFalse(p['other_event_evidence_present'])
    def test_no_event_extension(self):
        ir=neighbor();w=build(ir)
        for r in compare(ir,w)['records']:
            for stage in r['member_stages']:
                self.assertGreaterEqual(f(stage['span']['start']),f(r['span']['start']))
                self.assertLessEqual(f(stage['span']['end']),f(r['span']['end']))
