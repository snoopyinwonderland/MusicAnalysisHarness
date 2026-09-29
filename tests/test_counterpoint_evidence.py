import unittest
from copy import deepcopy
from musicanote_harness.counterpoint_evidence import melodic_geometry, extract
from musicanote_harness.formal_ir import q
from fractions import Fraction


def fixture():
    notes=[];sounds=[]
    for i,(step,midi) in enumerate([('C',60),('D',62),('E',64)]):
        notes.append({'note_id':str(i),'voice_id':'v1'})
        sounds.append({'sounding_event_id':'s'+str(i),'attack_note_id':str(i),
                       'pitch':{'step':step,'alter':q(0),'octave':4,'midi_pitch':midi},
                       'span':{'start':q(i),'end':q(i+1)}})
    return {'ir_document_id':'test','note_events':notes,'sounding_events':sounds}


class CounterpointTest(unittest.TestCase):
    def test_passing_and_neighbor(self):
        self.assertEqual(melodic_geometry([('C',0,4),('D',0,4),('E',0,4)])['pattern'],'passing_geometry')
        self.assertEqual(melodic_geometry([('F',0,4),('E',0,4),('F',0,4)])['pattern'],'neighbor_geometry')

    def test_chromatic_spelling(self):
        self.assertEqual(melodic_geometry([('D',0,4),('D',1,4),('E',0,4)])['pattern'],'chromatic_passing_geometry')
        self.assertIsNone(melodic_geometry([('C',0,4),('C',2,4),('E',0,4)])['pattern'])

    def test_octave_not_neighbor_return(self):
        self.assertIsNone(melodic_geometry([('C',0,4),('D',0,4),('C',0,5)])['pattern'])

    def test_long_notes_not_discarded(self):
        ir=fixture()
        for s in ir['sounding_events']:
            for k in ('start','end'):
                s['span'][k]['numerator'] *= 4
        result=extract(ir)['records'][0]
        self.assertIsNone(result['nct_label'])
        self.assertEqual(result['durations'],[q(4)]*3)

    def test_label_independent(self):
        ir=fixture();other=deepcopy(ir)
        other['annotations']=[{'label':'V7'}];other['phrases']=[{'start':0}]
        self.assertEqual(extract(ir),extract(other))

    def test_gap_and_overlap_abstain(self):
        for endpoint in (Fraction(1,2),Fraction(3,2)):
            ir=fixture();ir['sounding_events'][0]['span']['end']=q(endpoint)
            self.assertEqual(extract(ir)['records'],[])

    def test_polyphonic_attack_abstains(self):
        ir=fixture();duplicate=deepcopy(ir['sounding_events'][1]);duplicate['sounding_event_id']='chord'
        ir['sounding_events'].append(duplicate)
        self.assertEqual(extract(ir)['records'],[])

    def test_transposition(self):
        self.assertEqual(melodic_geometry([('F',1,4),('G',1,4),('A',1,4)])['pattern'],'passing_geometry')


if __name__ == '__main__':unittest.main()
