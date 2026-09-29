import copy
from fractions import Fraction
import json
from pathlib import Path
import tempfile
import unittest
from musicanote_harness.diatonic_modulation import (
    triads, key_relation, memberships, harmonic_roles, compare_context,
    source_key_transitions, observe_support)
from musicanote_harness.diatonic_modulation_audit import build
from musicanote_harness.seventh_context import chord
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_curriculum import concepts

C=('C',0,'major');G=('G',0,'major');CM=('C',0,'minor')


def row(i,h=None,key=G):
    return {'ref':str(i),'span':{'start':q(i),'end':q(i+1)},'key':key,
            'verified':True,'hypothesis':h}


def progression():return [row(i,c) for i,c in enumerate([chord(['A',0],'m'),chord(['D',0],'Mm7'),chord(['G',0],'M')])]


def fixture(arpeggio=False):
    ir={'note_events':[],'sounding_events':[]}
    for i,(s,a) in enumerate([('C',0),('E',0),('G',0)]):
        ir['note_events'].append({'note_id':f'n{i}'})
        ir['sounding_events'].append({'sounding_event_id':f'e{i}','source_note_ids':[f'n{i}'],'attack_note_id':f'n{i}',
            'pitch':{'step':s,'alter':q(a),'octave':4,'midi_pitch':{'C':60,'E':64,'G':67}[s]},
            'span':{'start':q(Fraction(i,3) if arpeggio else 0),'end':q(Fraction(i+1,3) if arpeggio else 2)}})
    return ir


