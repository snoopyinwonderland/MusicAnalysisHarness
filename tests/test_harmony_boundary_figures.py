from copy import deepcopy
import unittest
from test_harmony_open_candidates import score
from test_harmony_segment_contrast import fixture,run,index,full_assignment
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_joint import f
from musicanote_harness.harmony_catalog_resolution import pitch_pair
from musicanote_harness.harmony_voice_paths import observe
from musicanote_harness.harmony_segment_contrast import grid
from musicanote_harness.harmony_boundary_figures import observe as figures,compare,augment


def pair_fixture(notes,left,right,cut=1,end=3):
    ir=score([(p,a,b,'v') for p,a,b in notes]);span={'start':q(0),'end':q(end)}
    lane=[ir['note_events'][0]['part_id'],ir['note_events'][0]['voice_id']];v=observe(ir,span,lane);events=v['events']
    def reading(members,a,b,name):
        return {'candidate_ref':name,'members':members,'span':{'start':q(a),'end':q(b)},
            'event_states':{s['sounding_event_id']:'member' if pitch_pair(s['pitch']) in members else 'nonmember_not_confirmed_nct' for s in events if f(s['span']['start'])<b and f(s['span']['end'])>a},
            'condition':{'abstention_reasons':[],'assignments':[{'assignment_ref':a['assignment_id'],'conditionally_explained_nonmember_refs':[]} for a in v['assignments']]}}
    result={'status':'ready','span':span,'events':events,'assignments':v['assignments'],'hold_readings':[reading(left,0,end,'hold')],
        'total_note_time':v['total_observed_note_time'],'boundaries':[{'status':'ready','boundary':q(cut),'cells':grid(events,span,q(cut)),
            'left':{'readings':[reading(left,0,cut,'left')]},'right':{'readings':[reading(right,cut,end,'right')]}}]}
    return result


C=[['C',0],['E',0],['G',0]]
F=[['F',0],['A',0],['C',0]]
G=[['G',0],['B',0],['D',0]]


