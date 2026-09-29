import copy
import tempfile
import unittest
from pathlib import Path
from musicanote_harness.harmony_visual_review import overlaps, roman_projection, source_reference_key, key_token, system_fragments, write_page, build, verified_comparison, verified_ablation
from test_harmony_candidate_explanation import spelled, chord, span


class VisualReviewTests(unittest.TestCase):
    def comparison_fixture(self):
        identity = {'case_id': 'case', 'target_span': span(0,1), 'ir_sha256': 'ir'}
        run = {'margin_quarters': 1, 'analysis_span': span(0,2), 'experiment': {'segments': ['saved']}}
        old = {**identity, 'runs': [run]}
        new = {**identity, 'previous_result_sha256': 'old', 'runs': [{**run, 'baseline': copy.deepcopy(run['experiment'])}]}
        return old, new, {**identity, 'result_sha256': 'new'}

    def test_comparison_exact_saved_baseline(self):
        old, new, expected = self.comparison_fixture()
        result = verified_comparison(old, 'old', new, 'new', expected)
        self.assertFalse(result['comparison_provenance']['inference_rerun_by_viewer'])
        self.assertNotIn('comparison_provenance', new)

    def test_comparison_tampering_rejected(self):
        old, new, expected = self.comparison_fixture()
        with self.assertRaisesRegex(ValueError, 'hash_mismatch'):
            verified_comparison(old, 'old', new, 'different', expected)
        new['runs'][0]['baseline']['segments'] = ['changed']
        with self.assertRaisesRegex(ValueError, 'previous_engine_changed'):
            verified_comparison(old, 'old', new, 'new', expected)

    def test_ablation_verifies_policy_and_saved_replays(self):
        from test_harmony_joint import fixture
        from musicanote_harness.formal_ir import q
        from musicanote_harness.harmony_ablation_review import ARMS, NAMES
        from musicanote_harness.harmony_multiscale_shadow import analyze
        ir = fixture([(60,0,2,'v'),(64,0,2,'m'),(67,0,2,'b')])
        window = {'start': q(0), 'end': q(2)}
        variants = {arm: analyze(ir, analysis_span=window, **switches) for arm, switches in ARMS.items()}
        common = {'case_id':'c', 'target_span':span(0,1), 'ir_sha256':'ir'}
        run = {'analysis_span':window, 'margin_quarters':q(1)}
        previous = {**common, 'comparison_provenance':{'previous_result_sha256':'old','new_result_sha256':'prior'},
                    'runs':[{**run,'baseline':variants['none'],'experiment':variants['both']}]}
        ablation = {**common,'previous_result_sha256':'old','multiscale_result_sha256':'prior',
                    'arm_names':NAMES,'stability_components':{},'runs':[{**run,**variants}]}
        expected = {**common,'result_sha256':'new'}
        result = verified_ablation(previous, ablation, 'new', expected)
        self.assertEqual(set(result['runs'][0]['variants']),set(ARMS))
        self.assertNotIn('variants',previous['runs'][0])
        with self.assertRaisesRegex(ValueError,'hash_mismatch'):
            verified_ablation(previous,ablation,'changed',expected)
        ablation['runs'][0]['fifth_only']['policy']['enable_distributed']=True
        with self.assertRaisesRegex(ValueError,'policy_changed'):
            verified_ablation(previous,ablation,'new',expected)

    def test_half_open_overlap(self):
        self.assertFalse(overlaps(span(0,1),span(1,2)))
        self.assertTrue(overlaps(span(0,2),span(1,3)))

    def test_roman_is_display_only_and_does_not_mutate(self):
        ir=spelled([(55,'G',0),(59,'B',0),(62,'D',0),(65,'F',0)])
        candidate=chord(ir,'G:dominant7'); before=copy.deepcopy((ir,candidate))
        r=roman_projection(ir,span(0,1),candidate,'C')
        self.assertEqual(r['text'],'V7')
        self.assertFalse(r['used_for_inference'])
        self.assertEqual((ir,candidate),before)

    def test_no_invented_secondary_function(self):
        ir=spelled([(62,'D',0),(66,'F',1),(69,'A',0),(72,'C',0)])
        r=roman_projection(ir,span(0,1),chord(ir,'D:dominant7'),'C')
        self.assertEqual(r['text'],'II7')
        self.assertNotIn('/',r['text'])

    def test_unknown_does_not_invent_root_spelling_or_key(self):
        ir=spelled([(64,'E',0),(67,'G',0)])
        self.assertEqual(roman_projection(ir,span(0,1),chord(ir,'C:major'),'C')['text'],'unknown')
        self.assertEqual(roman_projection(ir,span(0,1),chord(ir,'E:minor'),None)['text'],'unknown')

    def test_enharmonic_conflict_abstains(self):
        ir=spelled([(53,'E',1),(68,'A',-1),(71,'B',0)])
        self.assertEqual(roman_projection(ir,span(0,1),chord(ir,'F:diminished'),'F#')['text'],'unknown')

    def test_display_uses_explicit_source_local_key_and_handles_b_minor(self):
        def a(g,l,m):return {'raw_fields':{'globalkey':g,'localkey':l,'localkey_is_minor':m}}
        self.assertEqual(source_reference_key(a('Ab','III','0')),'C')
        self.assertEqual(source_reference_key(a('e','v','1')),'b')
        self.assertEqual(source_reference_key(a('b','i','1')),'b')
        self.assertEqual(key_token('b'),'b')
        self.assertEqual(key_token('Bb'),'B-')
        self.assertIsNone(source_reference_key(a('C','I','')))

    def test_system_context_keeps_defs_and_source_ids(self):
        svg='<svg xmlns="http://www.w3.org/2000/svg"><defs><path id="glyph"/></defs><g><g class="system"><g class="note" data-id="n1"/></g><g class="system"><g class="note" data-id="n2"/></g></g></svg>'
        r=system_fragments([svg],{'n2'})
        self.assertEqual(len(r),1)
        self.assertIn('glyph',r[0]['svg'])
        self.assertIn('n2',r[0]['svg'])
        self.assertNotIn('n1',r[0]['svg'])
        self.assertEqual(r[0]['system'],2)

    def test_payload_cannot_escape_script(self):
        with tempfile.TemporaryDirectory() as d:
            dest=Path(d)/'review.html'
            write_page({'title':'</script><img onerror="bad">'},[],dest)
            content=dest.read_text(encoding='utf-8')
            self.assertNotIn('<img onerror',content)
            self.assertIn('\\u003c/script',content)

    def test_svg_href_and_nested_scaling_are_preserved_for_html(self):
        svg='<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"><defs><path id="glyph"/></defs><svg class="definition-scale" viewBox="0 0 18000 25000"><g class="system"><g data-id="n1"><use xlink:href="#glyph"/></g></g></svg></svg>'
        rendered=system_fragments([svg],{'n1'})[0]['svg']
        self.assertIn('href="#glyph"',rendered)
        self.assertNotIn('ns1:href',rendered)
        self.assertNotIn('definition-scale',rendered)
        self.assertIn('viewBox="0 0 18000 25000"',rendered)

    def test_existing_artifacts_not_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,'output_exists'):
                build('missing','missing','missing',d,'missing')


if __name__=='__main__':unittest.main()
