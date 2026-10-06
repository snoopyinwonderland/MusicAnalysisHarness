"""Versioned codec/proof controls; synthetic tests confer no music authority."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import gc
import hashlib
import inspect
import json
import sys
import tracemalloc
import unittest
from unittest.mock import patch
import weakref

from musicanote_harness import lossless_json_dag as frozen
from musicanote_harness import lossless_json_dag_v2 as dag


def raw(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False).encode("utf-8")


class LosslessJsonDagV2Controls(unittest.TestCase):
    def test_plain_types_roundtrip_exact_unicode_aliases_ordinals_and_null_zero(self):
        value = {"entries": [None, False, 0, True, 1, -3, "F#4", "Gb4", "쉼표 ♭",
            {"source_note_ids": ["a", "a", "alias"], "start": {"n": 0, "d": 1}}],
            "empty_dict": {}, "empty_list": []}
        proof = dag.freeze_json(value)
        handle = dag.encode_proof(proof)
        self.assertEqual(dag.decode_json(handle), value)
        self.assertEqual(dag.proof_value_at(proof), value)
        self.assertIs(type(dag.value_at(handle, ("entries", 1))), bool)
        self.assertIs(type(dag.value_at(handle, ("entries", 2))), int)
        self.assertEqual(handle.stats()["expanded_bytes"], len(raw(value)))
        self.assertEqual(handle.stats()["codec_sha256"], hashlib.sha256(handle.json_bytes()).hexdigest())

    def test_frozen_codec_schema_and_structural_semantics_equivalence(self):
        cases = [{}, [], None, "", -5, True, {"b": [2, 1], "a": False},
            [{"x": [None, True, 0, "\x00쉼표"]}] * 4]
        for value in cases:
            with self.subTest(value=value):
                old = frozen.encode_json(value)
                new = dag.encode_json(value)
                old_record = old.record()
                old_record["schema_version"] = dag.VERSION
                self.assertEqual(new.record(), old_record)
                self.assertEqual(new.stats()["structural_sha256"], old.stats()["structural_sha256"])
                self.assertEqual(new.stats()["expanded_visits"], old.stats()["expanded_visits"])
                self.assertEqual(new.stats()["expanded_bytes"], old.stats()["expanded_bytes"])
                self.assertEqual(dag.decode_json(new), frozen.decode_json(old))
        self.assertNotEqual(dag.VERSION, frozen.VERSION)

    def test_identical_nodes_not_occurrences_and_different_roots_not_merged(self):
        row = {"source_note_ids": ["note-1", "note-1", "alias"], "payload": "common " * 80}
        value = {"entries": [{"selector_index": i, "row": deepcopy(row)} for i in range(50)],
            "requests": [{"source": "src", "completion": "a"}, {"source": "src", "completion": "b"}]}
        handle = dag.encode_json(value)
        self.assertLess(handle.stats()["encoded_bytes"], len(raw(value)))
        self.assertEqual(dag.node_at(handle, ("entries", 0, "row")), dag.node_at(handle, ("entries", 49, "row")))
        self.assertNotEqual(dag.node_at(handle, ("entries", 0)), dag.node_at(handle, ("entries", 49)))
        self.assertNotEqual(dag.node_at(handle, ("requests", 0)), dag.node_at(handle, ("requests", 1)))
        self.assertEqual([dag.value_at(handle, ("entries", i, "selector_index")) for i in range(50)], list(range(50)))

    def test_bool_integer_null_unknown_and_rational_zero_never_coalesce(self):
        handle = dag.encode_json([False, 0, True, 1, None, {"n": 0, "d": 1}])
        self.assertEqual(len({dag.node_at(handle, (i,)) for i in range(6)}), 6)
        self.assertEqual([dag.subtree_stats(handle, (i,))["type"] for i in range(6)],
            ["bool", "int", "bool", "int", "null", "dict"])
        self.assertIsNone(dag.subtree_stats(handle, (4,))["container_length"])
        self.assertEqual(dag.proof_subtree_stats(dag.freeze_json([]))["container_length"], 0)

    def test_dict_canonical_order_and_list_order_are_distinct(self):
        a = dag.encode_json({"b": [2, 1], "a": 0})
        b = dag.encode_json({"a": 0, "b": [2, 1]})
        c = dag.encode_json({"a": 0, "b": [1, 2]})
        self.assertEqual(a.json_bytes(), b.json_bytes())
        self.assertNotEqual(a.json_bytes(), c.json_bytes())
        self.assertEqual(list(dag.decode_json(a)), ["a", "b"])

    def test_reject_float_nonfinite_subclass_nonstring_keys_and_invalid_utf8(self):
        class Integer(int): pass
        class Text(str): pass
        class List(list): pass
        class Dict(dict): pass
        for value in (1.0, float("nan"), float("inf"), Integer(1), Text("x"), List([1]),
                Dict(a=1), {1: "x"}, {Text("x"): 1}, b"x", (1, 2), "\ud800", {"\ud800": 1}):
            with self.subTest(value=repr(value)):
                with self.assertRaises(ValueError):
                    dag.freeze_json(value)

    def test_cycles_reject_before_freeze_allocation(self):
        value = []
        value.append(value)
        other = {"child": None}
        other["child"] = other
        for obj in (value, other):
            with patch.object(dag, "_BuildState", side_effect=AssertionError("no allocation")):
                with self.assertRaisesRegex(ValueError, "cyclic"):
                    dag.freeze_json(obj)

    def test_logical_exponential_alias_bomb_precedes_snapshot_allocation(self):
        value = [0]
        for _ in range(35):
            value = [value, value]
        with patch.object(dag, "_BuildState", side_effect=AssertionError("no allocation")):
            with self.assertRaises(dag.DagHold) as caught:
                dag.freeze_json(value, limits=dag.DagLimits(max_expanded_bytes=10000, max_input_visits=10000))
        self.assertIn("logical_expanded", str(caught.exception))
        self.assertTrue(any("lower_bound" in key for key in caught.exception.diagnostics))

    def test_exact_multiplicity_visits_and_depth_are_not_physical_table_counts(self):
        shared = {"x": [1, True]}
        value = [shared, shared]
        report = dag.preflight_json(value)
        self.assertEqual(report["expanded_bytes"], len(raw(value)))
        self.assertEqual(report["expanded_visits"], 11)
        self.assertEqual(report["depth"], 4)
        self.assertLess(report["visited_input_values_and_keys"], report["expanded_visits"])
        self.assertEqual(report["charged_work_units"], report["expanded_bytes"] + 11)
        self.assertEqual(dag.freeze_json(value).stats()["structural_sha256"], report["structural_sha256"])

    def test_freeze_encoding_work_is_two_measured_passes_plus_actual_serializations(self):
        value = [{"x": "same"}] * 5
        proof = dag.freeze_json(value)
        stats = proof.stats()
        one = stats["expanded_bytes"] + stats["expanded_visits"]
        self.assertEqual(stats["reserved_input_guard_and_intern_work_units"], 2 * one)
        self.assertEqual(stats["charged_work_units"], 2 * one + stats["node_fragment_serialization_work_units"] +
            stats["node_fragment_size_measurement_work_units"])
        handle = dag.encode_proof(proof)
        self.assertEqual(handle.stats()["charged_work_units"], stats["charged_work_units"] + 2 * len(handle.json_bytes()))
        self.assertEqual(handle.stats()["incremental_encoding_work_units"], 2 * len(handle.json_bytes()))
        self.assertEqual(stats["encoding_work_upper_bound"], 2 * len(handle.json_bytes()))
        self.assertEqual(handle.stats()["codec_sha256_work_units"], len(handle.json_bytes()))
        self.assertEqual(handle.stats()["input_remeasurement_passes"], 0)

    def test_two_pass_work_reserved_before_any_snapshot_node_serialization(self):
        value = {"entries": [{"source_ref": "same"}] * 20}
        one = dag.preflight_json(value)["charged_work_units"]
        with patch.object(dag, "_node_record", side_effect=AssertionError("no node copy")):
            with self.assertRaises(dag.DagHold) as caught:
                dag.freeze_json(value, limits=dag.DagLimits(max_work_units=2 * one - 1))
        self.assertEqual(caught.exception.diagnostics["charged_work_units_lower_bound"], 2 * one)

    def test_all_caps_hold_whole_no_prefix_and_limits_exact(self):
        value = ["long text", {"x": 3}]
        report = dag.preflight_json(value)
        for limit in (dag.DagLimits(max_expanded_bytes=report["expanded_bytes"] - 1),
                dag.DagLimits(max_input_visits=report["expanded_visits"] - 1),
                dag.DagLimits(max_depth=1), dag.DagLimits(max_work_units=1),
                dag.DagLimits(max_nodes=1), dag.DagLimits(max_encoded_bytes=20)):
            with self.subTest(limit=limit):
                with self.assertRaises(dag.DagHold):
                    dag.encode_json(value, limits=limit)
        for value in (True, 1.5, -1):
            with self.assertRaises(ValueError):
                dag.DagLimits(max_nodes=value)
        with self.assertRaises(ValueError):
            dag.DagLimits(max_depth=257)

    def test_escaped_key_holds_before_json_copy(self):
        key = "\x00" * 8
        actual = dag._bytes
        def guarded(value):
            if value == key:
                raise AssertionError("escaped giant key copy")
            return actual(value)
        with patch.object(dag, "_bytes", guarded):
            with self.assertRaises(dag.DagHold):
                dag.preflight_json({key: 0}, limits=dag.DagLimits(max_expanded_bytes=32))

    def test_encoding_final_work_and_stricter_limits_before_exchange_copy(self):
        proof = dag.freeze_json([{ "x": "same"}] * 5)
        stats = proof.stats()
        expected = stats["charged_work_units"] + stats["encoding_work_upper_bound"]
        with patch.object(dag, "_record", side_effect=AssertionError("no final copy")):
            for limit in (dag.DagLimits(max_work_units=expected - 1),
                    dag.DagLimits(max_nodes=stats["table_nodes"] - 1),
                    dag.DagLimits(max_encoded_bytes=stats["encoded_bytes"] - 1),
                    dag.DagLimits(max_expanded_bytes=stats["expanded_bytes"] - 1)):
                with self.subTest(limit=limit):
                    with self.assertRaises(dag.DagHold):
                        dag.encode_proof(proof, limits=limit)

    def test_owned_proof_freeze_detaches_caller_and_encode_never_remeasures(self):
        value = [{"x": [1, 2]}, {"x": [1, 2]}]
        proof = dag.freeze_json(value)
        value[0]["x"][0] = 99
        with patch.object(dag, "_preflight", side_effect=AssertionError("no remeasurement")), \
                patch.object(dag, "_snapshot_visit", side_effect=AssertionError("no re-freeze")):
            handle = dag.encode_proof(proof)
        self.assertEqual(dag.decode_json(handle), [{"x": [1, 2]}, {"x": [1, 2]}])
        decoded = dag.proof_value_at(proof)
        decoded[0]["x"][0] = 88
        self.assertEqual(decoded[1]["x"], [1, 2])
        self.assertEqual(dag.proof_value_at(proof), [{"x": [1, 2]}, {"x": [1, 2]}])

    def test_same_size_snapshot_mutation_cannot_issue_proof(self):
        value = {"x": 1}
        actual = dag._snapshot_visit
        changed = False
        def altered(obj, depth, limits, state):
            nonlocal changed
            if not changed:
                changed = True
                obj["x"] = 2
            return actual(obj, depth, limits, state)
        with patch.object(dag, "_snapshot_visit", altered):
            with self.assertRaisesRegex(ValueError, "caller_input_changed"):
                dag.freeze_json(value)

    def test_foreign_summary_exchange_and_old_handles_never_proofs(self):
        proof = dag.freeze_json({"x": 1})
        handle = dag.encode_proof(proof)
        foreign = object.__new__(dag.JsonProof)
        for item in (foreign, proof.stats(), handle, handle.record(), json.loads(handle.json_bytes()),
                frozen.encode_json({"x": 1})):
            with self.subTest(item=type(item)):
                with self.assertRaises(ValueError):
                    dag.encode_proof(item)
                with self.assertRaises(ValueError):
                    dag.compose_proofs({"x": item})
        for cls in (dag.JsonProof, dag.JsonDag):
            with self.assertRaises(ValueError):
                cls()
        for owner in (proof, handle):
            with self.assertRaises(AttributeError):
                owner.changed = True

    def test_export_stats_and_decode_copies_are_independent(self):
        handle = dag.encode_json([{ "x": [1, 2]}] * 2)
        record = handle.record()
        record["nodes"].clear()
        stats = handle.stats()
        stats["expanded_bytes"] = 0
        result = dag.decode_json(handle)
        result[0]["x"][0] = 88
        self.assertEqual(result[1]["x"], [1, 2])
        self.assertEqual(dag.decode_json(handle), [{"x": [1, 2]}] * 2)

    def test_exact_paths_no_bool_alias_negative_index_or_subclass(self):
        proof = dag.freeze_json({"facets": [{"a": [[1, 2], [3, 4]]}]})
        handle = dag.encode_proof(proof)
        path = ("facets", 0, "a", 1)
        self.assertEqual(dag.value_at(handle, path), [3, 4])
        self.assertEqual(dag.proof_subtree_stats(proof, path)["expanded_bytes"], len(raw([3, 4])))
        for bad in (["facets"], ("facets", True), ("facets", -1), ("facets", 1), ("missing",)):
            with self.subTest(path=bad):
                with self.assertRaises(ValueError):
                    dag.value_at(handle, bad)
                with self.assertRaises(ValueError):
                    dag.proof_value_at(proof, bad)

    def test_compose_owned_snapshots_no_refreeze_and_multiplicity_exact(self):
        entries = dag.freeze_json([{ "source_note_ids": ["a", "a"]}] * 3)
        facets = dag.freeze_json([{"role": "unknown", "count": None}] * 3)
        with patch.object(dag, "_preflight", side_effect=AssertionError("no remeasurement")), \
                patch.object(dag, "_snapshot_visit", side_effect=AssertionError("no re-freeze")):
            proof = dag.compose_proofs({"entries": entries, "facets": facets, "again": entries})
        value = {"entries": dag.proof_value_at(entries), "facets": dag.proof_value_at(facets),
            "again": dag.proof_value_at(entries)}
        self.assertEqual(dag.proof_value_at(proof), value)
        self.assertEqual(proof.stats()["expanded_bytes"], len(raw(value)))
        self.assertEqual(proof.stats()["expanded_visits"], dag.preflight_json(value)["expanded_visits"])
        self.assertEqual(proof.stats()["inherited_proof_creation_work_units"],
            entries.stats()["charged_work_units"] + facets.stats()["charged_work_units"])
        self.assertEqual(proof.stats()["charged_work_units"],
            proof.stats()["inherited_proof_creation_work_units"] + proof.stats()["incremental_work_units"])
        direct = dag.encode_json(value)
        composed = dag.encode_proof(proof)
        self.assertEqual(composed.record(), direct.record())

    def test_compose_expansion_depth_and_work_gate_before_reindex(self):
        proof = dag.freeze_json(["payload"] * 20)
        size = len(raw({"a": dag.proof_value_at(proof), "b": dag.proof_value_at(proof)}))
        with patch.object(dag, "_append_node", side_effect=AssertionError("no reindex copy")):
            for limit in (dag.DagLimits(max_expanded_bytes=size - 1), dag.DagLimits(max_work_units=1),
                    dag.DagLimits(max_depth=1)):
                with self.subTest(limit=limit):
                    with self.assertRaises(dag.DagHold):
                        dag.compose_proofs({"a": proof, "b": proof}, limits=limit)

    def test_streamed_canonical_hash_exact_expanded_order_not_merkle_substitution(self):
        value = {"b": [{"q": "쉼표\n\x00"}] * 4, "a": [None, False, 0]}
        proof = dag.freeze_json(value)
        self.assertEqual(dag.proof_canonical_sha256(proof), hashlib.sha256(raw(value)).hexdigest())
        self.assertNotEqual(dag.proof_canonical_sha256(proof), proof.stats()["structural_sha256"])
        path = ("b", 3)
        self.assertEqual(dag.proof_canonical_sha256(proof, path), hashlib.sha256(raw(value["b"][3])).hexdigest())
        with patch.object(dag, "_hash_visit", side_effect=AssertionError("hash gate first")):
            with self.assertRaises(dag.DagHold):
                dag.proof_canonical_sha256(proof, limits=dag.DagLimits(max_work_units=1))

    def test_stream_hash_omits_top_keys_only_and_original_fields_remain(self):
        value = {"record_id": "r", "record_sha256": "digest", "body": {"record_id": "child",
            "record_sha256": "child-digest", "n": [None, 0]}}
        proof = dag.freeze_json(value)
        expected = hashlib.sha256(raw({"body": value["body"]})).hexdigest()
        self.assertEqual(dag.proof_canonical_sha256(proof,
            omit_root_keys=("record_id", "record_sha256")), expected)
        self.assertEqual(dag.proof_value_at(proof), value)
        for bad in (["record_id"], (True,), ("record_id", "record_id"), ("missing",)):
            with self.subTest(keys=bad):
                with self.assertRaises(ValueError):
                    dag.proof_canonical_sha256(proof, omit_root_keys=bad)

    def test_exchange_roundtrip_only_codec_authority_no_proof_creation(self):
        value = {"entries": [None, False, 0, {"source_refs": ["a", "a"]}]}
        original = dag.encode_json(value)
        baseline = len(dag._PROOFS)
        imported = dag.import_record(json.loads(original.json_bytes()))
        self.assertEqual(dag.decode_json(imported), value)
        self.assertEqual(imported.json_bytes(), original.json_bytes())
        self.assertEqual(imported.stats()["origin"], "validated_codec_exchange_not_domain_authority")
        self.assertEqual(len(dag._PROOFS), baseline)
        with self.assertRaises(ValueError):
            dag.encode_proof(imported)
        with self.assertRaises(ValueError):
            dag.import_record(frozen.encode_json(value).record())

    def test_exchange_closed_exact_schema_forward_duplicate_unreachable_and_types(self):
        base = dag.encode_json([0, 1]).record()
        malformed = []
        for change in (lambda r: r.update(authority="native"), lambda r: r.update(root=True),
                lambda r: r["nodes"][0].update(type="bool"),
                lambda r: r["nodes"][-1].update(children=[True, 1]),
                lambda r: r["nodes"][-1].update(children=[2]),
                lambda r: r["nodes"][1].update(value=0),
                lambda r: r["nodes"][-1].update(children=[0])):
            changed = deepcopy(base)
            change(changed)
            malformed.append(changed)
        for record in malformed:
            with self.subTest(record=record):
                with self.assertRaises(ValueError):
                    dag.import_record(record)

    def test_exchange_dictionary_pairs_duplicates_unsorted_subclasses(self):
        for pairs in ([["b", 0], ["a", 0]], [["a", 0], ["a", 0]]):
            record = {"schema_name": dag.SCHEMA_NAME, "schema_version": dag.VERSION, "root": 1,
                "nodes": [{"id": 0, "type": "int", "value": 0},
                    {"id": 1, "type": "dict", "children": pairs}]}
            with self.assertRaises(ValueError):
                dag.import_record(record)
        class Text(str): pass
        base = dag.encode_json(0).record()
        base["schema_version"] = Text(dag.VERSION)
        with self.assertRaises(ValueError):
            dag.import_record(base)
        base = dag.encode_json(0).record()
        with self.assertRaises(ValueError):
            dag.import_record({Text(key): value for key, value in base.items()})

    def test_import_work_is_incremental_and_expansion_bomb_before_decode(self):
        record = dag.encode_json(list(range(20))).record()
        with patch.object(dag, "_node_record", side_effect=AssertionError("work gate first")):
            with self.assertRaises(dag.DagHold):
                dag.import_record(record, limits=dag.DagLimits(max_work_units=1))
        nodes = [{"id": 0, "type": "int", "value": 0}]
        for i in range(1, 36):
            nodes.append({"id": i, "type": "list", "children": [i - 1, i - 1]})
        with patch.object(dag, "_decode_visit", side_effect=AssertionError("no decode")):
            with self.assertRaises(dag.DagHold):
                dag.import_record({"schema_name": dag.SCHEMA_NAME, "schema_version": dag.VERSION,
                    "root": 35, "nodes": nodes}, limits=dag.DagLimits(max_expanded_bytes=10000, max_input_visits=10000))

    def test_independent_work_cap_precedes_scalar_string_hash_and_copy(self):
        actual = dag._bytes
        for text, cap in (("long " * 20000, 1), ("\x00" * 20, 60), ("쉼" * 20, 40)):
            def no_large_copy(value):
                if value == text:
                    raise AssertionError("large scalar copied before work admission")
                return actual(value)
            with self.subTest(cap=cap), patch.object(dag, "_bytes", new=no_large_copy):
                with self.assertRaises(dag.DagHold):
                    dag.preflight_json(text, limits=dag.DagLimits(max_work_units=cap))
        with patch.object(dag, "_bytes", side_effect=AssertionError("huge integer copied")):
            with self.assertRaises(dag.DagHold):
                dag.preflight_json(1 << 500000, limits=dag.DagLimits(max_work_units=50))

    def test_incremental_measurement_work_stops_before_remaining_children(self):
        actual = dag._scalar
        calls = []
        def counted(value, limits):
            calls.append(value)
            return actual(value, limits)
        with patch.object(dag, "_scalar", new=counted):
            with self.assertRaises(dag.DagHold):
                dag.preflight_json(["x" * 100, 2, 3], limits=dag.DagLimits(max_work_units=105))
        self.assertEqual(calls, ["x" * 100])

    def test_exact_fragment_size_and_work_reserved_before_large_fragment_copy(self):
        value = "large " * 20000
        with patch.object(dag, "_node_record", side_effect=AssertionError("no encoded giant copy")):
            with self.assertRaises(dag.DagHold):
                dag.freeze_json(value, limits=dag.DagLimits(max_encoded_bytes=64))
        proof = dag.freeze_json([{ "\x00쉼": [None, True, 0]}] * 3)
        handle = dag.encode_proof(proof)
        self.assertEqual(proof.stats()["encoded_bytes"], len(handle.json_bytes()))
        self.assertGreater(proof.stats()["node_fragment_size_measurement_work_units"], 0)

    def test_compose_captured_fields_cannot_change_proven_roots_or_costs(self):
        first, second = dag.freeze_json([1]), dag.freeze_json([2, 3])
        fields = {"a": first}
        actual = dag._combine
        def mutate_after_capture(node, costs, limits):
            fields["a"] = second
            fields["extra"] = second
            return actual(node, costs, limits)
        with patch.object(dag, "_combine", new=mutate_after_capture):
            composed = dag.compose_proofs(fields)
        self.assertEqual(dag.proof_value_at(composed), {"a": [1]})
        self.assertEqual(composed.stats()["expanded_bytes"], len(raw({"a": [1]})))
        self.assertEqual(composed.stats()["structural_sha256"], dag.preflight_json({"a": [1]})["structural_sha256"])

    def test_signed_immutable_registry_state_rejects_copy_replace_and_foreign_spoof(self):
        proof = dag.freeze_json([None, False, 0])
        handle = dag.encode_proof(proof)
        for owner, registry, cls, action in ((proof, dag._PROOFS, dag.JsonProof, dag.proof_value_at),
                (handle, dag._DAGS, dag.JsonDag, dag.decode_json)):
            original = registry[owner]
            foreign = object.__new__(cls)
            registry[foreign] = original
            try:
                with self.assertRaisesRegex(ValueError, "state_binding"):
                    action(foreign)
                for damaged in ({"nodes": original.nodes}, replace(original, root=0),
                        replace(original, costs=tuple(reversed(original.costs))),
                        replace(original, seal="foreign")):
                    registry[owner] = damaged
                    with self.assertRaises(ValueError):
                        action(owner)
            finally:
                registry[owner] = original
                del registry[foreign]
            self.assertEqual(action(owner), [None, False, 0])


class LosslessJsonDagV2LifetimeControls(unittest.TestCase):
    def setUp(self):
        self.was_enabled = gc.isenabled()
        gc.disable()

    def tearDown(self):
        if self.was_enabled:
            gc.enable()

    def rows(self):
        return [{"source_ref": "source-" + str(i), "source_note_ids": ["a-" + str(i), "b-" + str(i)],
            "q": {"n": i % 16, "d": 1}, "padding": "common payload " * 12} for i in range(180)]

    def tracked(self, name, refs):
        actual = getattr(dag, name)
        def factory(*args, **kwargs):
            state = actual(*args, **kwargs)
            refs.append(weakref.ref(state))
            return state
        return patch.object(dag, name, factory)

    def held_error(self, action, expected):
        try:
            action()
        except expected as exc:
            return exc
        self.fail("expected held exception")

    def assert_banks_empty(self, refs):
        self.assertTrue(refs)
        for reference in refs:
            state = reference()
            if state is not None:
                for name in ("active", "memo", "nodes", "costs", "intern"):
                    if hasattr(state, name):
                        self.assertFalse(getattr(state, name), name)

    def assert_helper_temporaries_cleared(self, error):
        frame = error.__traceback__
        checked = 0
        while frame is not None:
            locals_ = frame.tb_frame.f_locals
            name = frame.tb_frame.f_code.co_name
            if name in ("_combine", "_append_node", "_snapshot_visit", "_fragment_size"):
                checked += 1
                if "node" in locals_:
                    self.assertIsNone(locals_["node"], name)
            if name in ("_scalar", "_string_bytes", "_issue") and "raw" in locals_:
                self.assertIsNone(locals_["raw"], name)
            frame = frame.tb_next
        self.assertGreater(checked, 0)

    def test_success_preflight_states_die_immediately_gc_disabled(self):
        refs = []
        with self.tracked("_ScanState", refs):
            for _ in range(4):
                dag.preflight_json(self.rows())
        self.assertEqual(len(refs), 4)
        self.assertTrue(all(reference() is None for reference in refs))

    def test_success_encode_and_decode_states_handles_die_gc_disabled(self):
        refs = []
        dag_count, proof_count = len(dag._DAGS), len(dag._PROOFS)
        with self.tracked("_BuildState", refs):
            handle = dag.encode_json(self.rows())
            handle_ref = weakref.ref(handle)
            result = dag.decode_json(handle)
            del result, handle
        self.assertTrue(all(reference() is None for reference in refs))
        self.assertIsNone(handle_ref())
        self.assertEqual(len(dag._DAGS), dag_count)
        self.assertEqual(len(dag._PROOFS), proof_count)

    def test_proof_and_composition_registry_no_self_key_strong_cycle(self):
        baseline = len(dag._PROOFS)
        proof = dag.freeze_json(self.rows())
        composed = dag.compose_proofs({"a": proof, "b": proof})
        refs = [weakref.ref(proof), weakref.ref(composed)]
        del proof, composed
        self.assertTrue(all(reference() is None for reference in refs))
        self.assertEqual(len(dag._PROOFS), baseline)

    def test_retained_preflight_hold_memo_cleared(self):
        refs = []
        with self.tracked("_ScanState", refs):
            error = self.held_error(lambda: dag.preflight_json(self.rows(),
                limits=dag.DagLimits(max_expanded_bytes=20000)), dag.DagHold)
        self.assert_banks_empty(refs)
        self.assertIsNotNone(error.__traceback__)

    def test_retained_preflight_value_error_memo_cleared(self):
        refs = []
        value = self.rows() + [1.5]
        with self.tracked("_ScanState", refs):
            error = self.held_error(lambda: dag.preflight_json(value), ValueError)
        self.assert_banks_empty(refs)
        self.assertEqual(value[-1], 1.5)
        self.assertIsNotNone(error.__traceback__)

    def test_retained_snapshot_hold_all_banks_and_new_vectors_cleared(self):
        refs = []
        with self.tracked("_BuildState", refs):
            error = self.held_error(lambda: dag.freeze_json(self.rows(),
                limits=dag.DagLimits(max_nodes=40)), dag.DagHold)
        self.assert_banks_empty(refs)
        self.assert_helper_temporaries_cleared(error)

    def test_retained_snapshot_keyboard_interrupt_banks_cleared(self):
        refs = []
        actual = dag._node_record
        def interrupted(index, node):
            if index == 40:
                raise KeyboardInterrupt("synthetic interruption")
            return actual(index, node)
        with self.tracked("_BuildState", refs), patch.object(dag, "_node_record", interrupted):
            error = self.held_error(lambda: dag.freeze_json(self.rows()), KeyboardInterrupt)
        self.assert_banks_empty(refs)
        self.assert_helper_temporaries_cleared(error)

    def test_retained_import_hold_error_and_interrupt_banks_cleared(self):
        base = dag.encode_json(self.rows()).record()
        refs = []
        with self.tracked("_BuildState", refs):
            hold = self.held_error(lambda: dag.import_record(base,
                limits=dag.DagLimits(max_work_units=1000)), dag.DagHold)
            changed = deepcopy(base)
            changed["nodes"][-1]["children"] = [len(changed["nodes"])]
            invalid = self.held_error(lambda: dag.import_record(changed), ValueError)
            with patch.object(dag, "_issue", side_effect=KeyboardInterrupt("synthetic import interrupt")):
                interrupted = self.held_error(lambda: dag.import_record(base), KeyboardInterrupt)
        self.assert_banks_empty(refs)
        self.assertTrue(all(exc.__traceback__ is not None for exc in (hold, invalid, interrupted)))

    def test_retained_final_exchange_error_does_not_retain_staged_proof_or_raw_copy(self):
        baseline = len(dag._PROOFS)
        actual = dag._bytes
        def failed_exchange(value):
            if type(value) is dict and "nodes" in value:
                raise ValueError("synthetic final exchange failure")
            return actual(value)
        with patch.object(dag, "_bytes", failed_exchange):
            error = self.held_error(lambda: dag.encode_json(self.rows()), ValueError)
        self.assertEqual(len(dag._PROOFS), baseline)
        frame = error.__traceback__
        while frame is not None:
            if frame.tb_frame.f_code.co_name == "_exchange_bytes":
                self.assertEqual(frame.tb_frame.f_locals["exchange"], {})
                self.assertIsNone(frame.tb_frame.f_locals["nodes"])
            frame = frame.tb_next

    def test_final_record_copy_interrupt_clears_owned_tuple_and_partial_records(self):
        proof = dag.freeze_json(self.rows())
        reference = weakref.ref(proof)
        actual = dag._node_record
        def interrupted(index, node):
            try:
                if index == 40:
                    raise KeyboardInterrupt("synthetic final record copy interrupt")
                return actual(index, node)
            finally:
                node = None
        with patch.object(dag, "_node_record", new=interrupted):
            error = self.held_error(lambda: dag.encode_proof(proof), KeyboardInterrupt)
        proof = None
        self.assertIsNone(reference())
        frame = error.__traceback__
        checked = 0
        while frame is not None:
            name = frame.tb_frame.f_code.co_name
            locals_ = frame.tb_frame.f_locals
            if name == "_record":
                checked += 1
                self.assertIsNone(locals_["nodes"])
                self.assertIsNone(locals_["node"])
                self.assertEqual(locals_["records"], [])
            frame = frame.tb_next
        self.assertEqual(checked, 1)

    def test_retained_decode_error_clears_partial_expanded_values(self):
        handle = dag.encode_json([{ "x": [1, 2]}] * 20)
        actual = dag._decode_visit
        calls = 0
        def interrupted(nodes, index):
            nonlocal calls
            calls += 1
            if calls == 12:
                raise KeyboardInterrupt("synthetic decode interrupt")
            return actual(nodes, index)
        with patch.object(dag, "_decode_visit", interrupted):
            error = self.held_error(lambda: dag.decode_json(handle), KeyboardInterrupt)
        frame = error.__traceback__
        checked = 0
        while frame is not None:
            if frame.tb_frame.f_code.co_name == "_decode_visit" and "result" in frame.tb_frame.f_locals:
                checked += 1
                self.assertFalse(frame.tb_frame.f_locals["result"])
            frame = frame.tb_next
        self.assertGreater(checked, 0)
        self.assertEqual(dag.decode_json(handle), [{"x": [1, 2]}] * 20)

    def test_saved_hash_interrupt_does_not_pin_new_owned_proof(self):
        baseline = len(dag._PROOFS)
        proof = dag.freeze_json(self.rows())
        reference = weakref.ref(proof)
        actual = dag._hash_visit
        calls = 0
        def interrupted(nodes, index, sha, omit_root_keys=()):
            nonlocal calls
            try:
                calls += 1
                if calls == 20:
                    raise KeyboardInterrupt("synthetic owned hash interrupt")
                return actual(nodes, index, sha, omit_root_keys)
            finally:
                nodes = sha = None
        with patch.object(dag, "_hash_visit", new=interrupted):
            error = self.held_error(lambda: dag.proof_canonical_sha256(proof), KeyboardInterrupt)
        proof = None
        self.assertIsNone(reference())
        self.assertEqual(len(dag._PROOFS), baseline)
        frame = error.__traceback__
        checked = 0
        while frame is not None:
            name = frame.tb_frame.f_code.co_name
            locals_ = frame.tb_frame.f_locals
            if name == "_hash_visit":
                checked += 1
                self.assertIsNone(locals_["nodes"])
                self.assertIsNone(locals_["content"])
            if name == "proof_canonical_sha256":
                self.assertIsNone(locals_["proof"])
                self.assertIsNone(locals_["data"])
            frame = frame.tb_next
        self.assertGreater(checked, 0)

    def test_saved_decode_interrupt_does_not_pin_new_owned_proof(self):
        baseline = len(dag._PROOFS)
        proof = dag.freeze_json(self.rows())
        reference = weakref.ref(proof)
        actual = dag._decode_visit
        calls = 0
        def interrupted(nodes, index):
            nonlocal calls
            try:
                calls += 1
                if calls == 20:
                    raise KeyboardInterrupt("synthetic owned decode interrupt")
                return actual(nodes, index)
            finally:
                nodes = None
        with patch.object(dag, "_decode_visit", new=interrupted):
            error = self.held_error(lambda: dag.proof_value_at(proof), KeyboardInterrupt)
        proof = None
        self.assertIsNone(reference())
        self.assertEqual(len(dag._PROOFS), baseline)
        frame = error.__traceback__
        while frame is not None:
            name = frame.tb_frame.f_code.co_name
            locals_ = frame.tb_frame.f_locals
            if name == "_decode_visit":
                self.assertIsNone(locals_["nodes"])
                self.assertIsNone(locals_["content"])
            if name in ("_value_at", "proof_value_at"):
                key = "data" if name == "_value_at" else "proof"
                self.assertIsNone(locals_[key])
            frame = frame.tb_next

    def test_saved_invalid_path_error_does_not_pin_new_owned_proof_or_dag(self):
        errors = []
        for action in (dag.proof_node_at, dag.proof_subtree_stats):
            proof = dag.freeze_json(self.rows())
            reference = weakref.ref(proof)
            errors.append(self.held_error(lambda: action(proof, ("missing",)), ValueError))
            proof = None
            self.assertIsNone(reference(), action.__name__)
        for action in (dag.node_at, dag.subtree_stats):
            handle = dag.encode_json(self.rows())
            reference = weakref.ref(handle)
            errors.append(self.held_error(lambda: action(handle, ("missing",)), ValueError))
            handle = None
            self.assertIsNone(reference(), action.__name__)
        self.assertTrue(all(error.__traceback__ is not None for error in errors))

    def test_recursive_workers_have_no_recursive_closure_cells_or_gc_calls(self):
        for name in ("_scan_visit", "_snapshot_visit", "_decode_visit", "_hash_visit"):
            worker = getattr(dag, name)
            self.assertEqual(worker.__code__.co_freevars, ())
            self.assertIsNone(worker.__closure__)
        self.assertNotIn("gc.collect", inspect.getsource(dag))

    def test_preflight_tracemalloc_does_not_accumulate_per_call_memos_gc_disabled(self):
        rows = self.rows()
        dag.preflight_json(rows)  # Warm Python/JSON allocations before measuring.
        tracemalloc.start()
        try:
            readings = []
            for _ in range(4):
                report = dag.preflight_json(rows)
                del report
                readings.append(tracemalloc.get_traced_memory()[0])
            self.assertLess(readings[-1] - readings[0], 32768, readings)
            self.assertLess(readings[-1], 65536, readings)
        finally:
            tracemalloc.stop()


if __name__ == "__main__":
    unittest.main()
