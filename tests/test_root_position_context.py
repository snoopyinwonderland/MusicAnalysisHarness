import copy
import json
from pathlib import Path
import tempfile
import unittest
from musicanote_harness.formal_ir import q
from musicanote_harness.root_position_context import candidate, root_relation, propose, source_symbol
from musicanote_harness.root_position_audit import windows, build
from musicanote_harness.harmony_curriculum import concepts


def roles(r):
    return {h['role'] for h in r['role_hypotheses']}


def ann(symbol, start, end, home='C', minor='0'):
    quality = 'o' if symbol.endswith('o') else 'M' if symbol[0].isupper() else 'm'
    return {'raw_fields':{'numeral':symbol.rstrip('o'),'form':'o' if symbol.endswith('o') else '',
            'chord_type':quality,'globalkey':home,'localkey':'i' if minor=='1' else 'I','localkey_is_minor':minor},
            'target':{'span':{'start':q(start),'end':q(end)}}}


class RootTest(unittest.TestCase):
    def test_root_spelling(self):
        c=candidate('III','F',0,'minor')
        self.assertEqual((c['root_step'],c['root_alter']),('A',-1))
        c=candidate('#viio','C',-1,'minor')
        self.assertEqual((c['root_step'],c['root_alter']),('B',-1))

    def test_v_and_V_remain_different(self):
        a=candidate('v','A',0,'minor');b=candidate('V','A',0,'minor')
        self.assertEqual(a['root_step'],b['root_step']);self.assertNotEqual(a['quality'],b['quality'])

    def test_diatonic_fifths_include_tritone(self):
        major=root_relation(candidate('IV','C'),candidate('viio','C'))
        minor=root_relation(candidate('VI','A',0,'minor'),candidate('iio','A',0,'minor'))
        for r in (major,minor):
            self.assertEqual(r['family'],'descending_fifth_or_ascending_fourth')
            self.assertTrue(r['tritone']);self.assertIsNone(r['actual_bass_direction'])

    def test_fifths_chain_not_sequence_verdict(self):
        r=propose(['ii','V','I'],'C')
        self.assertIn('root_chain_descending_fifth_or_ascending_fourth',roles(r))
        self.assertIsNone(r['sequence_confirmed']);self.assertIsNone(r['cadence'])

    def test_ascending_fifths(self):
        r=propose(['III','VII','iv'],'A',mode='minor')
        self.assertIn('root_chain_ascending_fifth_or_descending_fourth',roles(r))

    def test_descending_and_ascending_thirds(self):
        self.assertIn('root_chain_descending_third_or_ascending_sixth',roles(propose(['I','vi','IV'],'C')))
        self.assertIn('root_chain_ascending_third_or_descending_sixth',roles(propose(['I','iii','V'],'C')))

    def test_upper_fifth_not_automatic_merge(self):
        r=propose(['V','ii','V'],'C')
        self.assertIn('upper_fifth_expansion',roles(r));self.assertIsNone(r['merge_recommended'])
        self.assertIsNone(r['selected_role'])

    def test_upper_third(self):
        self.assertIn('upper_third_expansion',roles(propose(['I','iii','I'],'C')))
        self.assertNotIn('upper_third_expansion',roles(propose(['I','iii','vi'],'C')))

    def test_neighbor_candidates_require_voice_evidence(self):
        r=propose(['V','I','V'],'C')
        self.assertIn('upper_voice_neighbor_support',roles(r))
        self.assertIn('same_voice_neighbor_return',r['role_hypotheses'][0]['needs_evidence'])
        self.assertIn('bass_neighbor_support',roles(propose(['V','vi','V'],'C')))

    def test_apparent_tonic(self):
        r=propose(['IV','I','V'],'C')
        self.assertIn('apparent_tonic_supporting_passing_third',roles(r))
        self.assertIsNone(r['phrase_boundary'])

    def test_minor_v_passing_vs_major_V(self):
        name='minor_v_supporting_descending_natural_seventh'
        self.assertIn(name,roles(propose(['i','v','VI'],'A',mode='minor')))
        self.assertNotIn(name,roles(propose(['i','V','VI'],'A',mode='minor')))

    def test_enharmonic_root_relation(self):
        a={'root_step':'C','root_alter':0}
        b={'root_step':'F','root_alter':1};c={'root_step':'G','root_alter':-1}
        x,y=root_relation(a,b),root_relation(a,c)
        self.assertEqual(x['semitones_up_mod12'],y['semitones_up_mod12']);self.assertNotEqual(x['family'],y['family'])

    def test_invalid_input_and_immutability(self):
        s=['I','IV','I'];before=copy.deepcopy(s);propose(s,'C');self.assertEqual(s,before)
        with self.assertRaises(ValueError):propose(['I','V'],'C')
        with self.assertRaises(ValueError):propose(['I','IV6','I'],'C')
        with self.assertRaises(ValueError):candidate('I','C',mode='dorian')


class AuditTest(unittest.TestCase):
    def test_adapter(self):
        a=ann('v',0,1,'a','1');self.assertEqual(source_symbol(a),'v')
        a['raw_fields']['chord_type']='M';self.assertIsNone(source_symbol(a))
        for field in ('figbass','changes','relativeroot','pedal','special','added_tones'):
            a=ann('I',0,1);a['raw_fields'][field]='x';self.assertIsNone(source_symbol(a))

    def test_windows_preserve_nonmatches(self):
        a=[ann('I',0,1),ann('I',1,2),ann('V',2,3)]
        self.assertEqual(len(list(windows(a))),1)
        self.assertEqual(roles(propose(list(windows(a))[0][1],'C')),set())

    def test_no_bridge_gaps_unsupported_or_key_change(self):
        for kind in ('gap','key','unsupported'):
            a=[ann('I',0,1),ann('IV',1,2),ann('I',2,3)]
            if kind=='gap':a[1]['target']['span']['start']=q(3/2)
            elif kind=='key':a[1]['raw_fields']['globalkey']='G'
            else:a[1]['raw_fields']['figbass']='6'
            self.assertEqual(list(windows(a)),[])

    def test_rights_holdout_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            with self.assertRaisesRegex(ValueError,'output_exists'):build('missing',p)
            e={'split':'holdout','work_family_id':'w','score_sha256':'s','annotation_sha256':'a',
               'collection_id':'mozart-sonatas','package_path':'missing','rights':{'internal_research_use':False}}
            m=p/'m.json';m.write_text(json.dumps({'entries':[e]}))
            self.assertEqual(build(m,p/'out')['summary']['case_count'],0)
            e['split']='train';m.write_text(json.dumps({'entries':[e]}))
            with self.assertRaisesRegex(ValueError,'research_not_permitted'):build(m,p/'bad')

    def test_catalog(self):
        u=next(x for x in concepts() if x['concept_id']=='hvl.unit17')
        self.assertEqual(u['reviewed_sections'],list(range(1,15)))
        self.assertEqual(u['rule_status'],'candidate_not_production')


if __name__=='__main__':unittest.main()
