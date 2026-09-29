import copy
from fractions import Fraction as F
import unittest
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_joint import candidates, prepare, analyze_joint
from musicanote_harness.harmony_temporal_shadow import analyze
from musicanote_harness.harmony_candidate_explanation import explain_candidate, explain_path, spelling_evidence, score_fixed_path
from test_harmony_joint import fixture


def span(a,b):return {'start':q(a),'end':q(b)}


def chord(ir,label,a=0,b=1):
    rows,neighbors=prepare(ir)
    return next(c for c in candidates(rows,neighbors,F(a),F(b),F(1),limit=None,min_shared_pcs=0) if c['label']==label)


def spelled(specs):
    ir=fixture([(p,0,1,str(i)) for i,(p,step,alter) in enumerate(specs)])
    for s,(_,step,alter) in zip(ir['sounding_events'],specs):
        s['pitch'].update(step=step,alter=q(alter))
    return ir


class ExplanationTests(unittest.TestCase):
    def test_inversion_penalty_not_wrong_note(self):
        ir=fixture([(55,0,1,'b'),(59,0,1,'v'),(64,0,1,'w')]);original=copy.deepcopy(ir)
        r=explain_candidate(ir,span(0,1),chord(ir,'E:minor'),F(1))
        self.assertEqual(r['pooled_cost_parts'],{'unexplained_notes':0,'missing_template_members':0,'bass_not_root':.04})
        self.assertEqual(ir,original)

    def test_nct_explains_discount_and_original_span(self):
        ir=fixture([(48,0,4,'b'),(67,0,4,'i'),(60,0,1,'v'),(62,1,F(3,2),'v'),(64,F(3,2),4,'v')])
        c=chord(ir,'C:major',0,4);r=explain_candidate(ir,span(0,4),c,F(1))
        note=next(n for n in r['notes'] if n['sounding_event_id']=='s3')
        self.assertEqual(note['conditional_nct']['type'],'passing_like')
        self.assertAlmostEqual(sum(r['pooled_cost_parts'].values()),c['cost'])
        self.assertEqual(note['original_span'],span(1,F(3,2)))

    def test_e_sharp_spelling_without_relabeling_candidate(self):
        ir=spelled([(53,'E',1),(68,'G',1),(71,'B',0)])
        c=chord(ir,'F:diminished');original=copy.deepcopy(c)
        r=spelling_evidence(ir,span(0,1),c)
        self.assertEqual(r['candidates'][0]['conditional_label'],'E#:diminished')
        self.assertEqual(r['candidates'][0]['expected_members'],['E#','G#','B'])
        self.assertEqual(r['candidates'][0]['conflicting_event_refs'],[])
        self.assertEqual(c,original)

    def test_enharmonic_conflict_not_silently_corrected(self):
        ir=spelled([(53,'E',1),(68,'A',-1),(71,'B',0)])
        r=spelling_evidence(ir,span(0,1),chord(ir,'F:diminished'))
        self.assertEqual(r['candidates'][0]['conflicting_event_refs'],['s1'])

    def test_unobserved_root_abstains(self):
        ir=spelled([(64,'E',0),(67,'G',0)])
        r=spelling_evidence(ir,span(0,1),chord(ir,'C:major'))
        self.assertEqual(r['status'],'root_spelling_unobserved')
        self.assertEqual(r['candidates'],[])

    def test_double_accidental_supported_microtonal_abstains(self):
        ir=spelled([(62,'E',-2),(66,'G',-1),(69,'B',-2)])
        r=spelling_evidence(ir,span(0,1),chord(ir,'D:major'))
        self.assertEqual(r['candidates'][0]['expected_members'],['Ebb','Gb','Bbb'])
        ir['sounding_events'][0]['pitch']['alter']=q(F(1,2))
        r=spelling_evidence(ir,span(0,1),chord(ir,'D:major'))
        self.assertIn('s0',r['unsupported_pitch_event_refs'])

    def test_both_path_costs_reconstructed(self):
        ir=fixture([(p,a,b,str(i)) for a,b,ps in [(0,1,[55,59,62,65]),(1,2,[60,64,67])]
                    for i,p in enumerate(ps)])
        for result in [analyze_joint(ir,analysis_span=span(0,2)),analyze(ir,cell_divisions=2,analysis_span=span(0,2))]:
            self.assertAlmostEqual(explain_path(result)['reconstructed_path_cost'],result['path_cost'])
            result['path_cost']+=1
            with self.assertRaisesRegex(ValueError,'path_cost_reconstruction'):explain_path(result)

    def test_cost_drift_rejected(self):
        ir=fixture([(60,0,1,'b'),(64,0,1,'v'),(67,0,1,'w')]);c=chord(ir,'C:major');c['cost']+=1
        with self.assertRaisesRegex(ValueError,'candidate_cost_reconstruction'):
            explain_candidate(ir,span(0,1),c,F(1))

    def test_fixed_path_same_objective_matches_original(self):
        ir=fixture([(p,a,b,str(i)) for a,b,ps in [(0,1,[60,64,67]),(1,2,[62,65,69])]
                    for i,p in enumerate(ps)])
        for use_temporal in (False,True):
            r=analyze(ir,cell_divisions=2,analysis_span=span(0,2)) if use_temporal else analyze_joint(ir,analysis_span=span(0,2))
            original=copy.deepcopy(r)
            self.assertAlmostEqual(score_fixed_path(ir,r,use_temporal)['reconstructed_path_cost'],r['path_cost'])
            self.assertEqual(r,original)
