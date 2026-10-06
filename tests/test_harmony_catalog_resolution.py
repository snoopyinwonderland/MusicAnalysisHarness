from copy import deepcopy
from fractions import Fraction as F
import unittest
from test_harmony_open_candidates import score
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_candidate_catalog import propose
from musicanote_harness.harmony_catalog_resolution import compare


def fixture(added=False, wrong=False, late=False):
    rows = [('D3',0,2,'bass'), ('F#4',1 if late else 0,2,'lead'),
            ('A4',0,2,'fifth'), ('C5',0,2,'seventh'),
            ('G3',2,4,'bass'), ('E4' if wrong else 'G4',2,4,'lead'),
            ('D5',2,4,'fifth'), ('B4',2,4,'seventh')]
    if added:
        rows += [('E5',0,2,'ninth'), ('D5',2,4,'ninth')]
    return score(rows)


def catalogs(ir, a=0, b=2, c=4):
    return propose(ir, {'start':q(a),'end':q(b)}), propose(ir, {'start':q(b),'end':q(c)})


def chosen(result, provider='base', family='V7', root=('G',0)):
    return next(e for e in result['edges'] if e['source_provider']==provider
                and e['target_provider']=='base' and e['target_root']==list(root)
                and e['target_quality']=='M' and e['family']==family
                and not e['target_missing_spellings'])


