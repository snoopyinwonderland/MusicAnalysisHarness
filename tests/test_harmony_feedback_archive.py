from copy import deepcopy
import unittest
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_feedback_archive import context_measures,cells


def fixture():
    return {'measures':[{'measure_id':'m'+str(i),'printed_measure_number':str(i),'sequential_measure_index':i,
        'global_start_quarter':q((i-1)*4),'actual_duration_quarter':q(4),'time_signature':{'beats':2,'beat_type':2}} for i in range(1,5)],
        'sounding_events':[{'sounding_event_id':'a','span':{'start':q(3),'end':q(6)},'pitch':{'spelling':'C4','midi_pitch':60}},
            {'sounding_event_id':'b','span':{'start':q(5),'end':q(7)},'pitch':{'spelling':'G3','midi_pitch':55}}]}


class FeedbackArchiveTests(unittest.TestCase):
    def test_context_and_input_unchanged(self):
        ir=fixture();before=deepcopy(ir)
        self.assertEqual([m['printed_measure_number'] for m in context_measures(ir,['2','3'])],['1','2','3','4'])
        self.assertEqual(ir,before)
    def test_reject_ambiguous_printed_number(self):
        ir=fixture();ir['measures'][1]['printed_measure_number']='1'
        with self.assertRaises(ValueError):context_measures(ir,['1'])
    def test_reject_missing(self):
        with self.assertRaises(ValueError):context_measures(fixture(),['99'])
    def test_sustain_is_not_new_attack(self):
        r=cells(fixture(),fixture()['measures'][1])
        self.assertEqual(r[0]['active_event_refs'],['a']);self.assertEqual(r[0]['attacked_event_refs'],[])
        self.assertEqual(r[1]['active_event_refs'],['b','a']);self.assertEqual(r[1]['lowest_sounding_pitch'],'G3')
        self.assertEqual(r[1]['denominator_beat'],q(1.5))
        self.assertEqual(r[-1]['active_event_refs'],[])