class BoundaryFiguresTests(unittest.TestCase):
    def test_same_chord_restores_crossing_passing_without_membership_change(self):
        r=run(fixture());b=r['boundaries'][0];args=(0,index(r['hold_readings'],'G:major'),index(b['left']['readings'],'G:major'),index(b['right']['readings'],'G:major'),full_assignment(r))
        c=compare(r,*args);new=c['split_with_boundary_context']['note_time']
        self.assertEqual(new,c['baseline_comparison']['hold']['note_time']);self.assertEqual(new['conditional_nonmember'],q(1))
        self.assertEqual(c['split_with_boundary_context']['total_note_time'],q(9));self.assertIsNone(c['preferred'])

    def test_same_chord_neighbor_restored(self):
        r=pair_fixture([('G4',0,1),('A4',1,2),('G4',2,3)],C,C)
        self.assertIn('cross_boundary_neighbor_candidate',[p['kind'] for p in figures(r,0)['patterns']])

    def test_changed_chords_can_support_passing_geometry(self):
        r=pair_fixture([('C4',0,1),('D4',1,2),('E4',2,3)],F,C)
        self.assertIn('cross_boundary_passing_candidate',[p['kind'] for p in figures(r,0)['patterns']])

    def test_nonmember_middle_required_in_every_occupied_segment(self):
        r=pair_fixture([('C4',0,1),('D4',1,2),('E4',2,3)],F,G)
        self.assertFalse(figures(r,0)['patterns'])

    def test_no_link_does_not_gain_three_note_explanation(self):
        r=run(fixture());b=r['boundaries'][0];aid=next(a['assignment_id'] for a in r['assignments'] if not a['links'])
        c=compare(r,0,index(r['hold_readings'],'G:major'),index(b['left']['readings'],'G:major'),index(b['right']['readings'],'G:major'),aid)
        self.assertFalse(c['active_patterns']);self.assertFalse(c['newly_explained_cells'])

    def test_prepared_suspension_only_post_boundary_time(self):
        r=pair_fixture([('F4',0,2),('E4',2,3)],F,C);c=compare(r,0,0,0,0,full_assignment(r))
        self.assertEqual([p['kind'] for p in c['active_patterns']],['prepared_suspension_candidate'])
        self.assertEqual(c['active_patterns'][0]['nonmember_span'],{'start':q(1),'end':q(2)})
        self.assertEqual(c['split_with_boundary_context']['note_time']['member'],q(2))
        self.assertEqual(c['split_with_boundary_context']['note_time']['conditional_nonmember'],q(1))

    def test_reattack_is_not_suspension(self):
        r=pair_fixture([('F4',0,1),('F4',1,2),('E4',2,3)],F,C)
        self.assertNotIn('prepared_suspension_candidate',[p['kind'] for p in figures(r,0)['patterns']])

    def test_upward_resolution_not_downward_suspension(self):
        r=pair_fixture([('B4',0,2),('C5',2,3)],G,C)
        self.assertFalse(figures(r,0)['patterns'])

    def test_anticipation_held_only_pre_boundary_time(self):
        r=pair_fixture([('F4',0,2)],C,F,end=2);c=compare(r,0,0,0,0,full_assignment(r))
        self.assertEqual(c['active_patterns'][0]['kind'],'anticipation_held_candidate')
        self.assertEqual(c['active_patterns'][0]['nonmember_span'],{'start':q(0),'end':q(1)})
        self.assertEqual(c['split_with_boundary_context']['note_time']['member'],q(1))
        self.assertEqual(c['split_with_boundary_context']['note_time']['conditional_nonmember'],q(1))

    def test_anticipation_reattack_needs_same_register_spelling(self):
        r=pair_fixture([('F4',0,1),('F4',1,2)],C,F,end=2)
        self.assertIn('anticipation_reattack_candidate',[p['kind'] for p in figures(r,0)['patterns']])
        r=pair_fixture([('F4',0,1),('F5',1,2)],C,F,end=2)
        self.assertFalse(figures(r,0)['patterns'])

    def test_enharmonic_reattack_does_not_count(self):
        r=pair_fixture([('F#4',0,1),('Gb4',1,2)],C,[['G',-1],['B',-1],['D',-1]],end=2)
        self.assertFalse(figures(r,0)['patterns'])

    def test_gap_not_bridged(self):
        r=pair_fixture([('C4',0,0.5),('D4',1,2),('E4',2,3)],F,C)
        self.assertFalse(figures(r,0)['patterns'])

    def test_blocked_candidate_cannot_receive_boundary_explanation(self):
        r=pair_fixture([('C4',0,1),('D4',1,2),('E4',2,3)],F,C)
        r['boundaries'][0]['left']['readings'][0]['condition']['abstention_reasons']=['grace_timing']
        self.assertFalse(figures(r,0)['patterns'])

    def test_partial_preparation_outside_context_abstains(self):
        r=pair_fixture([('F4',-1,2),('E4',2,3)],F,C)
        self.assertFalse(figures(r,0)['patterns'])

    def test_input_and_previous_results_unchanged(self):
        r=run(fixture());old=deepcopy(r);out=augment(r);self.assertEqual(old,r)
        for b,oldb in zip(out['boundaries'],r['boundaries']):
            self.assertEqual({k:v for k,v in b.items() if k!='boundary_figures'},oldb)

    def test_invalid_voice_partition_rejected(self):
        r=pair_fixture([('G4',0,1),('A4',1,2),('G4',2,3)],C,C)
        r['assignments'][0]['tracks']=[]
        with self.assertRaises((ValueError,KeyError)):figures(r,0)

    def test_middle_crosses_boundary_time_counted_once(self):
        r=pair_fixture([('C4',0,1),('D4',1,3),('E4',3,4)],F,C,cut=2,end=4)
        c=compare(r,0,0,0,0,full_assignment(r))
        self.assertEqual(c['split_with_boundary_context']['note_time']['conditional_nonmember'],q(2))
        self.assertEqual(c['split_with_boundary_context']['total_note_time'],q(4))

    def test_duplicate_explanations_never_double_count(self):
        r=pair_fixture([('C4',0,1),('D4',1,2),('E4',2,3)],F,C)
        ev=figures(r,0);self.assertTrue(ev['patterns']);ev['patterns']*=2;r['boundaries'][0]['boundary_figures']=ev
        c=compare(r,0,0,0,0,full_assignment(r))
        self.assertEqual(c['split_with_boundary_context']['note_time']['conditional_nonmember'],q(1))
