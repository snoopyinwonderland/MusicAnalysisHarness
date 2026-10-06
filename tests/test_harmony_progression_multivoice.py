import unittest
from copy import deepcopy
from test_harmony_progression_resolution import fixture as base_fixture
from musicanote_harness.harmony_progression_resolution import analyze


def fixture(**kwargs):
    r,p,ir=base_fixture(**kwargs)
    # The original test had hand-supplied links; explicitly encode those voices here.
    ir['note_events'][6]['voice_id']='3'
    ir['note_events'][7]['voice_id']='2'
    return r,p,ir


class MultiVoiceTests(unittest.TestCase):
    def test_separate_voices_support_two_relations(self):
        r,p,ir=fixture(return_ir=True)
        old=analyze(r,p,'none');new=analyze(r,p,'none',ir=ir)
        self.assertEqual(old['relations'][0]['status'],'shape_relation_only')
        self.assertEqual(new['relations'][0]['status'],'direct_resolution_supported_hypothesis')
        self.assertEqual(len(new['relations'][0]['voice_evidence']),2)
        self.assertTrue(all(e['assignment_ref'] is None for e in new['relations'][0]['voice_evidence']))

    def test_wrong_direction_stays_shape(self):
        r,p,ir=fixture(wrong=True,return_ir=True)
        self.assertEqual(analyze(r,p,'none',ir=ir)['relations'][0]['status'],'shape_relation_only')

    def test_polyphonic_xml_voice_not_guessed(self):
        r,p,ir=fixture(return_ir=True)
        for n in ir['note_events']:n['voice_id']='shared'
        a=analyze(r,p,'linked',ir=ir)
        self.assertEqual(a['relations'][0]['status'],'shape_relation_only')
        self.assertFalse(a['voice_diagnostics']['links'])

    def test_missing_voice_not_filled_from_sampled_links(self):
        r,p,ir=fixture(return_ir=True)
        for n in ir['note_events']:n['voice_id']=None
        a=analyze(r,p,'linked',ir=ir)
        self.assertEqual(a['relations'][0]['status'],'shape_relation_only')

    def test_cross_staff_same_explicit_voice_allowed(self):
        r,p,ir=fixture(return_ir=True)
        for n in ir['note_events'][4:]:n['staff_id']='other-staff'
        self.assertEqual(analyze(r,p,'none',ir=ir)['relations'][0]['status'],'direct_resolution_supported_hypothesis')

    def test_wrong_ir_rejected(self):
        r,p,ir=fixture(return_ir=True);ir=deepcopy(ir)
        ir['sounding_events'][0]['pitch']['midi_pitch']+=1
        with self.assertRaisesRegex(ValueError,'identity_mismatch'):analyze(r,p,'none',ir=ir)

    def test_missing_event_rejected(self):
        r,p,ir=fixture(return_ir=True);ir=deepcopy(ir);ir['sounding_events'].pop()
        with self.assertRaisesRegex(ValueError,'coverage_mismatch'):analyze(r,p,'none',ir=ir)

    def test_input_unchanged(self):
        r,p,ir=fixture(return_ir=True);saved=deepcopy((r,ir))
        analyze(r,p,'linked',ir=ir);self.assertEqual((r,ir),saved)


if __name__=='__main__':unittest.main()
