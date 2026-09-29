import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from musicanote_harness.sonata_verification import sample_windows, observation_rows, projected_track
from musicanote_harness.source_identity_revision import revise, validate_revision
from musicanote_harness.dcml_import import parse_score_without_imported_harmony
from musicanote_harness.canonical import CanonicalIRBuilder
from musicanote_harness.formal_ir import FormalIRAdapter, q
from test_source_identity_revision import XML


class SonataVerificationTests(unittest.TestCase):
    def test_sample_is_annotation_independent(self):
        ir={'measures':[{'global_start_quarter':q(i*4),'actual_duration_quarter':q(4),
            'printed_measure_number':str(i)} for i in range(20)]}
        before=sample_windows(ir)
        ir['annotations']=[{'cadence':'PAC','time':3}]
        self.assertEqual(before,sample_windows(ir))
        self.assertEqual([w['physical_start'] for w in before],[1,9,17])
        self.assertEqual(before[-1]['span']['end'],q(80))

    def test_short_score_does_not_duplicate_windows(self):
        ir={'measures':[{'global_start_quarter':q(0),'actual_duration_quarter':q(1),
                        'printed_measure_number':'0'}]}
        self.assertEqual(len(sample_windows(ir)),1)
        self.assertEqual(sample_windows(ir)[0]['span']['end'],q(1))

    def test_empty_score_rejected(self):
        with self.assertRaises(ValueError): sample_windows({'measures':[]})

    def test_repair_context_selected_once_with_neighboring_measures(self):
        ir={'measures':[{'global_start_quarter':q(i*4),'actual_duration_quarter':q(4),
            'printed_measure_number':str(i)} for i in range(30)]}
        proof={'edits':[{'physical_measure':7}]*7}
        windows=sample_windows(ir,repair_proof=proof)
        repaired=[w for w in windows if w['repair_context']]
        self.assertEqual(len(repaired),1)
        self.assertEqual((repaired[0]['physical_start'],repaired[0]['physical_end']),(6,9))
        with self.assertRaisesRegex(ValueError,'out_of_range'):
            sample_windows(ir,repair_proof={'edits':[{'physical_measure':31}]})

    def test_replay_matches_graces_and_physical_measures(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'fixture.musicxml'; p.write_text(XML,encoding='utf-8')
            score,_,_=parse_score_without_imported_harmony(p)
            old=FormalIRAdapter().convert(CanonicalIRBuilder().build(score,p),p)
            frozen=deepcopy(old)
            rows=observation_rows(old,p)
            corrected,_=revise(old,rows,p)
            self.assertTrue(validate_revision(old,corrected)['schema'])
            self.assertEqual(old,frozen)
            self.assertEqual(len(rows),len(old['note_events'])+len(old['rest_events']))

    def test_source_key_missing_does_not_invent_roman(self):
        result={'engine_version':'test','segments':[{'span':{'start':q(0),'end':q(1)},
                 'selected':{'root':0,'label':'C:major'},'alternatives':[]}]}
        frozen=deepcopy(result)
        track=projected_track({},result,[],'experiment','test')
        self.assertEqual(track['segments'][0]['roman'],'unknown')
        self.assertEqual(result,frozen)
