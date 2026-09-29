from copy import deepcopy
from fractions import Fraction as F
import unittest
from test_harmony_open_candidates import score
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_candidate_catalog import propose,validate,resolve
from musicanote_harness.harmony_open_candidates import window


def fixture(ps):return score([(p,0,1,str(i)) for i,p in enumerate(ps)])
def run(ir,end=1):return propose(ir,{'start':q(0),'end':q(end)})
def seventh(r,quality,root=('C',0)):
    return next(c for c in r['providers']['additional_sevenths'] if c['quality']==quality and c['root_coordinate']==list(root))


class CandidateCatalogTests(unittest.TestCase):
    def test_augmented_major_seventh(self):
        c=seventh(run(fixture(['C3','E3','G#3','B3'])),'+M7');self.assertEqual(c['missing_spellings'],[])

    def test_minor_major_seventh(self):
        c=seventh(run(fixture(['C3','E-3','G3','B3'])),'mM7');self.assertEqual(c['missing_spellings'],[])

    def test_major7_competes_with_missing_augmented_fifth(self):
        r=run(fixture(['C3','E3','G3','B3']));c=seventh(r,'+M7')
        self.assertEqual(c['missing_spellings'],[['G',1]]);self.assertEqual(c['extra_spellings'],[['G',0]])
        self.assertTrue(any(c['root']==0 and c['label']=='C:major7' for c in r['providers']['base']['candidates']))

    def test_missing_root_not_invented_in_new_seventh(self):
        r=run(fixture(['E-3','G3','B3']))
        self.assertFalse(any(c['root_coordinate']==['C',0] for c in r['providers']['additional_sevenths']))

    def test_respelling_not_collapsed(self):
        c=seventh(run(fixture(['C3','E3','A-3','B3'])),'+M7')
        self.assertEqual(c['missing_spellings'],[['G',1]]);self.assertEqual(c['extra_spellings'],[['A',-1]])

    def test_all_providers_preserved(self):
        r=run(fixture(['C3','E3','B3','B-3','D4','A-3','F#4']))
        self.assertEqual({c['provider'] for c in r['candidates']},{'base','additional_seventh','augmented','extended'})
        self.assertTrue(validate(r)['passed'])
        for c in r['candidates']:self.assertEqual(resolve(r,c['origin_pointer'])['candidate_id'],c['candidate_id'])

    def test_original_base_ids_states_and_results_unchanged(self):
        ir=fixture(['C3','E3','G#3','B3']);r=run(ir)
        self.assertEqual(r['providers']['base'],window(ir,r['span']))

    def test_augmented_tonic_is_not_root(self):
        r=run(fixture(['A-3','C4','F#4']))
        c=next(c for c in r['candidates'] if c['provider']=='augmented' and c['tonal_coordinate']==['C',0])
        self.assertEqual(c['root'],{'pitch_class':None,'spelling':None})

    def test_rootless_legacy_spelling_stays_unknown(self):
        r=run(fixture(['E3','G3']))
        raw=next(c for c in r['providers']['base']['candidates'] if c['label']=='C:major')
        c=next(c for c in r['candidates'] if c['candidate_id']==raw['candidate_id'])
        self.assertEqual(c['spelling_alternatives'],[]);self.assertIsNone(c['root']['spelling'])

    def test_equal_note_time_for_every_candidate(self):
        ir=score([('C3',0,2,'a'),('E3',0,1,'b'),('B-3',1,2,'b'),('D4',F(1,2),F(3,2),'c')])
        r=run(ir,2)
        self.assertEqual({F(c['total_note_time_quarters']['numerator'],c['total_note_time_quarters']['denominator']) for c in r['candidates']},{F(5)})

    def test_annotation_blind_input_unchanged(self):
        ir=fixture(['C3','E3','G#3','B3']);old=deepcopy(ir);r=run(ir);self.assertEqual(ir,old)
        ir['annotations']=['anything'];self.assertEqual(run(ir),r)

    def test_output_does_not_alias_input_or_provider(self):
        ir=fixture(['C3','E3','G#3','B3']);old=deepcopy(ir);r=run(ir)
        c=r['candidates'][0];raw=deepcopy(resolve(r,c['origin_pointer']));sid=next(iter(c['event_states']))
        c['event_states'][sid]='changed';self.assertEqual(resolve(r,c['origin_pointer']),raw)
        r['providers']['base']['event_units'][sid]['pitch']['step']='X';self.assertEqual(ir,old)

    def test_transposition(self):
        c=seventh(run(fixture(['D3','F#3','A#3','C#4'])),'+M7',('D',0));self.assertFalse(c['missing_spellings'])

    def test_reproducible(self):
        ir=fixture(['C3','E-3','G3','B3']);self.assertEqual(run(ir),run(ir))

    def test_candidate_loss_rejected(self):
        r=run(fixture(['C3','E3','G3']));r['candidates'].pop()
        with self.assertRaisesRegex(ValueError,'provider_candidate_loss'):validate(r)

    def test_duplicates_rejected(self):
        r=run(fixture(['C3','E3','G3']));r['candidates'].append(deepcopy(r['candidates'][0]))
        with self.assertRaisesRegex(ValueError,'duplicate_candidate_id'):validate(r)

    def test_broken_pointer_rejected(self):
        r=run(fixture(['C3','E3','G3']));r['candidates'][0]['origin_pointer']='/providers/nonexistent'
        with self.assertRaisesRegex(ValueError,'broken_origin_pointer'):validate(r)

    def test_wrong_duration_rejected(self):
        r=run(fixture(['C3','E3','G3']));r['candidates'][0]['total_note_time_quarters']=q(999)
        with self.assertRaisesRegex(ValueError,'note_time_mismatch'):validate(r)

    def test_missing_cell_event_rejected(self):
        r=run(fixture(['C3','E3','G3']));cell=r['candidates'][0]['cells'][0]
        next(v for v in cell['state_event_refs'].values() if v).pop()
        with self.assertRaisesRegex(ValueError,'cell_event_mismatch'):validate(r)

    def test_unsupported_verdict_rejected(self):
        r=run(fixture(['C3','E3','G3']));r['selected']='winner'
        with self.assertRaisesRegex(ValueError,'unsupported_verdict'):validate(r)
