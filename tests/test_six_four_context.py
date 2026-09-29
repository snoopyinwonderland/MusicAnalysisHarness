import copy
import json
from pathlib import Path
import tempfile
import unittest
from musicanote_harness.formal_ir import q
from musicanote_harness.six_four_context import triad, source_triad, propose, assess_direct
from musicanote_harness.six_four_audit import windows, build
from musicanote_harness.harmony_curriculum import concepts
from test_cadential_six_four import fixture
from test_six_three_context import ann


def tags(r): return {x['role'] for x in r['role_candidates']}


class RoleTest(unittest.TestCase):
    def test_fifth_bass_spelling(self):
        for symbol,key,alter,mode,want in [('I','C',0,'major',['G',0]),('viio','C',0,'major',['F',0]),
                                          ('#viio','A',0,'minor',['D',0]),('III+','A',0,'minor',['G',1]),
                                          ('V','F',1,'major',['G',1])]:
            self.assertEqual(triad(symbol,2,key,alter,mode)['expected_bass_spelling'],want)

    def test_source_adapter_is_nonmutating_and_strict(self):
        a=ann('III+',0,1,'64','1'); saved=copy.deepcopy(a)
        self.assertEqual(source_triad(a),('III+',2)); self.assertEqual(a,saved)
        for f in ('changes','added_tones','relativeroot','pedal','special'):
            x=copy.deepcopy(a); x['raw_fields'][f]='x'; self.assertIsNone(source_triad(x))
        a['raw_fields']['figbass']='43'; self.assertIsNone(source_triad(a))

    def test_same_shape_different_roles(self):
        # C major 6/4 over G: passing IV6-I64-ii6 vs cadential candidate IV-I64-V.
        a=propose(['IV','I','ii'],[1,2,1],'C')
        b=propose(['IV','I','V'],[0,2,0],'C')
        self.assertIn('moving_bass_passing_six_four',tags(a))
        self.assertNotIn('stationary_bass_six_four_to_five_three',tags(a))
        self.assertIn('stationary_bass_six_four_to_five_three',tags(b))
        self.assertIsNone(b['cadence']); self.assertIsNone(b['selected_role'])

    def test_passing_v_in_both_directions(self):
        for inv in ([0,2,1],[1,2,0]):
            self.assertIn('moving_bass_passing_six_four',tags(propose(['I','V','I'],inv,'C')))

    def test_neighbor_does_not_require_weak_beat(self):
        r=propose(['I','IV','I'],[0,2,0],'C')
        x=next(x for x in r['role_candidates'] if x['role']=='stationary_bass_neighbor_six_four')
        self.assertFalse(x['weak_beat_required'])
        # It can also form 6/4->5/3 geometry; do not force a single functional role.
        self.assertIn('stationary_bass_six_four_to_five_three',tags(r))

    def test_nondominant_resolution(self):
        r=propose(['I','ii','vi'],[0,2,0],'C')
        x=next(x for x in r['role_candidates'] if x['role']=='stationary_bass_six_four_to_five_three')
        self.assertFalse(x['dominant_destination_candidate']); self.assertFalse(x['strong_beat_required'])

    def test_arpeggio_not_automatic_oscillation(self):
        r=propose(['I','I','I'],[0,2,0],'C')
        self.assertEqual(tags(r),{'bass_arpeggiation_or_retrospective_stability'})
        self.assertTrue(all(not x['oscillating_accompaniment_confirmed'] for x in r['role_candidates']))

    def test_diminished_alternative_keeps_literal(self):
        r=propose(['I','viio','I'],[0,2,1],'C')
        x=next(x for x in r['role_candidates'] if x['role']=='incomplete_dominant_four_two_alternative')
        self.assertEqual(x['alternative'],'V42_without_root')
        self.assertEqual(r['candidates'][1]['symbol'],'viio')
        self.assertIn('source_wording_conflict',x)

    def test_diminished_arpeggiation_does_not_imply_consonant_stability(self):
        r=propose(['IV','viio','viio'],[0,2,1],'C')
        self.assertNotIn('bass_arpeggiation_or_retrospective_stability',tags(r))

    def test_minor_and_transposition(self):
        self.assertIn('stationary_bass_six_four_to_five_three',tags(propose(['iv','i','V'],[0,2,0],'A',mode='minor')))
        self.assertEqual(tags(propose(['I','V','I'],[0,2,1],'C')),tags(propose(['I','V','I'],[0,2,1],'G',-1)))

    def test_no_role_is_not_rejection(self):
        r=propose(['iii','IV','vi'],[0,2,0],'C')
        self.assertEqual(r['role_candidates'],[]); self.assertIsNone(r['merge_recommended'])

    def test_invalid_input(self):
        for inv in ([0,2], [0,True,0],[0,3,0]):
            with self.assertRaises(ValueError): propose(['I','V','I'],inv,'C')


