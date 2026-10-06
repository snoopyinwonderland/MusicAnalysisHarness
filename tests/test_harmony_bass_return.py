import unittest
from copy import deepcopy
from test_harmony_distributed_resolution import fixture
from musicanote_harness.harmony_repeated_bass import chains
from musicanote_harness.harmony_bass_return import compare_chain,run


def setup(missing=False,foreign=False):
    specs=[('C3',0,1,'b'),('C3',1,2,'b'),('C3',2,3,'b')]
    for start,pitches in [(0,['C4','E4','G4']),(1,['G4','B4'] if missing else ['G4','B4','D5']),(2,['C4','E4','G4'])]:
        specs += [(pitch,start,start+1,str(i)) for i,pitch in enumerate(pitches)]
    if foreign:specs.append(('F#4',1,2,'foreign'))
    r,p,ir=fixture(specs)
    forms=[(['C',0],[['C',0],['E',0],['G',0]]),(['G',0],[['G',0],['B',0],['D',0]]),
           (['C',0],[['C',0],['E',0],['G',0],['B',0],['D',0]])]
    for edge in r['edges']:
        template=edge['readings'][0];edge['readings']=[]
        for i,(root,members) in enumerate(forms):
            edge['readings'].append({**deepcopy(template),'candidate_ref':str(i),'root_spelling':root,'members':members})
    return r,ir,chains(r,ir)['chains'][0]


class BassReturnTests(unittest.TestCase):
    def test_three_segments_have_return_but_no_pedal_verdict(self):
        r,ir,c=setup();a=compare_chain(r,c)
        self.assertEqual(len(a['comparisons']),1)
        self.assertEqual(a['comparisons'][0]['status'],'clean_membership_return_possible')
        self.assertFalse(a['pedal_confirmed']);self.assertFalse(a['bass_exempted'])
        self.assertFalse(a['comparisons'][0]['joint_voice_assignment_verified'])

    def test_unobserved_member_blocks_clean_shape(self):
        r,ir,c=setup(missing=True);a=compare_chain(r,c)['comparisons'][0]
        self.assertEqual(a['status'],'membership_return_shape_only')
        self.assertEqual(a['clean_combination_count'],0)

    def test_unexplained_upper_tone_not_excused_by_bass(self):
        r,ir,c=setup(foreign=True)
        self.assertEqual(compare_chain(r,c)['comparisons'][0]['status'],'membership_return_shape_only')

    def test_all_members_middle_has_no_return_candidate(self):
        r,ir,c=setup()
        for e in r['edges']:e['readings']=[e['readings'][0]]
        self.assertEqual(compare_chain(r,c)['comparisons'][0]['status'],'no_membership_return_shape')

    def test_whole_union_candidate_not_selected_by_coverage(self):
        r,ir,c=setup();a=compare_chain(r,c)
        self.assertIn(2,a['whole_interval_clean_bass_member_indices'])
        self.assertIsNone(a['selected'])

    def test_upper_events_retained(self):
        r,ir,c=setup();a=compare_chain(r,c)
        refs={sid for cell in a['upper_cells'] for sid in cell['other_event_refs']}
        self.assertEqual(refs,{s['sounding_event_id'] for s in r['events']}-set(c['event_refs']))
        self.assertNotEqual(a['upper_cells'][0]['other_spellings'],a['upper_cells'][1]['other_spellings'])

    def test_blocker_retained_and_not_clean(self):
        r,ir,c=setup()
        for e in r['edges']:e['readings'][1]['abstention_reasons']=['blocked']
        self.assertEqual(compare_chain(r,c)['comparisons'][0]['clean_combination_count'],0)

    def test_duplicate_origins_preserved_in_factors(self):
        r,ir,c=setup()
        for e in r['edges']:
            d=deepcopy(e['readings'][0]);d['candidate_ref']='duplicate-origin';e['readings'].append(d)
        a=compare_chain(r,c)['comparisons'][0]
        self.assertIn(3,a['clean_return_reading_groups'][0])
        self.assertIn(3,a['clean_return_reading_groups'][2])

    def test_budget_abstains_without_subset(self):
        r,ir,c=setup()
        # Use source with more grid cells, preserving its actual lattice.
        from test_harmony_repeated_bass import setup as repeated
        r,p,ir=repeated(extra=[('E5','1/2','3/2','extra')]);c=chains(r,ir)['chains'][0]
        a=compare_chain(r,c,partition_budget=1)
        self.assertEqual(a['status'],'partition_budget_abstention_no_pruning');self.assertEqual(a['comparisons'],[])

    def test_unchanged_input_and_gate(self):
        r,ir,c=setup();saved=deepcopy((r,ir));a=run(r,{'status':'ready'},ir)
        self.assertEqual((r,ir),saved);self.assertFalse(a['gate_changed'])

    def test_wrong_ir_rejected(self):
        r,ir,c=setup();ir=deepcopy(ir);ir['sounding_events'].pop()
        with self.assertRaisesRegex(ValueError,'coverage_mismatch'):run(r,{'status':'ready'},ir)


if __name__=='__main__':unittest.main()
