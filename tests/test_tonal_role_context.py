import json
from pathlib import Path
import tempfile
import unittest
from musicanote_harness.tonal_role_context import propose, source_symbol
from musicanote_harness.tonal_role_audit import build
from musicanote_harness.harmony_curriculum import concepts


def roles(r):
    return {x['role'] for x in r['role_hypotheses']}


class ContextTest(unittest.TestCase):
    def test_tonic_neighbor_not_automatic_cadence(self):
        r=propose('I','IV','I')
        self.assertIn('tonic_neighbor_expansion', roles(r))
        self.assertIn('plagal_progression', roles(r))
        self.assertIsNone(r['cadence'])
        self.assertIsNone(r['phrase_boundary'])
        self.assertEqual(r['cadence_hypotheses'][0]['status'],'unverified_candidate')

    def test_inverted_tonic_and_incomplete_context(self):
        r=propose('I6','IV','I6')
        self.assertIn('tonic_neighbor_expansion', roles(r))
        self.assertEqual(r['cadence_hypotheses'],[])
        r=propose(None,'IV','I')
        self.assertNotIn('tonic_neighbor_expansion', roles(r))
        self.assertIn('plagal_progression', roles(r))

    def test_passing_is_directional(self):
        for middle in ('IV6','vi'):
            self.assertIn('tonic_passing_expansion',roles(propose('I',middle,'I6')))
            self.assertNotIn('tonic_passing_expansion',roles(propose('I6',middle,'I')))

    def test_dominant_and_deceptive_alternatives_coexist(self):
        r=propose('V7','vi','V65')
        self.assertEqual(roles(r),{'dominant_passing_expansion','tonic_substitution_or_deflection'})
        self.assertIsNone(r['selected_role'])
        self.assertIsNone(r['cadence'])

    def test_iv6_deceptive_alternative(self):
        r=propose('V7','IV6','I6')
        self.assertEqual(r['cadence_hypotheses'][0]['type'],'deceptive')
        self.assertIn('authentic_cadence_expectation',r['cadence_hypotheses'][0]['needs_evidence'])

    def test_minor_lowered_and_raised_sixth(self):
        self.assertNotIn('dominant_passing_expansion',roles(propose('V','VI','V6','minor')))
        self.assertNotIn('dominant_passing_expansion',roles(propose('V','iv6','V6','minor')))
        self.assertIn('dominant_passing_expansion',roles(propose('V','IV6','V6','minor')))
        self.assertIn('tonic_neighbor_expansion',roles(propose('i','iv','i','minor')))

    def test_no_match_is_not_verdict(self):
        r=propose(None,'vi',None)
        self.assertEqual(r['role_hypotheses'],[])
        self.assertIsNone(r['cadence'])
        self.assertFalse(r['production_enabled'])

    def test_unsupported_not_silently_simplified(self):
        for x in ('V/V','V(4)','IV7','unknown'):
            with self.assertRaises(ValueError): propose(x,'vi','I')
        with self.assertRaises(ValueError): propose('i','VI','i','major')
        with self.assertRaises(ValueError): propose('I',None,'I')

    def test_source_adapter(self):
        def a(**kw): return {'raw_fields':dict(numeral='IV',figbass='6',chord_type='M',**kw)}
        self.assertEqual(source_symbol(a(),'major'),'IV6')
        self.assertEqual(source_symbol(a(),'minor'),'IV6')
        for k in ('changes','form','relativeroot','pedal','special','added_tones'):
            self.assertIsNone(source_symbol(a(**{k:'x'}),'major'))
        self.assertIsNone(source_symbol({'raw_fields':{'numeral':'VI','figbass':'','chord_type':'M'}},'major'))
        self.assertEqual(source_symbol({'raw_fields':{'numeral':'V','figbass':'65','chord_type':'Mm7'}},'minor'),'V65')

    def test_rights_and_holdout_and_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)
            with self.assertRaisesRegex(ValueError,'output_exists'): build('missing',p)
            e={'split':'holdout','work_family_id':'w','score_sha256':'s','annotation_sha256':'a',
               'collection_id':'mozart-sonatas','package_path':'missing','rights':{'internal_research_use':False}}
            manifest=p/'m.json';manifest.write_text(json.dumps({'entries':[e]}))
            self.assertEqual(build(manifest,p/'out')['summary']['case_count'],0)
            e['split']='train';manifest.write_text(json.dumps({'entries':[e]}))
            with self.assertRaisesRegex(ValueError,'research_not_permitted'): build(manifest,p/'other')

    def test_catalog(self):
        r=next(x for x in concepts() if x['concept_id']=='hvl.unit14')
        self.assertEqual(r['reviewed_sections'],list(range(1,9)))
        self.assertEqual(r['rule_status'],'candidate_not_production')


if __name__=='__main__':
    unittest.main()
