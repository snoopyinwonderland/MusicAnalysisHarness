import unittest
import hashlib
import json
import tempfile
from pathlib import Path
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_context_sensitivity import compare_target, edge_support, context_stable, build


def span(a,b):return {'start':q(a),'end':q(b)}


def result(rows):
    return {'analysis_span':span(rows[0][0],rows[-1][1]),
            'segments':[{'span':span(a,b),'selected':{'label':label}} for a,b,label in rows]}


class SensitivityTests(unittest.TestCase):
    def test_nontrain_rejected_before_score_or_ir_open(self):
        case={'case_id':'case','package_path':'MUST_NOT_OPEN','split':'dev',
              'work_family_id':'family','score_sha256':'score','annotation_sha256':'ann'}
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); manifest=root/'manifest.json'
            data=json.dumps({'entries':[case]}).encode()
            manifest.write_bytes(data)
            (root/'report.json').write_text(json.dumps({'manifest_sha256':hashlib.sha256(data).hexdigest(),
                                                       'plan':[case]}))
            (root/'cases.jsonl').write_text(json.dumps(case)+'\n')
            with self.assertRaisesRegex(ValueError,'non_train_case'):
                build(manifest,root,root/'out')

    def test_equal_label_order_but_shifted_boundary(self):
        a=result([(0,1,'C'),(1,4,'G')]);b=result([(0,2,'C'),(2,4,'G')])
        r=compare_target(a,b,span(0,4))
        self.assertEqual(r['disagreement_quarters'],q(1))
        self.assertEqual(r['disagreement_fraction'],{'numerator':1,'denominator':4})
        self.assertFalse(r['same_internal_boundaries'])

    def test_context_changes_outside_target_do_not_count(self):
        a=result([(0,4,'C')]);b=result([(0,1,'G'),(1,3,'C'),(3,4,'G')])
        r=compare_target(a,b,span(1,3))
        self.assertTrue(r['same_labels_at_all_target_times'])
        self.assertTrue(r['same_internal_boundaries'])

    def test_equal_labels_split_is_boundary_not_label_difference(self):
        a=result([(0,4,'C')]);b=result([(0,2,'C'),(2,4,'C')])
        r=compare_target(a,b,span(0,4))
        self.assertTrue(r['same_labels_at_all_target_times'])
        self.assertFalse(r['same_internal_boundaries'])

    def test_missing_or_overlapping_output_rejected(self):
        good=result([(0,4,'C')])
        for bad in [result([(1,4,'C')]),result([(0,1,'C'),(2,4,'C')]),result([(0,3,'C'),(2,4,'C')])]:
            with self.assertRaises(ValueError):compare_target(good,bad,span(0,4))

    def test_edge_support_does_not_claim_search_edge(self):
        r=result([(0,2,'C'),(2,4,'G')])
        self.assertEqual(edge_support(r,span(0,2)),{'start':None,'end':True})
        self.assertEqual(edge_support(r,span(1,3)),{'start':False,'end':False})

    def test_skipped_run_not_stability_success(self):
        r=result([(0,4,'C')])
        self.assertIsNone(context_stable([{'e':r}],'e',span(1,3),2))
        self.assertTrue(context_stable([{'e':r},{'e':r}],'e',span(1,3),2))

    def test_target_edge_change_is_instability(self):
        a=result([(0,4,'C')]);b=result([(0,1,'C'),(1,4,'C')])
        self.assertFalse(context_stable([{'e':a},{'e':b}],'e',span(1,3),2))
