import unittest
from musicanote_harness.tonal_foundations import spelled_seventh_shapes


class SeventhTest(unittest.TestCase):
    def test_seven_qualities(self):
        for e,g,b,quality in [(0,0,0,'major_seventh'),(-1,0,-1,'minor_seventh'),
                             (0,0,-1,'major_minor_seventh'),(-1,-1,-2,'diminished_seventh'),
                             (-1,-1,-1,'half_diminished_seventh'),(0,1,0,'augmented_major_seventh'),
                             (-1,0,0,'minor_major_seventh')]:
            r=spelled_seventh_shapes([('C',0,4),('E',e,4),('G',g,4),('B',b,4)])[0]
            self.assertEqual(r['quality'],quality)
            self.assertEqual(r['independent_harmony'],'unassessed')

    def test_inversions_and_doubling(self):
        upper=[('C',0,4),('E',0,4),('G',0,4),('B',-1,4)]
        for i,(s,a,_) in enumerate(upper):
            r=spelled_seventh_shapes(upper+[(s,a,2),('C',0,6)])[0]
            self.assertEqual(r['inversion'],i)
            self.assertEqual(r['figured_bass'],('7','65','43','42')[i])
            self.assertEqual(r['harmonic_function'],'unassessed')

    def test_spelling_not_pitch_class_only(self):
        # Bbb -> A preserves sound but changes the spelled root/inversion.
        original=spelled_seventh_shapes([('C',0,4),('E',-1,4),('G',-1,4),('B',-2,4)])[0]
        respelled=spelled_seventh_shapes([('C',0,4),('E',-1,4),('G',-1,4),('A',0,4)])[0]
        self.assertEqual((original['root_step'],original['inversion']),('C',0))
        self.assertEqual((respelled['root_step'],respelled['inversion']),('A',1))

    def test_missing_and_extra_abstain(self):
        pitches=[('C',0,4),('E',0,4),('G',0,4),('B',0,4)]
        self.assertEqual(spelled_seventh_shapes(pitches[:3]),[])
        self.assertEqual(spelled_seventh_shapes(pitches+[('D',0,5)]),[])

    def test_transposition(self):
        r=spelled_seventh_shapes([('F',1,3),('A',1,3),('C',1,4),('E',0,4)])[0]
        self.assertEqual((r['root_step'],r['root_alter'],r['quality']),('F',1,'major_minor_seventh'))

    def test_invalid_pitch(self):
        with self.assertRaises(ValueError):spelled_seventh_shapes([('C',0.5,4)])
        with self.assertRaises(ValueError):spelled_seventh_shapes([('C',0,True)])


if __name__ == '__main__':
    unittest.main()
