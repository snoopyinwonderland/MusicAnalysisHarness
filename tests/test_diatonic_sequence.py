import copy
from fractions import Fraction
import json
from pathlib import Path
import tempfile
import unittest
from musicanote_harness.formal_ir import q
from musicanote_harness.diatonic_sequence import propose, source_triad, compare_voices
from musicanote_harness.diatonic_sequence_audit import windows, build
from musicanote_harness.harmony_curriculum import concepts


def ann(symbol, start, end, figure='', home='C', minor='0'):
    return {'annotation_id': str(start), 'raw_fields': {'numeral': symbol.rstrip('o'),
        'form': 'o' if symbol.endswith('o') else '', 'chord_type': 'o' if symbol.endswith('o') else 'M' if symbol[0].isupper() else 'm',
        'figbass': figure, 'globalkey': home, 'localkey': 'i' if minor == '1' else 'I', 'localkey_is_minor': minor},
        'target': {'span': {'start': q(start), 'end': q(end)}}}


def ir_fixture(pitches=None, times=None):
    pitches = pitches or [('C', 0, 4), ('E', 0, 4), ('D', 0, 4), ('F', 0, 4)]
    times = times or [(0, 1), (1, 2), (2, 3), (3, 4)]
    notes, sounds = [], []
    for i, (p, (a, b)) in enumerate(zip(pitches, times)):
        nid = 'n'+str(i)
        notes.append({'note_id': nid, 'part_id': 'p', 'voice_id': 'v', 'display_staff_id': 'staff1', 'grace': {'is_grace': False}})
        sounds.append({'sounding_event_id': 's'+str(i), 'attack_note_id': nid, 'source_note_ids': [nid],
                       'span': {'start': q(a), 'end': q(b)},
                       'pitch': {'step': p[0], 'alter': q(p[1]), 'octave': p[2],
                                 'midi_pitch': 12*(p[2]+1)+{'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}[p[0]]+p[1]}})
    return {'note_events': notes, 'sounding_events': sounds}


def geometry(ir, first=None, second=None):
    return compare_voices(ir, first or {'start': q(0), 'end': q(2)}, second or {'start': q(2), 'end': q(4)})


class PatternTest(unittest.TestCase):
    def test_four_models(self):
        for symbols, inv, name in [(['I','IV','viio','iii'], [0,0,0,0], 'descending_fifths'),
                                   (['I','V','ii','vi'], [0,0,0,0], 'ascending_fifths'),
                                   (['I','vi','ii','viio'], [0,1,0,1], 'ascending_five_six'),
                                   (['I','V','vi','iii'], [0,1,0,1], 'descending_five_six')]:
            with self.subTest(name=name):
                result = propose(symbols, inv, 'C')
                self.assertEqual(result['pattern_candidates'][0]['pattern'], name)
                self.assertIsNone(result['sequence_confirmed'])
                self.assertIsNone(result['merge_recommended'])
                self.assertIsNone(result['cadence'])

    def test_diminished_interval_not_filtered(self):
        result = propose(['I','IV','viio','iii'], [1,0,1,0], 'C')
        self.assertTrue(result['root_relations'][1]['tritone'])
        self.assertTrue(result['pattern_candidates'])

    def test_five_six_root_variants(self):
        for symbols in (['I','vi','ii','viio'], ['I','V','vi','iii']):
            self.assertTrue(propose(symbols, [0]*4, 'C')['pattern_candidates'])

    def test_minor_natural_and_raised_distinct(self):
        r = propose(['i','v','VI','III'], [0,1,0,1], 'A', mode='minor')
        self.assertEqual(r['pattern_candidates'][0]['pattern'], 'descending_five_six')
        self.assertFalse(r['minor_raised_seventh_harmony_present'])
        s = propose(['i','V','VI','III'], [0,1,0,1], 'A', mode='minor')
        self.assertTrue(s['minor_raised_seventh_harmony_present'])
        self.assertNotEqual(r['candidates'][1]['quality'], s['candidates'][1]['quality'])

    def test_unrecognized_inversion_or_pattern_not_rejection(self):
        self.assertEqual(propose(['I','V','I','IV'], [0]*4, 'C')['pattern_candidates'], [])
        self.assertEqual(propose(['I','V','vi','iii'], [1,1,1,1], 'C')['pattern_candidates'], [])

    def test_invalid_hypotheses(self):
        for inv in ([0]*3, [0,True,0,1], [0,2,0,1]):
            with self.assertRaises(ValueError): propose(['I','V','vi','iii'], inv, 'C')

    def test_adapter_preserves_source(self):
        a = ann('viio',0,1,'6'); before = copy.deepcopy(a)
        self.assertEqual(source_triad(a), ('viio',1)); self.assertEqual(a,before)
        for field in ('changes','added_tones','relativeroot','pedal','special'):
            b = copy.deepcopy(a); b['raw_fields'][field] = 'x'; self.assertIsNone(source_triad(b))
        a['raw_fields']['figbass']='64'; self.assertIsNone(source_triad(a))


class GeometryTest(unittest.TestCase):
    def test_diatonic_not_exact_semitone_transposition(self):
        ir = ir_fixture(); before = copy.deepcopy(ir)
        c = geometry(ir)['voices'][0]['comparison']
        self.assertEqual(c['diatonic_displacements'], [1,1])
        self.assertEqual(c['semitone_displacements'], [2,1])
        self.assertTrue(c['nonzero_shifted_rhythm_and_spelled_shape'])
        self.assertFalse(c['constant_semitone_displacement'])
        self.assertFalse(c['diatonic_key_fit_verified']); self.assertEqual(ir,before)

    def test_exact_repetition_not_shift(self):
        ir = ir_fixture([('C',0,4),('E',0,4)]*2)
        c = geometry(ir)['voices'][0]['comparison']
        self.assertTrue(c['constant_diatonic_displacement'])
        self.assertFalse(c['nonzero_shifted_rhythm_and_spelled_shape'])

    def test_augmentation_and_fraction(self):
        ir = ir_fixture(times=[(0,Fraction(1,3)),(Fraction(1,3),1),(1,Fraction(5,3)),(Fraction(5,3),3)])
        c = geometry(ir, {'start':q(0),'end':q(1)}, {'start':q(1),'end':q(3)})['voices'][0]['comparison']
        self.assertTrue(c['normalized_rhythm_equal']); self.assertEqual(c['duration_scale_factor'],q(2))

    def test_rhythm_variation_not_force_matched(self):
        ir = ir_fixture(times=[(0,1),(1,2),(2,Fraction(5,2)),(Fraction(5,2),4)])
        c = geometry(ir)['voices'][0]['comparison']
        self.assertTrue(c['constant_diatonic_displacement']); self.assertFalse(c['normalized_rhythm_equal'])

    def test_overlap_abstains(self):
        ir = ir_fixture(times=[(0,2),(1,2),(2,3),(3,4)])
        v = geometry(ir)['voices'][0]
        self.assertIn('polyphonic_notated_voice', v['abstention_reasons']); self.assertIsNone(v['comparison'])

    def test_held_sound_keeps_duration_and_no_reattack(self):
        ir = ir_fixture(times=[(0,1),(1,3),(3,4),(4,5)])
        ir['sounding_events'][1]['source_note_ids'].append('continuation')
        ir['note_events'].append({**ir['note_events'][1], 'note_id':'continuation'})
        v = geometry(ir)['voices'][0]
        self.assertIsNone(v['comparison'])
        self.assertIn('sounding_event_crosses_block_boundary', v['abstention_reasons'])
        self.assertEqual(v['blocks'][0]['events'][1]['release'], q(3))
        self.assertEqual(v['blocks'][1]['events'][0]['event_id'], 's1')

    def test_cross_staff_same_voice(self):
        ir = ir_fixture(); ir['note_events'][2]['display_staff_id']='staff2'
        self.assertTrue(geometry(ir)['voices'][0]['comparison']['nonzero_shifted_rhythm_and_spelled_shape'])

    def test_parts_not_mixed_and_unequal_counts_abstain(self):
        ir = ir_fixture(); ir['note_events'][2]['part_id']='other'
        r = geometry(ir); self.assertEqual(len(r['voices']),2)
        self.assertTrue(all(v['comparison'] is None for v in r['voices']))
        self.assertTrue(any('different_event_counts_no_forced_alignment' in v['abstention_reasons'] for v in r['voices']))

    def test_grace_reported_and_excluded_not_crash(self):
        ir = ir_fixture(); n = {**ir['note_events'][0], 'note_id':'grace', 'grace':{'is_grace':True}}
        s = {**ir['sounding_events'][0], 'sounding_event_id':'grace', 'attack_note_id':'grace',
             'source_note_ids':['grace'], 'span':{'start':q(0),'end':q(0)}}
        ir['note_events'].append(n); ir['sounding_events'].append(s)
        r = geometry(ir); self.assertEqual(r['excluded_grace_event_ids'],['grace'])
        self.assertTrue(r['voices'][0]['comparison']['nonzero_shifted_rhythm_and_spelled_shape'])

    def test_invalid_time_and_source_references(self):
        for kind in ('float','negative','zero','reference','duplicate'):
            ir = ir_fixture()
            if kind=='float': ir['sounding_events'][0]['span']['start']=0.0
            if kind=='negative': ir['sounding_events'][0]['span']['end']=q(-1)
            if kind=='zero': ir['sounding_events'][0]['span']['end']=q(0)
            if kind=='reference': ir['sounding_events'][0]['source_note_ids']=['missing']
            if kind=='duplicate': ir['sounding_events'].append(ir['sounding_events'][0])
            with self.subTest(kind=kind), self.assertRaises(ValueError): geometry(ir)

    def test_pitch_mismatch_and_enharmonic_distinction(self):
        ir = ir_fixture(); ir['sounding_events'][0]['pitch']['midi_pitch'] += 1
        with self.assertRaisesRegex(ValueError,'pitch_spelling'): geometry(ir)
        ir = ir_fixture([('F',1,4),('A',0,4),('G',-1,4),('B',-2,4)])
        c = geometry(ir)['voices'][0]['comparison']
        self.assertEqual(c['semitone_displacements'],[0,0]); self.assertEqual(c['diatonic_displacements'],[1,1])
        self.assertFalse(c['diatonic_key_fit_verified'])

    def test_bounds_reject_gap(self):
        with self.assertRaises(ValueError): geometry(ir_fixture(),second={'start':q(3),'end':q(4)})


class AuditTest(unittest.TestCase):
    def test_window_preserves_nonmatch(self):
        a = [ann(s,i,i+1) for i,s in enumerate(['I','V','I','IV'])]
        self.assertEqual(len(list(windows(a))),1)

    def test_no_bridge_unverified_gap_key_or_unsupported(self):
        base = [ann(s,i,i+1) for i,s in enumerate(['I','V','vi','iii'])]
        self.assertEqual(list(windows(base,{'0','1','3'})),[])
        for kind in ('gap','key','unsupported'):
            a = copy.deepcopy(base)
            if kind=='gap': a[1]['target']['span']['start']=q(Fraction(3,2))
            if kind=='key': a[1]['raw_fields']['globalkey']='G'
            if kind=='unsupported': a[1]['raw_fields']['figbass']='7'
            self.assertEqual(list(windows(a)),[])

    def test_rights_holdout_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            with self.assertRaisesRegex(ValueError,'output_exists'): build('missing',p)
            e = {'split':'holdout','work_family_id':'w','score_sha256':'s','annotation_sha256':'a',
                 'collection_id':'mozart-sonatas','package_path':'missing','rights':{'internal_research_use':False}}
            m = p/'manifest.json'; m.write_text(json.dumps({'entries':[e]}))
            self.assertEqual(build(m,p/'out')['summary']['case_count'],0)
            e['split']='train'; m.write_text(json.dumps({'entries':[e]}))
            with self.assertRaisesRegex(ValueError,'research_not_permitted'): build(m,p/'bad')

    def test_catalog(self):
        u = next(x for x in concepts() if x['concept_id']=='hvl.unit18')
        self.assertEqual(u['reviewed_sections'],list(range(1,23)))
        self.assertEqual(u['rule_status'],'candidate_not_production')


if __name__ == '__main__': unittest.main()
