from copy import deepcopy
import unittest
from music21 import pitch
from test_harmony_bass import score, segment
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_bass import attach_bass, display_groups
from musicanote_harness.harmony_applied_context import attach_applied_context, applied_projection


def example(source=('C3','E4','Bb3'), target=('C3','F4','Ab3'), quality='dominant7', root=0, target_root=5, target_quality='minor', late=False):
    names=list(source)+list(target)
    specs=[(pitch.Pitch(n).midi,3 if late and i else 0,4,'v') for i,n in enumerate(source)]
    specs += [(pitch.Pitch(n).midi,4,5,'v') for n in target]
    ir=score(specs)
    for s,n in zip(ir['sounding_events'],names):
        p=pitch.Pitch(n)
        s['pitch'].update(step=p.step,alter=q(int(p.accidental.alter) if p.accidental else 0),spelling=p.nameWithOctave)
    result={'segments':[segment(root,quality,0,4),segment(target_root,target_quality,4,5)]}
    return ir,result


def run(ir,result):return attach_applied_context(ir,attach_bass(ir,result))


class AppliedContextTests(unittest.TestCase):
    def test_secondary_resolution_and_no_mutation(self):
        ir,result=example();before=deepcopy((ir,result));out=run(ir,result)
        self.assertEqual((ir,result),before)
        h=out['segments'][0]['applied_context_hypotheses'][0]
        self.assertEqual(h['status'],'resolution_supported_candidate')
        self.assertEqual(applied_projection(h,'c',0)['text'],'V7/iv')
        self.assertEqual(applied_projection(h,'c',1)['text'],'V65/iv')
        self.assertFalse(h['function_confirmed'])
        self.assertEqual(out['segments'][0]['selected'],result['segments'][0]['selected'])

    def test_late_critical_tones_not_backdated(self):
        ir,result=example(late=True);out=run(ir,result);s=out['segments'][0]
        self.assertEqual(s['span'],result['segments'][0]['span'])
        self.assertEqual(s['applied_context_hypotheses'][0]['support_span']['start'],q(3))
        self.assertFalse(s['bass_realization']['cells'][0].get('applied_context_refs'))
        self.assertEqual(len(display_groups(s)),2)

    def test_primary_and_no_key_do_not_get_secondary_display(self):
        ir,result=example();h=run(ir,result)['segments'][0]['applied_context_hypotheses'][0]
        self.assertIsNone(applied_projection(h,'f',0))
        self.assertIsNone(applied_projection(h,None,0))
        self.assertIsNone(applied_projection(h,'c',None))

    def test_plain_tonic_to_subdominant_not_automatically_secondary(self):
        ir,result=example(('C3','E4','G3'),('F3','F4','A3'),'major',target_quality='major')
        h=run(ir,result)['segments'][0]['applied_context_hypotheses'][0]
        self.assertIsNone(applied_projection(h,'C',0))

    def test_missing_leading_tone_abstains(self):
        ir,result=example(('C3','G3','Bb3'))
        self.assertEqual(run(ir,result)['segments'][0]['applied_context_hypotheses'],[])

    def test_wrong_enharmonic_spelling_abstains(self):
        ir,result=example(('C3','F-4','Bb3'))
        self.assertEqual(run(ir,result)['segments'][0]['applied_context_hypotheses'],[])

    def test_no_immediate_target_or_rest_abstains(self):
        ir,result=example();result['segments'][1]['span']['start']=q(4.5)
        self.assertEqual(run(ir,result)['segments'][0]['applied_context_hypotheses'],[])
        ir,result=example(target=('C3','E4','G3'),target_root=0,target_quality='major')
        self.assertEqual(run(ir,result)['segments'][0]['applied_context_hypotheses'],[])

    def test_target_third_not_yet_present_abstains(self):
        ir,result=example();ir['sounding_events'][-1]['span']['start']=q(4.5)
        self.assertEqual(run(ir,result)['segments'][0]['applied_context_hypotheses'],[])

    def test_non_resolving_register_is_shape_only(self):
        ir,result=example(target=('C3','F5','Ab3'))
        h=run(ir,result)['segments'][0]['applied_context_hypotheses'][0]
        self.assertEqual(h['status'],'shape_relation_only')
        self.assertIsNone(applied_projection(h,'c',0))

    def test_source_annotations_not_inputs(self):
        ir,result=example();before=run(ir,result)
        ir['annotations']=[{'roman':'N6','localkey':'D','pedal':'V'}]
        self.assertEqual(run(ir,result),before)

    def test_transposition_and_diminished_families(self):
        cases=[(('D3','F#4','C4'),('G3','G4','B3'),'dominant7',2,7,'major','C','V7/V'),
               (('F#4','A3','C4'),('G4','G3','B3'),'diminished',6,7,'major','C','viio/V'),
               (('F#4','A3','C4','Eb4'),('G4','G3','B3','D4'),'diminished7',6,7,'major','C','viio7/V'),
               (('F#4','A3','C4','E4'),('G4','G3','B3','D4'),'half-diminished7',6,7,'major','C','viiø7/V')]
        for src,dst,quality,root,tr,tq,key,expected in cases:
            ir,result=example(src,dst,quality,root,tr,tq)
            h=run(ir,result)['segments'][0]['applied_context_hypotheses'][0]
            self.assertEqual(applied_projection(h,key,0)['text'],expected)

    def test_projection_track_uses_only_support_span(self):
        from musicanote_harness.sonata_verification import projected_track
        ir,result=example(late=True);out=run(ir,result);out['engine_version']='test'
        track=projected_track(ir,out,[],'experiment','test',True)
        self.assertFalse(track['segments'][0]['applied_context_hypotheses'])
        self.assertTrue(track['segments'][1]['applied_context_hypotheses'])
        self.assertFalse(track['segments'][1]['applied_display']) # No borrowed reference key.

    def test_actual_engine_attaches_version(self):
        from musicanote_harness.harmony_multiscale_shadow import analyze
        ir,_=example();out=analyze(ir)
        self.assertEqual(out['applied_context_version'],'applied-context-bridge-0.1.0')
        self.assertTrue(all('applied_context_hypotheses' in s for s in out['segments']))


if __name__=='__main__':unittest.main()