class CatalogResolutionTests(unittest.TestCase):
    def test_display_uses_selected_spelling_not_pitch_class_catalog_name(self):
        from musicanote_harness.harmony_catalog_resolution_trial import label
        ir=score([('D#3',0,2,'a'),('F#3',0,2,'b'),('A3',0,2,'c'),
                  ('E3',2,4,'a'),('G#3',2,4,'b'),('B3',2,4,'c')])
        left,right=catalogs(ir)
        edge=chosen(compare(ir,left,right),family='vii',root=('E',0))
        candidate=next(c for c in left['candidates'] if c['candidate_id']==edge['source_candidate_ref'])
        self.assertEqual(label(left,candidate,edge['source_alternative_index']),'D#:diminished')

    def test_secondary_core_has_two_actual_voice_paths(self):
        ir=fixture();r=compare(ir,*catalogs(ir));e=chosen(r)
        self.assertEqual(e['status'],'resolution_supported_hypothesis')
        self.assertEqual(e['missing_direct_relations'],[])
        self.assertEqual(e['key_projections'],[])
        self.assertFalse(e['function_confirmed'])

    def test_key_hypotheses_separate_primary_and_applied(self):
        ir=fixture();keys=[{'key_id':k,'tonic':[k,0],'mode':'major','provenance':'test_hypothesis'} for k in ('C','G')]
        e=chosen(compare(ir,*catalogs(ir),keys));a,b=e['key_projections']
        self.assertEqual(a['symbol_without_inversion'],'V7/V')
        self.assertEqual(b['symbol_without_inversion'],'V7')
        self.assertEqual(b['relation_to_key'],'primary_target_hypothesis')

    def test_extended_candidate_keeps_its_own_origin_and_missing_notes(self):
        ir=fixture(added=True);l,r=catalogs(ir);e=chosen(compare(ir,l,r),'extended')
        self.assertEqual(e['status'],'resolution_supported_hypothesis')
        self.assertIn(e['source_candidate_ref'],[c['candidate_id'] for c in l['candidates'] if c['provider']=='extended'])

    def test_minor_major_seventh_can_be_target_without_becoming_dominant(self):
        ir=score([('G3',0,2,'b'),('B3',0,2,'l'),('D4',0,2,'f'),('F4',0,2,'s'),
                  ('C3',2,4,'b'),('C4',2,4,'l'),('G4',2,4,'f'),('E-4',2,4,'s'),('B4',2,4,'x')])
        l,r=catalogs(ir);result=compare(ir,l,r)
        self.assertTrue(any(e['target_provider']=='additional_seventh' and e['status']=='resolution_supported_hypothesis' for e in result['edges']))
        self.assertEqual(result['candidate_refs'],[[c['candidate_id'] for c in cat['candidates']] for cat in (l,r)])

    def test_late_chromatic_tone_does_not_extend_support_backwards(self):
        ir=fixture(late=True);e=chosen(compare(ir,*catalogs(ir)))
        self.assertEqual(e['source_time']['terminal_support_span'],{'start':q(1),'end':q(2)})
        self.assertEqual(e['source_span']['start'],q(0))

    def test_wrong_direction_keeps_shape_but_not_resolution(self):
        ir=fixture(wrong=True);e=chosen(compare(ir,*catalogs(ir)))
        self.assertEqual(e['status'],'shape_relation_only')
        self.assertIn('leading_tone_to_target_root',e['missing_direct_relations'])

    def test_enharmonic_wrong_spelling_does_not_get_secondary_edge(self):
        ir=score([('D3',0,2,'b'),('G-4',0,2,'l'),('A4',0,2,'f'),('C5',0,2,'s'),
                  ('G3',2,4,'b'),('G4',2,4,'l'),('D5',2,4,'f'),('B4',2,4,'s')])
        result=compare(ir,*catalogs(ir))
        self.assertFalse(any(e['family']=='V7' and e['target_root']==['G',0] for e in result['edges']))

    def test_polyphonic_voice_does_not_guess_connections(self):
        ir=fixture()
        for n in ir['note_events']:n['voice_id']='one'
        e=chosen(compare(ir,*catalogs(ir)))
        self.assertEqual(e['direct_voice_support'],[])
        self.assertEqual(e['status'],'shape_relation_only')

    def test_missing_third_extension_remains_shape_only(self):
        ir=score([('D3',0,2,'b'),('A4',0,2,'f'),('C5',0,2,'s'),('G4',0,2,'x'),
                  ('G3',2,4,'b'),('D5',2,4,'f'),('B4',2,4,'s'),('G4',2,4,'x')])
        e=chosen(compare(ir,*catalogs(ir)),'extended')
        self.assertEqual(e['status'],'shape_relation_only')
        self.assertIn(['F',1],e['source_missing_spellings'])

    def test_rest_inside_window_blocks_context_not_candidate_list(self):
        ir=fixture()
        for s in ir['sounding_events']:
            if s['span']['end']==q(2):s['span']['end']=q(1)
        l,r=catalogs(ir);e=chosen(compare(ir,l,r))
        self.assertEqual(e['status'],'blocked_context')
        self.assertIn('silence_inside_window',e['abstention_reasons'])

    def test_repeat_at_join_blocks_context(self):
        ir=fixture();m=ir['measures'][0];m['actual_duration_quarter']=q(2)
        m['repeat_barline']={'location':'right','repeat_direction':'backward'}
        ir['measures'].append({**deepcopy(m),'global_start_quarter':q(2),'repeat_barline':{}})
        e=chosen(compare(ir,*catalogs(ir)))
        self.assertEqual(e['status'],'blocked_context')
        self.assertIn('repeat_barrier',e['abstention_reasons'])

    def test_nonadjacent_inputs_rejected(self):
        ir=fixture();l,_=catalogs(ir);r=propose(ir,{'start':q(3),'end':q(4)})
        with self.assertRaisesRegex(ValueError,'adjacent_windows'):compare(ir,l,r)

    def test_stale_score_catalog_rejected(self):
        ir=fixture();l,r=catalogs(ir);ir['sounding_events'][0]['span']['end']=q(1)
        with self.assertRaisesRegex(ValueError,'catalog_does_not_match_score'):compare(ir,l,r)

    def test_no_mutation_label_leakage_or_shared_output(self):
        ir=fixture();l,r=catalogs(ir);old=deepcopy((ir,l,r));out=compare(ir,l,r)
        self.assertEqual((ir,l,r),old)
        ir['annotations']=[{'label':'wrong'}];ir['phrases']=[{'end':1}]
        self.assertEqual(compare(ir,l,r),out)
        out['edges'][0]['source_span']['end']=q(99)
        self.assertEqual(l,old[1])

    def test_metre_scaling_keeps_support(self):
        ir=fixture(late=True);small=deepcopy(ir)
        for s in small['sounding_events']:s['span']={k:q(fraction(v)/2) for k,v in s['span'].items()}
        small['measures'][0]['actual_duration_quarter']=q(2)
        small['measures'][0]['time_signature']['beat_type']=8
        e=chosen(compare(small,*catalogs(small,0,1,2)))
        self.assertEqual(e['status'],'resolution_supported_hypothesis')
        self.assertEqual(e['source_time']['terminal_support_span']['start'],q(F(1,2)))

    def test_unattributed_key_is_rejected(self):
        ir=fixture()
        with self.assertRaisesRegex(ValueError,'unattributed'):compare(ir,*catalogs(ir),[{'key_id':'x','mode':'major','tonic':['C',0]}])

    def test_diatonic_tonic_to_subdominant_not_excluded_by_accidental_gate(self):
        ir=score([('C3',0,2,'b'),('E4',0,2,'l'),('G4',0,2,'f'),('F3',2,4,'b'),('F4',2,4,'l'),('A4',2,4,'f'),('C5',2,4,'x')])
        e=chosen(compare(ir,*catalogs(ir),[{'key_id':'c','tonic':['C',0],'mode':'major','provenance':'test'}]),family='V',root=('F',0))
        self.assertEqual(e['key_projections'][0]['chromatic_core_spellings'],[])
        self.assertFalse(e['function_confirmed'])

    def test_held_critical_tone_is_not_a_new_resolution_attack(self):
        ir=fixture();ir['sounding_events'][1]['span']['end']=q(3)
        e=chosen(compare(ir,*catalogs(ir)))
        self.assertNotEqual(e['status'],'resolution_supported_hypothesis')


def fraction(qvalue):return F(qvalue['numerator'],qvalue['denominator'])
