import unittest
from fractions import Fraction
from musicanote_harness.formal_ir import q
from musicanote_harness.foundation_sonata_audit import inspect_span, compare


def fixture(arpeggio=False):
    specs=[('C',60),('E',64),('G',67)]
    return {'note_events':[{'note_id':f'n{i}','voice_id':f'v{i}'} for i in range(3)],
            'sounding_events':[{'sounding_event_id':f's{i}','source_note_ids':[f'n{i}'],
                'pitch':{'step':step,'alter':q(0),'octave':4,'midi_pitch':midi},
                'span':{'start':q(i if arpeggio else 0),'end':q(i+1 if arpeggio else 3)}}
                for i,(step,midi) in enumerate(specs)]}


class SonataAuditTest(unittest.TestCase):
    def test_vertical_and_distributed_not_conflated(self):
        span={'start':q(0),'end':q(3)}
        a=inspect_span(fixture(),span);b=inspect_span(fixture(True),span)
        self.assertTrue(a['union_shapes']);self.assertTrue(b['union_shapes'])
        self.assertTrue(a['slices'][0]['shapes'])
        self.assertTrue(all(not s['shapes'] for s in b['slices']))

    def test_label_does_not_enter_features(self):
        ir=fixture();span={'start':q(0),'end':q(3)}
        before=inspect_span(ir,span);ir['harmony']='wrong'
        self.assertEqual(before,inspect_span(ir,span))

    def test_no_false_accuracy_claim(self):
        obs=inspect_span(fixture(),{'start':q(0),'end':q(3)})
        c=compare({'raw_fields':{'chord_type':'M','figbass':''}},obs)
        self.assertEqual(c['quality_inversion_agreement_duration_ratio'],1)
        self.assertFalse(c['root_compared']);self.assertFalse(c['harmonic_accuracy_measured'])

    def test_rational_slice_and_midi_mismatch(self):
        ir=fixture(True);span={'start':q(Fraction(1,3)),'end':q(Fraction(8,3))}
        obs=inspect_span(ir,span)
        self.assertEqual(obs['slices'][0]['start'],q(Fraction(1,3)))
        ir['sounding_events'][0]['pitch']['midi_pitch']=61
        with self.assertRaises(ValueError):inspect_span(ir,span)


if __name__=='__main__':unittest.main()
