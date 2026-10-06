import faulthandler
from contextlib import redirect_stderr
import io
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from musicanote_harness.harmony_execution import child, read_events
from musicanote_harness.harmony_stack_diagnostic import (
    bind_bootstrap, diagnostic_facade, workload, run)


def fake_handler():
    calls = []
    return SimpleNamespace(
        enable=lambda: calls.append(('enable',)),
        dump_traceback_later=lambda *args, **kwargs: calls.append(('timer', args, kwargs)),
        cancel_dump_traceback_later=lambda: calls.append(('cancel',))), calls


class StackDiagnosticTests(unittest.TestCase):
    def test_passive_keeps_fatal_handler_without_watchdog(self):
        handler, calls = fake_handler()
        facade = diagnostic_facade(False, handler)
        facade.enable()
        facade.dump_traceback_later(5, repeat=True)
        facade.cancel_dump_traceback_later()
        self.assertEqual(calls, [('enable',)])

    def test_opt_in_preserves_original_timer_arguments(self):
        handler, calls = fake_handler()
        facade = diagnostic_facade(True, handler)
        facade.enable()
        facade.dump_traceback_later(5, repeat=True)
        facade.cancel_dump_traceback_later()
        self.assertEqual(calls, [('enable',), ('timer', (5,), {'repeat': True}), ('cancel',)])

    def test_non_boolean_policy_rejected(self):
        for value in (None, 0, 'off'):
            with self.assertRaises(ValueError):
                diagnostic_facade(value)

    def test_private_binding_preserves_original_globals_and_bytecode(self):
        before = dict(child.__globals__)
        timer = faulthandler.dump_traceback_later
        wrapped = bind_bootstrap()
        self.assertIs(wrapped.__code__, child.__code__)
        self.assertEqual(child.__globals__, before)
        self.assertIs(faulthandler.dump_traceback_later, timer)
        self.assertIsNot(wrapped.__globals__['faulthandler'], faulthandler)

    def test_original_bootstrap_events_and_default_off(self):
        handler, calls = fake_handler()
        with TemporaryDirectory() as directory:
            path = Path(directory)
            bind_bootstrap(handler=handler)(path, 'fixture', 'noop')
            rows, issues = read_events(path/'events.jsonl', 'fixture')
        self.assertEqual(issues, [])
        self.assertEqual([row['event'] for row in rows], ['bootstrap_enter', 'probe_returned'])
        self.assertEqual(calls, [('enable',)])

    def test_timer_cancelled_after_original_bootstrap_exception(self):
        handler, calls = fake_handler()
        with TemporaryDirectory() as directory:
            with redirect_stderr(io.StringIO()), self.assertRaises(ValueError):
                bind_bootstrap(True, handler=handler)(Path(directory), 'fixture', 'wrong')
            rows, issues = read_events(Path(directory)/'events.jsonl', 'fixture')
        self.assertEqual(issues, [])
        self.assertEqual(rows[-1]['event'], 'bootstrap_error')
        self.assertEqual(calls[-1], ('cancel',))

    def test_cpu_and_sleep_verify_the_same_kernel(self):
        cpu, wait = workload('cpu', .01), workload('sleep', .01)
        self.assertGreater(cpu['iterations'], 0)
        self.assertEqual(cpu['kernel_sha256'], wait['kernel_sha256'])
        self.assertEqual(cpu['kernel_result'], wait['kernel_result'])
        self.assertTrue(cpu['kernel_verified'])

    def test_invalid_workload_and_score_action_rejected(self):
        with self.assertRaises(ValueError):
            workload('cpu', 0)
        with self.assertRaises(ValueError):
            workload('score')
        with self.assertRaises(ValueError):
            run(Path('unused'), 'fixture', 'wrong', Path('unused'))
