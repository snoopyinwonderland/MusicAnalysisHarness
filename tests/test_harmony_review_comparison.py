import copy
from fractions import Fraction
import unittest
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_review_comparison import merge_rows,semantic_key,window_ir,compare_outputs
from test_harmony_joint import fixture


def row():
    return {'case_id':'a','annotation_id':'ann','target_span':{'start':q(1),'end':q(2)},
            'tags':['triad'],'split':'train','package_path':'p','score_id':'s','ir_document_id':'ir',
            'work_family_id':'w','collection':'c','score_sha256':'hash','annotation_sha256':'ah','rights':{}}


class ComparisonTests(unittest.TestCase):
    def test_holdout_rejected_before_context_open(self):
        import tempfile,json
        from pathlib import Path
        from musicanote_harness.harmony_review_comparison import build
        a=row();a['split']='holdout';a['context_excerpt_path']='MUST_NOT_OPEN'
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);m=root/'manifest.json';c=root/'cases.jsonl'
            m.write_text(json.dumps({'entries':[a]}));c.write_text(json.dumps(a)+'\n')
            with self.assertRaisesRegex(ValueError,'non_train_case'):build(m,[c],root/'out')

    def test_two_formats_merge_preserving_sources(self):
        a=row();b=copy.deepcopy(a);b['case_id']='b';b['tags']=['short']
        del b['annotation_id']
        b['source_annotation_refs']=[{'annotation_id':'ann','target':{'span':a['target_span']}}]
        result=merge_rows([a,b])
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]['tags'],['short','triad'])
        self.assertEqual(len(result[0]['members']),2)
        self.assertEqual(result,merge_rows([b,a]))

    def test_geometry_not_merged_with_annotation_at_same_span(self):
        a=row();b=copy.deepcopy(a);b.pop('annotation_id');b['evidence']={'event_refs':['s1','s2','s3']}
        self.assertNotEqual(semantic_key(a),semantic_key(b))

    def test_conflicts_and_nontrain_fail(self):
        a=row();b=copy.deepcopy(a);b['score_sha256']='wrong'
        with self.assertRaises(ValueError):merge_rows([a,b])
        a['split']='dev'
        with self.assertRaises(ValueError):merge_rows([a])

    def test_crop_retains_carried_sound_no_negative_timeline(self):
        ir=fixture([(60,0,4,'v'),(64,3,4,'b')]);original=copy.deepcopy(ir)
        local=window_ir(ir,Fraction(2),Fraction(3))
        self.assertEqual(len(local['sounding_events']),1)
        self.assertEqual(local['sounding_events'][0]['span'],{'start':q(0),'end':q(1)})
        self.assertEqual(local['measures'][0]['global_start_quarter'],q(0))
        self.assertEqual(ir,original)

    def test_boundary_deltas_not_accuracy(self):
        def seg(a,b,label):return {'span':{'start':q(a),'end':q(b)},'selected':{'label':label}}
        a={'segments':[seg(0,2,'C')]};b={'segments':[seg(0,1,'C'),seg(1,2,'G')]}
        r=compare_outputs(a,b,Fraction(10))
        self.assertEqual(r['added_boundaries'],[q(11)])
        self.assertTrue(r['more_segments_review_flag']);self.assertIsNone(r['musical_improvement'])

    def test_ambiguous_target_rejected(self):
        a=row();a.pop('annotation_id');a['source_annotation_refs']=[]
        with self.assertRaises(ValueError):semantic_key(a)
