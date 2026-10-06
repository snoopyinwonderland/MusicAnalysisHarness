"""Independent exact-supply tests; no corpus, parent replay or native authority.

Musical equivalence uses genuine MusicXML round-trips and the untouched legacy
catalog. Mocks are restricted to producer freshness and window-call accounting.
Only the fixture functions are reused; no existing test class is inherited.
"""
from copy import copy, deepcopy
from fractions import Fraction
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from xml.etree import ElementTree

from music21 import bar, chord, converter, meter, note, stream

from test_musical_role_evidence import event, make_ir
from musicanote_harness.canonical import CanonicalIRBuilder
from musicanote_harness.formal_ir import FormalIRAdapter, q
from musicanote_harness import harmony_candidate_catalog as legacy
from musicanote_harness import harmony_open_candidates as opened
from musicanote_harness import harmony_shared_candidate_supply as shared
from musicanote_harness import musical_pattern_observation as pattern


def span(start=0, end=4):
    return {"start": q(start), "end": q(end)}


def wire_span(start_num, start_den, end_num, end_den):
    return {"start": {"numerator": start_num, "denominator": start_den},
            "end": {"numerator": end_num, "denominator": end_den}}


def fraction(value):
    return Fraction(value["numerator"], value["denominator"])


class SharedCandidateSupplyTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def fixture(self, lanes=None):
        if lanes is None:
            lanes = [[event(["C3", "E3", "G3"], 0, 4)]]
        return make_ir(self.temp.name, lanes)

    def four_provider_fixture(self):
        return self.fixture([[event(
            ["C3", "E3", "B3", "B-3", "D4", "A-3", "F#4"], 0, 4)]])

    def meter_repeat_fixture(self):
        score = stream.Score()
        part = stream.Part(id="P0")
        first = stream.Measure(number=1)
        first.append(meter.TimeSignature("4/4"))
        first.append(chord.Chord(["C3", "E3", "G3"], quarterLength=2))
        first.append(note.Rest(quarterLength=2))
        first.rightBarline = bar.Repeat(direction="end")
        second = stream.Measure(number=2)
        second.append(meter.TimeSignature("3/4"))
        second.append(chord.Chord(["C3", "E3", "G3"], quarterLength=3))
        part.append(first)
        part.append(second)
        score.append(part)
        path = Path(self.temp.name) / "meter-repeat.musicxml"
        score.write("musicxml", fp=path, makeNotation=False)
        parsed = converter.parse(path)
        ir = FormalIRAdapter().convert(CanonicalIRBuilder().build(parsed, path), path)
        # FormalIRAdapter currently defers barline import (sets it to None).
        # Restore this observed fixture field from the genuine XML, not from a
        # guessed musical boundary, so the supply contract can test its handling.
        source = ElementTree.parse(path).getroot()
        for source_measure in source.findall("./part/measure"):
            source_barline = source_measure.find("./barline/repeat/..")
            if source_barline is None:
                continue
            source_repeat = source_barline.find("repeat")
            target = next(m for m in ir["measures"]
                          if m["printed_measure_number"] == source_measure.get("number"))
            target["repeat_barline"] = {
                "location": source_barline.get("location", "right"),
                "repeat_direction": source_repeat.get("direction"),
                "ending_number": None}
        pattern.validate_core(ir)
        return ir

    def exact_batch(self, ir, context, requests, **limits):
        # Baseline first: any legacy lazy imports are completed before ownership.
        expected = [legacy.propose(ir, s, context) for s in requests]
        before = deepcopy((ir, context, requests))
        session = shared.prepare_supply(ir, context)
        result = shared.supply_catalogs(session, requests, **limits)
        self.assertEqual((ir, context, requests), before)
        self.assertEqual(result["receipt"]["status"], "complete")
        self.assertIsNone(result["receipt"]["hold_reason"])
        self.assertEqual(shared.canonical_json(result["catalogs"]),
                         shared.canonical_json(expected))
        self.assertEqual(result["receipt"]["catalog_candidate_counts"],
                         [len(c["candidates"]) for c in expected])
        payload = shared.canonical_json(expected).encode("utf-8")
        self.assertEqual(result["receipt"]["payload_bytes"], len(payload))
        self.assertEqual(result["receipt"]["payload_sha256"], sha256(payload).hexdigest())
        for field in ("production_enabled", "native_lattice_authority", "music_accuracy_evaluated"):
            self.assertIs(result["receipt"][field], False)
        for catalog in result["catalogs"]:
            self.assertEqual(catalog["engine_version"], legacy.VERSION)
            self.assertTrue(legacy.validate(catalog)["passed"])
            self.assertIsNone(catalog["selected"])
            for candidate in catalog["candidates"]:
                self.assertEqual(legacy.resolve(catalog, candidate["origin_pointer"])["candidate_id"],
                                 candidate["candidate_id"])
                self.assertTrue(all(candidate[k] is None for k in ("selected", "confidence", "function")))
                total = sum((fraction(v) for v in candidate["note_time_quarters"].values()), Fraction())
                self.assertEqual(total, fraction(candidate["total_note_time_quarters"]))
        return session, result

    def assert_held(self, result, reason):
        self.assertIsNone(result["catalogs"])
        self.assertEqual(result["receipt"]["status"], "held")
        self.assertEqual(result["receipt"]["hold_reason"], reason)
        for key in ("catalog_candidate_counts", "payload_bytes", "payload_sha256"):
            self.assertIsNone(result["receipt"][key])

    def test_basic_full_window_catalog_is_exact(self):
        _, result = self.exact_batch(self.fixture(), span(), [span()])
        self.assertEqual(result["receipt"]["stats"]["window_calls"], 1)
        self.assertFalse(result["receipt"]["stats"]["context_cache_hit"])

    def test_all_four_provider_orders_and_origin_pointers_are_exact(self):
        _, result = self.exact_batch(self.four_provider_fixture(), span(), [span()])
        providers = [c["provider"] for c in result["catalogs"][0]["candidates"]]
        self.assertEqual(set(providers), {"base", "additional_seventh", "augmented", "extended"})
        order = {"base": 0, "additional_seventh": 1, "augmented": 2, "extended": 3}
        self.assertEqual([order[p] for p in providers], sorted(order[p] for p in providers))

    def test_full_and_narrow_windows_share_only_exact_window_calls(self):
        _, result = self.exact_batch(self.four_provider_fixture(), span(),
                                    [span(), span(1, 2), span(2, 3)])
        self.assertEqual(result["receipt"]["planned_window_calls"], 3)
        self.assertEqual(result["receipt"]["stats"]["window_calls"], 3)

    def test_repeated_requests_preserve_every_occurrence_without_aliasing(self):
        session, result = self.exact_batch(self.fixture(), span(),
                                          [span(1, 2), span(), span(1, 2)])
        self.assertEqual(result["receipt"]["requests"], 3)
        self.assertEqual(result["receipt"]["distinct_raw_spans"], 2)
        self.assertEqual(result["receipt"]["stats"]["window_calls"], 2)
        first = deepcopy(result["catalogs"][0])
        self.assertIsNot(result["catalogs"][0], result["catalogs"][2])
        result["catalogs"][0]["span"]["start"]["numerator"] = 999
        self.assertEqual(result["catalogs"][2], first)
        again = shared.supply_catalogs(session, [span(1, 2)])
        self.assertEqual(again["catalogs"], [first])

    def test_context_cache_is_session_local_and_targets_are_not_retained(self):
        session, first = self.exact_batch(self.fixture(), span(), [span(1, 2)])
        second = shared.supply_catalogs(session, [span(1, 2), span()])
        third = shared.supply_catalogs(session, [span()])
        self.assertEqual(first["receipt"]["stats"]["window_calls"], 2)
        self.assertEqual(second["receipt"]["stats"]["window_calls"], 1)
        self.assertEqual(third["receipt"]["stats"]["window_calls"], 0)
        self.assertTrue(second["receipt"]["stats"]["context_cache_hit"])
        self.assertEqual(second["catalogs"][0], first["catalogs"][0])

    def test_reported_window_call_counts_match_real_wrapped_window_calls(self):
        ir = self.fixture()
        requests = [span(1, 2), span(), span(1, 2)]
        expected = [legacy.propose(ir, s, span()) for s in requests]
        original_window = opened.window
        # Wrapper is established before ownership; it counts genuine calculation.
        with patch.object(opened, "window", wraps=original_window) as counted:
            session = shared.prepare_supply(ir, span())
            first = shared.supply_catalogs(session, requests)
            self.assertEqual(first["catalogs"], expected)
            self.assertEqual(counted.call_count, 2)
            self.assertEqual(first["receipt"]["stats"]["window_calls"], counted.call_count)
            second = shared.supply_catalogs(session, [span(1, 2)])
            self.assertEqual(counted.call_count, 3)
            self.assertEqual(second["receipt"]["stats"]["window_calls"], 1)

    def test_nonreduced_rationals_remain_distinct_raw_requests(self):
        canonical = span(1, 2)
        unreduced = wire_span(2, 2, 4, 2)
        _, result = self.exact_batch(self.fixture(), span(), [canonical, unreduced, canonical])
        self.assertEqual(result["receipt"]["distinct_raw_spans"], 2)
        self.assertEqual(result["receipt"]["stats"]["window_calls"], 3)
        left, right = result["catalogs"][:2]
        self.assertEqual(left["providers"]["base"]["window_id"], right["providers"]["base"]["window_id"])
        self.assertEqual(left["span"], canonical)
        self.assertEqual(right["span"], unreduced)
        self.assertNotEqual(shared.canonical_json(left), shared.canonical_json(right))

    def test_numerically_equal_raw_context_is_not_assumed_identical(self):
        context = wire_span(0, 2, 8, 2)
        _, result = self.exact_batch(self.fixture(), context, [context, span()])
        self.assertEqual(result["receipt"]["stats"]["window_calls"], 2)
        self.assertEqual(result["catalogs"][1]["context_span"], context)

    def test_triplet_exact_time_and_partial_overlap_catalogs_are_preserved(self):
        ir = self.fixture([[event("C4", 0, Fraction(1, 3)),
                            event("E4", Fraction(1, 3), Fraction(1, 3)),
                            event("G4", Fraction(2, 3), Fraction(10, 3))]])
        self.exact_batch(ir, span(), [span(0, Fraction(2, 3)),
                                     span(Fraction(1, 3), Fraction(5, 3)), span()])

    def test_tie_continuation_preserves_full_sound_and_source_note_refs(self):
        ir = self.fixture([[event("C4", 0, 2, tie_role="start"),
                            event("C4", 2, 2, tie_role="stop")],
                           [event("E4", 0, 4)]])
        _, result = self.exact_batch(ir, span(), [span(2, 3)])
        tied = next(s for s in ir["sounding_events"] if len(s["source_note_ids"]) == 2)
        base = result["catalogs"][0]["providers"]["base"]
        self.assertEqual(base["event_units"][tied["sounding_event_id"]]["span"], span())
        self.assertEqual(base["event_units"][tied["sounding_event_id"]]["source_note_ids"], tied["source_note_ids"])
        self.assertIn(tied["sounding_event_id"], base["cells"][0]["continued_refs"])
        self.assertNotIn(tied["sounding_event_id"], base["cells"][0]["attack_refs"])

    def test_rest_meter_change_and_repeat_barrier_match_legacy(self):
        _, result = self.exact_batch(self.meter_repeat_fixture(), span(0, 7),
                                    [span(0, 7), span(0, 2), span(4, 7)])
        blockers = result["catalogs"][0]["providers"]["base"]["abstention_reasons"]
        self.assertIn("silence_inside_window", blockers)
        self.assertIn("meter_missing_or_changed", blockers)
        self.assertIn("repeat_barrier", blockers)

    def test_outer_grace_is_retained_as_context_blocker(self):
        ir = self.fixture([[event(["A-3", "C4", "F#4"], 0, 4)],
                           [event("G5", 3, 0, grace=True), event("G5", 3, 1)]])
        _, result = self.exact_batch(ir, span(), [span(0, 1)])
        catalog = result["catalogs"][0]
        self.assertNotIn("grace_timing", catalog["providers"]["base"]["abstention_reasons"])
        self.assertIn("grace_timing", catalog["providers"]["augmented"]["abstention_reasons"])
        self.assertEqual(catalog["providers"]["augmented"]["augmented_sixth_candidates"], [])

    def test_outer_microtonal_pitch_is_not_projected_out_of_context(self):
        ir = self.fixture([[event(["C3", "E3", "B-3", "D4"], 0, 4)],
                           [event("C~5", 3, 1)]])
        _, result = self.exact_batch(ir, span(), [span(0, 1)])
        catalog = result["catalogs"][0]
        self.assertNotIn("unsupported_pitch", catalog["providers"]["base"]["abstention_reasons"])
        self.assertIn("unsupported_pitch", catalog["providers"]["extended"]["abstention_reasons"])
        self.assertEqual(catalog["providers"]["extended"]["extended_candidates"], [])

    def test_in_window_microtone_preserves_unresolved_sounds(self):
        ir = self.fixture([[event(["C3", "E3", "G3", "C~5"], 0, 4)]])
        _, result = self.exact_batch(ir, span(), [span()])
        catalog = result["catalogs"][0]
        self.assertIn("unsupported_pitch", catalog["providers"]["base"]["abstention_reasons"])
        self.assertTrue(any("spelling_unresolved" in c["event_states"].values()
                            for c in catalog["candidates"]))

    def test_silence_is_computed_zero_candidates_not_unknown(self):
        _, result = self.exact_batch(self.fixture([[event(None, 0, 4)]]), span(), [span()])
        self.assertEqual(result["receipt"]["catalog_candidate_counts"], [0])
        self.assertEqual(result["catalogs"][0]["candidates"], [])
        self.assertEqual(result["receipt"]["stats"]["window_calls"], 1)

    def test_empty_request_batch_is_computed_empty_without_windows(self):
        session = shared.prepare_supply(self.fixture(), span())
        result = shared.supply_catalogs(session, [], max_requests=0, max_window_calls=0,
                                       max_output_bytes=2)
        self.assertEqual(result["catalogs"], [])
        self.assertEqual(result["receipt"]["catalog_candidate_counts"], [])
        self.assertEqual(result["receipt"]["status"], "complete")
        self.assertEqual(result["receipt"]["stats"]["window_calls"], 0)
        self.assertEqual(result["receipt"]["payload_bytes"], 2)
        following = shared.supply_catalogs(session, [span()])
        self.assertFalse(following["receipt"]["stats"]["context_cache_hit"])

    def test_request_budget_holds_whole_batch_before_calculation(self):
        session = shared.prepare_supply(self.fixture(), span())
        result = shared.supply_catalogs(session, [span(), span()], max_requests=1)
        self.assert_held(result, "request_budget")
        self.assertEqual(result["receipt"]["requests"], 2)
        self.assertEqual(result["receipt"]["stats"]["window_calls"], 0)

    def test_window_budget_holds_whole_batch_and_does_not_warm_context(self):
        session = shared.prepare_supply(self.fixture(), span())
        result = shared.supply_catalogs(session, [span(1, 2)], max_window_calls=1)
        self.assert_held(result, "window_budget")
        self.assertEqual(result["receipt"]["planned_window_calls"], 2)
        self.assertEqual(result["receipt"]["stats"]["window_calls"], 0)
        following = shared.supply_catalogs(session, [span(1, 2)])
        self.assertEqual(following["receipt"]["stats"]["window_calls"], 2)
        self.assertFalse(following["receipt"]["stats"]["context_cache_hit"])

    def test_output_budget_returns_no_prefix_and_does_not_warm_context(self):
        session = shared.prepare_supply(self.fixture(), span())
        result = shared.supply_catalogs(session, [span(1, 2), span()], max_output_bytes=0)
        self.assert_held(result, "output_bytes_budget")
        self.assertGreater(result["receipt"]["stats"]["window_calls"], 0)
        following = shared.supply_catalogs(session, [span()])
        self.assertEqual(following["receipt"]["stats"]["window_calls"], 1)
        self.assertFalse(following["receipt"]["stats"]["context_cache_hit"])

    def test_exact_output_byte_limit_and_one_byte_under(self):
        ir = self.fixture()
        baseline = legacy.propose(ir, span(), span())
        size = len(shared.canonical_json([baseline]).encode("utf-8"))
        session = shared.prepare_supply(ir, span())
        rejected = shared.supply_catalogs(session, [span()], max_output_bytes=size - 1)
        self.assert_held(rejected, "output_bytes_budget")
        accepted = shared.supply_catalogs(session, [span()], max_output_bytes=size)
        self.assertEqual(accepted["catalogs"], [baseline])
        self.assertEqual(accepted["receipt"]["payload_bytes"], size)

    def test_ir_snapshot_budget_has_exact_utf8_denominator(self):
        ir = self.fixture()
        ir["score"]["metadata"]["test_text"] = "음악 🎵"
        size = len(shared.canonical_json(ir).encode("utf-8"))
        with self.assertRaisesRegex(ValueError, "full_IR_snapshot_budget_or_type"):
            shared.prepare_supply(ir, span(), max_ir_bytes=size - 1)
        session = shared.prepare_supply(ir, span(), max_ir_bytes=size)
        self.assertEqual(shared.session_binding(session)["full_ir_sha256"],
                         sha256(shared.canonical_json(ir).encode("utf-8")).hexdigest())

    def test_context_window_bytes_hold_whole_batch_without_warming_cache(self):
        session = shared.prepare_supply(self.fixture(), span(), max_context_window_bytes=0)
        for _ in range(2):
            result = shared.supply_catalogs(session, [span(), span(1, 2)])
            self.assert_held(result, "context_window_bytes_budget")
            self.assertEqual(result["receipt"]["stats"]["window_calls"], 1)
            self.assertFalse(result["receipt"]["stats"]["context_cache_hit"])

    def test_context_window_bytes_exact_limit_and_one_byte_under(self):
        ir = self.fixture()
        size = len(shared.canonical_json(opened.window(ir, span())).encode("utf-8"))
        smaller = shared.prepare_supply(ir, span(), max_context_window_bytes=size - 1)
        self.assert_held(shared.supply_catalogs(smaller, [span()]), "context_window_bytes_budget")
        exact = shared.prepare_supply(ir, span(), max_context_window_bytes=size)
        result = shared.supply_catalogs(exact, [span()])
        self.assertEqual(result["receipt"]["status"], "complete")
        self.assertEqual(result["receipt"]["binding"]["max_context_window_bytes"], size)

    def test_caps_reject_bool_float_none_string_and_negative_before_freshness(self):
        session = shared.prepare_supply(self.fixture(), span())
        for bad in (True, False, -1, 1.0, None, "1"):
            with self.subTest(prepare=bad), patch.object(shared, "producer_contract", side_effect=AssertionError("not reached")):
                with self.assertRaisesRegex(ValueError, "explicit_nonnegative_integer_required"):
                    shared.prepare_supply({}, span(), max_ir_bytes=bad)
            with self.subTest(context_budget=bad), patch.object(shared, "producer_contract", side_effect=AssertionError("not reached")):
                with self.assertRaisesRegex(ValueError, "explicit_nonnegative_integer_required"):
                    shared.prepare_supply({}, span(), max_context_window_bytes=bad)
            for name in ("max_requests", "max_window_calls", "max_output_bytes"):
                with self.subTest(name=name, value=bad), patch.object(shared, "producer_contract", side_effect=AssertionError("not reached")):
                    with self.assertRaisesRegex(ValueError, "explicit_nonnegative_integer_required"):
                        shared.supply_catalogs(session, [], **{name: bad})

    def test_closed_exact_spans_reject_invalid_wire_types_and_ranges(self):
        malformed = [None, [], {}, {**span(), "extra": True}, span(1, 1), span(2, 1), span(-1, 1),
                     {"start": 0.0, "end": q(1)}, wire_span(0, 0, 1, 1),
                     wire_span(0, -1, 1, 1), wire_span(True, 1, 1, 1),
                     {"start": {**q(0), "extra": 0}, "end": q(1)}]
        session = shared.prepare_supply(self.fixture(), span())
        for value in malformed:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    shared.prepare_supply({}, value)
                with self.assertRaises(ValueError):
                    shared.supply_catalogs(session, [value])
        with self.assertRaisesRegex(ValueError, "span_outside_owned_context"):
            shared.supply_catalogs(session, [span(3, 5)])

    def test_request_container_and_full_ir_json_types_are_strict(self):
        session = shared.prepare_supply(self.fixture(), span())
        for value in (None, {}, (), "span"):
            with self.subTest(requests=value), self.assertRaisesRegex(ValueError, "closed_span_request_list_required"):
                shared.supply_catalogs(session, value)
        for value in ([], None, "IR"):
            with self.subTest(ir=value), self.assertRaisesRegex(ValueError, "full_IR_snapshot_budget_or_type"):
                shared.prepare_supply(value, span())
        with self.assertRaises(ValueError):
            shared.prepare_supply({"invalid_json": float("nan")}, span())
        for value in ({"non_json_tuple": (1, 2)}, {1: "nonstring key"}, {"non_json_set": {1, 2}}):
            with self.subTest(non_json=value), self.assertRaisesRegex(ValueError, "JSON_only_full_IR_snapshot_required"):
                shared.prepare_supply(value, span())

    def test_caller_snapshot_and_context_mutation_do_not_change_owned_inputs(self):
        ir = self.fixture()
        context = span()
        baseline = legacy.propose(ir, span(1, 2), context)
        session = shared.prepare_supply(ir, context)
        original_binding = shared.session_binding(session)
        ir["sounding_events"][0]["pitch"]["step"] = "X"
        ir["note_events"].clear()
        context["end"]["numerator"] = 2
        result = shared.supply_catalogs(session, [span(1, 2)])
        self.assertEqual(result["catalogs"], [baseline])
        self.assertEqual(shared.session_binding(session), original_binding)

    def test_returned_catalog_receipt_and_binding_mutations_do_not_persist(self):
        session, first = self.exact_batch(self.fixture(), span(), [span()])
        baseline = deepcopy(first["catalogs"])
        binding = shared.session_binding(session)
        first["catalogs"][0]["candidates"][0]["selected"] = "caller mutation"
        first["catalogs"][0]["providers"]["base"]["event_units"].clear()
        first["receipt"]["binding"]["full_ir_sha256"] = "bad"
        binding["context_span_sha256"] = "bad"
        next_result = shared.supply_catalogs(session, [span()])
        self.assertEqual(next_result["catalogs"], baseline)
        self.assertNotEqual(shared.session_binding(session)["context_span_sha256"], "bad")
        self.assertNotEqual(next_result["receipt"]["binding"]["full_ir_sha256"], "bad")

    def test_copied_constructed_and_serialized_sessions_are_foreign(self):
        session = shared.prepare_supply(self.fixture(), span())
        for foreign in (copy(session), deepcopy(session), shared.SupplySession(session.token),
                        {"token": session.token}, session.token, None):
            with self.subTest(kind=type(foreign).__name__):
                with self.assertRaises(ValueError):
                    shared.session_binding(foreign)
                with self.assertRaises(ValueError):
                    shared.supply_catalogs(foreign, [])

    def test_copied_registry_state_replacement_is_not_issued_authority(self):
        session = shared.prepare_supply(self.fixture(), span())
        with shared._OWNERS_LOCK:
            state, seal = shared._OWNERS[session]
            shared._OWNERS[session] = (copy(state), seal)
        with self.assertRaisesRegex(ValueError, "owned_supply_state_changed"):
            shared.supply_catalogs(session, [])

    def test_bypassed_frozen_ir_snapshot_mutation_is_rejected(self):
        session = shared.prepare_supply(self.fixture(), span())
        with shared._OWNERS_LOCK:
            state, _ = shared._OWNERS[session]
        object.__setattr__(state, "ir_json", shared.canonical_json({"tampered": True}))
        with self.assertRaisesRegex(ValueError, "owned_supply_state_changed"):
            shared.session_binding(session)
        with self.assertRaisesRegex(ValueError, "owned_supply_state_changed"):
            shared.supply_catalogs(session, [])

    def test_changed_context_cache_with_plain_recomputed_digest_is_rejected(self):
        session, _ = self.exact_batch(self.fixture(), span(), [span()])
        with shared._OWNERS_LOCK:
            state, _ = shared._OWNERS[session]
        state.cache.value = shared.canonical_json({"replaced": True})
        # A public digest is not the process-owned cache seal. No secret is used.
        state.cache.seal = sha256(state.cache.value.encode("utf-8")).hexdigest()
        with self.assertRaisesRegex(ValueError, "owned_context_cache_changed"):
            shared.supply_catalogs(session, [])

    def test_cross_session_context_cache_copy_is_rejected_even_for_equal_ir(self):
        ir = self.fixture()
        legacy.propose(ir, span(), span())
        first = shared.prepare_supply(ir, span())
        second = shared.prepare_supply(ir, span())
        shared.supply_catalogs(first, [span()])
        with shared._OWNERS_LOCK:
            first_state, _ = shared._OWNERS[first]
            second_state, _ = shared._OWNERS[second]
        second_state.cache.value = first_state.cache.value
        second_state.cache.seal = first_state.cache.seal
        with self.assertRaisesRegex(ValueError, "owned_context_cache_changed"):
            shared.supply_catalogs(second, [])

    def test_changed_session_token_cannot_reseal_owned_state(self):
        session = shared.prepare_supply(self.fixture(), span())
        object.__setattr__(session, "token", "caller edited token")
        with self.assertRaisesRegex(ValueError, "owned_supply_state_changed"):
            shared.supply_catalogs(session, [])

    def test_equal_content_sessions_have_equal_bindings_but_separate_caches(self):
        ir = self.fixture()
        baseline = legacy.propose(ir, span(), span())
        first = shared.prepare_supply(ir, span())
        second = shared.prepare_supply(deepcopy(ir), span())
        self.assertIsNot(first, second)
        self.assertEqual(shared.session_binding(first), shared.session_binding(second))
        shared.supply_catalogs(first, [span()])
        result = shared.supply_catalogs(second, [span()])
        self.assertEqual(result["catalogs"], [baseline])
        self.assertFalse(result["receipt"]["stats"]["context_cache_hit"])
        self.assertEqual(result["receipt"]["stats"]["window_calls"], 1)

    def test_distinct_ir_and_context_sessions_never_share_musical_catalogs(self):
        first_ir = self.fixture()
        second_ir = self.fixture([[event(["D3", "F#3", "A3"], 0, 4)]])
        contexts = [span(), span(1, 3)]
        for ir in (first_ir, second_ir):
            expected = [legacy.propose(ir, span(1, 2), c) for c in contexts]
            sessions = [shared.prepare_supply(ir, c) for c in contexts]
            for session, baseline in zip(sessions, expected):
                self.assertEqual(shared.supply_catalogs(session, [span(1, 2)])["catalogs"], [baseline])
            self.assertNotEqual(shared.session_binding(sessions[0])["context_span_sha256"],
                                shared.session_binding(sessions[1])["context_span_sha256"])

    def test_producer_contract_tracks_transitive_files_not_only_facade_version(self):
        contract = shared.producer_contract()
        files = contract["file_sha256"]
        names = {Path(path).name for path in files}
        self.assertTrue({"harmony_candidate_catalog.py", "harmony_open_candidates.py",
                         "harmony_candidate_windows_catalog.py", "augmented_sixth.py",
                         "added_dissonance.py", "harmony_conditional_ornaments.py"} <= names)
        for path, digest in files.items():
            self.assertTrue(Path(path).is_absolute())
            self.assertEqual(sha256(Path(path).read_bytes()).hexdigest(), digest)

    def test_changed_source_contract_invalidates_even_empty_or_budget_held_batch(self):
        with patch.object(shared, "producer_contract", return_value={"file": "old"}):
            session = shared.prepare_supply(self.fixture(), span())
        for requests, limits in (([], {}), ([span()], {"max_requests": 0})):
            with self.subTest(requests=requests), patch.object(shared, "producer_contract", return_value={"file": "new"}):
                with self.assertRaisesRegex(ValueError, "stale_supply_producer"):
                    shared.supply_catalogs(session, requests, **limits)

    def test_producer_change_during_prepare_issues_no_session(self):
        ir = self.fixture()
        with patch.object(shared, "producer_contract", side_effect=[{"file": "old"}, {"file": "new"}]):
            with self.assertRaisesRegex(ValueError, "producer_changed_during_prepare"):
                shared.prepare_supply(ir, span())

    def test_producer_change_during_supply_rejects_and_does_not_warm_cache(self):
        ir = self.fixture()
        with patch.object(shared, "producer_contract", return_value={"file": "old"}):
            session = shared.prepare_supply(ir, span())
        with patch.object(shared, "producer_contract", side_effect=[{"file": "old"}, {"file": "new"}]):
            with self.assertRaisesRegex(ValueError, "producer_changed_during_supply"):
                shared.supply_catalogs(session, [span()])
        with patch.object(shared, "producer_contract", return_value={"file": "old"}):
            result = shared.supply_catalogs(session, [span()])
        self.assertFalse(result["receipt"]["stats"]["context_cache_hit"])
        self.assertEqual(result["receipt"]["stats"]["window_calls"], 1)

    def test_persistent_runtime_window_replacement_invalidates_owned_session(self):
        session = shared.prepare_supply(self.fixture(), span())
        original = opened.window
        def changed_window(ir, value):
            return original(ir, value)
        with patch.object(opened, "window", changed_window):
            with self.assertRaisesRegex(ValueError, "stale_supply_producer"):
                shared.supply_catalogs(session, [span()])
        result = shared.supply_catalogs(session, [span()])
        self.assertFalse(result["receipt"]["stats"]["context_cache_hit"])

    def test_persistent_provider_constant_replacement_invalidates_owned_session(self):
        session = shared.prepare_supply(self.fixture(), span())
        with patch.object(legacy, "STATES", tuple(reversed(legacy.STATES))):
            with self.assertRaisesRegex(ValueError, "stale_supply_producer"):
                shared.supply_catalogs(session, [])

    def test_persistent_runtime_code_replacement_with_same_function_identity_is_rejected(self):
        session = shared.prepare_supply(self.fixture(), span())
        original_code = opened.window.__code__
        constants = list(original_code.co_consts)
        index = next(i for i, value in enumerate(constants) if type(value) is str)
        constants[index] = constants[index] + "_runtime_changed"
        try:
            opened.window.__code__ = original_code.replace(co_consts=tuple(constants))
            with self.assertRaisesRegex(ValueError, "stale_supply_producer"):
                shared.supply_catalogs(session, [])
        finally:
            opened.window.__code__ = original_code

    def test_binding_has_content_authority_not_original_file_or_native_authority(self):
        ir = self.fixture()
        context = wire_span(0, 2, 8, 2)
        binding = shared.session_binding(shared.prepare_supply(ir, context))
        self.assertEqual(set(binding), {"full_ir_sha256", "context_span_sha256",
                                       "producer_contract_sha256", "max_context_window_bytes", "authority"})
        self.assertEqual(binding["context_span_sha256"],
                         sha256(shared.canonical_json(context).encode("utf-8")).hexdigest())
        self.assertEqual(binding["authority"], "owned_full_IR_content_not_original_file_or_parent_replay")


if __name__ == "__main__":
    unittest.main()