class MotionTest(unittest.TestCase):
    def test_key_free_geometry_and_input_immutable(self):
        ir=fixture(); saved=copy.deepcopy(ir); r=assess_direct(ir,0,1)
        self.assertTrue(r['direct_resolution_geometry_supported']); self.assertEqual(ir,saved)
        self.assertIsNone(r['cadence']); self.assertIsNone(r['functional_verdict'])
        self.assertEqual(r['metric_relation'],'unassessed')

    def test_nondominant_same_geometry(self):
        ir=fixture()
        pitches=[('A',0,2,45),('D',0,4,62),('F',0,4,65),('A',0,2,45),('C',0,4,60),('E',0,4,64)]
        for s,(step,alter,octave,midi) in zip(ir['sounding_events'],pitches):
            s['pitch']={'step':step,'alter':q(alter),'octave':octave,'midi_pitch':midi}
        r=assess_direct(ir,0,1); self.assertTrue(r['direct_resolution_geometry_supported'])
        self.assertIsNone(r['cadence'])

    def test_octave_bass_not_stationary(self):
        ir=fixture(); ir['sounding_events'][3]['pitch']['octave']-=1; ir['sounding_events'][3]['pitch']['midi_pitch']-=12
        r=assess_direct(ir,0,1); self.assertTrue(r['surface_pair_supported'])
        self.assertFalse(r['direct_resolution_geometry_supported'])

    def test_polyphonic_voice_abstains(self):
        ir=fixture()
        for n in ir['note_events']: n['voice_id']='v'
        r=assess_direct(ir,0,1); self.assertTrue(r['surface_pair_supported'])
        self.assertFalse(r['direct_resolution_geometry_supported']); self.assertEqual(r['ambiguous_voice_refs'],[['p','v']])

    def test_gap_and_intervening_event_not_direct(self):
        ir=fixture(); ir['sounding_events'][1]['span']['end']=q('1/2')
        self.assertFalse(assess_direct(ir,0,1)['direct_resolution_geometry_supported'])

    def test_tie_keeps_original_duration(self):
        ir=fixture(); ir['sounding_events'][0]['span']['end']=q(3); del ir['sounding_events'][3]
        r=assess_direct(ir,0,1); self.assertTrue(r['direct_resolution_geometry_supported'])
        self.assertEqual(r['events'][0]['original_span']['end'],q(3))
        self.assertEqual(r['bass_event_pairs'],[['s0','s0']])

    def test_enharmonic_changes_geometry(self):
        ir=fixture(); ir['sounding_events'][1]['pitch'].update(step='B',alter=q(1),octave=3)
        self.assertFalse(assess_direct(ir,0,1)['direct_resolution_geometry_supported'])

    def test_half_open_empty_and_rational_guards(self):
        self.assertFalse(assess_direct(fixture(),1,2)['surface_pair_supported'])
        for a,b in [(-1,1),(1,1),(0.0,1)]:
            with self.assertRaises(ValueError): assess_direct(fixture(),a,b)

    def test_duplicate_and_missing_reference_guards(self):
        for kind in ('note','sound','reference','negative'):
            ir=fixture()
            if kind=='note': ir['note_events'].append(ir['note_events'][0])
            if kind=='sound': ir['sounding_events'].append(ir['sounding_events'][0])
            if kind=='reference': ir['sounding_events'][0]['attack_note_id']='missing'
            if kind=='negative': ir['sounding_events'][0]['span']['end']=q(-1)
            with self.subTest(kind=kind),self.assertRaises(ValueError): assess_direct(ir,0,1)


class AuditTest(unittest.TestCase):
    def test_window_includes_nonmatches_and_preserves_barriers(self):
        base=[ann(s,i,i+1,'64' if i==1 else '') for i,s in enumerate(['iii','IV','vi'])]
        self.assertEqual(len(list(windows(base))),1)
        self.assertEqual(list(windows(base,{'0','2'})),[])
        for kind in ('gap','key','unsupported','no64'):
            a=copy.deepcopy(base)
            if kind=='gap': a[1]['target']['span']['start']=q('3/2')
            if kind=='key': a[1]['raw_fields']['globalkey']='G'
            if kind=='unsupported': a[1]['raw_fields']['figbass']='7'
            if kind=='no64': a[1]['raw_fields']['figbass']='6'
            self.assertEqual(list(windows(a)),[])

    def test_rights_holdout_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            with self.assertRaisesRegex(ValueError,'output_exists'): build('missing',p)
            e={'split':'holdout','work_family_id':'w','score_sha256':'s','annotation_sha256':'a',
               'collection_id':'mozart-sonatas','package_path':'missing','rights':{'internal_research_use':False}}
            m=p/'m.json';m.write_text(json.dumps({'entries':[e]}))
            self.assertEqual(build(m,p/'out')['summary']['case_count'],0)
            e['split']='train';m.write_text(json.dumps({'entries':[e]}))
            with self.assertRaisesRegex(ValueError,'research_not_permitted'):build(m,p/'bad')

    def test_catalog(self):
        u=next(x for x in concepts() if x['concept_id']=='hvl.unit20')
        self.assertEqual(u['reviewed_sections'],list(range(1,19)))
        self.assertEqual(u['rule_status'],'candidate_not_production')


if __name__=='__main__': unittest.main()
