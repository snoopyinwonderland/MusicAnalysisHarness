"""Phase29 storage mocks plus one small genuine synthetic packet integration.

The old archive fixture is composed, never inherited. Only temporary synthetic
archives and mock replay packets are written. The genuine XML factory is used
only for a tiny new synthetic packet contract, never for corpus or accuracy.
"""
from copy import deepcopy
import gzip
import json
from pathlib import Path
import unittest
import tempfile
import io
from contextlib import redirect_stdout
from unittest.mock import patch

from musicanote_harness import source_progression_replay_trial as trial
import test_source_progression_proposal_trial as fixtures
from test_factor_expanded_hypotheses import ExpandedHypothesisFixture, event, span
from test_factor_musical_view import reseal


class SourceReplayStorageTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.SavedSourceProposalStorageTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.parent = self.fixture.output
        self.parent_report, _ = self.fixture.run_mock()
        self.assertTrue(self.parent_report["computation_integrity_passed"])
        self.plan = self.read(self.parent / "run-plan.json")
        self.rows = self.read(self.parent / "context-index.json")
        self.replay = self.read(self.parent / "native-replay-plan.json")
        self.output = self.root / "output/source-replay"
        self.code = self.root / "mock-new-replay-code.txt"
        self.code.write_text("storage fixture, no native authority", encoding="utf-8")
        historical = trial.parent._code_paths()
        for item in (patch.object(trial, "ROOT", self.root),
                patch.object(trial, "_code_paths", return_value=[*historical, self.code]),
                patch.object(trial, "_new_code_paths", return_value={self.code})):
            item.start()
            self.addCleanup(item.stop)

    def read(self, path):
        path = Path(path)
        with (gzip.open(path, "rt", encoding="utf-8") if path.suffix == ".gz" else path.open(encoding="utf-8")) as f:
            return json.load(f)

    def write(self, path, body):
        fixtures.fixtures.fixtures.write(Path(path), body)

    def refresh(self):
        for name, body in (("run-plan.json", self.plan), ("context-index.json", self.rows), ("native-replay-plan.json", self.replay)):
            path = self.parent / name
            self.write(path, body)
            self.parent_report["artifact_hashes"][str(path)] = trial.old._file_sha(path)
        self.write(self.parent / "report.json", self.parent_report)

    def test_direct_all_source_admission_without_any_predecessor_or_producer(self):
        forbidden = AssertionError("storage admission cannot call any producer or predecessor loader")
        with patch.object(trial.parent, "load_inputs", side_effect=forbidden), \
                patch.object(trial.parent.engine, "propose", side_effect=forbidden), \
                patch.object(trial.engine, "prepare_replay", side_effect=forbidden), \
                patch.object(trial.engine.native, "prepare_lattice", side_effect=forbidden):
            data = trial.load_inputs(self.parent)
        self.assertEqual(len(data["cases"]), 2)
        self.assertEqual([len(c["completion_controls"]) for c in data["cases"]], [2, 2])
        self.assertEqual([len(i) for _, i in data["inventories"]], [6, 7, 7, 148])
        self.assertEqual(data["report"]["denominators"], self.parent_report["denominators"])
        self.assertFalse(self.output.exists())

    def test_closed_strict_caps_and_exclusive_output_before_admission(self):
        with patch.object(trial, "load_inputs") as load:
            for key in trial._settings({}):
                for value in (True, -1, 1.5, "2", None):
                    with self.assertRaises(ValueError):
                        trial.run(self.parent, self.output, **{key: value})
            for size in (0, 65):
                with self.assertRaises(ValueError):
                    trial.run(self.parent, self.output, batch_size=size)
            with self.assertRaises(ValueError):
                trial.run(self.parent, self.output, undeclared=1)
            self.output.mkdir()
            for path in (self.output, self.root, self.root / "output/nested/new"):
                with self.assertRaises(ValueError):
                    trial.run(self.parent, path)
            load.assert_not_called()

    def test_read_all_admission_caps_no_prefix_or_output(self):
        for caps in ({"max_file_bytes": 0}, {"max_decoded_file_bytes": 0}, {"max_total_decoded_bytes": 0},
                {"max_contexts": 1}, {"max_catalogs": 5}, {"max_origins": 11}):
            with patch.object(trial.engine, "prepare_replay") as prepare:
                with self.assertRaises(ValueError):
                    trial.run(self.parent, self.output, **caps)
                prepare.assert_not_called()
                self.assertFalse(self.output.exists())

    def test_changed_source_or_unregistered_artifact_rejected(self):
        path = Path(self.rows[0]["proposal"]["artifact"])
        original = path.read_bytes()
        path.write_bytes(original + b"changed")
        with self.assertRaises(ValueError):
            trial.load_inputs(self.parent)
        path.write_bytes(original)
        (self.parent / "foreign.json").write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "inventory"):
            trial.load_inputs(self.parent)

    def test_historical_code_not_retrospectively_extended(self):
        self.plan["code"][str(self.code)] = trial.old._file_sha(self.code)
        self.refresh()
        with self.assertRaisesRegex(ValueError, "historical_phase28"):
            trial.load_inputs(self.parent)

    def test_conflicting_creation_hash_and_typed_json_rejected(self):
        path = next(iter(self.plan["code"]))
        self.plan["inputs"][path] = "0" * 64
        self.refresh()
        with self.assertRaisesRegex(ValueError, "conflicting"):
            trial.load_inputs(self.parent)
        for text in ('{"duplicate":1,"duplicate":2}', '{"finite":NaN}'):
            path = self.root / "typed-bad.json"
            path.write_text(text, encoding="utf-8")
            with self.assertRaises(ValueError):
                trial.parent.parent.parent.BoundedReader(trial._settings({})).read(path)

    def test_missing_or_reordered_replay_jobs_never_accepted(self):
        original = deepcopy(self.replay["jobs"])
        for changed in (original[:-1], list(reversed(original))):
            self.replay["jobs"] = changed
            self.refresh()
            with self.assertRaises(ValueError):
                trial.load_inputs(self.parent)

    def test_completion_links_and_full_IR_registration_are_exact(self):
        self.rows[0]["completion_controls"][0]["required_links"] = [["foreign", "sound"]]
        self.refresh()
        with self.assertRaisesRegex(ValueError, "completion_links"):
            trial.load_inputs(self.parent)
        self.rows[0]["completion_controls"][0]["required_links"] = []
        self.rows[0]["full_IR"]["ir_content_sha256"] = "0" * 64
        self.refresh()
        with self.assertRaisesRegex(ValueError, "content_binding"):
            trial.load_inputs(self.parent)

    def test_saved_unknown_summary_not_coerced_to_known_zero(self):
        self.parent_report["summary"]["total_selectors"] = None
        self.refresh()
        with self.assertRaisesRegex(ValueError, "summary"):
            trial.load_inputs(self.parent)


