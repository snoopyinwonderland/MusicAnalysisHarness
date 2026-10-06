from copy import deepcopy
from fractions import Fraction as F
import unittest
from test_harmony_catalog_paths import fixture, run
from test_harmony_open_candidates import score
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_path_context import augment, plan


def narrow(ir):
    base=run(ir)[0]
    base['span']={'start':q(1),'end':q(F(3,2))}
    for p in base['arrival_path_assessment']['paths'].values():
        p['observation']['abstention_reasons'].append('full_path_outside_frozen_context')
    return base


class PathContextTests(unittest.TestCase):
    def test_expansion_is_minimal_union_not_chord_extension(self):
        ir=fixture();base=narrow(ir);r=augment(ir,base)
        self.assertTrue(r['bounded_path_context']['paths'])
        for p in r['bounded_path_context']['paths'].values():
            c=p['context_policy'];self.assertTrue(c['accepted'])
            self.assertEqual(c['proposed_span']['start'],q(0))
            self.assertEqual(c['proposed_span']['end'],p['observation']['span']['end'])
            self.assertFalse(c['chord_spans_extended'])
            self.assertIn('full_path_outside_frozen_context',p['cleared_context_reasons'])

    def test_original_result_and_ir_immutable(self):
        ir=fixture();base=narrow(ir);snapshot=deepcopy((ir,base));r=augment(ir,base)
        self.assertEqual((ir,base),snapshot)
        self.assertEqual({k:r[k] for k in base},base)

    def test_sound_limit_never_prunes(self):
        ir=score([('C4',0,2,str(i)) for i in range(129)])
        p=plan(ir,{'start':q(0),'end':q(1)},{'span':{'start':q(0),'end':q(2)}})
        self.assertFalse(p['accepted']);self.assertEqual(len(p['sound_refs']),129)

    def test_duration_limit_rejects_whole_expansion(self):
        ir=fixture();p=plan(ir,{'start':q(0),'end':q(1)},{'span':{'start':q(0),'end':q(17)}})
        self.assertIn('context_beat_limit_no_truncation',p['abstention_reasons'])
        self.assertEqual(p['proposed_span']['end'],q(17))

    def test_missing_meter_abstains(self):
        ir=fixture();ir['measures'][0]['time_signature']={}
        self.assertFalse(plan(ir,{'start':q(0),'end':q(1)},{'span':{'start':q(0),'end':q(2)}})['accepted'])

    def test_repeat_barrier_blocks(self):
        ir=fixture();m=ir['measures'][0];m['actual_duration_quarter']=q(1)
        m['repeat_barline']={'location':'right','repeat_direction':'backward'}
        p=plan(ir,{'start':q(0),'end':q(1)},{'span':{'start':q(0),'end':q(2)}})
        self.assertIn('repeat_or_ending_barrier',p['abstention_reasons'])

    def test_meter_change_and_missing_measure_coverage(self):
        ir=fixture();m=ir['measures'][0];m['actual_duration_quarter']=q(1)
        second=deepcopy(m);second['global_start_quarter']=q(F(3,2))
        second['time_signature']['beats']=3;ir['measures']=[m,second]
        p=plan(ir,{'start':q(0),'end':q(1)},{'span':{'start':q(0),'end':q(2)}})
        self.assertIn('meter_changed',p['abstention_reasons'])
        self.assertIn('measure_coverage_gap',p['abstention_reasons'])

    def test_polyphony_keeps_no_link_and_every_partial_matching(self):
        # Two releases at 1.5 and two attacks at 1.5 in the same voice.
        ir=score([('D3',0,1,'b'),('F#3',0,1,'l'),('A3',0,1,'f'),('C5',0,1,'v'),
            ('G3',1,3,'b'),('D4',1,3,'f'),('G4',F(5,4),F(3,2),'v'),
            ('D5',F(5,4),F(3,2),'v'),('B4',F(3,2),2,'v'),
            ('E5',F(3,2),2,'v')])
        base=narrow(ir);r=augment(ir,base)
        groups=[g for p in r['bounded_path_context']['paths'].values() for g in p['polyphonic_observation']['groups']]
        two=next(g for g in groups if len(g['source_refs'])==len(g['target_refs'])==2)
        self.assertEqual(len(two['assignments']),7)
        self.assertTrue(any(not a['edge_indices'] for a in two['assignments']))
        self.assertIsNone(two['selected_assignment'])
        self.assertTrue(any(a['crossing_count'] for a in two['assignments']))

    def test_no_rest_bridge_or_resolution_promotion(self):
        ir=fixture();base=narrow(ir);r=augment(ir,base)
        for p in r['bounded_path_context']['paths'].values():
            self.assertEqual(p['observation']['initial_gap'],{'start':q(1),'end':q(F(5,4))})
            self.assertFalse(p['connection_across_initial_gap_confirmed'])
            self.assertIsNone(p['global_voice_path_selected'])

    def test_annotations_do_not_choose_extent_or_match(self):
        ir=fixture();base=narrow(ir);a=augment(ir,base)
        ir['annotations']=[{'label':'V7/V','end':999}];ir['phrases']=[0,999]
        self.assertEqual(a,augment(ir,base))

    def test_outside_sound_in_ledger_without_clipping(self):
        ir=fixture();base=narrow(ir);r=augment(ir,base)
        for p in r['bounded_path_context']['paths'].values():
            self.assertTrue(p['context_policy']['added_sound_refs'])
            self.assertEqual(p['observation']['events'],base['arrival_path_assessment']['paths'][p['observation']['path_id']]['observation']['events'])

    def test_meter_scaling_preserves_limit_units(self):
        ir=fixture();span={'start':q(0),'end':q(2)}
        a=plan(ir,span,{'span':span});small=deepcopy(ir)
        from musicanote_harness.harmony_joint import f
        for m in small['measures']:
            m['time_signature']['beat_type']*=2
            m['global_start_quarter']=q(f(m['global_start_quarter'])/2)
            m['actual_duration_quarter']=q(f(m['actual_duration_quarter'])/2)
        for s in small['sounding_events']:s['span']={k:q(f(v)/2) for k,v in s['span'].items()}
        half={'start':q(0),'end':q(1)};b=plan(small,half,{'span':half})
        self.assertEqual(a['denominator_units'],b['denominator_units'])

    def test_rejected_context_has_no_partial_computation(self):
        ir=fixture();base=narrow(ir)
        for p in base['arrival_path_assessment']['paths'].values():p['observation']['span']['end']=q(99)
        for p in augment(ir,base)['bounded_path_context']['paths'].values():
            self.assertFalse(p['context_policy']['accepted']);self.assertNotIn('polyphonic_observation',p)
