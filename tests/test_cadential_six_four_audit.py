import json
from pathlib import Path
import tempfile
import unittest
from musicanote_harness.cadential_six_four_audit import build, source_key
from musicanote_harness.harmony_curriculum import concepts


class CadentialAuditTest(unittest.TestCase):
    def test_source_key_distinguishes_b_minor_and_flat(self):
        def a(g,l,minor):
            return {'raw_fields':{'globalkey':g,'localkey':l,'localkey_is_minor':minor}}
        self.assertEqual(source_key(a('b','i','1')),('B',0,'minor'))
        self.assertEqual(source_key(a('Bb','I','0')),('B',-1,'major'))
        self.assertEqual(source_key(a('f','III','0')),('A',-1,'major'))

    def test_output_is_immutable(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError,'output_exists'): build('not_read',temp)

    def test_holdout_not_opened_and_rights_checked_before_packages(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp); m=p/'manifest.json'
            entry={'split':'holdout','work_family_id':'w','score_sha256':'s','annotation_sha256':'a',
                   'collection_id':'mozart-sonatas','package_path':'does_not_exist',
                   'rights':{'internal_research_use':False}}
            m.write_text(json.dumps({'entries':[entry]}))
            self.assertEqual(build(m,p/'out')['summary']['score_count'],0)
            entry['split']='train'; m.write_text(json.dumps({'entries':[entry]}))
            with self.assertRaisesRegex(ValueError,'internal_research_not_allowed'): build(m,p/'out2')
            self.assertFalse((p/'out2').exists())

    def test_reading_is_not_full_implementation(self):
        unit=next(c for c in concepts() if c['concept_id']=='hvl.unit11')
        self.assertEqual(unit['reviewed_sections'],list(range(1,15)))
        self.assertEqual(unit['rule_status'],'candidate_not_production')
