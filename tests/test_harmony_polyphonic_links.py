from copy import deepcopy
from fractions import Fraction as F
import unittest
from test_harmony_reading_voice_context import score,chord
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_polyphonic_links import observe,evaluate,partial_matchings
from musicanote_harness.harmony_polyphonic_trial import compare_readings,verify_groups


def block(left=('B3','F4'),right=('C4','E4')):
    return score([(p,0,1,'v') for p in left]+[(p,1,2,'v') for p in right])
def run(ir):return observe(ir,[{'start':q(0),'end':q(3)}])


class PolyphonicLinksTests(unittest.TestCase):
    def test_all_partial_maps_and_empty_hypothesis(self):
        self.assertEqual(len(partial_matchings(['a','b'],['c','d'])),7)
        self.assertEqual(len(partial_matchings(list('abcd'),list('efgh'))),209)
        g=run(block())['groups'][0]
        self.assertEqual(len(g['edges']),4);self.assertEqual(len(g['assignments']),7)
        self.assertEqual(g['assignments'][0]['edge_indices'],[]);self.assertIsNone(g['selected_assignment'])

    def test_parallel_leading_tone_and_seventh_are_hypotheses(self):
        g=run(block())['groups'][0];e=evaluate(g,chord(7,'dominant7'),chord(0,'major'))
        self.assertEqual(len(e['conditional_resolution_edge_indices']),2)
        self.assertTrue(e['assignment_sensitive']);self.assertFalse(e['function_confirmed'])

    def test_crossing_retained_not_filtered(self):
        g=run(block())['groups'][0]
        self.assertTrue(any(a['crossing_count'] for a in g['assignments']))

    def test_unequal_cardinality_not_forced(self):
        g=run(block(right=('C4',)))['groups'][0]
        self.assertEqual(len(g['assignments']),3)
        self.assertTrue(all(a['unmatched_source_refs'] for a in g['assignments']))

    def test_held_sound_not_new_attack(self):
        ir=block();extra=score([('G3',0,2,'v')]);n=extra['note_events'][0];n['note_id']='holdn'
        s=extra['sounding_events'][0];s.update(sounding_event_id='holds',attack_note_id='holdn',source_note_ids=['holdn'])
        ir['note_events'].append(n);ir['sounding_events'].append(s)
        g=run(ir)['groups'][0];self.assertEqual(g['held_refs'],['holds'])
        self.assertTrue(all('holds' not in e['source_refs'] for e in g['edges']))

    def test_gap_not_bridged(self):
        ir=block()
        for s in ir['sounding_events'][2:]:s['span']['start']=q(F(3,2))
        self.assertEqual(run(ir)['groups'],[])

    def test_endpoint_cap_abstains(self):
        self.assertEqual(run(block(left=('C3','D3','E3','F3','G3')))['abstentions'][0]['reason'],'endpoint_limit_no_silent_pruning')

    def test_no_cross_voice_connections(self):
        ir=block()
        for n in ir['note_events'][2:]:n['voice_id']='other'
        self.assertFalse(run(ir)['groups'])

    def test_bad_spelling_never_becomes_leading_tone(self):
        g=run(block(left=('C-4','F4')))['groups'][0];e=evaluate(g,chord(7,'dominant7'),chord(0,'major'))
        self.assertFalse(any('conditional_dominant_family_leading_tone_up' in ts for ts in e['edge_relations']))

    def test_immutable_and_no_label_feedback(self):
        ir=block();old=deepcopy(ir);a=run(ir)
        self.assertEqual(ir,old);self.assertEqual(a,run({**ir,'annotations':['wrong'],'title':'another'}))
        g=a['groups'][0];oldg=deepcopy(g);evaluate(g,chord(0,'major'),chord(5,'major'));self.assertEqual(g,oldg)

    def test_duplicate_contexts_do_not_duplicate_groups(self):
        ir=block();span={'start':q(0),'end':q(3)}
        self.assertEqual(observe(ir,[span]),observe(ir,[span,span]))

    def test_invalid_span(self):
        with self.assertRaises(ValueError):observe(block(),[{'start':q(2),'end':q(1)}])

    def test_independent_combinatorial_oracle(self):
        for n in range(1,5):
            for m in range(1,5):
                ir=block(left=('C3','E3','G3','B3')[:n],right=('D3','F3','A3','C4')[:m])
                self.assertTrue(verify_groups(ir,run(ir))['passed'])

    def test_reading_attachment_only_at_exact_boundary(self):
        observed=run(block());g=observed['groups'][0]
        path={'segments':[{'candidate':chord(7,'dominant7')},{'candidate':chord(0,'major')}],'local_cost':0.25}
        c={'span':{'start':q(0),'end':q(2)},'boundary':q(1),'merged_seventh':[],'split_triads':[path]}
        old=deepcopy(c)
        records=compare_readings(c,{'external_shape_candidates':[]},[g])
        self.assertEqual(len(records),1);self.assertEqual(records[0]['original_cost'],0.25)
        self.assertEqual(len(records[0]['comparisons'][0]['evaluation']['conditional_resolution_edge_indices']),2)
        self.assertEqual(c,old)
        c['boundary']=q(F(3,2))
        self.assertEqual(compare_readings(c,{'external_shape_candidates':[]},[g]),[])

    def test_empty_assignment_prevents_universal_resolution_claim(self):
        ir=block();g=run(ir)['groups'][0];ev=evaluate(g,chord(7,'dominant7'),chord(0,'major'))
        self.assertNotIn(0,ev['supporting_assignment_indices'])
        self.assertIsNone(ev['probability']);self.assertFalse(ev['used_for_ranking'])

    def test_verifier_detects_duplicate_assignments(self):
        ir=block();o=run(ir);o['groups'][0]['assignments'][-1]=deepcopy(o['groups'][0]['assignments'][0])
        with self.assertRaises(AssertionError):verify_groups(ir,o)


if __name__=='__main__':unittest.main()
