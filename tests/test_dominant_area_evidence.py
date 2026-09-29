import copy
import json
from pathlib import Path
import tempfile
import unittest
from musicanote_harness.formal_ir import q
from musicanote_harness.dominant_area_evidence import observe, dominant_reference
from musicanote_harness.dominant_area_audit import applied_anchor, dominant_regions, build
from musicanote_harness.harmony_curriculum import concepts


def span(a=0, b=1):
    return {'start': q(a), 'end': q(b)}


def score(pitches):
    return {'sounding_events': [{'sounding_event_id': str(i), 'span': span(),
            'pitch': {'step': s, 'alter': q(a), 'octave': o,
                      'midi_pitch': 12*(o+1)+dict(C=0,D=2,E=4,F=5,G=7,A=9,B=11)[s]+a}}
            for i, (s,a,o) in enumerate(pitches)]}


class DualReferenceTest(unittest.TestCase):
    def test_fifths_preserve_spelling(self):
        for home, target in [(('C',0),('G',0)),(('F',0),('C',0)),(('B',-1),('F',0)),
                             (('F',1),('C',1)),(('C',-1),('G',-1)),(('B',1),('F',2))]:
            self.assertEqual(dominant_reference(*home),target)

    def test_raised_fourth_is_not_always_sharp_sign(self):
        r=observe(score([('B',0,4),('B',-1,4)]),span(),'F')
        self.assertEqual(r['raised_fourth_event_refs'],['0'])
        self.assertEqual(r['unaltered_fourth_event_refs'],['1'])
        self.assertEqual(r['event_coordinates'][0]['dominant_area']['degree'],7)
        self.assertIsNone(r['modulation'])

    def test_enharmonic_not_same_scale_degree(self):
        r=observe(score([('F',1,4),('G',-1,4)]),span(),'C')
        self.assertEqual(r['raised_fourth_event_refs'],['0'])
        self.assertEqual(r['event_coordinates'][1]['home']['degree'],5)

    def test_common_chord_is_not_pivot(self):
        r=observe(score([('C',0,4),('E',0,4),('G',0,4)]),span(),'C')
        s=r['shared_diatonic_triad_slices'][0]['shapes'][0]
        self.assertEqual(s['root_coordinates']['home']['degree'],1)
        self.assertEqual(s['root_coordinates']['dominant_area']['degree'],4)
        self.assertIsNone(r['pivot_span'])
        self.assertIsNone(r['shared_diatonic_triad_slices'][0]['pivot_verified'])

    def test_vi_can_be_target_ii(self):
        r=observe(score([('A',0,3),('C',0,4),('E',0,4)]),span(),'C')
        s=r['shared_diatonic_triad_slices'][0]['shapes'][0]
        self.assertEqual(s['root_coordinates']['home']['degree'],6)
        self.assertEqual(s['root_coordinates']['dominant_area']['degree'],2)

    def test_home_iv_not_diatonic_in_dominant(self):
        r=observe(score([('F',0,3),('A',0,3),('C',0,4)]),span(),'C')
        self.assertEqual(r['shared_diatonic_triad_slices'],[])

    def test_arpeggio_not_collapsed_into_vertical(self):
        ir=score([('C',0,4),('E',0,4),('G',0,4)])
        for i,s in enumerate(ir['sounding_events']):s['span']=span(i,i+1)
        self.assertEqual(observe(ir,span(0,3),'C')['shared_diatonic_triad_slices'],[])

    def test_half_open_tie_and_no_mutation(self):
        ir=score([('F',1,4),('C',0,4)])
        ir['sounding_events'][0]['span']=span(0,3)
        ir['sounding_events'][1]['span']=span(2,3)
        before=copy.deepcopy(ir);r=observe(ir,span(1,2),'C')
        self.assertEqual(r['held_at_start_ids'],['0'])
        self.assertEqual(len(r['event_coordinates']),1)
        self.assertEqual(ir,before)

    def test_no_length_threshold(self):
        ir=score([('G',0,4)])
        ir['sounding_events'][0]['span']=span(0,1000)
        r=observe(ir,span(0,1000),'C')
        self.assertIsNone(r['key_area']);self.assertIsNone(r['modulation'])

    def test_invalid_inputs(self):
        with self.assertRaisesRegex(ValueError,'major_home'):observe(score([]),span(),'C',mode='minor')
        with self.assertRaisesRegex(ValueError,'rational_time'):observe(score([]),{'start':0.0,'end':1},'C')
        ir=score([('C',0,4)]);ir['sounding_events'][0]['pitch']['midi_pitch']=61
        with self.assertRaisesRegex(ValueError,'spelling_midi'):observe(ir,span(),'C')


class AuditTest(unittest.TestCase):
    def test_applied_scope(self):
        a={'raw_fields':{'numeral':'V','form':'','figbass':'65','chord_type':'Mm7','relativeroot':'V','localkey_is_minor':'0'}}
        self.assertTrue(applied_anchor(a))
        a['raw_fields']['relativeroot']='ii';self.assertFalse(applied_anchor(a))
        a['raw_fields'].update(numeral='vii',form='o',figbass='6',chord_type='o',relativeroot='V')
        self.assertTrue(applied_anchor(a))
        a['raw_fields'].update(figbass='7',chord_type='o7');self.assertFalse(applied_anchor(a))

    def test_region_gaps_and_home_changes(self):
        def a(start,end,local='V',home='C'):
            return {'raw_fields':{'globalkey':home,'localkey':local,'localkey_is_minor':'0'},'target':{'span':span(start,end)}}
        xs=[a(0,1),a(1,2),a(2,3,'I'),a(3,4),a(5,6),a(6,7,home='G'),a(7,8,home='c')]
        self.assertEqual(dominant_regions(xs),[[0,1],[3],[4],[5]])

    def test_rights_holdout_overwrite(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)
            with self.assertRaisesRegex(ValueError,'output_exists'):build('missing',p)
            e={'split':'holdout','work_family_id':'w','score_sha256':'s','annotation_sha256':'a',
               'collection_id':'mozart-sonatas','package_path':'missing','rights':{'internal_research_use':False}}
            m=p/'m.json';m.write_text(json.dumps({'entries':[e]}))
            self.assertEqual(build(m,p/'out')['summary']['case_count'],0)
            e['split']='train';m.write_text(json.dumps({'entries':[e]}))
            with self.assertRaisesRegex(ValueError,'research_not_permitted'):build(m,p/'other')

    def test_catalog(self):
        u=next(r for r in concepts() if r['concept_id']=='hvl.unit15')
        self.assertEqual(u['reviewed_sections'],list(range(1,14)))
        self.assertEqual(u['rule_status'],'candidate_not_production')


if __name__=='__main__':unittest.main()
