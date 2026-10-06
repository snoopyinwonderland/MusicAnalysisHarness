from copy import deepcopy
from fractions import Fraction as F
import unittest
from test_harmony_open_candidates import score
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_candidate_catalog import propose
from musicanote_harness.harmony_catalog_microtime import enrich
from musicanote_harness.harmony_catalog_paths import analyze, condition


def fixture(names=('G4','A4','B4'),poly=False,gap=False):
    rows=[('D3',0,1,'b'),('F#3',0,1,'l'),('A3',0,1,'f'),('C5',0,1,'v'),
          ('G3',1,3,'b'),('D4',1,3,'f')]
    rows += [(p,F(5+i,4), F(6+i,4)-(F(1,8) if gap and i==0 else 0),'v') for i,p in enumerate(names)]
    if poly:rows.append(('D5',F(5,4),2,'v'))
    return score(rows)


def run(ir):
    a=propose(ir,{'start':q(0),'end':q(1)});b=propose(ir,{'start':q(1),'end':q(3)})
    return analyze(ir,a,b),a,b


def selected(result):
    return next(p for p in result['arrival_path_assessment']['paths'].values()
                if len(p['observation']['arrival_event_refs'])==3)


def target(path):
    return next(c for c in path['conditions'] if c['hypothesis']=='target_arrival_hypothesis'
                and c['compatible_patterns'])


class CatalogPathsTests(unittest.TestCase):
    def test_parsed_xml_controls(self):
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from musicanote_harness.harmony_catalog_paths_trial import controls
        with TemporaryDirectory() as folder:
            rows=controls(Path(folder)/'controls')
            self.assertEqual(len(rows),18);self.assertTrue(all(r['passed'] for r in rows))

    def test_passing_path_preserves_all_intermediate_notes(self):
        r,_,_=run(fixture());p=selected(r);c=target(p)
        self.assertEqual(c['conditional_ornaments'][0]['conditional_role'],'passing_candidate')
        self.assertEqual(len(p['observation']['arrival_event_refs']),3)
        self.assertTrue(p['observation']['all_intervening_refs_preserved'])
        self.assertFalse(p['observation']['voice_connection_confirmed'])

    def test_unfolding_requires_three_distinct_members(self):
        p=selected(run(fixture(('G4','D4','B4')))[0])
        self.assertIn('chord_member_unfolding_compatible',target(p)['compatible_patterns'])

    def test_neighbor_is_conditional_not_nct_truth(self):
        r,_,_=run(fixture(('B4','C5','B4')))
        p=selected(r);o=target(p)['conditional_ornaments'][0]
        self.assertEqual(o['conditional_role'],'neighbor_candidate');self.assertFalse(o['nct_confirmed'])

    def test_polyphony_blocks_fictional_melody(self):
        r,_,_=run(fixture(poly=True))
        for p in r['arrival_path_assessment']['paths'].values():
            self.assertTrue(p['observation']['abstention_reasons'])
            self.assertTrue(all(not c['compatible_patterns'] for c in p['conditions']))

    def test_arrival_gap_does_not_disappear(self):
        p=selected(run(fixture(gap=True))[0])
        self.assertTrue(p['observation']['arrival_gaps'])
        self.assertFalse(any(c['compatible_patterns'] for c in p['conditions']))

    def test_enharmonic_nonstep_not_passing(self):
        p=selected(run(fixture(('G4','G##4','B4')))[0])
        self.assertFalse(any(c['conditional_ornaments'] for c in p['conditions']))

    def test_source_hold_declares_extension(self):
        p=selected(run(fixture())[0]);cs=[c for c in p['conditions'] if c['hypothesis']=='source_hold_counterfactual']
        self.assertTrue(cs);self.assertTrue(all(c['outside_extension_assumption'] for c in cs))

    def test_local_chord_alternatives_never_prove_change(self):
        r,_,_=run(fixture());p=selected(r)
        self.assertTrue(p['alternative_cell_catalog_refs']);self.assertFalse(p['local_cells_prove_change'])
        for wid in p['alternative_cell_catalog_refs']:
            cat=r['arrival_path_assessment']['local_catalogs'][wid]
            self.assertIsNone(cat['selected']);self.assertTrue(cat['candidates'])

    def test_input_and_all_old_edge_fields_unchanged(self):
        ir=fixture();old=deepcopy(ir);r,l,rt=run(ir);base=enrich(ir,l,rt)
        self.assertEqual(ir,old)
        for new,b in zip(r['edges'],base['edges']):self.assertEqual({k:new[k] for k in b},b)

    def test_initial_gap_never_becomes_resolution(self):
        p=selected(run(fixture())[0]);obs=p['observation']
        self.assertEqual(obs['initial_gap'],{'start':q(1),'end':q(F(5,4))})
        self.assertFalse(obs['independent_resolution_vote_allowed'])

    def test_partial_candidate_cannot_claim_full_arrival(self):
        r,l,rt=run(fixture());p=selected(r)
        c=deepcopy(next(c for c in rt['candidates'] if c['spelling_alternatives']));c['span']['end']=q(F(3,2))
        v=condition(p['observation'],c,0,'target_arrival_hypothesis')
        self.assertIn('arrival_not_covered_by_candidate',v['abstention_reasons'])
        self.assertTrue(v['outside_candidate_span']);self.assertFalse(v['outside_extension_assumption'])

    def test_annotations_do_not_supply_answers(self):
        ir=fixture();a=run(ir)[0];ir['annotations']=[{'label':'V7/V'}];ir['phrases']=[123]
        self.assertEqual(a,run(ir)[0])
