import hashlib
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from musicanote_harness import harmony_execution as execution
from musicanote_harness import harmony_windows_import as windows

FIXTURE = Path(__file__).parent/'_harmony_execution_worker_fixture.py'


def platform_fn():
    calls = []
    scope = dict(platform=SimpleNamespace(system=lambda: calls.append('original') or 'Windows'), os=os)
    exec('def getPlatform():\n'
         '    if platform.system() == "Windows": return "win"\n'
         '    elif platform.system() == "Darwin": return "darwin"\n'
         '    elif os.name == "posix": return "nix"\n'
         '    else: return os.name\n', scope)
    return scope['getPlatform'], calls


class EventTests(unittest.TestCase):
    def events(self, rows, tail=b''):
        with TemporaryDirectory() as directory:
            path = Path(directory)/'events.jsonl'
            raw = b''.join(json.dumps(row).encode()+b'\n' for row in rows)+tail
            path.write_bytes(raw)
            result = execution.read_events(path, 'test')
            self.assertEqual(path.read_bytes(), raw)
            return result

    def row(self, n=0):
        return dict(nonce='test', sequence=n, clock_ns=n+10, pid=5,
                    event='bootstrap_enter' if n == 0 else 'worker_returned')

    def test_complete_and_torn_last_event_preserved(self):
        rows, issues = self.events([self.row(), self.row(1)], b'{"torn":')
        self.assertEqual(len(rows), 2)
        self.assertEqual(issues, ['incomplete_last_event_preserved'])

    def test_foreign_and_out_of_order_rejected(self):
        foreign = self.row(1); foreign['nonce'] = 'other'
        rows, issues = self.events([self.row(), foreign, self.row(2)])
        self.assertEqual(len(rows), 1)
        self.assertEqual(len(issues), 2)

    def test_clock_and_pid_change_rejected(self):
        for key, value in (('clock_ns', 0), ('clock_ns', '11'), ('pid', 6)):
            bad = self.row(1); bad[key] = value
            rows, issues = self.events([self.row(), bad])
            self.assertEqual(len(rows), 1)
            self.assertIn('invalid_clock_or_identity', issues[0])

    def test_non_object_invalid_json_and_missing_file(self):
        rows, issues = self.events([[], self.row()], b'bad\n')
        self.assertEqual(len(rows), 1)
        self.assertEqual(len(issues), 2)
        with TemporaryDirectory() as directory:
            self.assertEqual(execution.read_events(Path(directory)/'absent', 'test'),
                             ([], ['no_bootstrap_events']))

    def test_missing_or_negative_interval_is_unknown(self):
        rows = [dict(event='bootstrap_enter', clock_ns=5),
                dict(event='platform_query_begin', clock_ns=10),
                dict(event='platform_query_returned', clock_ns=20)]
        timing = execution.event_times(rows, 0, 30)
        self.assertEqual(timing['platform_query_seconds'], 1e-8)
        self.assertIsNone(timing['worker_call_seconds'])
        self.assertIsNone(execution.event_times(rows, 30, 0)['process_wall_seconds'])

    def test_atomic_failure_preserves_previous_file(self):
        with TemporaryDirectory() as directory:
            path = Path(directory)/'summary.json'
            path.write_bytes(b'old')
            with patch.object(execution.os, 'replace', side_effect=PermissionError('fixture')):
                with self.assertRaises(PermissionError):
                    execution.atomic_json(path, dict(new=True))
            self.assertEqual(path.read_bytes(), b'old')
            self.assertTrue(path.with_name('summary.json.pending').exists())


