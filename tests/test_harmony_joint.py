import unittest
from fractions import Fraction
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_joint import analyze_joint, candidates, prepare


def fixture(specs):
    return {"note_events": [{"note_id": f"n{i}", "voice_id": v} for i, (p,a,b,v) in enumerate(specs)],
            "sounding_events": [{"sounding_event_id": f"s{i}", "attack_note_id": f"n{i}",
                "pitch": {"midi_pitch": p, "spelling": str(p)}, "span": {"start": q(a), "end": q(b)}}
                for i,(p,a,b,v) in enumerate(specs)],
            "measures": [{"global_start_quarter": q(0), "actual_duration_quarter": q(4),
                          "time_signature": {"beat_type": 4}}]}


class JointTest(unittest.TestCase):
    def test_sequential_chord_tones_form_one_chord(self):
        ir = fixture([(60,0,1,'v'), (64,1,2,'v'), (67,2,3,'v'), (64,3,4,'v')])
        out = analyze_joint(ir)
        self.assertEqual(len(out['segments']), 1)
        self.assertEqual(out['segments'][0]['selected']['label'], 'C:major')

    def test_passing_tone_is_conditional_and_does_not_create_chord_change(self):
        ir = fixture([(48,0,4,'bass'), (67,0,4,'inner'), (60,0,1,'v'),
                      (62,1,Fraction(3,2),'v'), (64,Fraction(3,2),4,'v')])
        rows, neighbors = prepare(ir)
        c = next(c for c in candidates(rows,neighbors,Fraction(0),Fraction(4),Fraction(1)) if c['label']=='C:major')
        self.assertEqual(c['nct'][0]['type'], 'passing_like')
        self.assertEqual(analyze_joint(ir)['segments'][0]['selected']['label'], 'C:major')

    def test_seventh_is_not_removed_as_nct(self):
        ir = fixture([(55,0,4,'b'),(59,0,4,'v1'),(62,0,4,'v2'),(65,0,4,'v3')])
        c = analyze_joint(ir)['segments'][0]['selected']
        self.assertEqual(c['label'], 'G:dominant7')
        self.assertEqual(c['nct'], [])

    def test_clear_chord_change_is_preserved(self):
        ir = fixture([(p,a,b,f'v{i}') for a,b,ps in [(0,2,[48,52,55]),(2,4,[55,59,62])] for i,p in enumerate(ps)])
        self.assertEqual([s['selected']['label'] for s in analyze_joint(ir)['segments']], ['C:major','G:major'])

    def test_source_and_phrase_labels_do_not_influence_output(self):
        ir = fixture([(60,0,4,'b'),(64,0,4,'v'),(67,0,4,'w')])
        self.assertEqual(analyze_joint(ir), analyze_joint({**ir,'annotations':[{'label':'V'}], 'phrases':[{'end':1}]}))

if __name__ == '__main__':
    unittest.main()