class ReplayPacketStorageTests(unittest.TestCase):
    """Mock admission/stream storage; packet schemas come from tiny real XML."""
    @classmethod
    def setUpClass(cls):
        factory = ExpandedHypothesisFixture()
        factory.addCleanup = cls.addClassCleanup
        factory.setUp()
        ir, scope = factory.fixture([[event('C4', 0, 2, tie_role='start'), event('C4', 2, 2, tie_role='stop')],
            [event(['C3', 'E3', 'G3'], 0, 4)]], extent=span(1, 2), signatures=[{'fifths': 0, 'mode_hint': None}])
        native, core = trial.engine.native, trial.engine
        lattice = native.build_lattice(ir, scope)
        session = native.prepare_lattice(ir, scope, lattice)
        from musicanote_harness import factor_source_evidence_panel as prior
        panel = prior.panel_prepared(prior.prepare_panel(session))
        proposal = core.proposals.propose(scope, lattice, panel, work_budget=100000000)
        cls.limits = core._limits({'batch_size': 64, 'native_query_work_budget': 1000000000, 'role_query_work_budget': 1000000000})
        handle = core.prepare_replay(ir, scope, lattice, proposal, prior_panel=panel)
        cls.binding = core.binding_prepared(handle)
        cls.plan = core.plan_saved(scope, lattice, proposal, prior_panel=panel, **cls.limits)
        cls.packets = list(core.stream_prepared(handle, [], **cls.limits))
        cls.base = {'ir': ir, 'scope': scope, 'lattice': lattice, 'panel': panel, 'proposal': proposal}
        # A real single pitch has no admissible complete chord proposal. Known
        # zero and budget-withheld empty requests must remain distinguishable.
        ir, scope = factory.fixture([[event('C3', 0, 4)]], extent=span(1, 2), signatures=[{'fifths': 0, 'mode_hint': None}])
        lattice = native.build_lattice(ir, scope)
        session = native.prepare_lattice(ir, scope, lattice)
        panel = prior.panel_prepared(prior.prepare_panel(session))
        cls.empty = {}
        for name, budget in (('ready', 100000000), ('held', 0)):
            proposal = core.proposals.propose(scope, lattice, panel, work_budget=budget)
            handle = core.prepare_replay(ir, scope, lattice, proposal, prior_panel=panel)
            cls.empty[name] = {'base': {'ir': ir, 'scope': scope, 'lattice': lattice, 'panel': panel, 'proposal': proposal},
                'binding': core.binding_prepared(handle), 'fresh': core.lattice_prepared(handle),
                'plan': core.plan_saved(scope, lattice, proposal, prior_panel=panel, **cls.limits),
                'packets': list(core.stream_prepared(handle, [], **cls.limits))}

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        (self.root / 'output').mkdir()
        self.parent = self.root / 'output/parent'
        self.parent.mkdir()
        (self.parent / 'report.json').write_text('{}', encoding='utf8')
        self.output = self.root / 'output/replay'
        self.code = self.root / 'mock-code.txt'
        self.code.write_text('mock admitted code, not original corpus', encoding='utf8')
        info = {'artifact': str(self.parent / 'report.json'), 'sha256': trial.old._file_sha(self.parent / 'report.json'),
            'record_ref': {'record_id': 'mock_registration', 'record_sha256': '0' * 64}, 'status': 'storage_mock'}
        cases = []
        for index in range(2):
            cases.append({**deepcopy(self.base), 'context_key': ['synthetic-mocked-admission', index, 'tiny-tied'],
                'source_identity_sha256': str(index) * 64, 'full_IR': deepcopy(info), 'scope_info': deepcopy(info),
                'lattice_info': deepcopy(info), 'panel_info': deepcopy(info), 'proposal_info': deepcopy(info),
                'original_source_files': [], 'parent_policy_rows': [],
                'native_counts': {'native_catalogs': 0, 'native_origins': 0, 'registered_key_hypotheses': 0},
                'completion_controls': [{'kind': kind, 'required_links': [], 'bundle': deepcopy(info), 'policy': deepcopy(info),
                    'policy_status': 'storage_mock', 'native_and_role_replay_executed': False} for kind in ('all_no_link', 'admissible_links')]})
        self.data = {'parent': self.parent, 'cases': cases, 'hashes': {str(self.code): trial.old._file_sha(self.code)},
            'inventories': [], 'report': {'denominators': {'declared_original_contexts': 322, 'declared_original_raw_lanes': 1013},
                'source_authority': 'mock_archive_admission_not_native'}, 'reader_counts': {'files_read': 0, 'decoded_bytes': 0}}
        for item in (patch.object(trial, 'ROOT', self.root), patch.object(trial, '_code_paths', return_value=[self.code])):
            item.start()
            self.addCleanup(item.stop)

    def run_mock(self, packets=None, mutate=None, **limits):
        source = deepcopy(self.packets if packets is None else packets)
        if mutate:
            mutate(source)
        with patch.object(trial, 'load_inputs', return_value=deepcopy(self.data)), \
                patch.object(trial.engine, 'plan_saved', return_value=deepcopy(self.plan)), \
                patch.object(trial.engine, 'prepare_replay', return_value=object()) as prepares, \
                patch.object(trial.engine, 'binding_prepared', return_value=deepcopy(self.binding)), \
                patch.object(trial.engine, 'lattice_prepared', return_value=deepcopy(self.base['lattice'])), \
                patch.object(trial.engine, 'stream_prepared', side_effect=lambda *a, **k: iter(deepcopy(source))) as streams:
            report = trial.run(self.parent, self.output, **{**self.limits, **limits})
        return report, prepares.call_count, streams.call_count

    def rows(self):
        return json.loads((self.output / 'context-index.json').read_text(encoding='utf8'))

    def test_genuine_tied_packets_pass_every_intrinsic_validator(self):
        case = deepcopy(self.base)
        trial._plan(self.plan, case, self.limits)
        trial._binding(self.binding, case, case['lattice'])
        header = deepcopy(self.packets[0])
        bundle, reasons = trial._header(header, case, self.binding, self.plan, {'required_links': []}, self.limits)
        counts = trial._empty_counts(self.plan['planned_selectors'], self.plan['planned_batches'])
        counts['fresh_bundle_registrations'] = 1
        refs = []
        for packet, planned in zip(self.packets[1:-1], self.plan['batches']):
            lo, hi = planned['selector_start'], planned['selector_end_exclusive']
            trial._batch(packet['comparison'], packet['explanation'], case['proposal']['selectors'][lo:hi], case, bundle, planned, self.limits)
            trial._add_batch(counts, packet['comparison'], packet['explanation'], bundle)
            refs.append({**deepcopy(planned), 'comparison_ref': trial.sealed._ref(packet['comparison']),
                'explanation_ref': trial.sealed._ref(packet['explanation'])})
        trial._job(deepcopy(self.packets[-1]['record']), case, self.binding, self.plan, bundle,
            {'required_links': []}, refs, counts, self.limits, reasons)
        self.assertGreater(counts['planned_selectors'], 0)
        self.assertEqual(counts['native_computed_paths'], counts['planned_selectors'])

    def test_all_original_jobs_stream_once_and_exact_inventory_progress(self):
        events = []
        report, preparations, streams = self.run_mock(progress_callback=events.append)
        self.assertTrue(report['computation_integrity_passed'])
        self.assertTrue(report['submitted_nonempty_requests_completed'])
        self.assertEqual((preparations, streams), (2, 4))
        self.assertEqual(report['summary']['planned_selectors'], 4 * self.plan['planned_selectors'])
        self.assertEqual(report['summary']['native_comparison_calls'], 8 * self.plan['planned_batches'])
        self.assertEqual([j['status'] for row in self.rows() for j in row['jobs']], ['computed_native_role_source_requests_not_selected'] * 4)
        actual = {str(p) for p in self.output.rglob('*') if p.is_file()}
        self.assertEqual(actual, set(report['artifact_hashes']) | {str(self.output / 'report.json')})
        self.assertEqual(events[0]['event'], 'admission_started')
        self.assertEqual(events[-1]['event'], 'report_saved')
        self.assertLessEqual(sum(Path(p).stat().st_size for p in actual), 2147483648)

    def test_reordered_extra_and_truncated_packets_never_complete(self):
        variants = [self.packets[:-1], [self.packets[1], self.packets[0], *self.packets[2:]], [*self.packets, self.packets[-1]]]
        for index, packets in enumerate(variants):
            self.output = self.root / ('output/fault-' + str(index))
            report, _, _ = self.run_mock(packets)
            self.assertFalse(report['computation_integrity_passed'])
            self.assertFalse(report['submitted_nonempty_requests_completed'])
            self.assertEqual(report['incomplete_or_unstarted_completion_requests'], 4)
            self.assertEqual(report['summary']['planned_selectors'], 4 * self.plan['planned_selectors'])
            self.assertIsNone(report['summary']['conditional_explained_note_time_selector_occurrence_sum'])

    def test_resealed_wrong_header_and_terminal_counts_rejected(self):
        variants = []
        packets = deepcopy(self.packets)
        packets[0]['plan']['planned_replay_work'] += 1
        packets[0]['plan'] = reseal(packets[0]['plan'], trial.engine.PLAN_PREFIX)
        variants.append(packets)
        packets = deepcopy(self.packets)
        packets[-1]['record']['summary']['native_comparison_calls'] += 1
        packets[-1]['record'] = reseal(packets[-1]['record'], trial.engine.PREFIX)
        variants.append(packets)
        packets = deepcopy(self.packets)
        packets[-1]['record']['reasons'] = ['forged_hold_reason']
        packets[-1]['record'] = reseal(packets[-1]['record'], trial.engine.PREFIX)
        variants.append(packets)
        for index, packets in enumerate(variants):
            self.output = self.root / ('output/resealed-' + str(index))
            report, _, _ = self.run_mock(packets)
            self.assertFalse(report['computation_integrity_passed'])
            self.assertEqual(report['saved_terminal_jobs'], 0)

    def test_promoted_or_wrong_resource_batch_rejected_before_body_save(self):
        for index, kind in enumerate(('selected', 'flag', 'resources', 'pathflag')):
            packets = deepcopy(self.packets)
            record = packets[1]['comparison']
            if kind == 'selected':
                record['selected'] = False
            elif kind == 'flag':
                record['flags'][next(iter(record['flags']))] = True
            elif kind == 'pathflag':
                record['paths'][0]['flags'][next(iter(record['paths'][0]['flags']))] = True
                record['paths'][0] = reseal(record['paths'][0], 'fmilpath_')
            else:
                record['resource_limits']['max_slots'] += 1
            packets[1]['comparison'] = reseal(record, trial.engine.native.COMPARISON_PREFIX)
            # Keep the explanation snapshot current to isolate the new guards.
            explanation = packets[1]['explanation']
            explanation['native_comparison_ref'] = trial.sealed._ref(packets[1]['comparison'])
            explanation['native_request'] = {k: deepcopy(packets[1]['comparison'][k]) for k in ('selectors', 'resource_limits', 'status', 'reasons', 'summary', 'query_plan')}
            packets[1]['explanation'] = reseal(explanation, trial.engine.roles.PREFIX)
            self.output = self.root / ('output/promoted-' + str(index))
            report, _, _ = self.run_mock(packets)
            self.assertFalse(report['computation_integrity_passed'])
            self.assertEqual(report['summary']['native_computed_paths'], 0)

    def test_binding_status_contract_reasons_and_plan_work_are_exact(self):
        for key, value in (('reasons', ['fake']), ('contract', {}), ('native_authority_issued', False)):
            record = deepcopy(self.binding)
            record[key] = value
            record = reseal(record, trial.engine.BINDING_PREFIX)
            with self.assertRaises(ValueError):
                trial._binding(record, self.base, self.base['lattice'])
        plan = deepcopy(self.plan)
        plan['planned_replay_work'] -= 1
        with self.assertRaises(ValueError):
            trial._plan(reseal(plan, trial.engine.PLAN_PREFIX), self.base, self.limits)

    def test_reserved_cap_and_record_dedup_collision_and_partial_write(self):
        self.output.mkdir()
        settings = trial._settings({'max_total_output_bytes': 100, 'manifest_reserve_bytes': 50})
        writer = trial._Writer(self.output, settings)
        with self.assertRaises(trial.OutputBudgetExceeded):
            writer._write(self.output / 'too-large', b'x' * 51, body=True)
        self.assertFalse((self.output / 'too-large').exists())
        path = self.output / 'partial'
        original_open = Path.open
        class Partial:
            def __enter__(inner):
                inner.stream = original_open(path, 'xb')
                return inner
            def __exit__(inner, *args):
                inner.stream.close()
            def write(inner, raw):
                inner.stream.write(raw[:3])
                inner.stream.flush()
                raise OSError('mock disk interruption')
        def opening(item, *args, **kwargs):
            return Partial() if item == path and args == ('xb',) else original_open(item, *args, **kwargs)
        with patch.object(Path, 'open', opening):
            with self.assertRaises(OSError):
                writer._write(path, b'1234567890', body=True)
        self.assertEqual(writer.bytes, 10)
        self.assertEqual(path.stat().st_size, 3)
        self.assertEqual(writer.partial_files[0]['physical_bytes'], 3)
        self.assertIn(str(path), writer.artifacts)
        writer2 = trial._Writer(self.output, trial._settings({}))
        info = writer2.record('plans', deepcopy(self.plan), trial.engine.PLAN_PREFIX)
        byte_count = writer2.bytes
        self.assertEqual(writer2.record('plans', deepcopy(self.plan), trial.engine.PLAN_PREFIX), info)
        self.assertEqual(writer2.bytes, byte_count)
        Path(info['artifact']).write_bytes(b'changed')
        with self.assertRaises(ValueError):
            writer2.record('plans', deepcopy(self.plan), trial.engine.PLAN_PREFIX)

    def test_predeclared_manifest_insufficiency_and_two_GiB_ceiling_before_output(self):
        with self.assertRaises(ValueError):
            trial._settings({'max_total_output_bytes': 2147483649})
        with patch.object(trial, 'load_inputs', return_value=deepcopy(self.data)), \
                patch.object(trial.engine, 'plan_saved', return_value=deepcopy(self.plan)), \
                patch.object(trial.engine, 'prepare_replay') as prepare:
            with self.assertRaises(trial.OutputBudgetExceeded):
                trial.run(self.parent, self.output, **self.limits, manifest_reserve_bytes=1)
            self.assertFalse(self.output.exists())
            prepare.assert_not_called()

    def test_output_body_cap_retains_all_uncomputed_positions_and_null_credit(self):
        # The precise small physical budget admits the manifests but no lattice.
        report, preparations, streams = self.run_mock(max_total_output_bytes=1048576, manifest_reserve_bytes=1048576)
        self.assertFalse(report['computation_integrity_passed'])
        self.assertEqual(preparations, 0)
        self.assertEqual(streams, 0)
        self.assertEqual(report['planned_completion_requests'], 4)
        self.assertEqual(report['incomplete_or_unstarted_completion_requests'], 4)
        self.assertEqual(report['summary']['planned_selectors'], 4 * self.plan['planned_selectors'])
        self.assertIsNone(report['summary']['conditional_explained_note_time_selector_occurrence_sum'])

    def test_observer_exception_does_not_mutate_packets_or_claim_accuracy(self):
        def observer(event):
            event.clear()
            raise RuntimeError('observer fault')
        report, _, _ = self.run_mock(progress_callback=observer)
        self.assertTrue(report['computation_integrity_passed'])
        self.assertTrue(report['observer_errors'])
        self.assertTrue(all(v is False for v in report['flags'].values()))
        self.assertIsNone(report['selected'])

    def test_saved_runtime_hold_terminal_preserves_incomplete_complement(self):
        # Explicit producer-fault injection: a typed whole role hold is not a
        # musical observation and must not disappear after its terminal saves.
        packets = deepcopy(self.packets)
        for packet in packets[1:-1]:
            explanation = packet['explanation']
            explanation.update(paths=[], status='whole_explanation_hold', reasons=['native_comparison_unavailable'])
            summary = explanation['summary']
            for key in summary:
                if key in ('planned_paths', 'native_computed_paths', 'planned_clause_upper_bound'):
                    continue
                summary[key] = {} if key == 'role_clause_occurrences' else summary['planned_paths'] if key == 'withheld_paths' else 0
            packet['explanation'] = reseal(explanation, trial.engine.roles.PREFIX)
        counts = trial._empty_counts(self.plan['planned_selectors'], self.plan['planned_batches'])
        counts['fresh_bundle_registrations'] = 1
        refs, reasons = [], ['unexpected_runtime_batch_hold', 'native_comparison_unavailable']
        for packet, planned in zip(packets[1:-1], self.plan['batches']):
            trial._add_batch(counts, packet['comparison'], packet['explanation'], packets[0]['bundle'])
            refs.append({**planned, 'comparison_ref': trial.sealed._ref(packet['comparison']), 'explanation_ref': trial.sealed._ref(packet['explanation'])})
        trial._finish_counts(counts, True)
        terminal = packets[-1]['record']
        terminal.update(summary=counts, batch_refs=refs, status='incomplete_native_role_source_replay', reasons=sorted(reasons))
        packets[-1]['record'] = reseal(terminal, trial.engine.PREFIX)
        report, _, _ = self.run_mock(packets)
        self.assertTrue(report['computation_integrity_passed'])
        self.assertEqual(report['saved_terminal_jobs'], 4)
        self.assertEqual(report['missing_terminal_completion_requests'], 0)
        self.assertEqual(report['incomplete_or_unstarted_completion_requests'], 4)
        self.assertEqual(report['computed_completion_requests'] + report['whole_completion_holds'] + report['incomplete_or_unstarted_completion_requests'], 4)
        self.assertIsNone(report['summary']['conditional_explained_note_time_selector_occurrence_sum'])
        self.assertFalse(report['submitted_nonempty_requests_completed'])

    def test_genuine_known_empty_and_held_empty_are_not_conflated(self):
        for name, expected_credit in (('ready', trial.q(0)), ('held', None)):
            item = self.empty[name]
            for case in self.data['cases']:
                case.update(deepcopy(item['base']))
            self.output = self.root / ('output/empty-' + name)
            with patch.object(trial, 'load_inputs', return_value=deepcopy(self.data)), \
                    patch.object(trial.engine, 'plan_saved', return_value=deepcopy(item['plan'])), \
                    patch.object(trial.engine, 'prepare_replay', return_value=object()), \
                    patch.object(trial.engine, 'binding_prepared', return_value=deepcopy(item['binding'])), \
                    patch.object(trial.engine, 'lattice_prepared', return_value=deepcopy(item['fresh'])), \
                    patch.object(trial.engine, 'stream_prepared', side_effect=lambda *a, **k: iter(deepcopy(item['packets']))):
                report = trial.run(self.parent, self.output, **self.limits)
            self.assertTrue(report['computation_integrity_passed'])
            self.assertEqual(report['planned_selector_occurrences'], 0)
            self.assertEqual(report['summary']['conditional_explained_note_time_selector_occurrence_sum'], expected_credit)
            self.assertEqual(report['known_empty_request_set'], name == 'ready')
            self.assertFalse(report['submitted_nonempty_requests_completed'])
            self.assertEqual(report['summary']['native_comparison_calls'], 0)

    def test_cli_integrity_failure_exits_nonzero_without_producer(self):
        with patch('sys.argv', ['trial', '--parent', str(self.parent), '--output', str(self.output)]), \
                patch.object(trial, 'run', return_value={'status': 'fresh_source_replay_incomplete', 'computation_integrity_passed': False}) as run, \
                redirect_stdout(io.StringIO()) as output:
            with self.assertRaises(SystemExit) as exit_code:
                trial.main()
        self.assertEqual(exit_code.exception.code, 1)
        self.assertEqual(run.call_count, 1)
        self.assertIn('"integrity": false', output.getvalue())


if __name__ == "__main__":
    unittest.main()
