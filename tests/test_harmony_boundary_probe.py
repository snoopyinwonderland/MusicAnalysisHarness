import unittest
from fractions import Fraction
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_boundary_probe import probe


def fixture():
    specs=[(48,0,4,'b'),(67,0,4,'i'),(60,0,1,'v'),(62,1,Fraction(3,2),'v'),(64,Fraction(3,2),4,'v')]
    return {'note_events':[{'note_id':f'n{i}','voice_id':v} for i,(_,_,_,v) in enumerate(specs)],
            'sounding_events':[{'sounding_event_id':f's{i}','attack_note_id':f'n{i}',
               'pitch':{'midi_pitch':p,'spelling':str(p)},'span':{'start':q(a),'end':q(b)}}
               for i,(p,a,b,_) in enumerate(specs)]}


class BoundaryProbeTest(unittest.TestCase):
    def test_attack_carry_release_are_distinct(self):
        r=probe(fixture(),0,1,4)
        self.assertEqual({x['sounding_event_id'] for x in r['attacked']},{'s3'})
        self.assertEqual({x['sounding_event_id'] for x in r['carried']},{'s0','s1'})
        self.assertEqual({x['sounding_event_id'] for x in r['released']},{'s2'})

    def test_keep_and_change_both_recorded(self):
        r=probe(fixture(),0,1,4)
        self.assertIsNotNone(r['best_continue']);self.assertIsNotNone(r['best_change'])
        self.assertIsNone(r['automatically_selected'])
        self.assertTrue(any(h['nct'] for alt in r['ranked_alternatives'] for h in alt['hypotheses']))

    def test_source_labels_do_not_change_output(self):
        ir=fixture();a=probe(ir,0,1,4);ir['annotations']=['V7'];ir['phrases']=['end']
        self.assertEqual(a,probe(ir,0,1,4))

    def test_outside_context_is_not_used(self):
        ir=fixture();a=probe(ir,0,1,4)
        ir['sounding_events'].append({'sounding_event_id':'future','pitch':{'midi_pitch':65},
             'span':{'start':q(4),'end':q(5)}})
        self.assertEqual(a,probe(ir,0,1,4))

    def test_invalid_boundary(self):
        with self.assertRaises(ValueError):probe(fixture(),0,0,4)


if __name__=='__main__':unittest.main()
