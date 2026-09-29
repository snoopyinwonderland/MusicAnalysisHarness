import unittest
from musicanote_harness.harmony_review_cohort import validate_split,tags


class CohortTests(unittest.TestCase):
    def test_cross_family_split_rejected(self):
        e={'split':'train','work_family_id':'w','score_sha256':'s','annotation_sha256':'a'}
        for field in ('work_family_id','score_sha256','annotation_sha256'):
            other={'split':'dev','work_family_id':'w2','score_sha256':'s2','annotation_sha256':'a2'}
            other[field]=e[field]
            with self.assertRaises(ValueError):validate_split([e,other])

    def test_nonvertical_is_not_called_nct(self):
        r={'observation':{'union_shapes':[],'slices':[{'shapes':[]}]},
           'comparison':{'source_quality':'major','source_inversion':1}}
        t=tags(r)
        self.assertIn('no_complete_shape_needs_review',t)
        self.assertFalse(any('nct' in x or 'omission' in x for x in t))

    def test_distributed_is_candidate(self):
        r={'observation':{'union_shapes':[{}],'slices':[{'shapes':[]}]},
           'comparison':{'source_quality':'minor','source_inversion':0}}
        self.assertIn('distributed_complete_shape_candidate',tags(r))
