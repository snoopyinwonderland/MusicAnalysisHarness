from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from musicanote_harness import harmony_recipe_balance_trial as t
from musicanote_harness.harmony_source_clock import SourceClockGuard
from musicanote_harness.harmony_common_benchmark import evaluate, native_prediction, native_reference, summarize
from musicanote_harness.harmony_progression_search import _hash
from test_harmony_bounded_recovery import fixture, sample
from test_harmony_exact_frontier import problem
from test_harmony_structured_learning import entry, contract
from test_harmony_recipe_balance_learning import row as train_row


class TrialTests(unittest.TestCase):
    def disk(self, mode):
        with TemporaryDirectory() as folder:
            root = Path(folder); source = root/'prior'; source.mkdir(); output = root/'new'
            ir = fixture(); target = sample(); graph, ev = problem(ir)
            fixed = {k: t.scoring.F(1, 3) for k in t.scoring.support.FEATURES}
            ip = source/'ir.json.gz'; t.expanded.write_packet(ip, ir)
            xml = source/'source.musicxml'; xml.write_bytes(b"<score-partwise/>")
            src = {'canonical_ir_path': str(ip), 'source_musicxml_path': str(xml),
                'original_ir_content_sha256': _hash(ir), 'original_musicxml_sha256': t.expanded.digest(xml),
                'full_score_saved_with_surrounding_context': True}
            gp = source/'graph.json.gz'
            def save_graph():
                t.expanded.write_packet(gp, {'pair_id': 'pair', 'sample_id': target['sample_id'],
                    'span': target['span'], 'source': src, 'problem': t.prior.prior.graph_packet(graph)})
            save_graph(); chosen = t.scoring.support.Scorer(graph, ev, fixed).decode()
            arm = {'status': 'source_preflight_abstention', 'selected_prediction': None} if mode == 'abstention' else {
                'status': chosen['status'], 'selected_prediction': chosen['selected']}
            packet = {'pair_id': 'pair', 'sample_id': target['sample_id'], 'sample_span': target['span'],
                'plan_index': 0, 'collection_id': 'c', 'work_family_id': 'dev_family', 'reference_binding_verified': True,
                'attempted': mode != 'abstention', 'known_prior_diagnostic': True,
                'source_clock_gate': SourceClockGuard(ir).scope(target['span']), 'arms': {'train_calibrated': arm},
                'graph_artifact': str(gp), 'graph_sha256': t.expanded.digest(gp)}
            if mode == 'contamination': packet['arms']['train_calibrated']['evaluation'] = {}
            if mode == 'graph': packet['graph_sha256'] = 'changed'
            if mode == 'source':
                src['original_musicxml_sha256'] = 'changed'; save_graph(); packet['graph_sha256'] = t.expanded.digest(gp)
            pred = source/'p.json.gz'; t.expanded.write_packet(pred, packet)
            t.expanded.write(source/'run-contract.json', {'code_pins': {}, 'source_labels_used_at_inference': False})
            t.expanded.write(source/'prediction-freeze.json', {'contexts': 1, 'labels_read': False,
                'prediction_hashes': {str(pred): t.expanded.digest(pred)}})
            record = deepcopy(packet)
            record['reference_cells'] = [{'span': target['span'], 'signature': [['C', 0], [['C', 0], ['E', 0], ['G', 0]]]}]
            record['candidate_ceiling'] = {'oracle_reference_witness': None}
            result = record['arms']['train_calibrated']
            result['evaluation'] = evaluate(native_reference(record), native_prediction(result['selected_prediction'],
                target['span']), target['span'], selected=result['selected_prediction'] is not None)
            table = summarize([record | result])
            t.expanded.write(source/'report.json', {'records': [record], 'tables': {'control': table, 'train_calibrated': table},
                'input_hashes': {}, 'code_hashes': {}, 'artifact_hashes': {}, 'cases': []})
            original = t.load
            def read(p):
                if Path(p) == source/'report.json':
                    seal = original(output/'prediction-freeze.json')
                    self.assertFalse(seal['dev_labels_read'])
                    self.assertEqual(seal['model_sha256'], t.expanded.digest(output/'model.json'))
                return original(p)
            def prepare(read_fn, save, dest):
                manifest = [entry()]; use = contract(manifest); use['parent_recall_sha256'] = t.training.PARENT_SHA
                model = t.learning.fit([train_row()], use, manifest, t.training.PARENT_SHA)
                save(dest/'model.json', model)
                return model, use, manifest, {'counts': {'eligible_contrasts': 1}}, fixed
            with patch.object(t, 'BASELINE_REPORT_SHA', t.expanded.digest(source/'report.json')), \
                 patch.object(t, 'load', side_effect=read), patch.object(t.training, 'prepare', side_effect=prepare), \
                 patch.object(t.prior.prior, 'prepare', side_effect=AssertionError('dev_graph_rebuild_forbidden')):
                if mode in ('contamination', 'graph', 'source'):
                    with self.assertRaisesRegex(ValueError, 'changed|reference_bearing'): t.run(source, output)
                else:
                    result = t.run(source, output); report = original(output/'report.json')
                    self.assertEqual(report['tables']['support_calibrated'], table)
                    self.assertFalse(result['production_modified'])
                    self.assertFalse(result['dev_graph_generation_performed'])
                    self.assertEqual(result['named_family_overlap'], [])

    def test_seal_and_same_frozen_support_control(self): self.disk('selected')
    def test_old_abstentions_kept(self): self.disk('abstention')
    def test_reference_contamination_rejected(self): self.disk('contamination')
    def test_graph_tamper_rejected(self): self.disk('graph')
    def test_source_tamper_rejected(self): self.disk('source')
    def test_no_overwrite(self):
        with TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError, 'output_exists'): t.run('missing', d)

    def test_training_fixed_coefficients_included_in_base_cost(self):
        # The new fit must not silently use the pre-step67 base score.
        from musicanote_harness import harmony_recipe_balance_training as train
        from musicanote_harness.harmony_structured_learning import content_hash
        from musicanote_harness.harmony_margin_learning import training_loss, path_loss
        from test_harmony_functional_scoring import C, G
        graph, ev = problem(); by = {(e.start, e.end, e.signature): e.group_id for e in graph.edges}
        negative = (by[t.scoring.F(), t.scoring.F(4), G],)
        target = (by[t.scoring.F(), t.scoring.F(4), C],)
        cells = ({'start': t.scoring.F(), 'end': t.scoring.F(4), 'signature': C},)
        loss = training_loss(graph, cells, t.scoring.F(1, 4))
        details = path_loss(graph, {'selected': {'segments': [{'semantic_group_ref': i} for i in negative]}}, loss)
        item = {'contrast_id': content_hash([negative, target]), 'negative_ids': negative, 'target_ids': target,
                'loss_details': details, 'historical_kind': 'update'}
        fixed = {k: t.scoring.F(1, 2) for k in t.scoring.support.FEATURES}
        result = train.contrast_row(item, entry(), graph, ev, {}, fixed, cells)
        scorer = t.scoring.support.Scorer(graph, ev, fixed, build_index=False)
        self.assertEqual(result['base_cost_gap'], t.scoring.support.q(scorer.score_path(negative)-scorer.score_path(target)))
        self.assertEqual(set(result['feature_delta']), {t.scoring.FEATURE})
