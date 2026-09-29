import json
from pathlib import Path
import tempfile
import unittest
from musicanote_harness.sixth_degree_audit import build, source_anchor
from musicanote_harness.harmony_curriculum import concepts


class SixthAuditTest(unittest.TestCase):
    def test_anchor_is_not_any_vi_or_applied_label(self):
        def a(**fields):return {'raw_fields':fields}
        self.assertTrue(source_anchor(a(numeral='VI',figbass='')))
        self.assertTrue(source_anchor(a(numeral='iv',figbass='6')))
        self.assertFalse(source_anchor(a(numeral='VI',figbass='6')))
        self.assertFalse(source_anchor(a(numeral='VI',figbass='',relativeroot='V')))
        self.assertFalse(source_anchor(a(numeral='vi',figbass='',changes='#3')))

    def test_output_and_split_guard(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)
            with self.assertRaisesRegex(ValueError,'output_exists'):build('not_read',p)
            e={'split':'holdout','work_family_id':'w','score_sha256':'s','annotation_sha256':'a',
               'collection_id':'mozart-sonatas','package_path':'missing','rights':{'internal_research_use':False}}
            manifest=p/'m.json';manifest.write_text(json.dumps({'entries':[e]}))
            self.assertEqual(build(manifest,p/'out')['summary']['case_count'],0)
            e['split']='train';manifest.write_text(json.dumps({'entries':[e]}))
            with self.assertRaisesRegex(ValueError,'research_not_permitted'):build(manifest,p/'other')

    def test_catalog(self):
        unit=next(c for c in concepts() if c['concept_id']=='hvl.unit12')
        self.assertEqual(unit['reviewed_sections'],list(range(1,8)))
        self.assertEqual(unit['rule_status'],'candidate_not_production')
