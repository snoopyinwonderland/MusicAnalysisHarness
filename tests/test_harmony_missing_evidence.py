import unittest
from copy import deepcopy
from test_harmony_distributed_resolution import fixture
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_candidate_relation_survey import local_query
from musicanote_harness.harmony_missing_evidence import audit_pair, pattern_check, validate_ir, role


def data():
    r,p,ir=fixture()
    pair={'source':p[0],'target':p[1],'family':'V7','target_quality':'M'}
    item={'pair':pair,**local_query(r,pair,ir,temporal=True)}
    return r,p,ir,item


class MissingEvidenceTests(unittest.TestCase):
    def test_general_spelled_roles(self):
        self.assertEqual(role(['G',0],['C',0]),'fifth')
        self.assertEqual(role(['A',0],['D',0]),'fifth')
        self.assertEqual(role(['B',-1],['C',0]),'seventh')

    def test_missing_in_candidate_but_present_elsewhere_not_merged(self):
        r,p,ir=fixture([('C3',0,1,'b'),('E4',0,2,'l'),('B-4',0,1,'s'),
                        ('F3',1,3,'b'),('F4',2,3,'l'),('A4',1,3,'s'),('C5',1,3,'g'),('G4',1,2,'extra')])
        pair={'source':p[0],'target':p[1],'family':'V7','target_quality':'M'}
        a=audit_pair(r,{'pair':pair,**local_query(r,pair,ir,temporal=True)})
        m=a['sides']['source']['missing'][0]
        self.assertEqual(m['status'],'available_elsewhere_in_parent')
        self.assertFalse(m['boundary_extension_authorized']);self.assertFalse(m['omission_confirmed'])

    def test_absent_in_parent_does_not_confirm_omission(self):
        r,p,ir=fixture([('C3',0,1,'b'),('E4',0,2,'l'),('B-4',0,1,'s'),
                        ('F3',1,3,'b'),('F4',2,3,'l'),('A4',1,3,'s'),('C5',1,3,'g')])
        pair={'source':p[0],'target':p[1],'family':'V7','target_quality':'M'}
        a=audit_pair(r,{'pair':pair,**local_query(r,pair,ir,temporal=True)})
        self.assertEqual(a['sides']['source']['missing'][0]['status'],'not_observed_in_parent')

    def pattern(self):
        r,p,ir,item=data();sid=r['events'][2]['sounding_event_id']
        shape={'pattern_id':'test','kind':'held_candidate','event_refs':[sid],'affected_event_ref':sid,
               'nonmember_span':{'start':q(1),'end':q(2)},'supporting_assignment_refs':['none'],
               'requirements':[{'event_ref':sid,'state':'member','span':{'start':q('1/2'),'end':q(1)}},
                               {'event_ref':sid,'state':'nonmember_not_confirmed_nct','span':{'start':q(1),'end':q(2)}}]}
        r['patterns']=[shape]
        return r,p,ir,item,shape

    def test_pattern_is_conditional_with_exact_coverage(self):
        r,p,ir,item,shape=self.pattern();a=audit_pair(r,item)
        note=next(n for n in a['sides']['target']['nonmembers'] if n['event_ref']==shape['affected_event_ref'])
        evidence=note['pattern_alternatives'][0]
        self.assertEqual(evidence['status'],'conditional_pattern_compatible')
        self.assertTrue(evidence['covers_entire_nonmember_span']);self.assertFalse(evidence['confirmed_nct'])

    def test_pattern_conflict_does_not_excuse_note(self):
        r,p,ir,item,shape=self.pattern();shape['requirements'][0]['state']='nonmember_not_confirmed_nct'
        a=audit_pair(r,item)['sides']['target']['nonmembers'][0]['pattern_alternatives'][0]
        self.assertEqual(a['status'],'membership_conflict')

    def test_withheld_pattern_not_promoted(self):
        r,p,ir,item,shape=self.pattern();r['withheld_pattern_reasons']={'test':['unverified_preparation']}
        a=audit_pair(r,item)['sides']['target']['nonmembers'][0]['pattern_alternatives'][0]
        self.assertEqual(a['status'],'withheld_conditions')

    def test_external_requirement_not_silently_dropped(self):
        r,p,ir,item,shape=self.pattern()
        readings=[deepcopy(r['edges'][choice['edge']]['readings'][choice['reading']]) for choice in p]
        readings[0]['span']['start']=q('3/4')
        self.assertEqual(pattern_check(shape,readings,r)['status'],'requires_external_candidate_context')

    def test_partial_span_not_whole_note(self):
        r,p,ir,item,shape=self.pattern();shape['nonmember_span']['end']=q('3/2')
        a=audit_pair(r,item)['sides']['target']['nonmembers'][0]['pattern_alternatives'][0]
        self.assertFalse(a['covers_entire_nonmember_span'])

    def test_profile_mutation_rejected(self):
        r,p,ir,item=data();item['temporal_query']['source_profile']['missing_members']=[['C',0]]
        with self.assertRaisesRegex(ValueError,'saved_profile_mismatch'):audit_pair(r,item)

    def test_candidate_identity_checked(self):
        r,p,ir,item=data();item['source_candidate_ref']='wrong'
        with self.assertRaisesRegex(ValueError,'origin_mismatch'):audit_pair(r,item)

    def test_ir_identity_checked(self):
        r,p,ir,item=data();ir=deepcopy(ir);ir['sounding_events'][0]['pitch']['midi_pitch']+=1
        with self.assertRaisesRegex(ValueError,'identity_mismatch'):validate_ir(r,ir)

    def test_unknown_assignment_rejected(self):
        r,p,ir,item,shape=self.pattern();shape['supporting_assignment_refs']=['invented']
        with self.assertRaisesRegex(ValueError,'unknown_pattern_assignment'):audit_pair(r,item)

    def test_inputs_preserved(self):
        r,p,ir,item,shape=self.pattern();saved=deepcopy((r,item));audit_pair(r,item)
        self.assertEqual((r,item),saved)


if __name__=='__main__':unittest.main()
