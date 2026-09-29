import copy
import unittest
from musicanote_harness.harmony_medium_review import select, categories, aggregate
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_temporal_shadow import analyze
from test_harmony_joint import fixture


def row(i, family='family', collection='c', tags=None):
    return {'case_id':str(i),'work_family_id':family,'collection':collection,'split':'train',
            'tags':tags or ['source_short_change_candidate']}


class MediumReviewTests(unittest.TestCase):
    def test_review_flags_not_musical_error_or_unknown_success(self):
        item={'case_id':'x','stratum':'short_change','context_stable':{'baseline':True,'experiment':False},
              'runs':[{'margin_quarters':q(2),'delta':{'same_labels_at_all_target_times':False,'same_internal_boundaries':True},
                       'target_segments':{'baseline':1,'experiment':1},
                       'target_edge_support':{'experiment':{'start':False,'end':True}}}]}
        unknown={'case_id':'z','stratum':'short_change','context_stable':{'baseline':None,'experiment':None},'runs':[]}
        r=aggregate([item,unknown]);group=r['strata']['short_change']
        self.assertEqual(r['lost_context_stability'],1)
        self.assertEqual(group['unknown_stability'],1)
        self.assertEqual(group['paired_cases_at_margin_two'],1)
        self.assertFalse(r['review_queue'][0]['musical_error_confirmed'])
        self.assertIn('short_change_proxy_edges_not_both_supported',r['review_queue'][0]['flags'])

    def test_selection_order_independent_and_nonmutating(self):
        rows=[row(i,'f'+str(i%4),'c'+str(i%2)) for i in range(12)];original=copy.deepcopy(rows)
        self.assertEqual(select(rows),select(list(reversed(rows))))
        self.assertEqual(rows,original)

    def test_family_cap_and_category_budget(self):
        rows=[row(i,tags=['distributed_complete_shape_candidate','source_short_change_candidate']) for i in range(12)]
        chosen=select(rows,per_category=5,family_cap=4)
        self.assertEqual(len(chosen),4)
        self.assertEqual(len({r['case_id'] for c,r in chosen}),4)

    def test_prefers_underrepresented_collections(self):
        rows=[row('a'+str(i),'fa'+str(i),'a') for i in range(8)]+[row('z','fz','z')]
        chosen=select(rows,per_category=2)
        self.assertEqual({r['collection'] for c,r in chosen},{'a','z'})

    def test_rejects_reserved_duplicate_and_invalid_caps(self):
        r=row(0);r['split']='holdout'
        with self.assertRaisesRegex(ValueError,'non_train'):select([r])
        with self.assertRaisesRegex(ValueError,'duplicate'):select([row(0),row(0)])
        with self.assertRaises(ValueError):select([],family_cap=0)

    def test_seventh_tags_case_sensitive_and_overlapping(self):
        r=row(0,tags=['source_seventh_Mm7','source_short_change_candidate'])
        self.assertEqual(categories(r),['short_change','seventh'])

    def test_distributed_triad_not_split_by_temporal_penalty(self):
        ir=fixture([(60,0,1,'v'),(64,1,2,'v'),(67,2,3,'v'),(64,3,4,'v')])
        r=analyze(ir,cell_divisions=2)
        self.assertEqual([s['selected']['label'] for s in r['segments']],['C:major'])

    def test_clear_vertical_change_remains(self):
        ir=fixture([(p,a,b,str(i)) for a,b,ps in [(0,2,[48,52,55]),(2,4,[55,59,62])] for i,p in enumerate(ps)])
        self.assertEqual([s['selected']['label'] for s in analyze(ir,cell_divisions=2)['segments']],['C:major','G:major'])
