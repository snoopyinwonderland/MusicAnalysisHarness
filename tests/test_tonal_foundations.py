import unittest
from musicanote_harness.tonal_foundations import major_degree
from musicanote_harness.tonal_foundations import scale_degree, spelled_interval, metric_coordinate, spelled_triad_shapes
from fractions import Fraction


class FoundationTest(unittest.TestCase):
    def test_major_pattern(self):
        for degree, step in enumerate('CDEFGAB', 1):
            result = major_degree(step, 0, 'C')
            self.assertEqual(result['degree'], degree)
            self.assertTrue(result['diatonic_to_candidate'])
            self.assertFalse(result['key_inferred'])

    def test_spelling_preserved(self):
        self.assertEqual(major_degree('C',1,'C')['degree'],1)
        self.assertEqual(major_degree('D',-1,'C')['degree'],2)
        self.assertEqual(major_degree('D',-1,'C')['alteration_from_major'],-1)

    def test_transposed_and_double_accidental(self):
        self.assertTrue(major_degree('F',1,'G')['diatonic_to_candidate'])
        self.assertTrue(major_degree('F',2,'G',1)['diatonic_to_candidate'])
        self.assertTrue(major_degree('B',-1,'E',-1)['diatonic_to_candidate'])

    def test_no_guess_for_unknown_or_microtone(self):
        for args in [(None,0,'C'),('F',0.5,'C'),('C',0,'unknown')]:
            with self.assertRaises(ValueError):
                major_degree(*args)

    def test_candidate_dependent_not_intrinsic(self):
        self.assertEqual(major_degree('C',0,'C')['degree'],1)
        self.assertEqual(major_degree('C',0,'G')['degree'],4)

    def test_minor_forms_not_new_keys(self):
        self.assertEqual(scale_degree('G',1,'A',form='natural_minor')['alteration_from_scale'],1)
        self.assertEqual(scale_degree('G',1,'A',form='harmonic_minor')['alteration_from_scale'],0)
        self.assertEqual(scale_degree('F',1,'A',form='melodic_minor_ascending')['alteration_from_scale'],0)

    def test_modal_coordinate(self):
        self.assertTrue(scale_degree('B',0,'D',form='dorian')['diatonic_to_candidate'])
        self.assertFalse(scale_degree('B',0,'D',form='natural_minor')['diatonic_to_candidate'])

    def test_interval_spelling_and_register(self):
        self.assertEqual(spelled_interval(('C',0,4),('F',1,4))['name'],'A4')
        self.assertEqual(spelled_interval(('C',0,4),('G',-1,4))['name'],'d5')
        self.assertEqual(spelled_interval(('C',0,3),('E',0,4))['name'],'M10')
        self.assertEqual(spelled_interval(('E',0,4),('C',0,4))['directed_name'],'M-3')
        self.assertEqual(spelled_interval(('C',0,4),('F',0,4))['consonance'],'context_not_assessed')

    def test_meter_relative_duration(self):
        self.assertEqual(metric_coordinate(0,Fraction(1,4),4,4)['duration_in_groups'],'1/4')
        self.assertEqual(metric_coordinate(0,Fraction(1,4),2,2)['duration_in_groups'],'1/8')
        self.assertEqual(metric_coordinate(Fraction(3,2),1,6,8)['group_index'],1)
        self.assertEqual(metric_coordinate(0,1,5,8)['status'],'grouping_required')
        self.assertEqual(metric_coordinate(1,1,5,8,[2,3])['group_index'],1)
        self.assertEqual(metric_coordinate(Fraction(1,3),1,4,4)['position_in_group'],'1/3')

    def test_four_triad_qualities(self):
        for third,fifth,quality in [(0,0,'major'),(-1,0,'minor'),(-1,-1,'diminished'),(0,1,'augmented')]:
            self.assertEqual(spelled_triad_shapes([('C',0,4),('E',third,4),('G',fifth,4)])[0]['quality'],quality)

    def test_inversion_and_doubling(self):
        for bass,inv in [(('C',0,2),0),(('E',0,2),1),(('G',0,2),2)]:
            result=spelled_triad_shapes([bass,('C',0,4),('E',0,5),('G',0,3),('C',0,6)])[0]
            self.assertEqual(result['inversion'],inv)
            self.assertEqual(result['harmonic_function'],'unassessed')

    def test_missing_extra_and_enharmonic_not_silently_reduced(self):
        self.assertEqual(spelled_triad_shapes([('C',0,4),('G',0,4)]),[])
        self.assertEqual(spelled_triad_shapes([('C',0,4),('E',0,4),('G',0,4),('B',0,4)]),[])
        self.assertEqual(spelled_triad_shapes([('C',0,4),('F',-1,4),('G',0,4)]),[])

    def test_metric_rejects_float_and_bad_group(self):
        with self.assertRaises(ValueError):metric_coordinate(0.1,1,4,4)
        with self.assertRaises(ValueError):metric_coordinate(0,1,5,8,[2,2])
        with self.assertRaises(ValueError):metric_coordinate(4,1,4,4)


if __name__ == '__main__':
    unittest.main()
