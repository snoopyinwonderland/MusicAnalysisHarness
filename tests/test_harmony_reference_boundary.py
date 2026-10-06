from copy import deepcopy
import unittest
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_reference_boundary import classify, diagnose
from test_harmony_shared_context import fixture
from musicanote_harness.harmony_reference_boundary_trial import time_axis


def ann(ident, start, end, numeral='I', fig='', quality='M'):
    return {'annotation_id': ident, 'raw_label': numeral+fig,
        'raw_fields': {'globalkey': 'C', 'localkey': 'I', 'localkey_is_minor': '0',
                       'numeral': numeral, 'figbass': fig, 'chord_type': quality, 'form': ''},
        'target': {'span': {'start': q(start), 'end': q(end)}}}


class ReferenceBoundaryTests(unittest.TestCase):
    def run_ref(self, rows, cut=1, valid=None):
        return classify({'start': q(0), 'end': q(3)}, q(cut), rows,
                        {a['annotation_id'] for a in rows} if valid is None else valid)

    def test_hold_inside_label(self):
        self.assertEqual(self.run_ref([ann('a',0,3)])['source_class'],'source_hold')

    def test_same_label_rows_not_change(self):
        self.assertEqual(self.run_ref([ann('a',0,1),ann('b',1,3)])['source_class'],'source_hold')

    def test_real_member_change(self):
        self.assertEqual(self.run_ref([ann('a',0,1),ann('b',1,3,'V')])['source_class'],'source_member_change')

    def test_inversion_not_member_change(self):
        self.assertEqual(self.run_ref([ann('a',0,1),ann('b',1,3,fig='6')])['source_class'],
                         'source_same_members_semantic_change')

    def test_gap_not_bridged(self):
        self.assertEqual(self.run_ref([ann('a',0,1),ann('b',2,3)])['status'],'annotation_gap')

    def test_overlap_not_arbitrated(self):
        self.assertEqual(self.run_ref([ann('a',0,2),ann('b',1,3)])['status'],'annotation_overlap')

    def test_invalid_row_not_skipped(self):
        self.assertEqual(self.run_ref([ann('a',0,1),ann('b',1,3)],valid={'a'})['status'],'unverified_alignment')

    def test_offcut_change_not_relocated(self):
        self.assertEqual(self.run_ref([ann('a',0,2),ann('b',2,3,'V')])['status'],
                         'multiple_reference_changes_within_side')

    def test_secondary_not_silently_erased(self):
        a=ann('a',0,3,'V',fig='7',quality='Mm7');a['raw_fields']['relativeroot']='V'
        self.assertEqual(self.run_ref([a])['status'],'unsupported_reference_chord')

    def test_pedal_is_explicit_exclusion(self):
        a=ann('a',0,3);a['raw_fields']['pedal']='I'
        ref=self.run_ref([a]);self.assertEqual(ref['unsupported_features'],['pedal'])
        self.assertEqual(ref['source_annotations'],[a])

    def test_endpoint_is_half_open(self):
        self.assertEqual(self.run_ref([ann('a',0,3),ann('b',3,4,'V')])['annotation_refs'],['a'])

    def test_empty_identity(self):
        a=ann('a',0,3);a['raw_fields']['numeral']=''
        self.assertEqual(self.run_ref([a])['status'],'missing_chord_identity')

    def test_diagnostic_not_prediction_or_mutation(self):
        r=fixture();saved=deepcopy(r);ref=self.run_ref([ann('a',0,3)])
        d=diagnose(r,0,ref)
        self.assertEqual(d['status'],'ready');self.assertIsNone(d['preferred'])
        self.assertTrue(all(c['same_harmony_invariant_passed'] for c in d['comparisons']))
        self.assertEqual(saved,r)

    def test_missing_candidate_is_not_detection_error(self):
        r=fixture();ref=self.run_ref([ann('a',0,3,'V')])
        self.assertEqual(diagnose(r,0,ref)['status'],'reference_members_missing_from_candidates')

    def test_rejected_reference_has_no_comparison(self):
        self.assertEqual(diagnose(fixture(),0,{'status':'annotation_gap'})['comparisons'],[])

    def test_invalid_cut(self):
        with self.assertRaises(ValueError): self.run_ref([ann('a',0,3)],cut=0)

    def test_written_time_not_printed_number(self):
        a={'measures':[{'printed_measure_number':'8','sequential_measure_index':9,
            'global_start_quarter':q(24),'actual_duration_quarter':q(1),
            'nominal_duration_quarter':q(3),'time_signature':{'beats':3,'beat_type':4}}]}
        b=deepcopy(a);b['measures'][0]['printed_measure_number']='X1'
        self.assertEqual(time_axis(a),time_axis(b))
        b['measures'][0]['global_start_quarter']=q(25)
        self.assertNotEqual(time_axis(a),time_axis(b))


if __name__ == '__main__': unittest.main()
