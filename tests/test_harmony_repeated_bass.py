import unittest
from copy import deepcopy
from test_harmony_distributed_resolution import fixture
from musicanote_harness.harmony_repeated_bass import chains,compare_interval,run
from musicanote_harness.harmony_candidate_relation_survey import local_query


def setup(bass='C3',gap=False,voice='b',extra=()):
    specs=[(bass,0,1,'b'),(bass,'3/2' if gap else 1,2,voice),(bass,2,3,voice),
           ('E4',0,1,'l'),('G4',0,1,'g'),('B-4',0,1,'s'),
           ('F4',1,3,'l'),('A4',1,3,'s'),('C5',1,3,'g')]+list(extra)
    return fixture(specs)


class RepeatedBassTests(unittest.TestCase):
    def test_repeated_lowest_not_pedal_proof(self):
        r,p,ir=setup();g=chains(r,ir)
        self.assertEqual(len(g['chains']),1)
        self.assertEqual(len(g['chains'][0]['event_refs']),3)
        self.assertFalse(g['chains'][0]['pedal_confirmed'])
        self.assertTrue(g['chains'][0]['touches_context_start'])
        self.assertTrue(g['chains'][0]['touches_context_end'])

    def test_rest_not_bridged(self):
        r,p,ir=setup(gap=True);g=chains(r,ir)
        self.assertEqual(len(g['chains'][0]['event_refs']),2)
        self.assertNotEqual(g['chains'][0]['event_refs'][0],r['events'][0]['sounding_event_id'])

    def test_cross_voice_not_bridged(self):
        r,p,ir=setup(voice='other');g=chains(r,ir)
        self.assertEqual(len(g['chains'][0]['event_refs']),2)

    def test_cross_staff_same_voice_allowed(self):
        r,p,ir=setup();ir['note_events'][1]['staff_id']='other'
        self.assertEqual(len(chains(r,ir)['chains'][0]['event_refs']),3)

    def test_lower_interruption_breaks_lowest_chain(self):
        r,p,ir=setup(extra=[('B2',1,2,'low')])
        self.assertEqual(chains(r,ir)['chains'],[])

    def test_unison_ambiguity_not_arbitrarily_chosen(self):
        r,p,ir=setup(extra=[('C3',1,2,'b')]);g=chains(r,ir)
        self.assertEqual(g['chains'],[]);self.assertTrue(g['ambiguous_links'])

    def test_octave_not_equivalent_to_reattack(self):
        r,p,ir=setup();r['events'][1]['pitch'].update(octave=4,midi_pitch=60,spelling='C4')
        self.assertEqual(chains(r,ir)['chains'],[])

    def test_enharmonic_not_equivalent(self):
        r,p,ir=setup(bass='F#3');r['events'][1]['pitch'].update(step='G',alter={'numerator':-1,'denominator':1},spelling='G-3')
        self.assertEqual(chains(r,ir)['chains'],[])

    def test_sustained_single_event_not_called_repeated(self):
        r,p,ir=fixture([('C3',0,3,'b'),('E4',0,1,'l'),('F4',1,3,'l')])
        self.assertEqual(chains(r,ir)['chains'],[])

    def test_competitors_keep_same_interval_all_origins_and_blockers(self):
        r,p,ir=setup(bass='F3');chain=chains(r,ir)['chains'][0];edge=p[0]['edge']
        duplicate=deepcopy(r['edges'][edge]['readings'][1]);duplicate['candidate_ref']='other-origin';duplicate['abstention_reasons']=['blocked']
        r['edges'][edge]['readings'].append(duplicate)
        table=compare_interval(r,edge,chain)
        self.assertEqual(table['bass_member_reading_indices'],[1,2])
        self.assertEqual(table['readings'][2]['candidate_blockers'],['blocked'])
        self.assertIsNone(table['winner'])
        self.assertEqual(table['span'],r['edges'][edge]['span'])

    def test_input_and_original_gate_preserved(self):
        r,p,ir=setup(bass='F3');pair={'source':p[0],'target':p[1],'family':'V7','target_quality':'M'}
        item={'pair':pair,**local_query(r,pair,ir,temporal=True)}
        survey={'status':'ready','results':[item],'plan':{'pairs':[pair]}}
        before=deepcopy((r,survey,ir));a=run(r,survey,ir)
        self.assertEqual(a['summary']['with_bass_member_competitor'],1)
        self.assertFalse(a['pair_results'][0]['findings'][0]['return_anchor_verified'])
        self.assertFalse(a['gate_changed']);self.assertEqual((r,survey,ir),before)

    def test_wrong_ir_rejected(self):
        r,p,ir=setup();ir=deepcopy(ir);ir['sounding_events'][0]['pitch']['midi_pitch']+=1
        with self.assertRaisesRegex(ValueError,'identity_mismatch'):
            run(r,{'status':'ready','results':[],'plan':{'pairs':[]}},ir)


if __name__=='__main__':unittest.main()
