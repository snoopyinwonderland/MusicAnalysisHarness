import copy
import unittest
from musicanote_harness.cadential_six_four import assess
from musicanote_harness.formal_ir import q


def fixture(minor=False):
    pitches = [('G',0,2),('C',0,4),('E',-1 if minor else 0,4),
               ('G',0,2),('B',0,3),('D',0,4)]
    natural = {'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}
    ir = {'note_events': [], 'sounding_events': []}
    for i,(s,a,o) in enumerate(pitches):
        nid = 'n'+str(i)
        ir['note_events'].append({'note_id':nid,'voice_id':'v'+str(i%3),'part_id':'p'})
        ir['sounding_events'].append({'sounding_event_id':'s'+str(i),'attack_note_id':nid,
            'source_note_ids':[nid],'pitch':{'step':s,'alter':q(a),'octave':o,
            'midi_pitch':12*(o+1)+natural[s]+a},'span':{'start':q(i//3),'end':q(i//3+1)}})
    return ir


class CadentialSixFourTest(unittest.TestCase):
    def test_complete_geometry_not_cadence(self):
        ir=fixture(); saved=copy.deepcopy(ir)
        r=assess(ir,q(0),q(1),'C')
        self.assertTrue(r['surface_pair_supported'])
        self.assertTrue(r['direct_resolution_geometry_supported'])
        self.assertIsNone(r['cadence']); self.assertIsNone(r['functional_verdict'])
        self.assertEqual(r['metric_relation'],'unassessed'); self.assertEqual(ir,saved)

    def test_minor(self):
        self.assertTrue(assess(fixture(True),0,1,'C',mode='minor')['direct_resolution_geometry_supported'])

    def test_enharmonic_is_not_degree1(self):
        ir=fixture(); p=ir['sounding_events'][1]['pitch']; p.update(step='B',alter=q(1),octave=3)
        self.assertFalse(assess(ir,0,1,'C')['surface_pair_supported'])

    def test_polyphonic_voice_not_strand(self):
        ir=fixture()
        for n in ir['note_events']: n['voice_id']='v'
        r=assess(ir,0,1,'C')
        self.assertTrue(r['surface_pair_supported']); self.assertFalse(r['direct_resolution_geometry_supported'])
        self.assertEqual(r['ambiguous_voice_refs'],[['p','v']])

    def test_octave_bass_displacement(self):
        ir=fixture(); p=ir['sounding_events'][3]['pitch']; p['octave']=1; p['midi_pitch']-=12
        self.assertTrue(assess(ir,0,1,'C')['direct_resolution_geometry_supported'])

    def test_rest_gap_not_direct_resolution(self):
        ir=fixture(); ir['sounding_events'][1]['span']['end']=q('1/2')
        self.assertFalse(assess(ir,0,1,'C')['direct_resolution_geometry_supported'])

    def test_half_open_and_held_note(self):
        ir=fixture(); ir['sounding_events'][0]['span']['end']=q(2); del ir['sounding_events'][3]
        r=assess(ir,0,1,'C'); l,h=r['observations']
        self.assertIn('s0',h['event_refs']); self.assertNotIn('s1',h['event_refs'])
        self.assertTrue(r['direct_resolution_geometry_supported'])

    def test_six_to_seven(self):
        ir=fixture(); p=ir['sounding_events'][5]['pitch']; p.update(step='F',midi_pitch=65)
        r=assess(ir,0,1,'C')
        self.assertEqual(r['observations'][1]['dominant_shape'],'V7_missing_fifth')
        self.assertTrue(r['direct_resolution_geometry_supported'])

    def test_transposition(self):
        from music21 import pitch
        ir=fixture()
        for s in ir['sounding_events']:
            p=pitch.Pitch(); p.midi=s['pitch']['midi_pitch']; p=p.transpose(2)
            s['pitch']={'step':p.step,'alter':q(int(p.accidental.alter) if p.accidental else 0),
                        'octave':p.octave,'midi_pitch':p.midi}
        self.assertTrue(assess(ir,0,1,'D')['direct_resolution_geometry_supported'])

    def test_six_four_to_four_two_is_not_root_bass_resolution(self):
        ir=fixture(); ir['sounding_events'][3]['pitch'].update(step='F',midi_pitch=41)
        r=assess(ir,0,1,'C')
        self.assertTrue(r['observations'][0]['complete_tonic_six_four_shape'])
        self.assertFalse(r['surface_pair_supported']); self.assertIsNone(r['cadence'])

    def test_unidentified_voice_not_invented(self):
        ir=fixture()
        for n in ir['note_events']: n.pop('voice_id')
        r=assess(ir,0,1,'C')
        self.assertTrue(r['surface_pair_supported']); self.assertEqual(r['motion_evidence'],[])
        self.assertFalse(r['direct_resolution_geometry_supported'])

    def test_invalid_input(self):
        with self.assertRaises(ValueError): assess(fixture(),1,0,'C')
        ir=fixture(); ir['sounding_events'][0]['pitch']['midi_pitch']=0
        with self.assertRaises(ValueError): assess(ir,0,1,'C')
        ir=fixture(); ir['sounding_events'][0]['attack_note_id']='missing'
        with self.assertRaises(ValueError): assess(ir,0,1,'C')
