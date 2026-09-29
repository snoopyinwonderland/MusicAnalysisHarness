import copy
from fractions import Fraction
import json
from pathlib import Path
import tempfile
import unittest
from musicanote_harness.formal_ir import q
from musicanote_harness.six_three_context import triad, propose, source_triad, observe_surface
from musicanote_harness.six_three_audit import windows, build
from musicanote_harness.harmony_curriculum import concepts


def tags(result):
    return {r['role'] for r in result['role_candidates']}


def ann(symbol,start,end,figure='6',minor='0'):
    form = symbol[-1] if symbol[-1] in ('o','+') else ''
    return {'annotation_id':str(start),'raw_fields':{'numeral':symbol[:-1] if form else symbol,
            'form':form,'chord_type':form or ('M' if symbol[0].isupper() else 'm'),
            'figbass':figure,'globalkey':'a' if minor=='1' else 'C','localkey':'i' if minor=='1' else 'I',
            'localkey_is_minor':minor},'target':{'span':{'start':q(start),'end':q(end)}}}


def inventory():
    return {'span':{'start':q(0),'end':q(2)},'slices':[
        {'span':{'start':q(0),'end':q(1)},'events':[
            {'event_id':'e1','pitch':['E',0,3]}, {'event_id':'e2','pitch':['G',0,3]}, {'event_id':'e3','pitch':['C',0,4]}]},
        {'span':{'start':q(1),'end':q(2)},'events':[]}]}


class ContextTest(unittest.TestCase):
    def test_first_inversion_bass_spelling(self):
        self.assertEqual(triad('vi',1,'C')['expected_bass_spelling'],['C',0])
        self.assertEqual(triad('III+',1,'F',0,'minor')['expected_bass_spelling'],['C',0])
        self.assertEqual(triad('V',1,'F',1,'major')['expected_bass_spelling'],['E',1])
        self.assertEqual(triad('V',0,'C')['expected_bass_spelling'],['G',0])

    def test_ascending_descending_and_thirds(self):
        for symbols, motion in [(['IV','iii','ii'],'step_down'),(['I','ii','iii'],'step_up'),
                                (['vi','IV','ii'],'third_down'),(['I','iii','V'],'third_up')]:
            r = propose(symbols,(1,1,1),'C')
            role = next(x for x in r['role_candidates'] if x['role']=='linear_first_inversion_chain')
            self.assertEqual(role['nominal_root_motion'],motion)
            self.assertFalse(r['parallel_voice_motion_verified']); self.assertIsNone(r['merge_recommended'])

    def test_root_position_insertion_not_collapsed(self):
        self.assertNotIn('linear_first_inversion_chain',tags(propose(['IV','iii','ii'],[1,0,1],'C')))

    def test_neighbor_candidate(self):
        for symbols, inv in [(['I','V','I'],[0,1,0]),(['IV','I','IV'],[0,1,0])]:
            r = propose(symbols,inv,'C')
            self.assertIn('neighboring_first_inversion',tags(r)); self.assertIsNone(r['selected_role'])

    def test_passing_candidate(self):
        for symbols, inv in [(['I','viio','I'],[0,1,1]),(['V','IV','V'],[0,1,1]),(['I','V','vi'],[0,1,0])]:
            r = propose(symbols,inv,'C')
            self.assertIn('passing_first_inversion',tags(r)); self.assertIsNone(r['cadence'])

    def test_not_every_sixth_is_passing_or_neighbor(self):
        t = tags(propose(['I','ii','V'],[0,1,0],'C'))
        self.assertNotIn('passing_first_inversion',t); self.assertNotIn('neighboring_first_inversion',t)

    def test_substitution_keeps_original(self):
        r = propose(['I','vi','V'],[0,1,0],'C')
        s = next(x for x in r['role_candidates'] if x['role']=='sixth_decorating_or_replacing_fifth')
        self.assertEqual(s['governing_harmony_candidate'],'I'); self.assertEqual(r['candidates'][1]['symbol'],'vi')
        self.assertIn('retain_independent_first_inversion_alternative',s['needs_evidence'])

    def test_augmented_III_not_augmented_sixth(self):
        r = propose(['i','III+','V'],[0,1,0],'A',mode='minor')
        self.assertEqual(r['candidates'][1]['quality'],'augmented')
        self.assertEqual(r['candidates'][1]['expected_bass_spelling'],['E',0])
        s = next(x for x in r['role_candidates'] if x['role']=='sixth_decorating_or_replacing_fifth')
        self.assertEqual(s['governing_harmony_candidate'],'V')
        natural = propose(['i','III','V'],[0,1,0],'A',mode='minor')
        self.assertNotIn('sixth_decorating_or_replacing_fifth',tags(natural))

    def test_minor_v_and_transposed_roles(self):
        r = propose(['i','v','iv'],[0,1,1],'D',mode='minor')
        self.assertIn('passing_first_inversion',tags(r))
        self.assertEqual(tags(propose(['I','viio','I'],[0,1,1],'C')),
                         tags(propose(['I','viio','I'],[0,1,1],'G',-1)))

    def test_input_contract(self):
        for inv in ([0,1], [0,True,0], [0,2,0]):
            with self.assertRaises(ValueError): propose(['I','V','I'],inv,'C')
        with self.assertRaises(ValueError): triad('III+',1,'C',mode='major')

    def test_source_augmented_adapter(self):
        a = ann('III+',0,1,minor='1'); before=copy.deepcopy(a)
        self.assertEqual(source_triad(a),('III+',1)); self.assertEqual(a,before)
        for field in ('changes','added_tones','relativeroot','pedal','special'):
            a=copy.deepcopy(before); a['raw_fields'][field]='x'; self.assertIsNone(source_triad(a))


