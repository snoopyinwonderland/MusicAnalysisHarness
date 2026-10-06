from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from musicanote_harness import harmony_exact_beat_dev_audit_v2 as a


class CapAudit(unittest.TestCase):
    def row(self, cap):
        return {'arms': {a.t.ARM: {'result': {'resource_guard': {'raw_segment_cap': cap}}}}}

    def result(self, cap): return {'resource_guard': {'raw_segment_cap': cap}}

    def test_default_matches_original(self):
        self.assertEqual(a.require_original_cap(SimpleNamespace(max_segments=6), self.row(6), self.result(6)), 6)

    def test_original_nondefault_caps_not_uniform_six(self):
        for cap in (18, 24):
            self.assertEqual(a.require_original_cap(SimpleNamespace(max_segments=cap), self.row(cap), self.result(cap)), cap)

    def test_changed_current_or_historical_rejected(self):
        for historical, current in ((18, 6), (6, 18), (18, 24)):
            with self.assertRaisesRegex(ValueError, 'original_cap_changed'):
                a.require_original_cap(SimpleNamespace(max_segments=18), self.row(historical), self.result(current))

    def test_invalid_type_or_nonpositive_rejected(self):
        for cap in (True, 0, -1, 6.0, '6'):
            with self.assertRaisesRegex(ValueError, 'original_cap_changed'):
                a.require_original_cap(SimpleNamespace(max_segments=cap), self.row(cap), self.result(cap))

    def test_no_overwrite_before_any_read(self):
        with TemporaryDirectory() as d:
            a.t.io.write(Path(d)/'post-seal-audit-v2.json', {'passed': False})
            with self.assertRaisesRegex(ValueError, 'output_exists_no_overwrite'): a.run(d)


if __name__ == '__main__': unittest.main()
