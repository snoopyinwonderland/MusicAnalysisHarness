from copy import deepcopy
from fractions import Fraction as F
import unittest
from test_harmony_reading_voice_context import score
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_distributed_readings import observe
from musicanote_harness.harmony_reading_voice_context import compare as voice_compare
from musicanote_harness.harmony_reading_contrast import compare


def inputs(kind):
    if kind=='merged':pitches=['C3','E3','G3','C3','E3','G3','B3','E3','F3','A3','C4','F3'];upper=('B4','A4')
    elif kind=='split':pitches=['B2','D3','F#3','B2','D3','F#3','A3','D3','G3','B3','D4','G3'];upper=('F#4','G4')
    else:pitches=['C3','E3','G3','C3','E3','G3','B-3','E3','F3','A3','C4','F3'];upper=('E4','F4')
    ir=score([(p,F(i,2),F(i+1,2),'lower') for i,p in enumerate(pitches)]+[(upper[0],F(7,2),4,'upper'),(upper[1],4,6,'upper')])
    ir['measures'][0]['actual_duration_quarter']=q(6)
    c=next(c for c in observe(ir)['alternatives'] if c['span']=={'start':q(0),'end':q(4)} and c['boundary']==q(2))
    return ir,c,voice_compare(ir,c)


class ContrastTests(unittest.TestCase):
    def test_shared_resolution_not_differentiating(self):
        ir,c,v=inputs('shared');r=compare(c,v)
        self.assertTrue(any(e['status']=='shared_between_families' for e in r['evidence_units']))
        self.assertFalse(r['has_family_differentiating_support'])

    def test_seventh_supports_merged_only_not_winner(self):
        ir,c,v=inputs('merged');r=compare(c,v)
        self.assertTrue(any(e['status']=='merged_seventh_only_conditional_support' for e in r['evidence_units']))
        self.assertIsNone(r['selected_hypothesis']);self.assertFalse(r['reranking_performed'])

    def test_dominant_third_supports_split_only_not_winner(self):
        ir,c,v=inputs('split');r=compare(c,v)
        self.assertTrue(any(e['status']=='split_triads_only_conditional_support' for e in r['evidence_units']))
        self.assertTrue(all(p['status']!='counterevidence' for e in r['evidence_units'] for p in e['per_reading']))

    def test_duplicates_do_not_increase_evidence_units(self):
        ir,c,v=inputs('shared');a=compare(c,v)
        for r in v['readings']:r['external_comparisons']+=deepcopy(r['external_comparisons'])
        self.assertEqual(a,compare(c,v))

    def test_different_role_tags_for_same_motion_are_shared(self):
        ir,c,v=inputs('shared')
        # Evidence interface fixture: two conditional roles on one physical pair.
        for r in v['readings']:
            for e in r['external_comparisons']:
                for p in e['relations']:
                    if p['relations'] and r['reading_type']=='merged_seventh':p['relations']=['conditional_seventh_down_step_to_member']
        self.assertFalse(compare(c,v)['has_family_differentiating_support'])

    def test_incomplete_evaluation_not_differentiating(self):
        ir,c,v=inputs('merged');v['readings'][-1]['external_comparisons']=[]
        r=compare(c,v)
        self.assertTrue(any(e['status']=='incomplete_comparison' for e in r['evidence_units']))
        self.assertFalse(r['has_family_differentiating_support'])

    def test_invalid_identity_and_cost_fail_closed(self):
        ir,c,v=inputs('merged')
        for key,value in [('candidate_ref','other')]:
            with self.assertRaises(ValueError):compare(c,{**v,key:value})
        v['readings'][0]['source_cost_unchanged']+=1
        with self.assertRaises(ValueError):compare(c,v)

    def test_missing_reading_fails_closed(self):
        ir,c,v=inputs('merged');v['readings'].pop()
        with self.assertRaises(ValueError):compare(c,v)

    def test_input_immutable_and_title_not_used(self):
        ir,c,v=inputs('merged');saved=deepcopy((c,v));a=compare(c,v)
        self.assertEqual((c,v),saved)
        self.assertEqual(a,compare({**c,'title':'other','annotations':['I']},v))

    def test_candidate_features_not_new_votes(self):
        ir,c,v=inputs('merged');r=compare(c,v)
        self.assertEqual(r['boundary_observations']['scope'],'candidate_construction_features_not_additional_votes')
        self.assertTrue(all(not e['independent_vote'] and e['ranking_weight'] is None for e in r['evidence_units']))


if __name__=='__main__':unittest.main()