class SurfaceTest(unittest.TestCase):
    def test_time_weighted_surface_and_silence(self):
        inv=inventory(); before=copy.deepcopy(inv)
        o=observe_surface(inv,triad('I',1,'C'))
        self.assertEqual(o['matching_lowest_duration_ratio'],q(Fraction(1,2)))
        self.assertEqual(o['sixth_class_extrema_duration_ratio'],q(Fraction(1,2)))
        self.assertEqual(o['silence_duration_ratio'],q(Fraction(1,2)))
        self.assertEqual(o['cells'][0]['lowest_event_ids'],['e1'])
        self.assertFalse(o['voice_path_verified']); self.assertIsNone(o['parallel_motion'])
        self.assertEqual(inv,before)

    def test_lowest_is_not_root_or_main_voice(self):
        o=observe_surface(inventory(),triad('I',0,'C'))
        self.assertEqual(o['matching_lowest_duration_ratio'],q(0))

    def test_enharmonic_bass_ambiguity(self):
        inv=inventory(); inv['slices'][0]['events'].append({'event_id':'enh','pitch':['F',-1,3]})
        o=observe_surface(inv,triad('I',1,'C'))
        self.assertEqual(o['matching_lowest_duration_ratio'],q(0))
        self.assertEqual(o['cells'][0]['lowest_event_ids'],['e1','enh'])

    def test_tenths_not_sixths(self):
        inv=inventory(); inv['slices'][0]['events'][-1]['pitch']=['G',0,4]
        o=observe_surface(inv,triad('I',1,'C'))
        self.assertEqual(o['sixth_class_extrema_duration_ratio'],q(0))
        self.assertEqual(o['cells'][0]['outer_intervals'][0]['generic'],10)

    def test_partition_and_rational_guard(self):
        for kind in ('gap','overlap','end','float','empty'):
            inv=inventory()
            if kind=='gap': inv['slices'][1]['span']['start']=q(Fraction(3,2))
            if kind=='overlap': inv['slices'][1]['span']['start']=q(0)
            if kind=='end': inv['slices'][1]['span']['end']=q(3)
            if kind=='float': inv['slices'][0]['span']['start']=0.0
            if kind=='empty': inv['slices']=[]
            with self.subTest(kind=kind),self.assertRaises(ValueError): observe_surface(inv,triad('I',1,'C'))


class AuditTest(unittest.TestCase):
    def test_keep_nonmatches_and_require_some_first_inversion(self):
        a=[ann(s,i,i+1) for i,s in enumerate(['I','V','I'])]
        self.assertEqual(len(list(windows(a))),1)
        for x in a: x['raw_fields']['figbass']=''
        self.assertEqual(list(windows(a)),[])

    def test_barriers(self):
        base=[ann(s,i,i+1) for i,s in enumerate(['IV','iii','ii'])]
        self.assertEqual(list(windows(base,{'0','2'})),[])
        for kind in ('gap','key','unsupported'):
            a=copy.deepcopy(base)
            if kind=='gap':a[1]['target']['span']['start']=q(Fraction(3,2))
            if kind=='key':a[1]['raw_fields']['globalkey']='G'
            if kind=='unsupported':a[1]['raw_fields']['figbass']='64'
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
        u=next(x for x in concepts() if x['concept_id']=='hvl.unit19')
        self.assertEqual(u['reviewed_sections'],list(range(1,10)))
        self.assertEqual(u['rule_status'],'candidate_not_production')


if __name__=='__main__':unittest.main()
