import copy
import json
from pathlib import Path
import tempfile
import unittest
from musicanote_harness.formal_ir import q
from musicanote_harness.mixture_evidence import templates, source_candidate, observe
from musicanote_harness.mixture_audit import build
from musicanote_harness.harmony_curriculum import concepts


def fixture(rows):
    ir={'note_events':[],'sounding_events':[]}
    for i,(step,alter,octave,start,end,voice) in enumerate(rows):
        ir['note_events'].append({'note_id':f'n{i}','part_id':'p','voice_id':voice,'display_staff_id':'s'})
        ir['sounding_events'].append({'sounding_event_id':f'e{i}','attack_note_id':f'n{i}','source_note_ids':[f'n{i}'],
            'pitch':{'step':step,'alter':q(alter),'octave':octave,
                     'midi_pitch':12*(octave+1)+{'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}[step]+alter},
            'span':{'start':q(start),'end':q(end)}})
    return ir


def run(ir,mode='major',end=2):
    return observe(ir,{'start':q(0),'end':q(end)},{'start':q(0),'end':q(4)},'C',0,mode)


def coverage(o,name):return next(c for c in o['template_coverage'] if c['hypothesis']['family']==name)


class MixtureTest(unittest.TestCase):
    def test_borrowed_triads_and_sevenths_spelling(self):
        t={x['family']:x for x in templates('C')}
        self.assertEqual(t['minor_subdominant']['members'],[['F',0],['A',-1],['C',0]])
        self.assertEqual(t['half_diminished_supertonic']['members'],[['D',0],['F',0],['A',-1],['C',0]])
        self.assertEqual(t['lowered_submediant']['members'],[['A',-1],['C',0],['E',-1]])

    def test_secondary_mixture_not_secondary_dominant(self):
        t={x['family']:x for x in templates('C')}
        self.assertEqual(t['major_mediant']['members'],[['E',0],['G',1],['B',0]])
        self.assertEqual(t['major_mediant']['mixture_type_hypothesis'],'secondary')
        self.assertFalse(t['major_mediant']['selected'])

    def test_transposition_preserves_spelling(self):
        t=templates('D',-1)
        self.assertEqual(t[1]['members'],[['G',-1],['B',-2],['D',-1]])

    def test_minor_major_tonic_not_picardy_automatic(self):
        ir=fixture([('C',0,3,0,1,'v1'),('E',0,4,0,1,'v2'),('G',0,4,0,1,'v3')]);o=run(ir,'minor')
        self.assertTrue(coverage(o,'major_tonic_in_minor')['complete_vertical_matches'])
        self.assertIsNone(o['picardy_third']);self.assertIsNone(o['cadence'])

    def test_minor_raised_six_seven_not_mixture_proof(self):
        o=run(fixture([('A',0,4,0,1,'v'),('B',0,4,1,2,'v')]),'minor')
        self.assertTrue(all(e['coordinate_tags']==['ordinary_minor_scale_variant_not_mixture_proof'] for e in o['events']))

    def test_single_borrowed_tone_not_chord_or_modulation(self):
        o=run(fixture([('A',-1,4,0,1,'v')]))
        self.assertEqual(o['events'][0]['coordinate_tags'],['parallel_minor_pitch_compatible'])
        self.assertFalse(any(c['complete_vertical_matches'] for c in o['template_coverage']))
        self.assertIsNone(o['modulation']);self.assertIsNone(o['mixture_confirmed'])

    def test_diatonic_negative_control(self):
        o=run(fixture([('C',0,4,0,1,'v1'),('E',0,4,0,1,'v2'),('G',0,4,0,1,'v3')]))
        self.assertFalse(any(c['complete_vertical_matches'] for c in o['template_coverage']))

    def test_arpeggio_union_not_vertical(self):
        o=run(fixture([('F',0,3,0,1,'v'),('A',-1,3,1,2,'v'),('C',0,4,2,3,'v')]),end=3)
        c=coverage(o,'minor_subdominant');self.assertEqual(c['missing_spellings'],[])
        self.assertEqual(c['complete_vertical_matches'],[]);self.assertFalse(c['union_is_simultaneous'])

    def test_inversion_from_actual_lowest(self):
        o=run(fixture([('F',0,4,0,1,'v1'),('A',-1,3,0,1,'v2'),('C',0,4,0,1,'v3')]))
        self.assertEqual(coverage(o,'minor_subdominant')['complete_vertical_matches'][0]['inversion'],1)

    def test_extra_pitch_preserved_not_discarded_as_nct(self):
        o=run(fixture([('F',0,3,0,1,'v1'),('A',-1,3,0,1,'v2'),('C',0,4,0,1,'v3'),('D',0,4,0,1,'v4')]))
        c=coverage(o,'minor_subdominant');self.assertEqual(c['complete_vertical_matches'],[])
        self.assertEqual(c['extra_event_refs'],['e3'])

    def test_natural_flat_six_five_path(self):
        o=run(fixture([('A',0,4,0,1,'v'),('A',-1,4,1,2,'v'),('G',0,4,2,3,'v')]))
        self.assertEqual(o['coordinate_paths'][0]['geometry_tags'],['entry_same_voice_chromatic_inflection','lowered_degree_descending_step'])

    def test_flat_six_natural_six_not_style_violation(self):
        o=run(fixture([('A',-1,4,0,1,'v'),('A',0,4,1,2,'v')]))
        self.assertEqual(o['coordinate_paths'][0]['geometry_tags'],['same_voice_chromatic_inflection'])
        self.assertIsNone(o['coordinate_paths'][0]['nct_verdict'])

    def test_flat_third_to_second(self):
        o=run(fixture([('E',-1,4,0,1,'v'),('D',0,4,1,2,'v')]))
        self.assertIn('lowered_degree_descending_step',o['coordinate_paths'][0]['geometry_tags'])

    def test_enharmonic_augmented_fifth_not_flat_six(self):
        o=run(fixture([('G',1,4,0,1,'v')]))
        self.assertEqual(o['events'][0]['degree'],5);self.assertEqual(o['coordinate_paths'],[])

    def test_polyphony_abstains(self):
        o=run(fixture([('A',-1,4,0,1,'v'),('C',0,5,0,1,'v'),('G',0,4,1,2,'v')]))
        self.assertEqual(o['coordinate_paths'][0]['departure_status'],'ambiguous_voice')

    def test_gap_and_other_voice_not_bridged(self):
        for rows in [[('A',-1,4,0,1,'v'),('G',0,4,2,3,'v')],[('A',-1,4,0,1,'v'),('G',0,4,1,2,'w')]]:
            self.assertEqual(run(fixture(rows))['coordinate_paths'][0]['departure_status'],'no_touching_event')

    def test_cross_staff_and_immutable(self):
        ir=fixture([('A',-1,4,0,1,'v'),('G',0,4,1,2,'v')]);ir['note_events'][1]['display_staff_id']='other';saved=copy.deepcopy(ir)
        self.assertEqual(run(ir)['coordinate_paths'][0]['departure_status'],'direct');self.assertEqual(ir,saved)

    def test_full_tie_span_and_half_open(self):
        ir=fixture([('A',-1,4,0,3,'v'),('G',0,4,3,4,'v')]);o=run(ir)
        self.assertEqual(o['events'][0]['original_span']['end'],q(3))
        self.assertEqual(len(o['events']),1)

    def test_invalid_inputs(self):
        for k in ('float','negative','ref','duplicate'):
            ir=fixture([('A',-1,4,0,1,'v')])
            if k=='float':ir['sounding_events'][0]['span']['end']=1.0
            if k=='negative':ir['sounding_events'][0]['span']['end']=q(-1)
            if k=='ref':ir['sounding_events'][0]['source_note_ids']=['missing']
            if k=='duplicate':ir['sounding_events'].append(copy.deepcopy(ir['sounding_events'][0]))
            with self.assertRaises(ValueError):run(ir)

    def test_grace_excluded(self):
        ir=fixture([('A',-1,4,0,0,'v')]);ir['note_events'][0]['grace']={'is_grace':True}
        self.assertEqual(run(ir)['excluded_grace_event_ids'],['e0'])

    def test_source_adapter_strict_figures_and_no_applied(self):
        a={'raw_fields':{'localkey_is_minor':'0','numeral':'III','form':'','chord_type':'M','figbass':'6'}}
        self.assertEqual(source_candidate(a),('major_mediant',1))
        for k,v in [('relativeroot','vi'),('changes','2'),('chord_type','m'),('figbass','7')]:
            b=copy.deepcopy(a);b['raw_fields'][k]=v;self.assertIsNone(source_candidate(b))

    def test_catalog(self):
        self.assertEqual(next(c for c in concepts() if c['concept_id']=='hvl.unit24')['reviewed_sections'],list(range(1,9)))

    def test_rights_guard_before_package_access(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'manifest.json';p.write_text(json.dumps({'entries':[{'split':'train','collection_id':'mozart-sonatas',
                'package_path':'not-to-open','rights':{'internal_research_use':False},'work_family_id':'x',
                'score_sha256':'s','annotation_sha256':'a'}]}))
            with self.assertRaisesRegex(ValueError,'research_not_permitted'):build(p,Path(td)/'out')


if __name__=='__main__':unittest.main()
