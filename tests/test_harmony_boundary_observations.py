from copy import deepcopy
from fractions import Fraction
import unittest
from test_harmony_open_candidates import score
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_joint import f
from musicanote_harness.harmony_segment_contrast import grid
from musicanote_harness.harmony_boundary_observations import meter_at,snapshot,support,observe,augment


def fixture(specs,cut=1,end=3,members=None):
    ir=score(specs);span={'start':q(0),'end':q(end)}
    for i,m in enumerate(ir['measures']):
        m.update(measure_id=f'measure_{i}',printed_measure_number=str(i+1),nominal_duration_quarter=deepcopy(m['actual_duration_quarter']))
    members=members or [['C',0],['E',0],['G',0]]
    reading=lambda a,b:{'span':{'start':q(a),'end':q(b)},'members':members}
    r={'status':'ready','span':span,'events':ir['sounding_events'],'hold_readings':[reading(0,end)],
       'boundaries':[{'status':'ready','boundary':q(cut),'cells':grid(ir['sounding_events'],span,q(cut)),
         'left':{'readings':[reading(0,cut)]},'right':{'readings':[reading(cut,end)]}}]}
    return ir,r


class BoundaryObservationsTests(unittest.TestCase):
    def test_release_excluded_and_attack_included_at_boundary(self):
        ir,r=fixture([('C3',0,1,'bass'),('D3',1,3,'bass'),('G4',0,3,'lead')]);o=observe(ir,r,0)
        a=o['cells'][o['before_cell_index']];b=o['cells'][o['after_cell_index']]
        self.assertEqual(a['lowest_midi_pitch'],48);self.assertEqual(b['lowest_midi_pitch'],50)
        self.assertEqual(len(b['attacked_event_refs']),1);self.assertEqual(len(b['continued_event_refs']),1)
        self.assertTrue(o['lowest_pitch_changed'])

    def test_bass_reattack_is_not_pitch_movement(self):
        ir,r=fixture([('C3',0,1,'bass'),('C3',1,3,'bass')]);o=observe(ir,r,0)
        self.assertFalse(o['lowest_pitch_changed']);self.assertEqual(len(o['cells'][1]['attacked_event_refs']),1)

    def test_all_equal_lowest_events_retained(self):
        ir,r=fixture([('C3',0,3,'a'),('C3',0,3,'b'),('E4',0,3,'c')]);c=observe(ir,r,0)['cells'][0]
        self.assertEqual(len(c['lowest_event_refs']),2);self.assertEqual(len(c['intervals_from_lowest']),6)

    def test_interval_spelling_not_just_pitch_class(self):
        ir,r=fixture([('C4',0,3,'a'),('F4',0,3,'b'),('E#4',0,3,'c')]);c=observe(ir,r,0)['cells'][0]
        pairs={(i['generic_interval'],i['semitones']) for i in c['intervals_from_lowest']}
        self.assertIn((4,5),pairs);self.assertIn((3,5),pairs)

    def test_unknown_pitch_does_not_silently_raise_bass(self):
        ir,r=fixture([('C3',0,3,'a'),('G4',0,3,'b')]);r['events'][0]['pitch']['step']='?'
        c=observe(ir,r,0)['cells'][0];self.assertEqual(c['bass_status'],'unknown_pitch_present')
        self.assertIsNone(c['lowest_midi_pitch']);self.assertFalse(c['intervals_from_lowest'])

    def test_silence_is_not_a_bass_or_chord(self):
        ir,r=fixture([('C4',0,1,'a'),('E4',2,3,'a')]);o=observe(ir,r,0)
        c=o['cells'][o['after_cell_index']];self.assertTrue(c['silence']);self.assertEqual(c['bass_status'],'silence')
        self.assertIsNone(o['lowest_pitch_changed'])

    def test_arpeggio_has_union_support_without_simultaneous_chord(self):
        ir,r=fixture([('C4',0,1,'a'),('E4',1,2,'a'),('G4',2,3,'a')]);o=observe(ir,r,0)
        p=o['candidate_support_profiles'][o['reading_profile_refs']['hold'][0]]
        self.assertEqual([x['observed_duration_quarters'] for x in p['member_coverage']],[q(1)]*3)
        self.assertEqual(p['all_members_simultaneous_duration_quarters'],q(0));self.assertFalse(p['candidate_rejected'])

    def test_unison_doubling_does_not_double_coverage(self):
        ir,r=fixture([('C4',0,3,'a'),('C5',0,3,'b')],members=[['C',0]]);o=observe(ir,r,0)
        p=o['candidate_support_profiles'][o['reading_profile_refs']['hold'][0]]
        self.assertEqual(p['member_coverage'][0]['observed_duration_quarters'],q(3))

    def test_unknown_absence_not_declared_certain(self):
        ir,r=fixture([('C4',0,3,'a')]);r['events'][0]['pitch']['midi_pitch']=None;o=observe(ir,r,0)
        p=o['candidate_support_profiles'][o['reading_profile_refs']['hold'][0]]
        self.assertEqual(p['unknown_pitch_duration_quarters'],q(3))
        self.assertFalse(p['cells'][0]['absence_certain_from_available_pitches'])

    def test_triplet_position_exact(self):
        ir,r=fixture([('C4',0,3,'a')]);m=meter_at(ir,q(Fraction(1,3)))
        self.assertEqual(m['denominator_unit_position_zero_based'],q(Fraction(1,3)))
        self.assertFalse(m['on_denominator_grid']);self.assertFalse(m['accent_assessed'])

    def test_compound_meter_does_not_guess_conducting_beat(self):
        ir,r=fixture([('C4',0,3,'a')]);ir['measures'][0]['time_signature']={'beats':6,'beat_type':8}
        m=meter_at(ir,q(Fraction(3,2)))
        self.assertEqual(m['denominator_unit_position_zero_based'],q(3));self.assertFalse(m['accent_assessed'])

    def test_pickup_does_not_claim_downbeat(self):
        ir,r=fixture([('C4',0,3,'a')]);ir['measures'][0]['pickup']=True
        m=meter_at(ir,q(0));self.assertTrue(m['is_measure_start']);self.assertIsNone(m['measure_start_downbeat'])

    def test_missing_and_ambiguous_measure(self):
        ir,r=fixture([('C4',0,3,'a')]);m=deepcopy(ir['measures'][0]);ir['measures'].append(m)
        self.assertEqual(meter_at(ir,q(0))['status'],'missing_or_ambiguous_measure')
        self.assertEqual(meter_at({'measures':[]},q(0))['status'],'missing_or_ambiguous_measure')

    def test_no_meter_still_keeps_offset(self):
        ir,r=fixture([('C4',0,3,'a')]);ir['measures'][0]['time_signature']={}
        m=meter_at(ir,q(1));self.assertEqual(m['onset_in_measure'],q(1));self.assertIsNone(m['on_denominator_grid'])

    def test_source_and_previous_result_unchanged(self):
        ir,r=fixture([('C4',0,3,'a')]);before=deepcopy((ir,r));o=augment(ir,r)
        self.assertEqual((ir,r),before);o.pop('temporal_observations_version')
        for b in o['boundaries']:b.pop('temporal_observations')
        self.assertEqual(o,r)

    def test_incomplete_cell_partition_rejected(self):
        with self.assertRaises(ValueError):support({'span':{'start':q(0),'end':q(3)},'members':[['C',0]]},[])

    def test_no_annotation_dependency(self):
        ir,r=fixture([('C4',0,3,'a')]);o=observe(ir,r,0);ir['annotations']=['V7/V']
        self.assertEqual(o,observe(ir,r,0))

    def test_abstention_preserved(self):
        ir,r=fixture([('C4',0,3,'a')]);r['boundaries'][0]['status']='no_spelled_comparison'
        self.assertEqual(observe(ir,r,0)['status'],'no_spelled_comparison')

    def test_overlapping_cells_cannot_hide_equal_length_gap(self):
        ir,r=fixture([('C4',0,3,'a')]);c=snapshot(r['events'],{'start':q(0),'end':q(1)},ir)
        other=deepcopy(c);other['span']={'start':q('1/2'),'end':q('3/2')}
        with self.assertRaises(ValueError):support({'span':{'start':q(0),'end':q(2)},'members':[['C',0]]},[c,other])

    def test_meter_at_barline_uses_new_measure(self):
        ir,r=fixture([('C4',0,3,'a')]);ir['measures']=[{'measure_id':'m1','printed_measure_number':'1','global_start_quarter':q(0),'actual_duration_quarter':q(1),'time_signature':{'beats':1,'beat_type':4}},
            {'measure_id':'m2','printed_measure_number':'2','global_start_quarter':q(1),'actual_duration_quarter':q(2),'time_signature':{'beats':4,'beat_type':8}}]
        m=meter_at(ir,q(1));self.assertEqual(m['measure_ref'],'m2');self.assertEqual(m['denominator_unit_quarters'],q('1/2'))

    def test_pattern_phase_cells_point_to_preparation_and_resolution(self):
        ir,r=fixture([('F4',0,2,'a'),('E4',2,3,'a'),('C3',0,3,'b')]);x,y=ir['sounding_events'][:2]
        r['boundaries'][0]['boundary_figures']={'patterns':[{'pattern_id':'p','event_refs':[x['sounding_event_id'],y['sounding_event_id']],
            'affected_event_ref':x['sounding_event_id'],'nonmember_span':{'start':q(1),'end':q(2)}}]}
        o=observe(ir,r,0);p=o['pattern_observations'][0]
        self.assertEqual(p['nonmember_cell_indices'],[1]);self.assertEqual([v['cell_index'] for v in p['event_onsets']],[0,2])
        self.assertEqual(o['cells'][1]['intervals_from_lowest'][0]['generic_interval'],11)

    def test_rhythm_scale_preserves_denominator_position(self):
        ir,r=fixture([('C4',0,3,'a')]);before=meter_at(ir,q('1/2'));small=deepcopy(ir)
        for m in small['measures']:
            for k in ('global_start_quarter','actual_duration_quarter','nominal_duration_quarter'):m[k]=q(f(m[k])/2)
            m['time_signature']['beat_type']*=2
        after=meter_at(small,q('1/4'))
        self.assertEqual(before['denominator_unit_position_zero_based'],after['denominator_unit_position_zero_based'])
