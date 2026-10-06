from copy import deepcopy
from dataclasses import replace
from fractions import Fraction as F
import unittest

from musicanote_harness import harmony_partial_support as s
from musicanote_harness import harmony_terminal_context as previous
from test_harmony_bounded_recovery import fixture
from test_harmony_exact_frontier import problem
from test_harmony_functional_scoring import C,G7,F64
from test_harmony_terminal_context import terminal_example


class PartialSupportTests(unittest.TestCase):
    def value(self,graph,ev,sig=C,**args):
        return s.observe(graph,ev,graph.points[0],graph.points[-1],sig,**args)

    def test_seventh_once_not_supported_in_later_two_beat_window(self):
        graph,ev=problem(fixture([('G2',0,4,'b'),('B3',0,4,'a'),('D4',0,4,'c'),('F4',0,1,'d')]))
        values,r=self.value(graph,ev,G7)
        self.assertEqual(values[s.FEATURES[0]],F(1,4))
        self.assertFalse(r['confirmed_boundary']);self.assertFalse(r['confirmed_nct'])

    def test_never_heard_seventh_not_charged_again(self):
        graph,ev=problem(fixture([('G2',0,4,'b'),('B3',0,4,'a'),('D4',0,4,'c')]))
        values,r=self.value(graph,ev,G7)
        self.assertEqual(values[s.FEATURES[0]],0)
        self.assertIn(('F',0),r['never_heard_members_not_charged_again'])

    def test_distributed_triad_need_not_sound_simultaneously(self):
        graph,ev=problem(fixture([('C3',0,F(1,2),'v'),('E3',F(1,2),1,'v'),('G3',1,2,'v'),
            ('C3',2,F(5,2),'v'),('E3',F(5,2),3,'v'),('G3',3,4,'v')]))
        values,r=self.value(graph,ev)
        self.assertEqual(values[s.FEATURES[0]],0);self.assertFalse(r['union_is_simultaneous'])

    def test_original_sounding_hold_is_not_missing_reattack(self):
        graph,ev=problem(fixture([('C3',0,4,'b'),('E4',0,4,'lead')]))
        self.assertEqual(self.value(graph,ev)[0][s.FEATURES[0]],0)

    def test_silent_window_not_charged(self):
        graph,ev=problem(fixture([('C3',0,1,'b'),('E4',0,1,'lead')],end=4))
        values,r=self.value(graph,ev)
        self.assertEqual(values[s.FEATURES[0]],0)
        self.assertTrue(r['windows'][-1]['silence_not_charged'])

    def test_enharmonic_does_not_replace_spelled_third(self):
        graph,ev=problem(fixture([('C3',0,4,'b'),('E4',0,1,'lead'),('F-4',2,4,'lead')]))
        values,r=self.value(graph,ev)
        self.assertEqual(values[s.FEATURES[0]],F(1,2))

    def test_partial_following_members_survive_missing_bass(self):
        graph,ev=terminal_example();ev.rows=tuple(r for r in ev.rows if r['token']!=('G',0))
        values,r=self.value(graph,ev,F64)
        self.assertEqual(values[s.FEATURES[1]],0)
        self.assertEqual(values[s.FEATURES[2]],F(2,3))
        self.assertEqual(values[s.FEATURES[3]],1)
        self.assertEqual(previous.observe(graph,ev,F(0),F(1),F64)[0],dict.fromkeys(previous.FEATURES,F()))

    def test_missing_left_member_does_not_veto_other_dimensions(self):
        graph,ev=terminal_example();ev.rows=tuple(r for r in ev.rows if not(r['token']==('E',0) and r['start']==0))
        ev.links=tuple((a,b) for a,b in ev.links if a['token']!=('E',0))
        values,r=self.value(graph,ev,F64)
        self.assertEqual(values[s.FEATURES[1]],1);self.assertEqual(values[s.FEATURES[2]],1)
        self.assertEqual(values[s.FEATURES[3]],F(1,2))
        self.assertFalse(r['all_support_dimensions_required'])

    def test_polyphonic_steps_unknown_other_dimensions_known(self):
        graph,ev=terminal_example();a=next(r for r in ev.rows if r['token']==('C',0))
        other=deepcopy(a);other['id']='overlap';other['token']=('D',0);ev.rows=(*ev.rows,other)
        values,r=self.value(graph,ev,F64)
        self.assertIsNone(values[s.FEATURES[3]])
        self.assertIsNotNone(values[s.FEATURES[1]]);self.assertIsNotNone(values[s.FEATURES[2]])

    def test_source_end_unknown_not_zero(self):
        graph,ev=terminal_example()
        for r in ev.rows:r['end']=min(F(1),r['end'])
        values,r=self.value(graph,ev,F64)
        self.assertTrue(all(values[k] is None for k in s.FEATURES[1:]))

    def test_history_gate_cannot_be_bypassed(self):
        graph,ev=terminal_example();values,r=self.value(graph,ev,F64,history_gate=lambda a,b:False)
        self.assertTrue(all(v is None for v in values.values()))

    def test_unknown_left_meter_does_not_impute_terminal_scale(self):
        graph,ev=terminal_example()
        ev.source.measures=((F(),(0,0),None),(F(1),(4,4),None))
        ev.source._measure_times=(F(),F(1));ev.source._metric_cache.clear()
        self.assertTrue(all(v is None for v in self.value(graph,ev,F64)[0].values()))

    def test_fraction_compound_and_meter_change_windows(self):
        graph,ev=problem(fixture([('C3',0,8,'b'),('E4',0,1,'a')],end=8),end=8)
        ev.source.measures=((F(),(6,8),None),(F(3),(2,2),None))
        ev.source._measure_times=(F(),F(3));ev.source._metric_cache.clear()
        values,r=self.value(graph,ev)
        self.assertEqual(s.horizon(ev.source,F(),F(2)),3)
        self.assertEqual(r['windows'][0]['span']['end'],s.q(3))
        self.assertEqual(values[s.FEATURES[0]],F(5,9))

    def test_internal_run_does_not_double_count_terminal_context(self):
        graph,ev=terminal_example();graph=replace(graph,points=(F(),F(1),F(3)))
        values,r=s.observe(graph,ev,F(),F(1),F64)
        self.assertTrue(all(values[k]==0 for k in s.FEATURES[1:]))

    def test_cached_and_uncached_observations_equal_no_source_mutation(self):
        graph,ev=terminal_example();before=deepcopy(ev.rows);ctx=s.Context(graph,ev)
        a=ctx.observe(F(),F(1),F64);b=s.observe(graph,ev,F(),F(1),F64)
        self.assertEqual(a,b);self.assertEqual(a,ctx.observe(F(),F(1),F64));self.assertEqual(before,ev.rows)

    def test_invalid_span(self):
        graph,ev=terminal_example()
        with self.assertRaises(ValueError): s.observe(graph,ev,F(-1),F(1),F64)

    def test_octave_doubling_does_not_multiply_missing_member_cost(self):
        graph,ev=problem(fixture([('C3',0,4,'b'),('E4',0,1,'a')]))
        doubled,more=problem(fixture([('C3',0,4,'b'),('E4',0,1,'a'),('E5',0,1,'c')]))
        self.assertEqual(self.value(graph,ev)[0][s.FEATURES[0]],self.value(doubled,more)[0][s.FEATURES[0]])

    def test_scaled_time_and_meter_preserve_relative_window_cost(self):
        graph,ev=problem(fixture([('C3',0,4,'b'),('E4',0,1,'a')]))
        short,other=problem(fixture([('C3',0,2,'b'),('E4',0,F(1,2),'a')],end=2),end=2)
        other.source.measures=((F(),(4,8),None),);other.source._measure_times=(F(),)
        other.source._metric_cache.clear()
        self.assertEqual(self.value(graph,ev)[0][s.FEATURES[0]],self.value(short,other)[0][s.FEATURES[0]])