class BindingTests(unittest.TestCase):
    def test_bytecode_and_original_global_platform_unchanged(self):
        original, calls = platform_fn()
        before = original.__globals__['platform']
        bound = windows.bind_windows_label(original)
        self.assertEqual(bound(), 'win')
        self.assertIs(bound.__code__, original.__code__)
        self.assertEqual(calls, [])
        self.assertIs(original.__globals__['platform'], before)
        self.assertEqual(original(), 'win')
        self.assertEqual(calls, ['original'])

    def test_unrecognized_function_refused(self):
        with self.assertRaisesRegex(ValueError, 'unrecognized'):
            windows.bind_windows_label(lambda: 'win')

    def test_pinned_loader_and_library_drift(self):
        with TemporaryDirectory() as directory:
            path = Path(directory)/'misc.py'
            path.write_bytes(b'fixture installed file')
            for expected, applied in ((hashlib.sha256(path.read_bytes()).hexdigest(), True), ('drift', False)):
                original, calls = platform_fn()
                module = SimpleNamespace(__file__=str(path), getPlatform=original)
                receipt = dict(applied=False)
                delegate = SimpleNamespace(exec_module=lambda module: None)
                with patch.object(windows, 'MISC_SHA', expected):
                    windows.MiscLoader(delegate, receipt).exec_module(module)
                self.assertEqual(receipt['applied'], applied)
                self.assertIs(module.getPlatform.__code__, original.__code__)
                self.assertEqual(module.getPlatform(), 'win')
                self.assertEqual(calls, [] if applied else ['original'])
                self.assertEqual(path.read_bytes(), b'fixture installed file')

    def test_disabled_non_windows_fresh_import_and_cleanup(self):
        before = list(sys.meta_path)
        with windows.isolated_windows_label(False) as receipt:
            self.assertFalse(receipt['applied'])
        with patch.object(sys, 'platform', 'darwin'):
            with windows.isolated_windows_label(True) as receipt:
                self.assertIn('not_native_windows', receipt['reason'])
        with patch.object(sys, 'platform', 'win32'), patch.object(os, 'name', 'nt'):
            with patch.dict(sys.modules, {windows.TARGET: SimpleNamespace()}):
                with self.assertRaisesRegex(ValueError, 'fresh_music21'):
                    with windows.isolated_windows_label(True):
                        pass
            with self.assertRaisesRegex(RuntimeError, 'fixture'):
                with windows.isolated_windows_label(True):
                    self.assertIsInstance(sys.meta_path[0], windows.MiscFinder)
                    raise RuntimeError('fixture')
        self.assertEqual(sys.meta_path, before)


class OwnedProcessTests(unittest.TestCase):
    def run_fixture(self, mode, *, seconds=5):
        with TemporaryDirectory() as directory:
            output = Path(directory)/'run'
            argv = [sys.executable, '-B', FIXTURE, '--output', output, '--nonce', 'owned-test', '--mode', mode]
            result = execution.run_owned(argv, output, seconds=seconds, nonce='owned-test')
            raw = (output/'worker.json').read_bytes()
            self.assertEqual(result['raw_result_sha256'], hashlib.sha256(raw).hexdigest())
            self.assertEqual(json.loads((output/'execution.json').read_text()), result)
            return result, raw

    def test_complete_result_and_return_are_eligible(self):
        result, raw = self.run_fixture('complete')
        self.assertTrue(result['prediction_eligible'])
        self.assertEqual(result['status'], 'complete')
        self.assertIsNotNone(result['timings']['worker_call_seconds'])
        self.assertEqual(json.loads(raw)['notes_preserved'], [60, 62, 64])

    def test_late_exit_never_eligible_and_complete_raw_preserved(self):
        result, raw = self.run_fixture('complete_wait')
        self.assertEqual(result['status'], 'whole_process_timeout')
        self.assertFalse(result['prediction_eligible'])
        self.assertEqual(json.loads(raw)['status'], 'complete')
        self.assertTrue(result['cleanup']['stopped'])
        self.assertTrue(result['cleanup']['tree_cleanup_confirmed'], result['cleanup'])

    def test_partial_timeout_never_promoted(self):
        result, raw = self.run_fixture('partial_wait')
        self.assertEqual(result['worker_status'], 'partial')
        self.assertFalse(result['prediction_eligible'])
        self.assertEqual(json.loads(raw)['status'], 'partial')

    def test_malformed_raw_and_foreign_event_are_not_eligible(self):
        for mode in ('malformed', 'foreign'):
            result, _ = self.run_fixture(mode)
            self.assertFalse(result['prediction_eligible'])
            if mode == 'malformed':
                self.assertEqual(result['raw_result_parse_error'], 'JSONDecodeError')
            else:
                self.assertEqual(result['status'], 'execution_protocol_error')

    def test_launch_error_has_separate_summary(self):
        with TemporaryDirectory() as directory:
            output = Path(directory)/'run'
            result = execution.run_owned([Path(directory)/'missing.exe'], output, seconds=1)
            self.assertEqual(result['status'], 'process_launch_error')
            self.assertFalse(result['prediction_eligible'])
            self.assertTrue((output/'execution.json').exists())

    def test_deadline_and_output_reuse_refused(self):
        with TemporaryDirectory() as directory:
            output = Path(directory)/'run'
            with self.assertRaisesRegex(ValueError, 'nonpositive'):
                execution.run_owned([], output, seconds=0)
            output.mkdir()
            with self.assertRaises(FileExistsError):
                execution.run_owned([], output, seconds=1)


if __name__ == '__main__':
    unittest.main()
