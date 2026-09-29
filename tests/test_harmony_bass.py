from copy import deepcopy
import unittest
from music21 import pitch
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_bass import attach_bass, display_groups
from musicanote_harness.harmony_visual_review import roman_projection
from musicanote_harness.harmony_surface import TEMPLATES
from test_harmony_joint import fixture


def score(specs):
    ir=fixture(specs)
    for s in ir['sounding_events']:
        p=pitch.Pitch(s['pitch']['midi_pitch'])
        s['pitch'].update(step=p.step,alter=q(int(p.accidental.alter) if p.accidental else 0),spelling=p.nameWithOctave)
    return ir


def segment(root,quality,a,b):
    return {'span':{'start':q(a),'end':q(b)},'selected':{'root':root,'label':f'C:{quality}',
        'pcs':[(root+x)%12 for x in dict(TEMPLATES)[quality]]},'beat_unit_quarter':q(1),'alternatives':[]}


class BassRealizationTests(unittest.TestCase):
    def test_all_triads_and_seventh_inversions_transpose(self):
        for root in (0,2,7):
            for quality,template in TEMPLATES:
                # Enharmonic spellings need deliberate chord-member spelling.
                for ix in range(len(template)):
                    pitches=[48+root+template[ix]]+[72+root+t for t in template]
                    ir=score([(p,0,1,str(i)) for i,p in enumerate(pitches)])
                    # Build correct tertian spelling via music21's root chord spelling helper.
                    from musicanote_harness.harmony_candidate_explanation import NATURAL
                    rootstep=pitch.Pitch(60+root).step
                    for s in ir['sounding_events']:
                        factor=template.index((s['pitch']['midi_pitch']-root)%12)
                        step='CDEFGAB'[('CDEFGAB'.index(rootstep)+2*factor)%7]
                        alter=((s['pitch']['midi_pitch']%12-NATURAL[step]+6)%12)-6
                        octave=(s['pitch']['midi_pitch']-NATURAL[step]-alter)//12-1
                        s['pitch'].update(step=step,alter=q(alter),spelling=step+('#'*alter if alter>0 else '-'*(-alter))+str(octave))
                    out=attach_bass(ir,{'segments':[segment(root,quality,0,1)]})
                    self.assertEqual(out['segments'][0]['bass_realization']['cells'][0]['inversion_index'],ix,(root,quality,ix))

    def test_single_melody_not_confident_inversion(self):
        ir=score([(60,0,1,'v'),(64,1,2,'v'),(67,2,3,'v')])
        out=attach_bass(ir,{'segments':[segment(0,'major',0,3)]})
        self.assertTrue(all(c['inversion_index'] is None for c in out['segments'][0]['bass_realization']['cells']))

    def test_nonchord_bass_abstains(self):
        ir=score([(50,0,1,'b'),(60,0,1,'u'),(64,0,1,'v'),(67,0,1,'w')])
        cell=attach_bass(ir,{'segments':[segment(0,'major',0,1)]})['segments'][0]['bass_realization']['cells'][0]
        self.assertEqual(cell['status'],'bass_outside_candidate')

    def test_pedal_is_alternative_not_replacement(self):
        ir=score([(48,0,6,'b'),(64,0,2,'a'),(67,0,2,'v'),(65,2,4,'a'),(69,2,4,'v'),(64,4,6,'a'),(67,4,6,'v')])
        result={'segments':[segment(0,'major',0,2),segment(5,'major',2,4),segment(0,'major',4,6)]}
        before=deepcopy((ir,result));out=attach_bass(ir,result)
        self.assertEqual((ir,result),before)
        self.assertEqual(len(out['pedal_hypotheses']),1)
        middle=out['segments'][1]['bass_realization']['cells'][0]
        self.assertEqual(middle['inversion_index'],2)
        self.assertEqual(middle['upper_if_pedal_excluded']['inversion_index'],0)
        self.assertEqual(out['pedal_hypotheses'][0]['status'],'candidate_not_confirmed')
        self.assertFalse(out['pedal_hypotheses'][0]['uses_source_annotation'])

    def test_single_chord_repeated_bass_is_not_pedal_hypothesis(self):
        ir=score([(48,0,6,'b'),(64,0,6,'v'),(67,0,6,'w')])
        result={'segments':[segment(0,'major',i,i+2) for i in (0,2,4)]}
        self.assertFalse(attach_bass(ir,result)['pedal_hypotheses'])

    def test_silence_breaks_pedal(self):
        ir=score([(48,0,2,'b'),(64,0,2,'v'),(48,3,4,'b'),(65,3,4,'v'),(48,5,6,'b'),(67,5,6,'v')])
        r={'segments':[segment(0,'major',0,2),segment(5,'major',2,4),segment(0,'major',4,6)]}
        self.assertFalse(attach_bass(ir,r)['pedal_hypotheses'])

    def test_inversion_change_does_not_change_parent_harmony(self):
        ir=score([(48,0,1,'b'),(52,1,2,'b'),(60,0,2,'u'),(64,0,2,'v'),(67,0,2,'w')])
        s=attach_bass(ir,{'segments':[segment(0,'major',0,2)]})['segments'][0]
        self.assertEqual(len(display_groups(s)),2)
        self.assertEqual(s['span'],{'start':q(0),'end':q(2)})

    def test_roman_uses_calculated_second_inversion_and_keeps_legacy(self):
        ir=score([(55,0,1,'b'),(60,0,1,'u'),(64,0,1,'v')]);s=segment(0,'major',0,1)
        cell=attach_bass(ir,{'segments':[s]})['segments'][0]['bass_realization']['cells'][0]
        self.assertEqual(roman_projection(ir,s['span'],s['selected'],'C',cell)['text'],'I64')
        self.assertEqual(roman_projection(ir,s['span'],s['selected'],'C')['text'],'I')
        self.assertEqual(roman_projection(ir,s['span'],s['selected'],'C',{'inversion_index':None,'status':'sparse'})['text'],'unknown')

    def test_source_annotations_do_not_influence_bass(self):
        ir=score([(48,0,1,'b'),(64,0,1,'u'),(67,0,1,'v')]);r={'segments':[segment(0,'major',0,1)]}
        a=attach_bass(ir,r);ir['annotations']=[{'pedal':'V','chord':'V6'}]
        self.assertEqual(a,attach_bass(ir,r))

    def test_engine_calls_bass_analysis(self):
        from musicanote_harness.harmony_multiscale_shadow import analyze
        result=analyze(score([(52,0,2,'b'),(60,0,2,'u'),(67,0,2,'v')]))
        self.assertIn('bass_realization_version',result)
        self.assertEqual(result['segments'][0]['bass_realization']['cells'][0]['inversion_index'],1)

    def test_unsupported_spelling_does_not_guess(self):
        ir=score([(52,0,1,'b'),(60,0,1,'u'),(67,0,1,'v')])
        ir['sounding_events'][0]['pitch'].pop('alter')
        s=attach_bass(ir,{'segments':[segment(0,'major',0,1)]})['segments'][0]
        self.assertIsNone(s['bass_realization']['cells'][0]['inversion_index'])

    def test_sustained_tie_has_no_invented_attack(self):
        ir=score([(52,0,2,'b'),(60,0,1,'u'),(67,1,2,'v')])
        s=attach_bass(ir,{'segments':[segment(0,'major',0,2)]})['segments'][0]
        self.assertEqual([c['bass_event_refs'] for c in s['bass_realization']['cells']],[['s0'],['s0']])
        self.assertEqual(len(display_groups(s)),1)

    def test_seventh_figured_bass_not_triads(self):
        ir=score([(53,0,1,'b'),(55,0,1,'u'),(59,0,1,'v'),(62,0,1,'w')]);s=segment(7,'dominant7',0,1)
        cell=attach_bass(ir,{'segments':[s]})['segments'][0]['bass_realization']['cells'][0]
        self.assertEqual(roman_projection(ir,s['span'],s['selected'],'C',cell)['text'],'V2')

    def test_no_silence_inversion(self):
        ir=score([]);s=attach_bass(ir,{'segments':[segment(0,'major',0,1)]})['segments'][0]
        self.assertEqual(s['bass_realization']['cells'][0]['status'],'silence')
