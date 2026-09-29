import unittest
from copy import deepcopy
from fractions import Fraction
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_joint import prepare, candidates, analyze_joint
from musicanote_harness.harmony_context_shadow import provider, analyze


def score():
    ir={'ir_document_id':'fixture','note_events':[],'sounding_events':[],'measures':[]}
    for i,(step,pitch,start,end,voice) in enumerate([
        ('C',60,0,2,'bass'),('G',67,0,2,'inner'),
        ('E',64,0,Fraction(1,2),'melody'),('F',65,Fraction(1,2),1,'melody'),
        ('E',64,1,2,'melody')]):
        ir['note_events'].append({'note_id':str(i),'voice_id':voice})
        ir['sounding_events'].append({'sounding_event_id':str(i),'attack_note_id':str(i),
            'pitch':{'step':step,'alter':q(0),'octave':4,'midi_pitch':pitch},
            'span':{'start':q(start),'end':q(end)}})
    return ir


class ShadowTest(unittest.TestCase):
    def test_default_provider_preserved(self):
        ir=score()
        self.assertEqual(analyze_joint(ir),analyze_joint(ir,candidate_provider=candidates))

    def test_geometry_used_on_member_and_nonmember(self):
        ir=score();choose,_=provider(ir);rows,neighbors=prepare(ir)
        result=choose(rows,neighbors,Fraction(0),Fraction(2),Fraction(1),limit=None)
        evidence=[e for c in result for e in c.get('context_evidence',[])]
        self.assertEqual({e['member_under_candidate'] for e in evidence},{True,False})

    def test_annotations_not_inputs_and_ir_not_mutated(self):
        ir=score();saved=deepcopy(ir)
        a=analyze(ir);self.assertEqual(ir,saved)
        ir['annotations']=[{'label':'V7'}];ir['phrases']=[{'start':0}]
        self.assertEqual(a,analyze(ir))

    def test_sustained_seventh_not_penalized_as_ornament(self):
        ir=score()
        for s in ir['sounding_events']:s['span']={'start':q(0),'end':q(2)}
        choose,geometry=provider(ir)
        self.assertEqual(geometry['records'],[])
        rows,neighbors=prepare(ir)
        for c in choose(rows,neighbors,Fraction(0),Fraction(2),Fraction(1)):
            self.assertAlmostEqual(c['cost'],c['baseline_local_cost'])

    def test_empty_score(self):
        ir={'ir_document_id':'empty','note_events':[],'sounding_events':[]}
        self.assertEqual(analyze(ir)['segments'],[])


if __name__=='__main__':unittest.main()
