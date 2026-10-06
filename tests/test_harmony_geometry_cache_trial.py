import gzip
import json
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock
from unittest.mock import patch

from test_harmony_breadth_trial import disk_package, write_json
from musicanote_harness import harmony_breadth_trial as breadth
from musicanote_harness import harmony_geometry_cache_trial as trial


def reference(root):
    track, entry, ir = disk_package(root/'input')
    folder = root/'reference'; folder.mkdir()
    _, source = breadth._freeze_package({'track':track, 'manifest_entry':entry,
                                        'pair_id':track['pair_id']}, folder, Mock())
    plan = breadth.freeze_score(ir, 1)
    sample_row = plan['selected_samples'][0]
    result = breadth.analyze_sample(ir, sample_row['sample'])
    artifact = folder/'sample.json.gz'
    artifact.write_bytes(gzip.compress(json.dumps(result).encode(), mtime=0))
    package = {'pair_id':track['pair_id'], 'source':source,
               'plan':{**plan, 'selected_samples':[sample_row]}}
    plan_path = folder/'frozen-plan.json'; write_json(plan_path, {'packages':[package]})
    write_json(folder/'run-contract.json', {'frozen_plan_sha256':trial.digest(plan_path),
                                           'input_hashes':{}})
    write_json(folder/'report.json', {'complete':True, 'inputs_unchanged':True,
        'source_labels_used':False, 'accuracy_measured':False, 'unique_work_families':1,
        'records':[{'pair_id':track['pair_id'], 'sample_id':sample_row['sample']['sample_id'],
                    'plan_index':sample_row['plan_index'], 'status':result['summary']['status'],
                    'artifact':str(artifact), 'sha256':trial.digest(artifact)}]})
    return folder, ir, result


class CacheTrialTests(unittest.TestCase):
    def test_real_pipeline_equality_and_input_preservation(self):
        with TemporaryDirectory() as tmp:
            folder, ir, saved = reference(Path(tmp))
            before = deepcopy((ir, saved)); observed = trial.compare_sample(ir, saved)
            self.assertEqual(observed['status'], 'equal')
            self.assertEqual(observed['reference_logical_sha256'], observed['observed_logical_sha256'])
            self.assertEqual((ir, saved), before)

    def test_mismatch_is_recorded_not_replaced_by_ready(self):
        with TemporaryDirectory() as tmp:
            folder, ir, saved = reference(Path(tmp))
            saved['stages']['relations']['status'] = 'poison'
            observed = trial.compare_sample(ir, saved)
            self.assertEqual(observed['status'], 'semantic_mismatch')
            self.assertFalse(observed['checks']['relations_equal'])

    def test_disk_replay_does_not_overwrite_or_promote(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp); folder, ir, saved = reference(root)
            report = trial.run(folder, root/'output', 0)
            self.assertEqual(report['status_counts'], {'equal':1})
            self.assertTrue(report['inputs_unchanged'])
            self.assertFalse(report['earlier_stages_recomputed'])
            self.assertFalse(report['accuracy_measured'])
            row = report['records'][0]; artifact = Path(row['artifact'])
            self.assertEqual(trial.digest(artifact), row['sha256'])
            self.assertEqual(json.loads(gzip.decompress(artifact.read_bytes()))['status'], 'equal')
            with self.assertRaisesRegex(ValueError, 'no_overwrite'):
                trial.run(folder, root/'output', 0)

    def test_reference_artifact_mutation_rejected(self):
        with TemporaryDirectory() as tmp:
            folder, ir, saved = reference(Path(tmp))
            (folder/'sample.json.gz').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'reference_input_changed'):
                trial.inputs(folder)

    def test_missing_frozen_record_rejected(self):
        with TemporaryDirectory() as tmp:
            folder, ir, saved = reference(Path(tmp))
            report = trial.load(folder/'report.json'); report['records'] = []
            write_json(folder/'report.json', report)
            with self.assertRaisesRegex(ValueError, 'coverage_mismatch'):
                trial.inputs(folder)

    def test_holdout_policy_is_never_promoted(self):
        with TemporaryDirectory() as tmp:
            folder, ir, saved = reference(Path(tmp))
            plan = trial.load(folder/'frozen-plan.json')
            plan['packages'][0]['source']['manifest_entry']['split'] = 'holdout'
            write_json(folder/'frozen-plan.json', plan)
            contract = trial.load(folder/'run-contract.json')
            contract['frozen_plan_sha256'] = trial.digest(folder/'frozen-plan.json')
            write_json(folder/'run-contract.json', contract)
            with self.assertRaisesRegex(ValueError, 'protected_or_unauthorized'):
                trial.inputs(folder)

    def test_benchmark_uses_both_orders_and_exact_results(self):
        with TemporaryDirectory() as tmp:
            folder, ir, saved = reference(Path(tmp))
            result = trial.benchmark(ir, saved['stages']['lattice'])
            self.assertEqual(result['rounds'][0]['order'], ['uncached', 'cached'])
            self.assertEqual(result['rounds'][1]['order'], ['cached', 'uncached'])
            self.assertTrue(result['all_results_equal'])
            self.assertFalse(result['musical_accuracy_measured'])

    def test_invalid_benchmark_arguments(self):
        for value in (True, 0, -1):
            with self.assertRaisesRegex(ValueError, 'invalid_benchmark_repeats'):
                trial.benchmark({}, {}, value)

    def test_consumed_artifact_bytes_checked(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp)/'value.json'; write_json(path, {'x':1})
            expected = trial.digest(path); write_json(path, {'x':2})
            with self.assertRaisesRegex(ValueError, 'consumed_input_hash_mismatch'):
                trial.load_hashed_json(path, expected)

    def test_mutating_saved_stage_is_rejected(self):
        with TemporaryDirectory() as tmp:
            folder, ir, saved = reference(Path(tmp))
            original_run = trial.relations.run
            def mutate(lattice, source, **kwargs):
                value = original_run(lattice, source, **kwargs)
                lattice['poison'] = True
                return value
            with patch.object(trial.relations, 'run', side_effect=mutate):
                with self.assertRaisesRegex(ValueError, 'mutated_frozen_stages'):
                    trial.compare_sample(ir, saved)

    def test_mutating_benchmark_lattice_is_rejected(self):
        with TemporaryDirectory() as tmp:
            folder, ir, saved = reference(Path(tmp))
            original_run = trial.relations.run
            def mutate(lattice, source, **kwargs):
                value = original_run(lattice, source, **kwargs)
                lattice['poison'] = True
                return value
            with patch.object(trial.relations, 'run', side_effect=mutate):
                with self.assertRaisesRegex(ValueError, 'benchmark_mutated_input'):
                    trial.benchmark(ir, saved['stages']['lattice'])


if __name__ == '__main__':
    unittest.main()