class ModulationTest(unittest.TestCase):
    def test_major_five_related_goals(self):
        goals=[(t['chord']['root'],t['chord']['quality']) for t in triads(C) if t['degree']!=1 and t['chord']['quality'] in ('M','m')]
        self.assertEqual(goals,[(['D',0],'m'),(['E',0],'m'),(['F',0],'M'),(['G',0],'M'),(['A',0],'m')])

    def test_minor_natural_goals(self):
        self.assertEqual(key_relation(CM,('G',0,'minor'))['relation'],'closely_related_diatonic_goal')
        self.assertEqual(key_relation(CM,G)['relation'],'outside_diatonic_goal_profile')
        self.assertEqual(key_relation(CM,('E',-1,'major'))['degree_in_old_natural_form'],3)

    def test_same_parallel_remote(self):
        self.assertEqual(key_relation(C,C)['relation'],'same_key')
        self.assertEqual(key_relation(C,CM)['relation'],'parallel_mode_not_diatonic_goal')
        self.assertEqual(key_relation(C,('F',1,'major'))['relation'],'outside_diatonic_goal_profile')

    def test_enharmonic_not_collapsed(self):
        self.assertEqual(key_relation(('D',-1,'major'),('G',-1,'major'))['relation'],'closely_related_diatonic_goal')
        self.assertEqual(key_relation(('D',-1,'major'),('F',1,'major'))['relation'],'outside_diatonic_goal_profile')

    def test_invalid_key(self):
        for key in [('C',0,'dorian'),('C',True,'major'),('C',0.5,'major')]:
            with self.assertRaises(ValueError):triads(key)

    def test_harmonic_minor_named_separately(self):
        m=memberships(chord(['G',0],'M'),CM)
        self.assertEqual([r['form'] for r in m],['harmonic_minor'])

    def test_common_chord_not_pivot(self):
        r=compare_context([row(0,chord(['A',0],'m'))],C,G)
        self.assertTrue(r['rows'][0]['common_triad_compatible']);self.assertIsNone(r['pivot'])
        self.assertEqual(r['rows'][0]['old_memberships'][0]['degree'],6)
        self.assertEqual(r['rows'][0]['new_memberships'][0]['degree'],2)

    def test_seventh_core_not_common_triad(self):
        r=compare_context([row(0,chord(['A',0],'mm7'))],C,G)
        self.assertFalse(r['rows'][0]['common_triad_compatible'])
        self.assertFalse(r['rows'][0]['new_memberships'][0]['full_triad'])

    def test_pd_d_t_not_cadence_or_modulation(self):
        r=compare_context(progression(),C,G)
        self.assertEqual(r['predominant_dominant_tonic_shape_triples'],[['0','1','2']])
        for k in ('modulation','tonicization','cadence'):self.assertIsNone(r[k])

    def test_no_pivot_prerequisite(self):
        r=compare_context([row(0,chord(['D',0],'Mm7')),row(1,chord(['G',0],'M'))],('D',-1,'major'),G)
        self.assertEqual(r['dominant_tonic_shape_pairs'],[['0','1']])
        self.assertFalse(any(x['common_triad_compatible'] for x in r['rows']))

    def test_tonic64_not_arrival(self):
        rs=progression();rs[-1]['hypothesis']=chord(['G',0],'M',2)
        self.assertEqual(compare_context(rs,C,G)['dominant_tonic_shape_pairs'],[])

    def test_source_half_cadence_not_replaced_by_authentic(self):
        rs=progression();rs[1]['source_cadence']='HC'
        r=compare_context(rs,C,G)
        self.assertEqual(r['source_cadence_markers'],[{'ref':'1','source_label':'HC'}])
        self.assertIsNone(r['cadence'])

    def test_silence_not_filled_by_annotation(self):
        r=observe_support(fixture(),{'start':q(0),'end':q(4)},chord(['C',0],'M'))
        self.assertEqual(r['silent_spans'],[{'start':q(2),'end':q(4)}])

    def test_dominant43_accepted_64_not(self):
        self.assertIn('dominant_shape',harmonic_roles(chord(['D',0],'Mm7',2),G))
        self.assertNotIn('dominant_shape',harmonic_roles(chord(['D',0],'M',2),G))

    def test_minor_dominant_not_strong_dominant(self):
        self.assertNotIn('dominant_shape',harmonic_roles(chord(['G',0],'m'),CM))
        self.assertIn('predominant_shape',harmonic_roles(chord(['D',0],'%7',1),CM))

    def test_unknown_never_skipped(self):
        rs=progression();rs[1]['hypothesis']=None
        r=compare_context(rs,C,G);self.assertIsNone(r['rows'][1]['new_key_role_candidates'])
        self.assertEqual(r['predominant_dominant_tonic_shape_triples'],[])

    def test_gap_overlap_break(self):
        for end in (Fraction(3,2),Fraction(5,2)):
            rs=progression();rs[1]['span']['end']=q(end)
            r=compare_context(rs,C,G)
            self.assertEqual(r['dominant_tonic_shape_pairs'],[]);self.assertEqual(len(r['timeline_breaks']),1)

    def test_rational_and_input_validation(self):
        rs=progression();saved=copy.deepcopy(rs);compare_context(rs,C,G);self.assertEqual(rs,saved)
        for r in rs:r['span']={k:q(Fraction(v['numerator'],3)) for k,v in r['span'].items()}
        self.assertEqual(len(compare_context(rs,C,G)['dominant_tonic_shape_pairs']),1)
        with self.assertRaises(ValueError):compare_context(list(reversed(rs)),C,G)
        rs[0]['span']['start']=0.0
        with self.assertRaises(ValueError):compare_context(rs,C,G)

    def test_duplicate_refs(self):
        rs=[row(0),row(0)]
        with self.assertRaises(ValueError):compare_context(rs,C,G)
        with self.assertRaises(ValueError):source_key_transitions(rs)

    def test_run_duration_not_modulation(self):
        rs=[row(0,key=C),row(1),row(2),row(3,key=C)]
        result=source_key_transitions(rs)
        self.assertEqual(len(result),2);self.assertEqual(result[0]['duration_quarters'],q(2))
        self.assertEqual(result[0]['annotation_refs'],['1','2'])
        self.assertFalse(result[0]['is_modulation_ground_truth'])
        self.assertEqual(result[0]['next_key'],C)

    def test_unverified_gap_not_source_transition(self):
        rs=[row(0,key=C),row(1),row(2)]
        rs[1]['verified']=False
        self.assertEqual(source_key_transitions(rs),[])
        rs[1]['verified']=True;rs[1]['span']['start']=q(Fraction(3,2))
        self.assertEqual(source_key_transitions(rs),[])

    def test_run_censored_at_missing(self):
        rs=[row(0,key=C),row(1),row(2)]
        rs[2]['key']=None
        r=source_key_transitions(rs)[0]
        self.assertEqual(r['termination'],'unverified_or_missing');self.assertIsNone(r['next_key'])

    def test_full_ties_and_core_immutable(self):
        ir=fixture();old=copy.deepcopy(ir);r=observe_support(ir,{'start':q(1),'end':q(2)},chord(['C',0],'M'))
        self.assertEqual(len(r['held_at_start_ids']),3);self.assertEqual(len(r['complete_vertical_matches']),1)
        self.assertEqual(ir,old)

    def test_arpeggio_union_not_vertical(self):
        r=observe_support(fixture(True),{'start':q(0),'end':q(1)},chord(['C',0],'M'))
        self.assertEqual(r['missing_spellings'],[]);self.assertEqual(r['complete_vertical_matches'],[])
        self.assertFalse(r['union_is_simultaneous'])

    def test_wrong_inversion(self):
        r=observe_support(fixture(),{'start':q(0),'end':q(1)},chord(['C',0],'M',1))
        self.assertEqual(r['complete_vertical_matches'],[])

    def test_grace_not_harmonic_support(self):
        ir=fixture();ir['note_events'][1]['grace']={'is_grace':True}
        r=observe_support(ir,{'start':q(0),'end':q(1)},chord(['C',0],'M'))
        self.assertEqual(r['excluded_grace_refs'],['e1']);self.assertEqual(r['missing_spellings'],[['E',0]])

    def test_broken_reference_pitch_and_time(self):
        for mutation in ('ref','pitch','time','duplicate'):
            ir=fixture()
            if mutation=='ref':ir['sounding_events'][0]['source_note_ids']=[]
            if mutation=='pitch':ir['sounding_events'][0]['pitch']['midi_pitch']=61
            if mutation=='time':ir['sounding_events'][0]['span']['start']=-1
            if mutation=='duplicate':ir['sounding_events'].append(ir['sounding_events'][0])
            with self.assertRaises(ValueError):observe_support(ir,{'start':q(0),'end':q(1)},chord(['C',0],'M'))

    def test_rights_before_output(self):
        with tempfile.TemporaryDirectory() as d:
            manifest=Path(d)/'manifest.json';out=Path(d)/'out'
            manifest.write_text(json.dumps({'entries':[{'split':'train','collection_id':'mozart-sonatas','package_path':'x','work_family_id':'w','score_sha256':'s','annotation_sha256':'a','rights':{'internal_research_use':False}}]}))
            with self.assertRaises(ValueError):build(manifest,out)
            self.assertFalse(out.exists())

    def test_catalog(self):
        r=next(c for c in concepts() if c['concept_id']=='hvl.unit27')
        self.assertEqual(r['reviewed_sections'],list(range(1,17)))
        self.assertEqual(r['rule_status'],'candidate_not_production')


if __name__=='__main__':unittest.main()
