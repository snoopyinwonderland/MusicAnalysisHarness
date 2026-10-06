from copy import deepcopy
from fractions import Fraction as F
import unittest

from musicanote_harness.harmony_candidate_recall import rational as q
from musicanote_harness.harmony_common_benchmark import (
    GRID, evaluate, identity_overlap, native_prediction, native_reference, onset_prediction,
    partition, readiness, summarize,
)

C = [["C", 0], [["C", 0], ["E", 0], ["G", 0]]]
G = [["G", 0], [["G", 0], ["B", 0], ["D", 0]]]


def span(a, b): return {"start": q(F(a)), "end": q(F(b))}
def cell(a, b, sig=None, **other):
    return {"span": span(a, b), "labels": ({"root": sig[0], "root_members": sig} if sig else {}) | other}


class CommonBenchmarkTests(unittest.TestCase):
    def metric(self, ref, pred, extent=(0, 2), selected=True):
        return evaluate(ref, pred, span(*extent), selected=selected)

    def test_perfect_exact_and_grid(self):
        v=self.metric([cell(0,1,C),cell(1,2,G)],[cell(0,1,C),cell(1,2,G)])
        self.assertTrue(v['selected_hit']); self.assertEqual(v['components']['root_members']['matched'],q(F(2)))
        self.assertEqual(v['components']['root']['grid_matched'],16)
        self.assertEqual(v['semantic_boundary_exact'],{'matched':1,'extra':0,'missed':0})

    def test_undersegmentation(self):
        v=self.metric([cell(0,1,C),cell(1,2,G)],[cell(0,2,C)])
        self.assertEqual(v['semantic_boundary_exact']['missed'],1)
        self.assertEqual(v['components']['root_members']['matched'],q(F(1)))

    def test_same_signature_split_is_not_boundary(self):
        v=self.metric([cell(0,2,C)],[cell(0,1,C),cell(1,2,C)])
        self.assertTrue(v['selected_hit']);self.assertEqual(v['semantic_boundary_exact']['extra'],0)

    def test_abstention_keeps_denominator(self):
        v=self.metric([cell(0,1,C),cell(1,2,G)],[cell(0,2)],selected=False)
        self.assertEqual(v['components']['root_members']['eligible'],q(F(2)))
        self.assertEqual(v['components']['root_members']['matched'],q(F()))
        self.assertEqual(v['semantic_boundary_exact']['missed'],1);self.assertFalse(v['selected_hit'])

    def test_partial_reference_not_full_boundary(self):
        v=self.metric([cell(0,1,C),cell(1,2)],[cell(0,2,C)])
        self.assertIsNone(v['selected_hit']);self.assertIsNone(v['semantic_boundary_exact'])
        self.assertEqual(v['components']['root_members']['eligible'],q(F(1)))

    def test_enharmonic_root_not_equal(self):
        a=[["F",1],[["F",1],["A",1],["C",1]]]
        b=[["G",-1],[["G",-1],["B",-1],["D",-1]]]
        self.assertFalse(self.metric([cell(0,2,a)],[cell(0,2,b)])['selected_hit'])

    def test_member_order_duplicate_normalization(self):
        b=deepcopy(C);b[1]=list(reversed(b[1]))+[b[1][0]]
        self.assertTrue(self.metric([cell(0,2,C)],[cell(0,2,b)])['selected_hit'])

    def test_root_correct_members_wrong(self):
        b=deepcopy(C);b[1].append(['B',0])
        v=self.metric([cell(0,2,C)],[cell(0,2,b)])
        self.assertEqual(v['components']['root']['matched'],q(F(2)))
        self.assertEqual(v['components']['root_members']['matched'],q(F()))

    def test_exact_thirds_not_grid_metric(self):
        v=self.metric([cell(0,F(1,3),C),cell(F(1,3),1,G)],[cell(0,1,C)],(0,1))
        self.assertEqual(GRID,F(1,8));self.assertEqual(v['components']['root']['matched'],q(F(1,3)))
        self.assertEqual(v['components']['root']['grid_matched'],3)

    def test_global_grid_phase_and_end_exclusion(self):
        v=self.metric([cell(F(1,16),F(3,16),C)],[cell(F(1,16),F(3,16),C)],(F(1,16),F(3,16)))
        self.assertEqual(v['components']['root']['grid_eligible'],1)
        v=self.metric([cell(0,F(1,8),C)],[cell(0,F(1,8),C)],(0,F(1,8)))
        self.assertEqual(v['components']['root']['grid_eligible'],1)

    def test_components_availability_and_zero_inversion(self):
        v=self.metric([cell(0,2,C,quality='major',inversion=0,local_key={'tonic':['C',0],'mode':'major'},degree='1',roman='I')],
                      [cell(0,2,C,inversion=0)])
        self.assertEqual(v['components']['inversion']['matched'],q(F(2)))
        self.assertEqual(v['components']['roman']['eligible'],q(F(2)))
        self.assertEqual(v['components']['roman']['covered'],q(F()))

    def test_missing_roman_does_not_inherit_root_success(self):
        v=self.metric([cell(0,2,C)],[cell(0,2,C)])
        r=summarize([{'work_family_id':'a','evaluation':v}])
        self.assertIsNone(r['components']['roman']['time_agreement'])
        self.assertEqual(r['components']['roman']['unavailable_reference_time'],q(F(2)))

    def test_micro_and_family_macro_are_distinct(self):
        a=self.metric([cell(0,2,C)],[cell(0,2,C)])
        b=self.metric([cell(0,1,G)],[cell(0,1,C)],(0,1))
        v=summarize([{'work_family_id':'a','evaluation':a},{'work_family_id':'b','evaluation':b}])
        self.assertEqual(v['components']['root']['time_agreement'],2/3)
        self.assertEqual(v['components']['root']['work_family_macro'],.5)

    def test_prefix_unknown_next_onset_and_last_release(self):
        rows=onset_prediction([{'onset':q(F(1,2)),'labels':{'root':C[0],'root_members':C}},
                               {'onset':q(F(1)),'labels':{'root':G[0],'root_members':G}}],span(0,2),clock='canonical_global_quarter')
        self.assertEqual(rows[0],cell(0,F(1,2)));self.assertEqual(rows[-1]['span'],span(1,2))
        self.assertEqual(rows[1]['span'],span(F(1,2),1))

    def test_empty_onsets_unknown_not_first_chord_fill(self):
        self.assertEqual(onset_prediction([],span(0,2),clock='canonical_global_quarter'),[cell(0,2)])

    def test_native_clock_is_not_quarter_assumption(self):
        with self.assertRaisesRegex(ValueError,'external_clock_mapping_required'):
            onset_prediction([],span(0,2),clock='partitura_onset_beat')

    def test_bad_onsets(self):
        for points in ([1,1],[1,0],[-1],[2]):
            with self.subTest(points=points), self.assertRaises(ValueError):
                onset_prediction([{'onset':q(F(x)),'labels':{}} for x in points],span(0,2),clock='canonical_global_quarter')

    def test_partition_invalid_and_float(self):
        for rows in ([cell(0,1,C)], [cell(0,1,C),cell(F(1,2),2,G)], [cell(0,0,C)], [cell(1,2,C)]):
            with self.assertRaises(ValueError):partition(rows,span(0,2))
        with self.assertRaises(ValueError):partition([cell(0,2,C)],{'start':0.0,'end':q(F(2))})

    def test_schema_rejects_unknown_string_bad_root_and_bool_inversion(self):
        for row in (cell(0,2,C,roman='unknown'),cell(0,2,C,inversion=True),cell(0,2,C,bogus='I'),
                    cell(0,2,C,root=['G',0])):
            with self.subTest(row=row),self.assertRaises(ValueError):partition([row],span(0,2))

    def test_abstention_with_output_rejected(self):
        with self.assertRaises(ValueError):self.metric([cell(0,2,C)],[cell(0,2,C)],selected=False)

    def test_native_adapter_no_function_invention(self):
        raw={'reference_cells':[{'span':span(0,2),'signature':C}]}
        self.assertEqual(native_reference(raw),[cell(0,2,C)])
        pred={'source_labels_used_for_selection':False,'segments':[{'span':span(0,2),'root_spelling':C[0],'members':C[1]}]}
        self.assertEqual(native_prediction(pred,span(0,2)),[cell(0,2,C)])
        self.assertEqual(native_prediction(None,span(0,2)),[cell(0,2)])

    def test_training_adversary_or_gold_input_rejected(self):
        for raw in ({'source_labels_used_for_selection':True},
                    {'source_labels_used_for_selection':False,'training_reference_labels_used':True}):
            with self.assertRaises(ValueError):native_prediction(raw,span(0,2))

    def test_empty_summary_no_zero_accuracy_claim(self):
        v=summarize([]);self.assertIsNone(v['selected_context_agreement'])
        self.assertIsNone(v['components']['root']['time_agreement'])


