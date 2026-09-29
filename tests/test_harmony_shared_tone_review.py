from copy import deepcopy
from fractions import Fraction as F
import unittest
from music21 import pitch
from test_harmony_joint import fixture as base_ir
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_joint import f
from musicanote_harness.harmony_shared_tone_trial import fixture,KINDS
from musicanote_harness.harmony_shared_tone_review import observe
from musicanote_harness.harmony_figure_trial import fixture_xml
from xml.etree import ElementTree as ET


def make_ir(kind,transpose=0,scale=F(1)):
    c=fixture(kind,transpose,scale)
    ir=base_ir([(int(pitch.Pitch(e['pitch']).midi),f(e['start']),f(e['start'])+f(e['duration']),e['voice']) for e in c['events']])
    ir['measures'][0].update(actual_duration_quarter=q(4*scale),time_signature={'beat_type':c['beat_type']})
    for s,e in zip(ir['sounding_events'],c['events']):
        p=pitch.Pitch(e['pitch']);s['pitch'].update(step=p.step,alter=q(int(p.accidental.alter) if p.accidental else 0),spelling=p.nameWithOctave)
    return ir


class SharedToneTests(unittest.TestCase):
    def test_keeps_both_readings_and_event_refs(self):
        ir=make_ir('shared_rearticulated');result=observe(ir);self.assertEqual(len(result['alternatives']),7)
        ids={s['sounding_event_id'] for s in ir['sounding_events']}
        c=result['alternatives'][0]
        self.assertEqual(c['merged_seventh'][0]['segments'][0]['candidate']['label'],'C:major7')
        self.assertEqual([s['candidate']['label'] for s in c['split_triads'][0]['segments']],['C:major','E:minor'])
        self.assertIsNone(c['selected_hypothesis']);self.assertLessEqual(set(c['event_refs']),ids)
        self.assertTrue(c['new_member_attack_refs']);self.assertTrue(c['old_member_release_refs'])

    def test_same_notes_different_intentions_have_same_evidence(self):
        self.assertEqual(observe(make_ir(KINDS[0])),observe(make_ir(KINDS[1])))

    def test_sustained_common_tones_are_not_new_attacks(self):
        c=observe(make_ir('shared_sustained_common'))['alternatives'][0]
        self.assertEqual(len(c['sustained_common_event_refs']),2)
        self.assertTrue(c['bass']['continued_refs']);self.assertFalse(c['bass']['new_attack_refs'])

    def test_seventh_pedal_block_arpeggio_are_not_split(self):
        for kind in KINDS[3:6]:self.assertEqual(observe(make_ir(kind))['alternatives'],[],kind)

    def test_disjoint_change_outside_this_detector(self):
        self.assertEqual(observe(make_ir('disjoint_change'))['alternatives'],[])

    def test_duration_relative_to_meter(self):
        base=observe(make_ir(KINDS[0]))['alternatives']
        scaled=observe(make_ir(KINDS[0],scale=F(1,2)))['alternatives']
        self.assertEqual(len(base),len(scaled))
        for a,b in zip(base,scaled):
            self.assertEqual(f(a['boundary'])/2,f(b['boundary']))
            self.assertAlmostEqual(a['split_minus_merge_cost'],b['split_minus_merge_cost'])
        ir=make_ir(KINDS[0],scale=F(1,2));ir['measures'][0]['time_signature']['beat_type']=4
        self.assertEqual(observe(ir)['alternatives'],[])

    def test_transposition(self):
        base=observe(make_ir(KINDS[0]))['alternatives'];tr=observe(make_ir(KINDS[0],transpose=2))['alternatives']
        self.assertEqual(len(base),len(tr))
        for a,b in zip(base,tr):
            self.assertEqual(sorted((x+2)%12 for x in a['common_pitch_classes']),b['common_pitch_classes'])
            self.assertAlmostEqual(a['split_minus_merge_cost'],b['split_minus_merge_cost'])

    def test_exact_cost_decomposition(self):
        for c in observe(make_ir(KINDS[0]))['alternatives']:
            for kind in ('merged_seventh','split_triads'):
                for path in c[kind]:
                    total=sum(sum(s['cost_parts'].values()) for s in path['segments'])+sum(path.get('transition_parts',{}).values())
                    self.assertAlmostEqual(total,path['local_cost'])
            self.assertAlmostEqual(c['split_minus_merge_cost'],c['split_triads'][0]['local_cost']-c['merged_seventh'][0]['local_cost'])

    def test_input_immutable_and_labels_ignored(self):
        ir=make_ir(KINDS[0]);copy=deepcopy(ir);base=observe(ir)
        self.assertEqual(ir,copy)
        self.assertEqual(base,observe({**ir,'annotations':['I7'],'phrases':['split']}))

    def test_window_does_not_invent_truncated_blocks(self):
        result=observe(make_ir(KINDS[0]),{'start':q(F(1,4)),'end':q(F(7,4))})
        self.assertEqual([f(c['boundary']) for c in result['alternatives']],[F(1)])

    def test_mixed_meter_pair_is_deferred(self):
        ir=make_ir(KINDS[0]);ir['measures'].append({'global_start_quarter':q(F(1,2)),
            'actual_duration_quarter':q(F(7,2)),'time_signature':{'beat_type':8}})
        self.assertNotIn(F(1,2),[f(c['boundary']) for c in observe(ir)['alternatives']])

    def test_empty_and_invalid_span(self):
        self.assertEqual(observe({'sounding_events':[]})['alternatives'],[])
        for a,b in [(-1,2),(2,2),(2,1)]:
            with self.assertRaises(ValueError):observe(make_ir(KINDS[0]),{'start':q(a),'end':q(b)})

    def test_whole_note_pedal_fixture_notation(self):
        root=ET.fromstring(fixture_xml(fixture('seventh_root_pedal')))
        pedal=root.find(".//note[voice='3']")
        self.assertEqual(pedal.findtext('type'),'whole')
        self.assertEqual(pedal.findtext('duration'),'32')
        root=ET.fromstring(fixture_xml(fixture('seventh_root_pedal',scale=F(1,2))))
        self.assertEqual(root.find(".//note[voice='3']").findtext('type'),'half')

    def test_gate_audit_accounts_for_all_contained_pairs(self):
        for kind in KINDS:
            audit=observe(make_ir(kind))['gate_audit']
            self.assertEqual(audit['fully_contained_adjacent_pairs'],audit['accepted']+sum(audit['first_failed_gate'].values()))


if __name__=='__main__':unittest.main()
