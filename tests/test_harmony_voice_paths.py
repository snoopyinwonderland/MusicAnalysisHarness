from copy import deepcopy
from fractions import Fraction as F
import unittest
from test_harmony_open_candidates import score
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_voice_paths import observe,partition,augment


def run(rows,end=4):return observe(score(rows),{'start':q(0),'end':q(end)},('part1','v'))


class VoicePathsTests(unittest.TestCase):
    def test_three_sequential_notes_four_partitions(self):
        r=run([('C4',0,1,'v'),('D4',1,2,'v'),('E4',2,3,'v')])
        self.assertEqual(len(r['assignments']),4)
        self.assertTrue(any(len(a['tracks'])==1 for a in r['assignments']))
        self.assertTrue(any(not a['links'] for a in r['assignments']))

    def test_two_polyphonic_boundaries_keep_all_49_combinations(self):
        r=run([(p,t,t+1,'v') for t,ps in enumerate([('C4','G4'),('D4','A4'),('E4','B4')]) for p in ps])
        self.assertEqual(len(r['assignments']),49)
        ids={e['sounding_event_id'] for e in r['events']}
        for a in r['assignments']:
            used=[sid for tr in a['tracks'] for sid in tr]
            self.assertEqual(len(used),len(set(used)));self.assertEqual(set(used),ids)
        self.assertIsNone(r['selected_assignment'])

    def test_rest_never_bridged(self):
        r=run([('C4',0,1,'v'),('B3',2,3,'v')])
        self.assertEqual(r['possible_assignments'],1)
        self.assertEqual(r['assignments'][0]['links'],[])
        self.assertEqual(len(r['assignments'][0]['tracks']),2)

    def test_held_note_is_single_event_not_reassigned(self):
        r=run([('C3',0,4,'v'),('G4',0,1,'v'),('A4',1,2,'v'),('B4',2,3,'v')])
        held=r['events'][0]['sounding_event_id']
        self.assertTrue(all(held in b['held_refs'] for b in r['boundaries']))
        self.assertTrue(all([held] in a['tracks'] for a in r['assignments']))

    def test_tie_source_notes_not_multiple_attacks(self):
        ir=score([('C4',0,2,'v'),('D4',2,3,'v')]);s=ir['sounding_events'][0]
        n=deepcopy(ir['note_events'][0]);n['note_id']='tie_cont';ir['note_events'].append(n)
        s['source_note_ids'].append(n['note_id'])
        r=observe(ir,{'start':q(0),'end':q(4)},('part1','v'))
        self.assertEqual(len(r['events']),2);self.assertEqual(len(r['boundaries']),1)

    def test_cap_abstains_without_preferred_subset(self):
        r=run([('C4',i,i+1,'v') for i in range(12)],13)
        self.assertEqual(r['possible_assignments'],2048);self.assertEqual(r['assignments'],[])
        self.assertFalse(r['enumeration_complete'])

    def test_endpoint_cap_abstains(self):
        r=run([(p,0,1,'v') for p in ('C4','D4','E4','F4','G4')]+[('A4',1,2,'v')])
        self.assertIn('endpoint_limit_no_pruning',r['abstention_reasons'])
        self.assertEqual(len(r['events']),6);self.assertEqual(r['assignments'],[])

    def test_branch_and_merge_invalid(self):
        events=score([('C4',0,1,'v'),('E4',0,1,'v'),('D4',1,2,'v'),('F4',1,2,'v')])['sounding_events']
        a,b,c,d=[s['sounding_event_id'] for s in events]
        for links in ([(a,c),(a,d)],[(a,c),(b,c)]):
            with self.assertRaisesRegex(ValueError,'branch_or_merge'):partition(events,links)

    def test_gap_overlap_invalid(self):
        for t in (F(1,2),F(3,2)):
            events=score([('C4',0,1,'v'),('D4',t,2,'v')])['sounding_events']
            with self.assertRaisesRegex(ValueError,'gap_overlap'):partition(events,[[s['sounding_event_id'] for s in events]])

    def test_other_voice_not_connected(self):
        r=run([('C4',0,1,'v'),('D4',1,2,'other')])
        self.assertEqual(len(r['events']),1);self.assertEqual(r['assignments'][0]['links'],[])

    def test_missing_identity_is_not_silently_discarded(self):
        ir=score([('C4',0,1,'v'),('D4',1,2,'v')]);ir['note_events'][1]['voice_id']=None
        r=observe(ir,{'start':q(0),'end':q(4)},('part1','v'))
        self.assertTrue(r['unlocated_sound_refs']);self.assertFalse(r['enumeration_complete'])

    def test_window_clips_note_time_not_events(self):
        ir=score([('C4',0,3,'v'),('G4',1,2,'v')]);r=observe(ir,{'start':q(1),'end':q(2)},('part1','v'))
        self.assertEqual(r['total_observed_note_time'],q(2))
        self.assertEqual(r['events'][0]['span']['start'],q(0))
        self.assertTrue(all(a['note_time_preserved'] for a in r['assignments']))

    def test_annotated_answer_never_selects_path(self):
        ir=score([('C4',0,1,'v'),('D4',1,2,'v')]);span={'start':q(0),'end':q(4)}
        old=deepcopy(ir);a=observe(ir,span,('part1','v'));self.assertEqual(ir,old)
        ir['annotations']=['V7'];ir['phrases']=[0,2]
        self.assertEqual(a,observe(ir,span,('part1','v')))

    def test_pipeline_preserves_previous_results_and_gap(self):
        from test_harmony_catalog_paths import fixture,run as base_run
        from musicanote_harness.harmony_path_context import augment as context
        ir=fixture();base=context(ir,base_run(ir)[0]);old=deepcopy(base);r=augment(ir,base)
        self.assertEqual(base,old);self.assertEqual({k:r[k] for k in base},base)
        self.assertTrue(r['continuous_voice_paths']['paths'])
        for p in r['continuous_voice_paths']['paths'].values():self.assertEqual(p['endpoint_same_track_assignments'],0)

    def test_transpose_and_duration_scale_preserve_partitions(self):
        a=run([('C4',0,1,'v'),('D4',1,2,'v'),('E4',2,3,'v')])
        b=run([('D4',0,F(1,2),'v'),('E4',F(1,2),1,'v'),('F#4',1,F(3,2),'v')],2)
        self.assertEqual([x['tracks'] for x in a['assignments']],[x['tracks'] for x in b['assignments']])
