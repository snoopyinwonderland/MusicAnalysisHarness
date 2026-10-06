import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from musicanote_harness.harmony_execution import atomic_json, child
from musicanote_harness.harmony_owned_score_worker import atomic_worker, bind, load_worker


def fake_module():
    original_writes = []
    scope = dict(write=lambda path, value: original_writes.append(value))
    exec('def worker(source, output):\n    write(output, {"status": "complete", "source": source})', scope)
    phase_worker = scope['worker']
    outer = dict(phases=SimpleNamespace(worker=phase_worker), write=scope['write'])
    exec('def worker(source, output):\n'
         '    phases.worker(source, output)\n'
         '    write(output, {"status": "complete", "source": source, "lookup": True})', outer)
    return SimpleNamespace(phases=outer['phases'], worker=outer['worker']), original_writes


class OwnedWorkerTests(unittest.TestCase):
    def test_original_bytecode_and_globals_unchanged(self):
        module, writes = fake_module()
        previous = dict(module.worker.__globals__)
        wrapped = atomic_worker(module)
        self.assertIs(wrapped.__code__, module.worker.__code__)
        with TemporaryDirectory() as directory:
            path = Path(directory)/'worker.json'
            wrapped('fixture.xml', path)
            self.assertTrue(json.loads(path.read_text())['lookup'])
        self.assertEqual(module.worker.__globals__, previous)
        self.assertEqual(writes, [])
        module.worker('fixture.xml', 'original-target')
        self.assertEqual(len(writes), 2)

    def test_interrupted_final_write_preserves_complete_phase_result(self):
        module, writes = fake_module()
        wrapped = atomic_worker(module)
        with TemporaryDirectory() as directory:
            path = Path(directory)/'worker.json'
            import os
            replace = os.replace
            calls = []
            def fail_second(source, target):
                calls.append(target)
                if len(calls) == 2:
                    raise PermissionError('interrupted final publication')
                return replace(source, target)
            with patch('musicanote_harness.harmony_execution.os.replace', side_effect=fail_second):
                with self.assertRaises(PermissionError):
                    wrapped('fixture.xml', path)
            self.assertEqual(json.loads(path.read_text()), dict(status='complete', source='fixture.xml'))
            self.assertTrue(json.loads(path.with_name('worker.json.pending').read_text())['lookup'])
        self.assertEqual(writes, [])

    def test_missing_dependency_and_wrong_module_refused(self):
        with self.assertRaises(ValueError):
            bind(lambda: None, {'absent': atomic_json})
        with self.assertRaises(ValueError):
            load_worker('music21')

    def test_bootstrap_bytecode_and_original_importlib_unchanged(self):
        original = child.__globals__['importlib']
        wrapped = bind(child, {'importlib': SimpleNamespace(import_module=lambda name: None)})
        self.assertIs(wrapped.__code__, child.__code__)
        self.assertIs(child.__globals__['importlib'], original)

