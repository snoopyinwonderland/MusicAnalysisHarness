import unittest
from copy import deepcopy
from test_harmony_bass_return import setup
from musicanote_harness.harmony_bass_return import compare_chain
from musicanote_harness.harmony_incomplete_triads import omission,augment_chain,run


def row(root=('F',0),members=None,missing=None):
    return {'candidate_ref':'test','alternative_index':0,'reading_index':0,'root_spelling':list(root),
            'members':members or [['F',0],['A',0],['C',0]],'missing_members':missing or [['C',0]],
            'nonmember_event_refs':[],'other_nonmember_refs':[],'candidate_blockers':[],'bass_is_member':True}


class IncompleteTriadTests(unittest.TestCase):
    def test_major_fifth_is_assumption_not_observation(self):
        a=omission(row());self.assertTrue(a['eligible_for_conditional_comparison'])
        self.assertEqual(a['assumed_missing_pitch'],['C',0])
        self.assertFalse(a['omission_confirmed']);self.assertFalse(a['virtual_events_created'])
        self.assertFalse(a['assumption_is_evidence'])

    def test_minor_and_transposition(self):
        a=omission(row(('G',0),[['G',0],['B',-1],['D',0]],[['D',0]]))
        self.assertTrue(a['eligible_for_conditional_comparison']);self.assertEqual(a['assumed_quality'],'m')

    def test_root_not_invented(self):
        a=omission(row(missing=[['F',0]]))
        self.assertFalse(a['eligible_for_conditional_comparison'])

    def test_third_not_invented(self):
        self.assertFalse(omission(row(missing=[['A',0]]))['eligible_for_conditional_comparison'])

    def test_multiple_missing_not_excused(self):
        self.assertFalse(omission(row(missing=[['A',0],['C',0]]))['eligible_for_conditional_comparison'])

    def test_augmented_and_diminished_fifth_not_ordinary_omission(self):
        for members,missing in [([['F',0],['A',0],['C',1]],[['C',1]]),([['F',0],['A',-1],['C',-1]],[['C',-1]])]:
            self.assertFalse(omission(row(members=members,missing=missing))['eligible_for_conditional_comparison'])

    def test_seventh_omissions_deferred(self):
        self.assertFalse(omission(row(members=[['F',0],['A',0],['C',0],['E',-1]]))['eligible_for_conditional_comparison'])

    def test_blocker_and_other_nonmember_not_erased(self):
        for field in ('candidate_blockers','other_nonmember_refs'):
            r=row();r[field]=['unresolved']
            self.assertFalse(omission(r)['eligible_for_conditional_comparison'])

    def test_original_strict_result_and_inputs_preserved(self):
        r,ir,c=setup(missing=True);before=deepcopy((r,ir));base=compare_chain(r,c)
        a=augment_chain(base)
        self.assertEqual(a['comparisons'][0]['status'],base['comparisons'][0]['status'])
        self.assertEqual(a['comparisons'][0]['clean_combination_count'],0)
        self.assertGreater(a['comparisons'][0]['omission_comparison']['assumption_dependent_combination_count'],0)
        self.assertEqual((r,ir),before);self.assertNotIn('omission_hypotheses',next(iter(base['interval_tables'].values())))

    def test_observationally_equivalent_augmented_candidate_preserved(self):
        r,ir,c=setup(missing=True);base=compare_chain(r,c)
        ref=base['comparisons'][0]['interval_refs'][1];table=base['interval_tables'][ref]
        aug=deepcopy(table['readings'][1]);aug.update(reading_index=3,candidate_ref='augmented',members=[['G',0],['B',0],['D',1]],missing_members=[['D',1]])
        table['readings'].append(aug)
        a=augment_chain(base);hypotheses=a['interval_tables'][ref]['omission_hypotheses']
        self.assertIn(3,hypotheses[1]['observationally_equivalent_reading_indices'])
        self.assertFalse(hypotheses[3]['eligible_for_conditional_comparison'])
        self.assertFalse(hypotheses[1]['quality_confirmed'])

    def test_labels_do_not_change_assumption(self):
        r=row();before=omission(r);r['display_label']='known answer';self.assertEqual(omission(r),before)

    def test_complete_triads_need_no_assumption(self):
        r,ir,c=setup();a=augment_chain(compare_chain(r,c))['comparisons'][0]['omission_comparison']
        self.assertEqual(a['status'],'strict_support_only');self.assertEqual(a['assumption_dependent_combination_count'],0)

    def test_pipeline_retains_gate_and_raw_events(self):
        r,ir,c=setup(missing=True);saved=deepcopy((r,ir));a=run(r,{'status':'ready'},ir)
        self.assertEqual((r,ir),saved);self.assertFalse(a['gate_changed'])


if __name__=='__main__':unittest.main()
