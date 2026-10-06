import itertools
from copy import deepcopy
from fractions import Fraction as F
from pathlib import Path
import random
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from music21 import chord, meter, note, stream, tie
from musicanote_harness import harmony_context_input as context
from musicanote_harness.canonical import CanonicalIRBuilder, _voice_id
from musicanote_harness.harmony_whole_score_compiled import CompiledSearch, infer as compiled
from musicanote_harness.harmony_whole_score_intervals import PatternIntervals, IntervalSearch, infer
from musicanote_harness.harmony_whole_score_units import model_weights
from test_harmony_bounded_recovery import fixture
from test_harmony_whole_score_fast import prepare, C, G, C7, G7, FUNC64
from test_harmony_whole_score import problem


def score_case(*, external=False, derived=False):
    score = stream.Score(id='score')
    part = stream.Part(id='P1')
    for number in (1, 2):
        measure = stream.Measure(number=number)
        measure.insert(0, meter.TimeSignature('4/4'))
        voice = stream.Voice(id='upper')
        n = note.Note('F#4', quarterLength=2)
        n.tie = tie.Tie('start' if number == 1 else 'stop')
        voice.insert(0, n)
        voice.insert(2, chord.Chord(['A4', 'C#5'], quarterLength=1))
        voice.insert(3, note.Rest(quarterLength=1))
        if external:
            # Keep the original Voice site strongly alive while the active
            # score has no Voice. This mimics split PartStaff import context.
            measure._test_external_voice = voice
            for e in list(voice.notesAndRests):
                used = deepcopy(e) if derived else e
                measure.insert(voice.elementOffset(e), used)
        else:
            measure.insert(0, voice)
        part.insert((number - 1) * 4, measure)
    score.insert(0, part)
    return score


class ContextTests(unittest.TestCase):
    def test_voice_traversal_current_external_and_derivation(self):
        self.assertEqual(context.RUNTIME_CONTEXT_SHA, context.DEFAULT_CONTEXT_SHA)
        for external, derived in ((False, False), (True, False), (True, True)):
            score = score_case(external=external, derived=derived)
            if external:
                self.assertEqual(len(score.recurse().getElementsByClass(stream.Voice)), 0)
            lookup = context.VoiceLookup()
            values = []
            for e in score.parts[0].recurse().notesAndRests:
                expected = _voice_id(e)
                actual = lookup(e)
                self.assertEqual(actual, expected)
                values.append(actual)
            # With an attached copied score the default lookup follows the
            # top-level derivation, not necessarily each copied note origin.
            self.assertEqual(set(values), {'voice_0'} if derived else {'upper'})
            self.assertGreater(lookup.tree_hits, 0)
        origin_voice = stream.Voice(id='origin')
        origin = note.Note('C4'); origin_voice.insert(0, origin)
        copied = deepcopy(origin)  # unattached object: origin chain is used
        self.assertEqual(context.VoiceLookup()(copied), _voice_id(copied))
        self.assertEqual(_voice_id(copied), 'origin')

    def test_entire_legacy_ir_ties_rests_source_unchanged(self):
        with TemporaryDirectory() as d:
            source = Path(d) / 'input.xml'
            source.write_bytes(b'fixture source reference')
            for external in (False, True):
                old_score, new_score = score_case(external=external), score_case(external=external)
                expected = CanonicalIRBuilder().build(old_score, source)
                builder = context.ContextBuilder()
                actual = builder.build(new_score, source)
                self.assertEqual(actual, expected)
                self.assertEqual(source.read_bytes(), b'fixture source reference')
                self.assertEqual(builder.lookup_receipt['fallbacks'], 0)
                self.assertTrue(any(len(e['segment_ids']) == 2 for e in actual['sounding_events']))

    def test_runtime_override_and_new_build_do_not_reuse_stale_trees(self):
        score = score_case()
        n = next(iter(score.parts[0].recurse().notes))
        with patch.object(context, 'RUNTIME_CONTEXT_SHA', 'different-version'):
            lookup = context.VoiceLookup()
            self.assertEqual(lookup(n), _voice_id(n))
            self.assertEqual(lookup.fallbacks, 1)
            self.assertEqual(lookup.tree_builds, 0)

        class SpecialNote(note.Note):
            def getContextByClass(self, className, **kwargs):
                return stream.Voice(id='custom') if className is stream.Voice else super().getContextByClass(className, **kwargs)
        custom = SpecialNote('C4')
        lookup = context.VoiceLookup()
        self.assertEqual(lookup(custom), 'custom')
        self.assertEqual(lookup.fallbacks, 1)
        voice = score.parts[0].measure(1).voices[0]
        voice.id = 'changed'
        self.assertEqual(context.VoiceLookup()(n), _voice_id(n))


