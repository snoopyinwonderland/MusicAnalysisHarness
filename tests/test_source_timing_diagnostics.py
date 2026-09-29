import unittest
from musicanote_harness.source_timing_diagnostics import grid_disagreements

class SourceTimingDiagnosticsTests(unittest.TestCase):
    def test_exact_fraction_difference_is_not_rounded_away(self):
        rows={('P1',1):{'label':'X1','start':'38','duration':'959/480'},
              ('P2',1):{'label':'X1','start':'38','duration':'2'}}
        result=grid_disagreements(rows)
        self.assertEqual(result[0]['duration_spread_quarters'],'1/480')
        self.assertEqual(rows['P1',1]['duration'],'959/480')

    def test_identical_pickup_is_not_a_conflict(self):
        rows={(p,1):{'label':'0','start':'0','duration':'1/2'} for p in ('P1','P2')}
        self.assertEqual(grid_disagreements(rows),[])

    def test_missing_part_measure_is_reported(self):
        rows={(p,1):{'label':'1','start':'0','duration':'4'} for p in ('P1','P2')}
        rows['P1',2]={'label':'2','start':'4','duration':'4'}
        self.assertEqual(grid_disagreements(rows)[0]['physical_measure'],2)
