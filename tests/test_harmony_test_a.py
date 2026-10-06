import unittest
from fractions import Fraction as F
from musicanote_harness.harmony_test_a import validated_spans, compare, boundary_matches, aggregate, merge_spans


def s(a='0', b='1', root=0, pcs=None, bass=0):
    return dict(start=a, end=b, root_pc=root, pcs=pcs or [0, 4, 7], bass_pc=bass)


class ScoringTests(unittest.TestCase):
    def test_overlap_rejected(self):
        with self.assertRaisesRegex(ValueError, 'overlapping'):
            validated_spans([s(), s()])

    def test_unsorted_rejected(self):
        with self.assertRaises(ValueError):
            validated_spans([s('1', '2'), s()])

    def test_null_bass_not_root(self):
        r = compare(validated_spans([s()]), validated_spans([s(bass=None)]))
        self.assertEqual(r['root'], 1)
        self.assertEqual(r['bass'], 0)

    def test_one_to_one(self):
        self.assertEqual(boundary_matches([F(1)], [F(3, 4), F(5, 4)]), (1, 2, 1))

    def test_missing_song_boundaries_retained(self):
        r = compare(validated_spans([s(), s('1', '2', 7, [7, 11, 2], 7)]), [])
        self.assertEqual(r['gold'], 2)
        self.assertEqual(r['boundary_gold'], 1)
        self.assertEqual(aggregate([r])['boundary_recall'], 0)

    def test_self_match(self):
        g = validated_spans([s(), s('1', '2', 7, [7, 11, 2], 7)])
        r = aggregate([compare(g, g)])
        self.assertTrue(all(r[k] == 1 for k in ('root', 'triad', 'pcs', 'bass', 'covered', 'boundary_f1')))

    def test_fraction_preserved(self):
        self.assertEqual(validated_spans([s('1/3', '2/3')])[0]['start'], F(1, 3))

    def test_bad_pc_and_empty_extent(self):
        for row in (s(root=True), s(root=12), s(bass=12), s('1', '1'), s('-1', '0')):
            with self.assertRaises(ValueError):
                validated_spans([row])

    def test_complete_domain(self):
        with self.assertRaises(ValueError):
            validated_spans([s('0', '5')], F(4))

    def test_merge_only_same_bass_and_chord(self):
        merged = merge_spans([s(), s('1', '2'), s('2', '3', bass=None)])
        self.assertEqual([(r['start'], r['end']) for r in merged], [('0', '2'), ('2', '3')])

    def test_no_cross_gap_double_count(self):
        r = compare(validated_spans([s('0', '3')]), validated_spans([s('0', '1'), s('2', '3')]))
        self.assertEqual(r['covered'], 2)
        self.assertEqual(r['gold'], 3)


if __name__ == '__main__':
    unittest.main()