class ReadinessTests(unittest.TestCase):
    def entry(self):
        return {'manifest_entry_id':'m','work_family_id':'f','collection_id':'c','movement_id':'1',
                'work_family_source_key':'w','package_path':'p','split':'holdout','score_sha256':'s',
                'annotation_sha256':'a','annotation_lineage_id':'l',
                'quality':{'source_note_mapping_complete':True},'eligibility':{'blind_evaluation':True},
                'rights':{'internal_research_use':True,'model_training_approved':False}}

    def test_all_identity_aliases_exclude(self):
        e=self.entry()
        for field in ('work_family_id','score_sha256','annotation_sha256','annotation_lineage_id'):
            self.assertEqual(identity_overlap(e,[{field:e[field]}]),[field])
            self.assertIn('known_development_identity_overlap',readiness([e],[{field:e[field]}],[])[0]['reasons'])

    def test_prior_result_excludes_whole_family(self):
        e=self.entry();d=deepcopy(e)
        r=readiness([e],[],[{'work_family_id':'f','musical_result_exposed':True}])[0]
        self.assertTrue(r['known_exposure_excluded']);self.assertEqual(e,d)

    def test_candidate_is_not_approved(self):
        r=readiness([self.entry()],[],[])[0]
        self.assertEqual(r['status'],'metadata_candidate_not_blind_approved')
        self.assertFalse(r['blind_evaluation_approved_by_this_audit'])

    def test_incomplete_mapping_and_rights_remain_blocked(self):
        e=self.entry();e['quality']['source_note_mapping_complete']=False;e['rights']['internal_research_use']=False
        r=readiness([e],[],[])[0]
        self.assertIn('incomplete_source_note_mapping',r['reasons']);self.assertIn('internal_research_use_absent',r['reasons'])

    def test_non_holdout_not_relabelled(self):
        e=self.entry();e['split']='dev';self.assertEqual(readiness([e],[],[]),[]);self.assertEqual(e['split'],'dev')


if __name__ == '__main__': unittest.main()
