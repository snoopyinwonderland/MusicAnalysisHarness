from copy import deepcopy
from unittest.mock import patch
import unittest
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_progression_context import plan, build, evaluate
from test_harmony_shared_context import fixture
from test_harmony_segment_contrast import full_assignment

MEMBERS = [[['C',0],['E',0],['G',0]], [['F',0],['A',0],['C',0]], [['G',0],['B',0],['D',0]]]


def provider(ir, span, context):
    return {'candidates':[{'candidate_id':str(i), 'origin_pointer':'/fixture/'+str(i), 'provider':'fixture',
        'span':span,'spelling_alternatives':[{'members':m}], 'missing_spellings_by_alternative':[[]],
        'abstention_reasons':[]} for i,m in enumerate(MEMBERS)]}


def make(notes=None):
    baseline=fixture(notes)
    with patch('musicanote_harness.harmony_progression_context.propose',side_effect=provider), \
         patch('musicanote_harness.harmony_progression_context.label',side_effect=lambda cat,c,i:c['candidate_id']):
        return build({},baseline), full_assignment(baseline)


def path(r, spans):
    return [{'edge':next(i for i,e in enumerate(r['edges']) if (e['from'],e['to'])==(a,b)), 'reading':c}
            for a,b,c in spans]


class ProgressionTests(unittest.TestCase):
    def test_all_intervals_and_releases(self):
        b=fixture();p=plan(b['events'],b['span'])
        self.assertEqual(len(p['intervals']),6)
        b['events'][0]['span']['end']=q('1/2')
        self.assertIn(q('1/2'),plan(b['events'],b['span'])['points'])

    def test_three_segments_same_chord_preserves_passing(self):
        r,aid=make();a=evaluate(r,path(r,[(0,3,0)]),aid);b=evaluate(r,path(r,[(0,1,0),(1,2,0),(2,3,0)]),aid)
        self.assertEqual(a['cells'],b['cells']);self.assertEqual(b['note_time']['conditional_nonmember'],q(1))

    def test_changing_three_chords_keeps_every_note(self):
        r,aid=make();a=evaluate(r,path(r,[(0,1,0),(1,2,2),(2,3,0)]),aid)
        self.assertEqual(a['note_time']['member'],q(3));self.assertEqual(a['total_note_time'],q(3))
        self.assertFalse(a['harmonic_progression_confirmed']);self.assertIsNone(a['selected'])

    def test_target_window_uses_external_context(self):
        r,aid=make();a=evaluate(r,path(r,[(0,3,0)]),aid,{'start':q(1),'end':q(2)})
        self.assertEqual(a['note_time']['conditional_nonmember'],q(1))
        self.assertEqual(a['context_span'],r['plan']['context_span'])

    def test_context_cannot_be_omitted(self):
        r,aid=make()
        with self.assertRaises(ValueError):evaluate(r,path(r,[(0,1,0),(1,2,0)]),aid)

    def test_gap_rejected(self):
        r,aid=make()
        with self.assertRaises(ValueError):evaluate(r,path(r,[(0,1,0),(2,3,0)]),aid)

    def test_overlap_rejected(self):
        r,aid=make()
        with self.assertRaises(ValueError):evaluate(r,path(r,[(0,2,0),(1,3,0)]),aid)

    def test_unknown_assignment_rejected(self):
        r,_=make()
        with self.assertRaises(ValueError):evaluate(r,path(r,[(0,3,0)]),'unknown')

    def test_projection_conservation(self):
        r,aid=make();p=path(r,[(0,3,0)])
        for lo,hi in [(0,1),(1,2),(2,3)]:
            self.assertEqual(evaluate(r,p,aid,{'start':q(lo),'end':q(hi)})['total_note_time'],q(1))

    def test_blocker_prevents_conditional_explanation(self):
        r,aid=make();p=path(r,[(0,3,0)]);r['edges'][p[0]['edge']]['readings'][0]['abstention_reasons']=['blocked']
        a=evaluate(r,p,aid);self.assertEqual(a['note_time']['conditional_nonmember'],q(0))
        self.assertEqual(a['blocked_candidate_refs'],['0'])

    def test_no_link_does_not_invent_ornament(self):
        r,_=make();aid=next(a['assignment_id'] for a in r['assignments'] if not a['links'])
        self.assertEqual(evaluate(r,path(r,[(0,3,0)]),aid)['note_time']['conditional_nonmember'],q(0))

    def test_budget_abstains_without_pruning(self):
        b=fixture();r=build({},b,max_edges=1)
        self.assertEqual(r['status'],'edge_budget_abstention_no_pruning');self.assertEqual(len(r['plan']['intervals']),6)
        self.assertEqual(r['edges'],[])

    def test_labels_do_not_enter_plan(self):
        b=fixture();p=plan(b['events'],b['span']);b['source_label']='V7';b['title']='other'
        self.assertEqual(p,plan(b['events'],b['span']))

    def test_preserve_input(self):
        r,aid=make();saved=deepcopy(r);evaluate(r,path(r,[(0,3,0)]),aid);self.assertEqual(r,saved)

    def test_silence_is_not_chord_attack(self):
        r,aid=make([('C4',0,1),('E4',2,3)])
        a=evaluate(r,path(r,[(0,3,0)]),aid);self.assertEqual(a['wall_time']['silence'],q(1))


if __name__=='__main__':unittest.main()
