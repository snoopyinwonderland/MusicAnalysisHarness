import copy
import json
import unittest
from fractions import Fraction as F
from musicanote_harness.formal_ir import q
from musicanote_harness.score_reduction import observe, proposal, notation_record, sequence_bass_form
from musicanote_harness.diatonic_sequence import propose as sequence
from musicanote_harness.harmony_curriculum import concepts
from test_chromatic_tonal_context import fixture, span


class ReductionTest(unittest.TestCase):
    def setUp(self):
        self.ir = fixture([(('C', 0, 3), 0, 2, 'v1'), (('C', 0, 4), 0, 2, 'v2'),
                           (('G', 0, 5), 0, 1, 'v3'), (('E', 0, 4), 1, 2, 'v2')])
        self.target = span(0, 2)

    def op(self, kind='retain', refs=None, **kw):
        return {'kind': kind, 'event_ids': refs or ['e0'], 'evidence_refs': ['ev-test'], **kw}

    def test_exact_octaves(self):
        r = observe(self.ir, self.target)
        self.assertEqual(r['exact_doublings'][0]['event_ids'], ['e0', 'e1'])
        self.assertIsNone(r['exact_doublings'][0]['may_omit'])

    def test_json_roundtrip(self):
        r=proposal(self.ir,self.target,[self.op('group_doubling',['e0','e1'])],[])
        self.assertEqual(json.loads(json.dumps(r)),r)

    def test_no_highest_melody(self):
        self.assertIsNone(observe(self.ir, self.target)['selected_melody'])

    def test_no_duration_ranking(self):
        self.assertTrue(all(r['structural_role'] is None for r in observe(self.ir, self.target)['events']))

    def test_different_release_not_doubling(self):
        self.ir['sounding_events'][1]['span']['end'] = q(1)
        self.assertEqual(observe(self.ir, self.target)['exact_doublings'], [])

    def test_different_onset_not_doubling(self):
        self.ir['sounding_events'][1]['span']['start'] = q(F(1, 3))
        self.assertEqual(observe(self.ir, self.target)['exact_doublings'], [])

    def test_enharmonic_not_same_spelling(self):
        ir = fixture([(('F',1,3),0,1,'a'), (('G',-1,4),0,1,'b')])
        self.assertEqual(observe(ir, span(0,1))['exact_doublings'], [])

    def test_tie_not_recut(self):
        r = observe(self.ir, span(1, 2))
        self.assertEqual(r['events'][0]['span'], span(0,2))

    def test_half_open(self):
        self.assertEqual(len(observe(self.ir, span(2,3))['events']), 0)

    def test_grace_pending(self):
        self.ir['note_events'][2]['grace'] = {'is_grace': True}
        self.ir['sounding_events'][2]['span']['end'] = q(0)
        r = observe(self.ir, self.target)
        self.assertEqual(len(r['grace_events_pending_role']), 1)

    def test_broken_reference(self):
        self.ir['sounding_events'][0]['source_note_ids'] = ['missing']
        with self.assertRaises(ValueError): observe(self.ir, self.target)

    def test_duplicate_id(self):
        self.ir['sounding_events'].append(copy.deepcopy(self.ir['sounding_events'][0]))
        with self.assertRaises(ValueError): observe(self.ir, self.target)

    def test_float_rejected(self):
        with self.assertRaises(ValueError): observe(self.ir, {'start':0.1, 'end':2.1})

    def test_group_keeps_every_source(self):
        r = proposal(self.ir, self.target, [self.op('group_doubling', ['e0','e1'])], [])
        self.assertEqual(len(r['operations'][0]['source_events']), 2)
        self.assertFalse(r['unreferenced_means_ornament'])
        self.assertEqual(r['unreferenced_event_ids'], ['e2','e3'])

    def test_group_must_be_observed(self):
        with self.assertRaises(ValueError): proposal(self.ir,self.target,[self.op('group_doubling',['e0','e2'])],[])

    def test_octave_projection_not_mutation(self):
        old = copy.deepcopy(self.ir)
        r = proposal(self.ir,self.target,[self.op('register_transfer',octave_shift=1)],[])
        self.assertEqual(r['operations'][0]['projected_pitches'], [['C',0,4]])
        self.assertEqual(self.ir,old)

    def test_noninteger_register_rejected(self):
        with self.assertRaises(ValueError): proposal(self.ir,self.target,[self.op('register_transfer',octave_shift=0.5)],[])

    def test_implied_tone_not_sounded(self):
        op = self.op('implied_tone',pitch=self.ir['sounding_events'][2]['pitch'],span=span(1,2))
        r = proposal(self.ir,self.target,[op],[])
        self.assertEqual(r['operations'][0]['representation'],'inferred_not_sounded')
        self.assertFalse(r['musically_validated'])

    def test_implied_outside_rejected(self):
        op=self.op('implied_tone',pitch=self.ir['sounding_events'][2]['pitch'],span=span(1,3))
        with self.assertRaises(ValueError): proposal(self.ir,self.target,[op],[])

    def test_no_deletion_operation(self):
        with self.assertRaises(ValueError): proposal(self.ir,self.target,[self.op('delete')],[])

    def test_requires_evidence(self):
        op=self.op(); op['evidence_refs']=[]
        with self.assertRaises(ValueError): proposal(self.ir,self.target,[op],[])

    def test_boundary_provenance_and_pace_preserved(self):
        refs=[{'id':'a1','time':q(F(1,3)),'origin':'analysis_hypothesis'}]
        r=proposal(self.ir,self.target,[self.op()],refs)
        self.assertEqual(r['boundary_refs'],refs)
        self.assertFalse(r['boundary_merging_allowed'])

    def test_invalid_boundary_origin(self):
        with self.assertRaises(ValueError): proposal(self.ir,self.target,[],[{'id':'a','time':q(1),'origin':'fact'}])

    def test_notation_case_and_scope(self):
        for label,profile,scope in [('II','hvl_stufe_uppercase','governing_span'),
                                     ('ii6','dcml_case_sensitive','local_chord'),
                                     ('I5–6','hvl_stufe_uppercase','interval_motion')]:
            r=notation_record(label,profile,scope,'source:1')
            self.assertEqual(r['raw_label'],label)
            self.assertIsNone(r['quality']); self.assertIsNone(r['inversion'])

    def test_unknown_dialect_rejected(self):
        with self.assertRaises(ValueError): notation_record('II','guess','local_chord','s')

    def test_model_variant_bass_not_label_similarity(self):
        self.assertEqual(sequence_bass_form('descending_fifths',[0,0,0,0]),'model')
        self.assertEqual(sequence_bass_form('descending_fifths',[0,1,0,1]),'variant')
        self.assertEqual(sequence_bass_form('ascending_five_six',[0,1,0,1]),'model')
        self.assertEqual(sequence_bass_form('ascending_five_six',[0,0,0,0]),'variant')
        self.assertEqual(sequence_bass_form('ascending_five_six',[0,2,0,2]),'unsupported')

    def test_progression_transposition(self):
        # Appendix I transposition practice -> generic metamorphic contract.
        for step,alter in [('C',0),('D',0),('E',-1),('F',1),('B',-1)]:
            r=sequence(['I','IV','viio','iii'],[0,0,0,0],step,alter)
            self.assertEqual(r['pattern_candidates'][0]['pattern'],'descending_fifths')
            self.assertIsNone(r['cadence']); self.assertIsNone(r['merge_recommended'])

    def test_time_scale_and_register_invariance(self):
        for scale in [F(1,3),1,3]:
            ir=fixture([(('D',0,2),0,scale,'a'),(('D',0,5),0,scale,'b')])
            self.assertEqual(len(observe(ir,span(0,scale))['exact_doublings']),1)

    def test_reading_gap_explicit(self):
        r=next(r for r in concepts() if r['concept_id']=='hvl.appendix03')
        self.assertEqual(r['source']['unavailable_printed_pages'],[708])


if __name__ == '__main__': unittest.main()
