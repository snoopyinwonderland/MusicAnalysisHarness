from copy import deepcopy
import unittest
from test_harmony_open_candidates import score
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_candidate_catalog import propose
from musicanote_harness.harmony_voice_paths import observe
from musicanote_harness.harmony_path_ornaments import explain,augment


def fixture(names=('G4','A4','B4'),poly=False,gap=False):
    rows=[(p,i,i+1,'v') for i,p in enumerate(names)]
    if gap:rows[1]=(names[1],1.25,2,'v')
    if poly:rows += [('D5',0,1,'v'),('E5',1,2,'v'),('F#5',2,3,'v')]
    rows += [('G3',0,3,'b'),('D4',0,3,'f')]
    ir=score(rows);span={'start':q(0),'end':q(3)}
    cat=propose(ir,span)
    c=next(c for c in cat['candidates'] if c['root']['spelling']==['G',0] and c['member_pitch_classes']==[2,7,11])
    return ir,observe(ir,span,('part1','v')),c


class PathOrnamentTests(unittest.TestCase):
    def test_passing_is_assignment_dependent_never_fact(self):
        _,row,c=fixture();r=explain(row,c,0)
        self.assertEqual(len(r['patterns']),1)
        p=r['patterns'][0];self.assertEqual(p['conditional_role'],'passing_candidate')
        self.assertFalse(p['common_to_all_assignments']);self.assertFalse(p['nct_confirmed'])
        self.assertFalse(p['remove_note']);self.assertEqual(len(p['supporting_assignment_refs']),1)

    def test_unconnected_alternative_preserves_nonmember(self):
        _,row,c=fixture();r=explain(row,c,0)
        self.assertEqual(r['assignments'][0]['conditional_nonmember_time'],q(0))
        self.assertEqual(r['assignments'][0]['unexplained_nonmember_time'],q(1))
        self.assertEqual(r['note_time_by_state']['nonmember_not_confirmed_nct'],q(1))

    def test_neighbor_role(self):
        _,row,c=fixture(('B4','C5','B4'));r=explain(row,c,0)
        self.assertEqual(r['patterns'][0]['conditional_role'],'neighbor_candidate')

    def test_spelling_not_enharmonic_shortcut(self):
        _,row,c=fixture(('G4','G##4','B4'));self.assertFalse(explain(row,c,0)['patterns'])

    def test_polyphonic_alternatives_do_not_vote(self):
        _,row,c=fixture(poly=True);r=explain(row,c,0)
        self.assertEqual(len(r['assignments']),49);self.assertTrue(r['patterns'])
        self.assertTrue(all(p['support']=='assignment_dependent' for p in r['patterns']))
        self.assertFalse(r['counts_are_confidence'])
        self.assertTrue(all(not a['note_removed'] for a in r['assignments']))

    def test_gap_not_deleted(self):
        _,row,c=fixture(gap=True);self.assertFalse(explain(row,c,0)['patterns'])

    def test_member_middle_is_not_nct(self):
        _,row,c=fixture(('G4','D4','B4'));self.assertFalse(explain(row,c,0)['patterns'])

    def test_short_candidate_scope_does_not_expand_to_fit_triple(self):
        _,row,c=fixture();c=deepcopy(c);c['span']['end']=q(2)
        r=explain(row,c,0);self.assertFalse(r['patterns'])
        self.assertFalse(r['outside_extension_assumption'])
        self.assertEqual(r['evaluation_span']['end'],q(2))
        held=explain(row,c,0,'source_hold_counterfactual');self.assertTrue(held['outside_extension_assumption'])
        self.assertTrue(held['patterns'])

    def test_candidate_warning_still_blocks(self):
        _,row,c=fixture();c['abstention_reasons']=['grace_timing']
        r=explain(row,c,0);self.assertFalse(r['patterns']);self.assertIn('grace_timing',r['abstention_reasons'])

    def test_incomplete_enumeration_never_common(self):
        _,row,c=fixture();row['enumeration_complete']=False;row['assignments']=[]
        r=explain(row,c,0);self.assertFalse(r['patterns'])
        self.assertIn('voice_path_enumeration_incomplete',r['abstention_reasons'])

    def test_input_unchanged(self):
        _,row,c=fixture();old=deepcopy((row,c));explain(row,c,0);self.assertEqual((row,c),old)

    def test_full_duration_required_no_partial_middle_explanation(self):
        _,row,c=fixture();c['span']['start']=q(0.5)
        r=explain(row,c,0);self.assertFalse(r['patterns']);self.assertEqual(r['all_note_time'],q(2.5))

    def test_every_assignment_retains_same_nonmember_total(self):
        _,row,c=fixture(poly=True);r=explain(row,c,0)
        from musicanote_harness.harmony_joint import f
        for a in r['assignments']:
            self.assertEqual(f(a['conditional_nonmember_time'])+f(a['unexplained_nonmember_time']),
                f(r['note_time_by_state']['nonmember_not_confirmed_nct']))

    def test_pipeline_preserves_earlier_fields(self):
        from test_harmony_catalog_paths import fixture as base_fixture,run
        from musicanote_harness.harmony_path_context import augment as context
        from musicanote_harness.harmony_voice_paths import augment as voices
        ir=base_fixture();base,left,right=run(ir);base=voices(ir,context(ir,base))
        r=augment(ir,base,left,right)
        self.assertEqual({k:r[k] for k in base},base)
        self.assertTrue(r['path_conditioned_ornaments']['paths'])

    def test_fabricated_track_rejected(self):
        _,row,c=fixture();row['assignments'][0]['tracks']=row['assignments'][-1]['tracks']
        with self.assertRaisesRegex(ValueError,'track_partition_mismatch'):explain(row,c,0)

    def test_removing_no_link_alternative_is_not_consensus(self):
        _,row,c=fixture();row['assignments']=row['assignments'][1:]
        with self.assertRaisesRegex(ValueError,'incomplete_or_missing'):explain(row,c,0)

    def test_polyphonic_xml_control_geometry_has_one_of_six_support(self):
        from musicanote_harness.harmony_catalog_paths_trial import control_specs
        ir=score(control_specs('polyphony'));span={'start':q(1),'end':q(3)}
        cat=propose(ir,span)
        c=next(c for c in cat['candidates'] if c['root']['spelling']==['G',0] and c['member_pitch_classes']==[2,7,11])
        row=observe(ir,{'start':q(0),'end':q(3)},('part1','4'));r=explain(row,c,0)
        self.assertEqual(len(r['assignments']),6);self.assertEqual(len(r['patterns']),1)
        p=r['patterns'][0];names={s['sounding_event_id']:s['pitch']['spelling'] for s in ir['sounding_events']}
        self.assertEqual([names[s] for s in p['event_refs']],['G4','A4','B4'])
        self.assertEqual(len(p['supporting_assignment_refs']),1);self.assertFalse(p['common_to_all_assignments'])
