import unittest
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_failure_context_audit import boundary_kind, cell_support
from musicanote_harness.harmony_context_sensitivity import stability_components
from test_harmony_joint import fixture


def annotation(a,b,**kw):
    fields={'globalkey':'C','localkey':'I','numeral':'V','chord_type':'Mm7','root':'1','chord':'V7',
            'figbass':'7','changes':'','form':'','relativeroot':''}
    fields.update(kw)
    return {'target':{'span':{'start':q(a),'end':q(b)}},'raw_fields':fields}


def result(rows):
    return {'analysis_span':{'start':q(rows[0][0]),'end':q(rows[-1][1])},
            'segments':[{'span':{'start':q(a),'end':q(b)},'selected':{'label':label}} for a,b,label in rows]}


class FailureContextTests(unittest.TestCase):
    def test_ornament_change_is_not_root_quality_change(self):
        self.assertEqual(boundary_kind(annotation(0,1,chord='V7(6)',changes='6'),annotation(1,2)),
                         'same_identity_surface_detail_change')

    def test_inversion_and_key_changes_remain_distinct(self):
        self.assertEqual(boundary_kind(annotation(0,1,figbass='65'),annotation(1,2)),'source_inversion_change')
        self.assertEqual(boundary_kind(annotation(0,1),annotation(1,2,localkey='V')),'source_harmonic_identity_change')

    def test_missing_fields_and_gaps_abstain(self):
        self.assertEqual(boundary_kind(annotation(0,1),annotation(1,2,numeral='')),'insufficient_source_fields')
        self.assertEqual(boundary_kind(annotation(0,1),annotation(2,3)),'noncontiguous_source_records')

    def test_incomplete_seventh_current_gate_abstains(self):
        ir=fixture([(54,0,1,'b'),(70,0,1,'v'),(76,0,1,'w')])
        cells=cell_support(ir,{'start':q(0),'end':q(1)})
        self.assertTrue(all(c['top_candidates'][0]['label']=='F#:dominant7' for c in cells))
        self.assertTrue(all(not c['used_by_current_temporal_gate'] for c in cells))
        self.assertTrue(all(c['abstention_reason']=='best_template_incomplete' for c in cells))

    def test_distributed_and_vertical_have_different_gate_evidence(self):
        target={'start':q(0),'end':q(2)}
        distributed=fixture([(60,0,1,'v'),(53,1,2,'b'),(68,1,2,'w')])
        vertical=fixture([(60,0,2,'v'),(53,0,2,'b'),(68,0,2,'w')])
        self.assertFalse(any(c['used_by_current_temporal_gate'] for c in cell_support(distributed,target)))
        self.assertTrue(all(c['used_by_current_temporal_gate'] for c in cell_support(vertical,target)))

    def test_edge_instability_does_not_mean_label_instability(self):
        runs=[{'e':result([(0,2,'G7'),(2,3,'C')])},
              {'e':result([(0,1,'Cm'),(1,2,'G7'),(2,4,'C')])}]
        r=stability_components(runs,'e',{'start':q(1),'end':q(2)},2)
        self.assertEqual(r,{'target_labels':True,'internal_boundaries':True,'target_edge_support':False})

    def test_missing_runs_stay_unknown(self):
        self.assertEqual(set(stability_components([],'e',{'start':q(0),'end':q(1)},2).values()),{None})
