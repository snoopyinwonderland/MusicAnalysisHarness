import unittest
from copy import deepcopy
from test_harmony_open_candidates import score
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_joint import f
from musicanote_harness.harmony_progression_context import plan
from musicanote_harness.harmony_progression_resolution import analyze
from musicanote_harness.harmony_catalog_resolution import pitch_pair


def fixture(wrong=False, delayed=False, transpose=False, return_ir=False):
    names=['D3','F#4','A4','C5','G3','G4','B4','D5'] if transpose else ['C3','E4','G4','B-4','F3','F4','A4','C5']
    if wrong:names[6]='D5' if transpose else 'C5'
    specs=[(p,0,2 if delayed and i==1 else 1,str(i)) for i,p in enumerate(names[:4])]
    specs += [(p,2 if delayed and i==1 else 1,3,str(i)) for i,p in enumerate(names[4:])]
    ir=score(specs);events=ir['sounding_events'];p=plan(events,{'start':q(0),'end':q(3)})
    pairs=[([['D',0],['F',1],['A',0],['C',0]],['D',0]),([['G',0],['B',0],['D',0]],['G',0])] if transpose else [([['C',0],['E',0],['G',0],['B',-1]],['C',0]),([['F',0],['A',0],['C',0]],['F',0])]
    rows=[]
    for edge in p['intervals']:
        readings=[]
        for i,(members,root) in enumerate(pairs):
            readings.append({'candidate_ref':str(i),'alternative_index':0,'members':members,'root_spelling':root,
                'span':edge['span'],'abstention_reasons':[],
                'event_states':{s['sounding_event_id']:'member' if pitch_pair(s['pitch']) in members else 'nonmember_not_confirmed_nct'
                                for s in events if f(s['span']['start'])<f(edge['span']['end']) and f(s['span']['end'])>f(edge['span']['start'])}})
        rows.append({**edge,'readings':readings})
    links=[]
    for a,b in [(1,5),(3,6)]:links.append([events[a]['sounding_event_id'],events[b]['sounding_event_id']])
    r={'status':'ready','plan':p,'events':events,'edges':rows,'patterns':[],'withheld_pattern_reasons':{},
       'assignments':[{'assignment_id':'linked','links':links},{'assignment_id':'none','links':[]}],
       'cells':[{'span':{'start':a,'end':b},'event_refs':[s['sounding_event_id'] for s in events if f(s['span']['start'])<f(b) and f(s['span']['end'])>f(a)]} for a,b in zip(p['points'],p['points'][1:])]}
    path=[{'edge':next(i for i,e in enumerate(rows) if e['span']=={'start':q(a),'end':q(b)}),'reading':n} for a,b,n in [(0,1,0),(1,3,1)]]
    return (r,path,ir) if return_ir else (r,path)


class ResolutionTests(unittest.TestCase):
    def test_dominant_triad_family(self):
        r,p=fixture();s=r['edges'][p[0]['edge']]['readings'][0]
        s['members']=[['C',0],['E',0],['G',0]]
        a=analyze(r,p,'linked')['relations'][0]
        self.assertEqual(a['family'],'V');self.assertEqual(a['status'],'direct_resolution_supported_hypothesis')

    def test_leading_triad_family(self):
        r,p=fixture();s=r['edges'][p[0]['edge']]['readings'][0]
        s['root_spelling']=['E',0];s['members']=[['E',0],['G',0],['B',-1]]
        a=analyze(r,p,'linked')['relations'][0]
        self.assertEqual(a['family'],'vii');self.assertEqual(a['status'],'direct_resolution_supported_hypothesis')

    def test_diminished_and_half_diminished_shapes(self):
        for seventh,family in [(['D',-1],'vii7'),(['D',0],'vii_half7')]:
            r,p=fixture();s=r['edges'][p[0]['edge']]['readings'][0]
            s['root_spelling']=['E',0];s['members']=[['E',0],['G',0],['B',-1],seventh]
            a=analyze(r,p,'linked')['relations'][0]
            self.assertEqual(a['family'],family);self.assertEqual(a['status'],'shape_relation_only')

    def test_intervening_path_not_promoted(self):
        r,p=fixture(delayed=True)
        p=[{'edge':next(i for i,e in enumerate(r['edges']) if e['span']=={'start':q(a),'end':q(b)}),'reading':n}
           for a,b,n in [(0,1,0),(1,2,0),(2,3,1)]]
        a=next(x for x in analyze(r,p,'linked')['relations'] if x['source_path_index']==0)
        self.assertEqual(a['intervening_path_indices'],[1]);self.assertEqual(a['status'],'shape_relation_only')

    def test_direct_seventh_resolution(self):
        r,p=fixture();a=analyze(r,p,'linked')['relations'][0]
        self.assertEqual(a['family'],'V7');self.assertEqual(a['status'],'direct_resolution_supported_hypothesis')
        self.assertFalse(a['function_confirmed']);self.assertEqual(a['key_projections'],[])

    def test_wrong_seventh_shape_only(self):
        r,p=fixture(wrong=True);a=analyze(r,p,'linked')['relations'][0]
        self.assertEqual(a['status'],'shape_relation_only')
        self.assertIn('seventh_down_step_to_target_member',a['missing_direct_relations'])

    def test_no_assignment_no_resolution_claim(self):
        r,p=fixture();self.assertEqual(analyze(r,p,'none')['relations'][0]['status'],'shape_relation_only')

    def test_delayed_evidence_retained_not_direct(self):
        r,p=fixture(delayed=True);a=analyze(r,p,'linked')['relations'][0]
        self.assertEqual(a['status'],'shape_relation_only')
        self.assertTrue(any(e['arrival']==q(2) for e in a['voice_evidence']))

    def test_transposition_same_rule(self):
        r,p=fixture(transpose=True)
        self.assertEqual(analyze(r,p,'linked')['relations'][0]['status'],'direct_resolution_supported_hypothesis')

    def test_explicit_key_only_conditional_projection(self):
        r,p=fixture();keys=[{'key_id':'assumed','tonic':['C',0],'mode':'major','provenance':'test_assumption'}]
        a=analyze(r,p,'linked',keys)['relations'][0]['key_projections'][0]
        self.assertEqual(a['symbol_without_inversion'],'V7/IV');self.assertFalse(a['function_confirmed'])

    def test_blocker_respected(self):
        r,p=fixture();r['edges'][p[0]['edge']]['readings'][0]['abstention_reasons']=['blocked']
        self.assertEqual(analyze(r,p,'linked')['relations'][0]['status'],'blocked_context')

    def test_legacy_root_unavailable(self):
        r,p=fixture();r['edges'][p[0]['edge']]['readings'][0].pop('root_spelling')
        self.assertEqual(analyze(r,p,'linked')['relations'],[])

    def test_wrong_spelling_shape_not_matched(self):
        r,p=fixture();r['edges'][p[0]['edge']]['readings'][0]['members'][-1]=['A',1]
        self.assertEqual(analyze(r,p,'linked')['relations'],[])

    def test_bad_voice_link_rejected(self):
        r,p=fixture();r['assignments'][0]['links'][0].reverse()
        with self.assertRaises(ValueError):analyze(r,p,'linked')

    def test_input_unchanged(self):
        r,p=fixture();saved=deepcopy(r);analyze(r,p,'linked');self.assertEqual(r,saved)


if __name__=='__main__':unittest.main()
