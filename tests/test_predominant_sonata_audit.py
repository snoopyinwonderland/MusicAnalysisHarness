import copy
import unittest
from musicanote_harness.formal_ir import q
from musicanote_harness.predominant_sonata_audit import span_observation, compare_spans, source_candidate


def sound(eid,start,end,step,octave,midi):
    return {'sounding_event_id':eid,'span':{'start':q(start),'end':q(end)},
            'pitch':{'step':step,'alter':q(0),'octave':octave,'midi_pitch':midi}}


class AdapterTests(unittest.TestCase):
    def test_holdout_not_loaded_and_null_target_skipped(self):
        import tempfile, json, hashlib
        from pathlib import Path
        from unittest.mock import patch
        from musicanote_harness.predominant_sonata_audit import build
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); source=root/'score.xml'; source.write_bytes(b'<score/>')
            entry={'split':'train','collection_id':'mozart-sonatas','package_path':'train',
                   'ir_document_id':'ir','score_id':'score','score_source_path':str(source),
                   'score_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'annotation_sha256':'ann'}
            manifest=root/'manifest.json'
            manifest.write_text(json.dumps({'entries':[dict(entry,split='holdout',package_path='holdout'),entry]}))
            package={'ir':{'ir_document_id':'ir','score':{'score_id':'score'}},
                     'alignments':[],'annotations':[{'annotation_id':'a','target':None,'source_asset_sha256':'ann'}]}
            with patch('musicanote_harness.predominant_sonata_audit.load_prepared_package',return_value=package) as loader:
                report=build(manifest,root/'out')
            loader.assert_called_once_with('train')
            self.assertEqual(report['skipped']['unverified_annotation'],1)
            self.assertEqual(report['errors'],[])

    def test_held_and_half_open(self):
        ir={'sounding_events':[sound('held',0,3,'F',3,53),sound('end',0,1,'A',3,57),
            sound('start',1,2,'D',4,62),sound('later',2,3,'C',4,60)]}
        original=copy.deepcopy(ir)
        r=span_observation(ir,{'start':q(1),'end':q(2)})
        self.assertEqual(r['held_at_start_ids'],['held'])
        self.assertEqual([x['event_id'] for x in r['union_events']],['held','start'])
        self.assertEqual(ir,original)

    def test_silence_and_fraction(self):
        from fractions import Fraction
        ir={'sounding_events':[sound('x',Fraction(1,3),Fraction(2,3),'C',4,60)]}
        r=span_observation(ir,{'start':q(0),'end':q(1)})
        self.assertEqual(len(r['slices']),3)
        self.assertEqual(r['slices'][0]['events'],[])
        self.assertEqual(r['slices'][1]['span']['start'],q(Fraction(1,3)))

    def test_snapshot_vs_union(self):
        ir={'sounding_events':[sound('f',0,2,'F',3,53),sound('a',0,1,'A',3,57),
            sound('c',0,1,'C',4,60),sound('a2',1,2,'A',3,57),sound('d',1,2,'D',4,62)]}
        r=compare_spans(ir,{'start':q(0),'end':q(1)},{'start':q(1),'end':q(2)},['IV','ii6'],'C')
        self.assertTrue(r['boundary_snapshot_evidence']['iv_to_ii6_five_six_candidate'])
        self.assertFalse(r['union_is_simultaneous'])

    def test_reject_gap_and_duplicate(self):
        with self.assertRaises(ValueError):
            compare_spans({'sounding_events':[]},{'start':q(0),'end':q(1)},
                         {'start':q(2),'end':q(3)},['IV','ii6'],'C')
        s=sound('x',0,1,'C',4,60)
        with self.assertRaises(ValueError):
            span_observation({'sounding_events':[s,s]},{'start':q(0),'end':q(1)})

    def test_source_normalization_not_secondary(self):
        r={'localkey':'I','globalkey':'C','numeral':'V','figbass':'2'}
        self.assertEqual(source_candidate({'raw_fields':r}),('V42','C','major'))
        r['relativeroot']='V'
        self.assertIsNone(source_candidate({'raw_fields':r}))