class IntervalTests(unittest.TestCase):
    def test_overlap_randomized_duplicates_original_order_and_fallback(self):
        rng = random.Random(102)
        points = tuple(F(i, 3) for i in range(40))
        rows = [(SimpleNamespace(start=points[rng.randrange(20)],
                                end=points[rng.randrange(20, 40)]), i) for i in range(90)]
        rows.extend((rows[7], rows[2]))
        index = PatternIntervals(rows, points)
        for a, b in itertools.product(points, repeat=2):
            self.assertEqual(index.query(a, b), tuple(row for row in rows if row[0].start < b and a < row[0].end))
        for a, b in ((F(1, 7), F(8, 7)), (F(-2), F(20)), (F(13), F(13))):
            self.assertEqual(index.query(a, b), tuple(row for row in rows if row[0].start < b and a < row[0].end))
        sparse = PatternIntervals(rows, (F(), F(20)))
        self.assertFalse(sparse.indexed)
        self.assertEqual(sparse.query(F(), F(20)), tuple(rows))
        self.assertEqual(PatternIntervals([], points).query(F(), F(1)), ())

    def test_boundary_long_overlapping_silent_and_zero_length(self):
        rows = [(SimpleNamespace(start=F(a), end=F(b)), i)
                for i, (a, b) in enumerate(((2, 3), (0, 4), (1, 2), (2, 3), (1, 1)))]
        index = PatternIntervals(rows, (F(), F(1), F(2), F(3), F(4), F(5)))
        self.assertEqual(index.query(F(2), F(3)), (rows[0], rows[1], rows[3]))
        self.assertEqual(index.query(F(4), F(5)), ())
        self.assertEqual(index.query(F(2), F(2)), (rows[1],))  # exactly original predicate
        self.assertEqual(index.query(F(), F(2)), (rows[1], rows[2], rows[4]))

    def test_positive_passing_neighbor_and_all_span_features_costs(self):
        cases = [fixture([('C3',0,4,'b'), ('E3',0,4,'i'), ('G3',0,4,'j'),
                 ('C4',0,F(1,2),'lead'), ('D4',F(1,2),1,'lead'), ('E4',1,4,'lead')]),
                 fixture([('C3',0,4,'b'), ('E3',0,4,'i'), ('G3',0,4,'j'),
                 ('C4',0,F(1,2),'lead'), ('D4',F(1,2),1,'lead'), ('C4',1,4,'lead')])]
        positive = False
        for ir in cases:
            p, ev, args = prepare(ir)
            old, new = (cls(p, ev, model_weights(), **args) for cls in (CompiledSearch, IntervalSearch))
            for i, j in itertools.combinations(range(len(p.points)), 2):
                a, b = p.points[i], p.points[j]
                self.assertEqual(old.index.domain(a,b), new.index.domain(a,b))
                for sig in (C, G, C7, G7, FUNC64, (None, C[1])):
                    values = old.index.features(a,b,sig)
                    positive |= bool(values[0]['conditional_step_ornament_exposure'])
                    self.assertEqual(values, new.index.features(a,b,sig))
                    self.assertEqual(old.run_cost(i,j,sig), new.run_cost(i,j,sig))
        self.assertTrue(positive)

    def test_frontier_budget_and_original_direct_finish(self):
        p, ev, batches = problem()
        for budget in (1, 2_000_000):
            old, new = (cls(p,ev,model_weights(),beam_width=2,operations=budget)
                        for cls in (CompiledSearch, IntervalSearch))
            for batch in batches:
                old.consume(batch); new.consume(batch)
                self.assertEqual(old.frontier,new.frontier)
                self.assertEqual(old.operations,new.operations)
                self.assertEqual(old.discarded,new.discarded)
                if old.status!='pending': break
            self.assertEqual(old.finish(),new.finish())

    def test_full_catalogs_score_features_and_source_immutability(self):
        ir = fixture(); before = deepcopy(ir)
        old, new = compiled(ir,F(4)), infer(ir,F(4))
        self.assertEqual(old[0],new[0]); self.assertEqual(old[2],new[2])
        for field in ('selected_path','page_inventory','score_cost','feature_values','feature_availability',
                      'actual_harmonic_runs','states_discarded','operations'):
            self.assertEqual(old[1][field],new[1][field])
        self.assertEqual(ir,before)


if __name__ == '__main__': unittest.main()
