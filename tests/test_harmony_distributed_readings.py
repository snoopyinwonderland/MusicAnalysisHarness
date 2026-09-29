from copy import deepcopy
from fractions import Fraction as F
import unittest
from test_harmony_joint import fixture
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_joint import f
from musicanote_harness.harmony_distributed_readings import observe
from musicanote_harness.harmony_shared_tone_review import observe as vertical


def melody(transpose=0,scale=F(1),delayed=False,pedal=False):
    notes=[48,52,55,48]+([55,59,52,55] if delayed else [52,55,59,52])
    specs=[(p+transpose,F(i,2)*scale,F(i+1,2)*scale,'melody') for i,p in enumerate(notes)]
    if pedal:specs.append((36+transpose,0,4*scale,'bass'))
    ir=fixture(specs);ir['measures'][0].update(actual_duration_quarter=q(4*scale),time_signature={'beat_type':int(4/scale)})
    return ir


class DistributedReadingsTests(unittest.TestCase):
    def test_finds_sequential_triads_without_vertical_chords(self):
        ir=melody();self.assertEqual(vertical(ir)['alternatives'],[])
        out=observe(ir);self.assertTrue(any(f(a['boundary'])==2 for a in out['alternatives']))
        a=next(a for a in out['alternatives'] if f(a['boundary'])==2)
        self.assertEqual([s['candidate']['label'] for s in a['split_triads'][0]['segments']],['C:major','E:minor'])
        self.assertEqual(a['merged_seventh'][0]['segments'][0]['candidate']['label'],'C:major7')
        self.assertIsNone(a['selected_hypothesis'])

    def test_common_tone_start_keeps_actual_entry_delay(self):
        out=observe(melody(delayed=True))
        a=next(a for a in out['alternatives'] if f(a['boundary'])==2)
        self.assertEqual(f(a['entry_delay_quarters']),F(1,2))
        self.assertEqual(a['boundary_support_band'],{'start':q(2),'end':q(F(5,2)),'semantics':'closed uncertainty interval, not an event span'})

    def test_root_pedal_not_deleted_to_invent_triad(self):
        self.assertFalse(any(f(a['boundary'])==2 for a in observe(melody(pedal=True))['alternatives']))

    def test_silence_not_bridged(self):
        ir=melody();ir['sounding_events'][3]['span']['end']=q(F(7,4))
        self.assertFalse(any(f(a['boundary'])==2 for a in observe(ir)['alternatives']))

    def test_transposition_scaling_cost_invariance(self):
        def normalized(ir,tr=0,scale=F(1)):
            return [(f(a['span']['start'])/scale,f(a['boundary'])/scale,f(a['span']['end'])/scale,
                     sorted((x-tr)%12 for x in a['left_pitch_classes']),round(a['split_minus_merge_cost'],8)) for a in observe(ir)['alternatives']]
        self.assertEqual(normalized(melody()),normalized(melody(2),2))
        self.assertEqual(normalized(melody()),normalized(melody(scale=F(1,2)),scale=F(1,2)))

    def test_costs_references_and_gate_totals(self):
        ir=melody();out=observe(ir);ids={s['sounding_event_id'] for s in ir['sounding_events']}
        self.assertEqual(out['gate_audit']['window_pairs'],len(out['alternatives'])+sum(out['gate_audit']['first_failed_gate'].values()))
        for a in out['alternatives']:
            self.assertLessEqual(set(a['event_refs']),ids)
            for key in ('merged_seventh','split_triads'):
                for p in a[key]:self.assertAlmostEqual(p['local_cost'],sum(sum(s['cost_parts'].values()) for s in p['segments'])+sum(p.get('transition_parts',{}).values()))

    def test_no_input_mutation_or_label_leakage(self):
        ir=melody();old=deepcopy(ir);a=observe(ir)
        self.assertEqual(ir,old)
        self.assertEqual(a,observe({**ir,'annotations':['I7'],'phrases':[1],'title':'different expected answer'}))

    def test_double_voice_does_not_double_pc_occupancy(self):
        ir=melody();a=observe(ir)['alternatives']
        for s in list(ir['sounding_events']):ir['sounding_events'].append({**s,'sounding_event_id':'double_'+s['sounding_event_id']})
        b=observe(ir)['alternatives']
        self.assertEqual([x['occupancy_quarters'] for x in a],[x['occupancy_quarters'] for x in b])

    def test_mixed_meter_window_deferred(self):
        ir=melody();ir['measures'].append({'global_start_quarter':q(2),'actual_duration_quarter':q(2),'time_signature':{'beat_type':8}})
        self.assertFalse(any(f(a['boundary'])==2 for a in observe(ir)['alternatives']))

    def test_analysis_window_not_extended(self):
        span={'start':q(1),'end':q(3)};result=observe(melody(),span)
        self.assertTrue(all(f(a['span']['start'])>=1 and f(a['span']['end'])<=3 for a in result['alternatives']))

    def test_empty_and_invalid(self):
        self.assertEqual(observe({'sounding_events':[]})['alternatives'],[])
        for a,b in [(-1,2),(2,2),(2,1)]:
            with self.assertRaises(ValueError):observe(melody(),{'start':q(a),'end':q(b)})

    def test_multiple_windows_not_votes(self):
        result=observe(melody())
        self.assertTrue(result['boundary_groups'])
        self.assertTrue(all(g['votes_or_confidence'] is False for g in result['boundary_groups']))


if __name__=='__main__':unittest.main()
