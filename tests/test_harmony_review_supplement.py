import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_review_supplement import short_change,context_excerpt,verified_annotations,build,select_pools


def annotation(label,a,b):
    return {'annotation_id':label+str(a),'raw_fields':{'chord':label,'globalkey':'C','localkey':'I'},
            'target':{'span':{'start':q(a),'end':q(b)}}}


class SupplementTests(unittest.TestCase):
    def test_sampling_is_deterministic_family_capped_and_deduplicated(self):
        rows=[{'case_id':str(i),'work_family_id':str(i//4)} for i in range(8)]
        a=select_pools({'x':rows,'y':rows},2)
        b=select_pools({'y':list(reversed(rows)),'x':list(reversed(rows))},2)
        self.assertEqual(a,b);self.assertEqual(len(a[0]),4)
        self.assertEqual(a[2]['x']['families'],2)

    def test_relative_short_change_and_compound_meter(self):
        ir={'measures':[{'global_start_quarter':q(0),'actual_duration_quarter':q(3),'time_signature':{'beats':6,'beat_type':8}}]}
        p,c,n=annotation('I',0,1),annotation('V',1,2),annotation('I',2,3)
        self.assertIsNotNone(short_change(p,c,n,ir))
        ir['measures'][0]['time_signature']={'beats':3,'beat_type':8}
        self.assertIsNone(short_change(p,c,n,ir))

    def test_no_change_or_gap_abstains(self):
        ir={'measures':[{'global_start_quarter':q(0),'actual_duration_quarter':q(4),'time_signature':{'beats':4,'beat_type':4}}]}
        self.assertIsNone(short_change(annotation('V',0,1),annotation('V',1,2),annotation('I',2,3),ir))
        self.assertIsNone(short_change(annotation('I',0,1),annotation('V',2,3),annotation('I',3,4),ir))

    def test_context_retains_held_note_and_global_time(self):
        sounds=[{'sounding_event_id':'s','source_note_ids':['n1','n2'],
                 'span':{'start':q(0),'end':q(12)}}]
        ir={'score':{'score_id':'s'},'ir_document_id':'ir','sounding_events':sounds,
            'note_events':[{'note_id':'n1'},{'note_id':'n2'}],
            'measures':[{'measure_id':str(i),'global_start_quarter':q(i*4),'actual_duration_quarter':q(4)} for i in range(4)]}
        r=context_excerpt(ir,{'start':q(8),'end':q(9)})
        self.assertEqual(r['context_span'],{'start':q(4),'end':q(16)})
        self.assertEqual(r['sounding_events'],sounds)
        self.assertFalse(r['is_full_canonical_ir'])

    def test_invalid_annotation_not_gold(self):
        e={'score_id':'s','ir_document_id':'i','annotation_sha256':'a'}
        p={'annotations':[{'annotation_id':'a','target':None}], 'alignments':[]}
        valid,skips=verified_annotations(p,e)
        self.assertEqual(valid,[]);self.assertEqual(skips['unverified_alignment'],1)

    def test_holdout_never_loaded(self):
        with tempfile.TemporaryDirectory() as d:
            m=Path(d)/'manifest.json'
            m.write_text(json.dumps({'entries':[{'split':'holdout','work_family_id':'w',
                'score_sha256':'s','annotation_sha256':'a','package_path':'MUST_NOT_OPEN'}]}))
            with patch('musicanote_harness.harmony_review_supplement.load_prepared_package') as loader:
                r=build(m,Path(d)/'out')
            loader.assert_not_called();self.assertEqual(r['unique_selected'],0)

    def test_duplicate_annotation_rejected(self):
        a={'annotation_id':'a','target':None}
        with self.assertRaises(ValueError):verified_annotations({'annotations':[a,a],'alignments':[]},{'score_id':'s','ir_document_id':'i','annotation_sha256':'a'})
