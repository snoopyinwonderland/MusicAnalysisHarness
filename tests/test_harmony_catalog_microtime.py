from copy import deepcopy
from fractions import Fraction as F
import unittest
from test_harmony_open_candidates import score
from test_harmony_catalog_resolution import catalogs, chosen, fixture
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_catalog_resolution import compare
from musicanote_harness.harmony_catalog_microtime import plan, enrich, arrival


def delayed_fixture():
    return score([('D3',0,2,'b'),('F#4',0,2,'l'),('A4',0,2,'f'),('C5',0,2,'s'),
                  ('G3',2,4,'b'),('G4',F(5,2),4,'l'),('D5',2,4,'f'),('B4',F(5,2),4,'s')])


class MicrotimeTests(unittest.TestCase):
    def test_parsed_xml_controls_and_transformation_invariance(self):
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from musicanote_harness.harmony_catalog_microtime_trial import controls
        with TemporaryDirectory() as folder:
            rows=controls(Path(folder)/'controls')
            self.assertEqual(len(rows),15)
            self.assertTrue(all(r['passed'] for r in rows))

    def test_actual_boundaries_not_arbitrary_grid(self):
        ir=fixture(late=True);r=plan(ir,{'start':q(0),'end':q(4)})
        self.assertEqual([w['boundary'] for w in r['windows']],[q(1),q(2)])
        self.assertFalse(r['boundary_selected'])

    def test_radius_tracks_denominator_not_fixed_quarter(self):
        ir=fixture();ir['measures'][0]['time_signature']['beat_type']=8
        w=plan(ir,{'start':q(0),'end':q(4)})['windows'][0]
        self.assertEqual(w['left']['start'],q(F(3,2)))
        self.assertEqual(w['right']['end'],q(F(5,2)))

    def test_unknown_meter_abstains_without_guessing(self):
        ir=fixture();ir['measures'][0]['time_signature']={}
        r=plan(ir,{'start':q(0),'end':q(4)})
        self.assertFalse(r['windows']);self.assertTrue(r['abstentions'])

    def test_invalid_span_rejected(self):
        with self.assertRaises(ValueError):plan(fixture(),{'start':q(2),'end':q(1)})

    def test_late_arrival_keeps_actual_time_and_direct_status(self):
        ir=delayed_fixture();left,right=catalogs(ir);before=compare(ir,left,right)
        r=enrich(ir,left,right);e=chosen(r)
        self.assertEqual(e['target_arrival']['cumulative_identity_time'],q(F(5,2)))
        self.assertEqual(e['target_arrival']['first_simultaneous_identity_time'],q(F(5,2)))
        self.assertEqual(e['status'],'shape_relation_only')
        self.assertEqual([e['status'] for e in r['edges']],[e['status'] for e in before['edges']])
        self.assertEqual(len(e['delayed_endpoint_hypotheses']),2)
        self.assertTrue(all(not x['eligible_as_direct_resolution'] for x in e['delayed_endpoint_hypotheses']))

    def test_sequential_sightings_never_claim_simultaneity(self):
        ir=score([('D3',0,2,'b'),('F#4',0,2,'l'),('A4',0,2,'f'),('C5',0,2,'s'),
                  ('G3',2,F(5,2),'b'),('B4',F(5,2),4,'s'),('D5',2,4,'f')])
        e=chosen(enrich(ir,*catalogs(ir)))
        self.assertEqual(e['target_arrival']['cumulative_identity_time'],q(F(5,2)))
        self.assertIsNone(e['target_arrival']['first_simultaneous_identity_time'])

    def test_rest_is_preserved_not_explained_away(self):
        ir=delayed_fixture()
        ir['rest_events']=[{'rest_id':'r1','part_id':'part1','voice_id':'l',
                           'global_onset_quarter':q(2),'notated_duration_quarter':q(F(1,2))}]
        e=chosen(enrich(ir,*catalogs(ir)))
        self.assertTrue(any('r1' in x['rest_refs'] for x in e['delayed_endpoint_hypotheses']))

    def test_wrong_direction_does_not_gain_endpoint_support(self):
        ir=delayed_fixture()
        for sound in ir['sounding_events']:
            if sound['pitch']['spelling']=='G4':
                sound['pitch'].update(step='E',spelling='E4',midi_pitch=64)
        e=chosen(enrich(ir,*catalogs(ir)))
        self.assertFalse(any('leading_tone_endpoint_compatible' in x['relations'] for x in e['delayed_endpoint_hypotheses']))

    def test_inputs_unchanged_and_existing_direct_evidence_unchanged(self):
        ir=fixture();l,r=catalogs(ir);saved=deepcopy((ir,l,r));base=compare(ir,l,r)
        newer=enrich(ir,l,r)
        self.assertEqual(saved,(ir,l,r))
        for edge,old in zip(newer['edges'],base['edges']):
            self.assertEqual({k:edge[k] for k in old},old)

    def test_context_edges_clip_window(self):
        w=plan(fixture(),{'start':q(F(3,2)),'end':q(F(5,2))})['windows'][0]
        self.assertTrue(w['clipped_by_context'])
        self.assertEqual(w['left']['start'],q(F(3,2)))
        self.assertEqual(w['right']['end'],q(F(5,2)))

    def test_release_only_anchor_is_preserved(self):
        ir=score([('C4',0,1,'a'),('E4',0,4,'b')])
        w=plan(ir,{'start':q(0),'end':q(4)})['windows'][0]
        self.assertFalse(w['attack_refs']);self.assertTrue(w['release_refs'])
