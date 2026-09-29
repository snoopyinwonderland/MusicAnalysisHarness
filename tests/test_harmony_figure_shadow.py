from copy import deepcopy
from fractions import Fraction as F
import unittest
from xml.etree import ElementTree as ET
from music21 import pitch
from test_harmony_joint import fixture as base_ir
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_joint import f
from musicanote_harness.harmony_figure_trial import fixture,fixture_xml
from musicanote_harness.harmony_figure_shadow import analyze,inspect_cells,explain
from musicanote_harness.harmony_multiscale_shadow import analyze as baseline
from musicanote_harness.harmony_arpeggio_benchmark import signature


def make_ir(kind,transpose=0,scale=F(1)):
    c=fixture(kind,transpose,scale)
    ir=base_ir([(int(pitch.Pitch(e['pitch']).midi),f(e['start']),f(e['start'])+f(e['duration']),e['voice']) for e in c['events']])
    ir['measures'][0].update(actual_duration_quarter=q(4*scale),time_signature={'beat_type':c['beat_type']})
    for s,e in zip(ir['sounding_events'],c['events']):
        p=pitch.Pitch(e['pitch']);s['pitch'].update(step=p.step,alter=q(int(p.accidental.alter) if p.accidental else 0),spelling=p.nameWithOctave)
    return ir


class FigureShadowTests(unittest.TestCase):
    def test_zero_weight_matches_existing_engine(self):
        ir=make_ir('same_chord');old=baseline(ir);new=analyze(ir,weight=0)
        self.assertEqual(signature(old),signature(new));self.assertAlmostEqual(old['path_cost'],new['path_cost'])

    def test_complete_vertical_replacement_veto_even_when_union_is_seventh(self):
        ir=make_ir('change_inside_cell_shared_seventh_union')
        cells=inspect_cells(ir,{'start':q(0),'end':q(4)})
        self.assertTrue(cells)
        self.assertTrue(all(c['eligibility']=='vertical_replacement_guard' for c in cells))
        self.assertTrue(all(any(x['quality']=='major7' for x in c['complete_shapes']) for c in cells))
        self.assertTrue(all(c['change_guards'] for c in cells))

    def test_arpeggio_eligible_but_repetitions_do_not_share_harmony(self):
        ir=make_ir('different_chords_between_cells')
        cells=inspect_cells(ir,{'start':q(0),'end':q(4)})
        self.assertTrue(any(c['eligibility']=='eligible_recurrent_complete_cell' for c in cells))
        out=analyze(ir)
        self.assertEqual([(s['selected']['root'],s['span']) for s in out['segments']],
                         [(0,{'start':q(0),'end':q(2)}),(7,{'start':q(2),'end':q(4)})])

    def test_transposition_and_time_scaling(self):
        initial=signature(analyze(make_ir('different_chords_between_cells')))
        for tr,scale in [(2,F(1)),(0,F(1,2))]:
            self.assertEqual(signature(analyze(make_ir('different_chords_between_cells',tr,scale)),tr,scale),initial)

    def test_cost_accounting_no_duplicate_cell_charge(self):
        result=analyze(make_ir('same_chord'))
        self.assertAlmostEqual(explain(result)['reconstructed_path_cost'],result['path_cost'])
        self.assertTrue(all(s['selected']['figure_split_charge']<=.08 for s in result['segments']))

    def test_inputs_and_labels_do_not_affect_results(self):
        ir=make_ir('same_chord');copy=deepcopy(ir);r=analyze(ir)
        self.assertEqual(ir,copy)
        self.assertEqual(r,analyze({**ir,'annotations':['V'],'phrases':[1,2]}))

    def test_half_scale_xml_has_correct_divisions_and_type(self):
        root=ET.fromstring(fixture_xml(fixture('same_chord',scale=F(1,2))))
        self.assertEqual(root.findtext('.//divisions'),'16')
        self.assertEqual(root.findtext('.//note/type'),'32nd')
        self.assertEqual(root.findtext('.//time/beat-type'),'8')

    def test_invalid_options(self):
        ir=make_ir('same_chord')
        for w in (-1,.16,float('nan'),True):
            with self.assertRaises(ValueError):analyze(ir,weight=w)
        with self.assertRaises(ValueError):analyze(ir,enable_guard='yes')


if __name__=='__main__':unittest.main()
