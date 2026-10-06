import unittest
from copy import deepcopy

from test_harmony_augmented_candidates import fixture
from test_harmony_open_candidates import score
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_candidate_catalog import propose, resolve
from musicanote_harness.harmony_catalog_resolution_trial import label
from musicanote_harness.harmony_continuous_survey import plan, analyze
from musicanote_harness.harmony_segment_contrast import build as contrast
from musicanote_harness.harmony_progression_context import build as progression


SHAPES = (('It', ()), ('Ger', ('E-4',)), ('Fr', ('D4',)), ('Ger43', ('D#4',)))


def rootless(catalog, family):
    return next(c for c in catalog['candidates'] if c['provider'] == 'augmented'
                and c['tonal_coordinate'] == ['C', 0]
                and resolve(catalog, c['origin_pointer'])['family'] == family)


def pipeline_fixture(extra):
    pitches = ('A-3', 'C4', 'F#4') + tuple(extra)
    return score([(p, 0, 3, 'held' + str(i)) for i, p in enumerate(pitches)] +
                 [('C5', 0, 1, 'lead'), ('B4', 1, 2, 'lead'), ('C5', 2, 3, 'lead')])


class RootlessLabelTests(unittest.TestCase):
    def test_all_augmented_sixth_families_preserved_without_tertian_root(self):
        for family, extra in SHAPES:
            with self.subTest(family=family):
                catalog = propose(fixture(extra), {'start': q(0), 'end': q(1)})
                c = rootless(catalog, family); before = deepcopy(catalog)
                self.assertIsNone(c['root']['spelling'])
                self.assertIsNone(c['root']['pitch_class'])
                self.assertIsNone(c['spelling_alternatives'][0]['root_spelling'])
                self.assertEqual(label(catalog, c, None), label(catalog, c, 0))
                self.assertIn(family, label(catalog, c, 0))
                self.assertEqual(catalog, before)

    def test_label_keeps_provider_origin_and_members_not_inventing_tonic_root(self):
        catalog = propose(fixture(('E-4',)), {'start': q(0), 'end': q(1)})
        c = rootless(catalog, 'Ger'); saved = deepcopy(c)
        raw = resolve(catalog, c['origin_pointer']); raw_before = deepcopy(raw)
        display = label(catalog, c, 0)
        self.assertTrue(display)
        self.assertEqual(c, saved); self.assertEqual(raw, raw_before)
        self.assertEqual(c['tonal_coordinate'], ['C', 0])
        self.assertIsNone(c['root']['spelling'])
        self.assertEqual(c['spelling_alternatives'][0]['members'], raw['members'])
        self.assertEqual(c['selected'], None)

    def test_rooted_alternate_label_unchanged(self):
        ir = score([('F#3', 0, 1, 'a'), ('A#3', 0, 1, 'b'), ('C#4', 0, 1, 'c')])
        catalog = propose(ir, {'start': q(0), 'end': q(1)})
        c = next(c for c in catalog['candidates'] if c['provider'] == 'base'
                 and any(a['root_spelling'] == ['F', 1] for a in c['spelling_alternatives'])
                 and resolve(catalog, c['origin_pointer'])['label'].endswith(':major'))
        index = next(i for i, alt in enumerate(c['spelling_alternatives']) if alt['root_spelling'] == ['F', 1])
        before = deepcopy(catalog)
        self.assertEqual(label(catalog, c, index), 'F#:major')
        self.assertEqual(label(catalog, c), resolve(catalog, c['origin_pointer'])['label'])
        self.assertEqual(catalog, before)

    def test_rootless_tonal_fallback_when_raw_label_absent(self):
        catalog = propose(fixture(), {'start': q(0), 'end': q(1)})
        c = rootless(catalog, 'It'); raw = resolve(catalog, c['origin_pointer'])
        raw.pop('label', None)
        self.assertEqual(label(catalog, c, 0), label(catalog, c, None))
        self.assertIn("['C', 0]", label(catalog, c, 0))
        self.assertIn('It', label(catalog, c, 0))
        self.assertIsNone(c['root']['spelling'])

    def test_real_contrast_and_progression_keep_rootless_candidates(self):
        for family, extra in SHAPES:
            with self.subTest(family=family):
                ir = pipeline_fixture(extra); saved = deepcopy(ir)
                sample = plan(ir, {'start': q(0), 'end': q(3)})['samples'][0]
                raw = analyze(ir, sample)
                self.assertEqual(raw['status'], 'evaluated')
                source = rootless(raw['catalog'], family)
                segment = contrast(ir, raw)
                self.assertEqual(segment['status'], 'ready')
                normalized = next(r for r in segment['hold_readings'] if r['candidate_ref'] == source['candidate_id'])
                self.assertEqual(normalized['members'], source['spelling_alternatives'][0]['members'])
                self.assertEqual(normalized['display_label'], label(raw['catalog'], source, 0))
                lattice = progression(ir, segment)
                self.assertEqual(lattice['status'], 'ready')
                whole = next(e for e in lattice['edges'] if e['span'] == {'start': q(0), 'end': q(3)})
                kept = [r for r in whole['readings'] if r['provider'] == 'augmented'
                        and r['members'] == source['spelling_alternatives'][0]['members']]
                self.assertTrue(kept)
                self.assertTrue(all(r['root_spelling'] is None for r in kept))
                self.assertEqual(ir, saved)
                self.assertIsNone(lattice['selected'])
                self.assertFalse(lattice['ranking_performed'])


if __name__ == '__main__': unittest.main()
