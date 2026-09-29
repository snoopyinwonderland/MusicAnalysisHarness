import copy
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from musicanote_harness.formal_ir import q
from musicanote_harness.melodic_figuration import compare_blocks, condition_on_triads
from musicanote_harness.melodic_figuration_audit import build
from musicanote_harness.six_four_context import triad
from musicanote_harness.harmony_curriculum import concepts


LEFT=[('E',-1,3),('A',-1,3),('C',0,4),('A',-1,3),('E',-1,3),('A',-1,3)]
RIGHT=[('E',-1,3),('G',0,3),('B',-1,3),('G',0,3),('E',-1,3),('G',0,3)]


def fixture(left=LEFT,right=RIGHT):
    ir={'note_events':[],'sounding_events':[]}
    for bi,pitches in enumerate((left,right)):
        for i,(step,alter,octave) in enumerate(pitches):
            nid=f'n{bi}-{i}'; sid=f's{bi}-{i}'; start=3*bi+Fraction(3*i,len(pitches)); duration=Fraction(3,len(pitches))
            ir['note_events'].append({'note_id':nid,'part_id':'p','voice_id':'v','display_staff_id':'staff1'})
            ir['sounding_events'].append({'sounding_event_id':sid,'attack_note_id':nid,'source_note_ids':[nid],
                'pitch':{'step':step,'alter':q(alter),'octave':octave,
                         'midi_pitch':12*(octave+1)+{'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}[step]+alter},
                'span':{'start':q(start),'end':q(start+duration)}})
    return ir


def compare(ir):return compare_blocks(ir,{'start':q(0),'end':q(3)},{'start':q(3),'end':q(6)})
def link(o):return condition_on_triads(o,triad('I',2,'A',-1),triad('V',0,'A',-1))


class FigurationTest(unittest.TestCase):
    def test_nonadjacent_links_from_rhythmic_slots(self):
        r=compare(fixture());v=r['voices'][0]
        self.assertTrue(v['compound_correspondence_candidate'])
        self.assertEqual([g['slot_count'] for g in v['slot_groups']],[2,3,1])
        self.assertEqual([g['motion']['semitones'] for g in v['slot_groups']],[0,-1,-2])
        self.assertEqual(v['slot_groups'][1]['slot_evidence'][0]['event_refs'],['s0-1','s1-1'])
        self.assertIsNone(v['selected_projection']); self.assertIsNone(r['nct_labels'])

    def test_conditional_resolution_singleton_not_hidden(self):
        r=link(compare(fixture())); p=r['voices'][0]['compound_resolution_candidates'][0]
        self.assertFalse(p['all_groups_have_repeated_support'])
        self.assertEqual({m['relation'] for m in p['upper_motion_groups']},{'4_to_3','6_to_5'})
        self.assertIsNone(r['cadence']);self.assertIsNone(r['functional_verdict'])

    def test_labels_only_in_separate_stage(self):
        observed=compare(fixture());saved=copy.deepcopy(observed)
        r=condition_on_triads(observed,triad('ii',2,'A',-1),triad('V',0,'A',-1))
        self.assertEqual(r['voices'][0]['compound_resolution_candidates'],[])
        self.assertEqual(observed,saved)

    def test_ir_immutable_full_durations_preserved(self):
        ir=fixture();saved=copy.deepcopy(ir);v=compare(ir)['voices'][0]
        self.assertEqual(ir,saved)
        self.assertEqual(v['blocks'][0]['events'][0]['release'],q(Fraction(1,2)))

    def test_inconsistent_mapping_not_projection(self):
        right=list(RIGHT);right[-1]=('A',-1,3)
        v=compare(fixture(right=right))['voices'][0]
        self.assertFalse(v['compound_correspondence_candidate'])
        self.assertTrue(any(g['alternative_mapping_present'] for g in v['slot_groups']))

    def test_many_to_one_mapping_not_projection(self):
        v=compare(fixture(right=[('E',-1,3)]*6))['voices'][0]
        self.assertFalse(v['pitch_mapping_consistent'])

    def test_no_repeat_and_constant_pitch_not_compound(self):
        for left,right in [([('C',0,4),('D',0,4),('E',0,4)],[('D',0,4),('E',0,4),('F',0,4)]),
                           ([('C',0,4)]*3,[('D',0,4)]*3)]:
            self.assertFalse(compare(fixture(left,right))['voices'][0]['compound_correspondence_candidate'])

    def test_neighbor_pattern_can_match_but_is_not_selected_voice(self):
        pitches=[('C',0,4),('D',0,4),('C',0,4),('D',0,4)]
        r=compare(fixture(pitches,pitches));v=r['voices'][0]
        self.assertTrue(v['compound_correspondence_candidate'])
        self.assertIsNone(v['selected_projection']);self.assertIsNone(r['reduction'])
        self.assertTrue(v['adjacent_melodic_geometry'])

    def test_unchanged_arpeggio_not_resolution(self):
        o=compare(fixture(LEFT,LEFT))
        r=condition_on_triads(o,triad('I',2,'A',-1),triad('I',2,'A',-1))
        self.assertTrue(o['voices'][0]['compound_correspondence_candidate'])
        self.assertEqual(r['voices'][0]['compound_resolution_candidates'],[])

    def test_event_count_mismatch_abstains(self):
        v=compare(fixture(right=RIGHT[:-1]))['voices'][0]
        self.assertIn('different_event_counts_no_forced_alignment',v['abstention_reasons'])
        self.assertEqual(v['slot_groups'],[])

    def test_rhythm_mismatch_abstains(self):
        ir=fixture();ir['sounding_events'][-1]['span']['end']=q(Fraction(23,4))
        v=compare(ir)['voices'][0]
        self.assertIn('different_normalized_rhythm_no_forced_alignment',v['abstention_reasons'])

    def test_duration_scaling_preserves_relative_slots(self):
        ir=fixture()
        for s in ir['sounding_events'][6:]:
            for field in ('start','end'):
                v=s['span'][field];t=Fraction(v['numerator'],v['denominator']);s['span'][field]=q(3+2*(t-3))
        r=compare_blocks(ir,{'start':q(0),'end':q(3)},{'start':q(3),'end':q(9)})
        self.assertTrue(r['voices'][0]['compound_correspondence_candidate'])
        self.assertEqual(r['voices'][0]['duration_scale_factor'],q(2))

    def test_polyphonic_voice_not_sorted_into_strands(self):
        ir=fixture();s=copy.deepcopy(ir['sounding_events'][0]);s['sounding_event_id']='extra'
        ir['sounding_events'].append(s)
        v=compare(ir)['voices'][0]
        self.assertIn('polyphonic_notated_voice',v['abstention_reasons'])
        self.assertFalse(v['compound_correspondence_candidate'])

    def test_tie_crossing_boundary_not_clipped(self):
        ir=fixture();s=ir['sounding_events'][5];s['span']['end']=q(4)
        v=compare(ir)['voices'][0]
        self.assertIn('sounding_event_crosses_block_boundary',v['abstention_reasons'])
        self.assertEqual(v['blocks'][0]['events'][-1]['release'],q(4))

    def test_cross_staff_same_voice_allowed(self):
        ir=fixture()
        for n in ir['note_events'][6:]:n['display_staff_id']='staff2'
        self.assertTrue(compare(ir)['voices'][0]['compound_correspondence_candidate'])

    def test_cross_voice_no_inferred_correspondence(self):
        ir=fixture()
        for n in ir['note_events'][6:]:n['voice_id']='other'
        self.assertFalse(any(v['compound_correspondence_candidate'] for v in compare(ir)['voices']))

    def test_grace_is_excluded_and_traceable(self):
        ir=fixture();n=copy.deepcopy(ir['note_events'][0]);n.update(note_id='ng',grace={'is_grace':True})
        ir['note_events'].append(n);s=copy.deepcopy(ir['sounding_events'][0]);s.update(sounding_event_id='sg',attack_note_id='ng',source_note_ids=['ng'])
        s['span']['end']=q(0);ir['sounding_events'].append(s)
        r=compare(ir);self.assertEqual(r['excluded_grace_event_ids'],['sg'])
        self.assertTrue(r['voices'][0]['compound_correspondence_candidate'])

    def test_step_geometry_not_nct_or_weak_beat_requirement(self):
        patterns=[([('C',0,4),('D',0,4),('E',0,4)],'passing_geometry'),
                  ([('C',0,4),('D',-1,4),('C',0,4)],'neighbor_geometry'),
                  ([('F',0,4),('F',1,4),('G',0,4)],'chromatic_passing_geometry')]
        for pitches,want in patterns:
            g=compare(fixture(pitches,pitches))['voices'][0]['adjacent_melodic_geometry'][0]
            self.assertEqual(g['pattern'],want);self.assertIsNone(g['nct_label'])

    def test_gap_does_not_form_adjacent_passing(self):
        pitches=[('C',0,4),('D',0,4),('E',0,4)];ir=fixture(pitches,pitches)
        ir['sounding_events'][0]['span']['end']=q(Fraction(1,2))
        g=compare(ir)['voices'][0]['adjacent_melodic_geometry']
        self.assertFalse(any(x['block_index']==0 for x in g))

    def test_transposition_preserves_correspondence(self):
        ir=fixture()
        for s in ir['sounding_events']:
            p=s['pitch'];p['octave']+=1;p['midi_pitch']+=12
        self.assertTrue(link(compare(ir))['voices'][0]['compound_resolution_candidates'])

    def test_extra_tone_does_not_get_deleted(self):
        left=list(LEFT);left[2]=('D',0,4)
        r=link(compare(fixture(left=left)))['voices'][0]
        self.assertEqual(r['compound_resolution_candidates'],[])
        self.assertEqual(r['conditional_member_coverage'][0]['extra_event_refs'],['s0-2'])

    def test_enharmonic_membership_not_pitch_class_only(self):
        left=list(LEFT);left[2]=('B',1,3)
        r=link(compare(fixture(left=left)))['voices'][0]
        self.assertFalse(r['compound_resolution_candidates'])

    def test_spans_and_reference_contract(self):
        with self.assertRaises(ValueError):compare_blocks(fixture(),{'start':q(0),'end':q(2)},{'start':q(3),'end':q(6)})
        ir=fixture();ir['sounding_events'][0]['source_note_ids']=[]
        with self.assertRaises(ValueError):compare(ir)


class AuditTest(unittest.TestCase):
    def test_bad_hash_rights_and_overwrite_before_package_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            with self.assertRaisesRegex(ValueError,'output_exists'):build('missing',p)
            contract={'entries':[{'split':'holdout','work_family_id':'w','score_sha256':'s',
                         'annotation_sha256':'a','rights':{'internal_research_use':True}}]}
            raw=json.dumps(contract).encode();(p/'run-contract.json').write_bytes(raw)
            (p/'report.json').write_text(json.dumps({'contract_sha256':'bad','records':[]}))
            with self.assertRaisesRegex(ValueError,'source_contract_hash_mismatch'):build(p,p/'out')
            (p/'report.json').write_text(json.dumps({'contract_sha256':hashlib.sha256(raw).hexdigest(),'records':[]}))
            with self.assertRaisesRegex(ValueError,'train_research_entries_required'):build(p,p/'out')

    def test_catalog(self):
        u=next(x for x in concepts() if x['concept_id']=='hvl.unit21')
        self.assertEqual(u['reviewed_sections'],list(range(1,18)))
        self.assertEqual(u['rule_status'],'candidate_not_production')


if __name__=='__main__':unittest.main()
