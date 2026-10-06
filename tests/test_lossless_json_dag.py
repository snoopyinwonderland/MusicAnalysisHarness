"""Lossless structural codec controls; no archive or musical authority."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import hashlib
import json
import unittest
from unittest.mock import patch

from musicanote_harness import lossless_json_dag as dag


class LosslessJsonDagControls(unittest.TestCase):
    def raw(self, value):
        return json.dumps(value, ensure_ascii=False, sort_keys=True,
            separators=(",", ":"), allow_nan=False).encode("utf-8")

    def test_all_plain_types_unicode_spelling_aliases_and_ordinals_roundtrip(self):
        value = {"entries": [None, True, False, 0, 1, -3, "F#4", "Gb4", "쉼표 ♭",
            {"source_note_ids": ["note-a", "note-a", "alias-b"], "start": {"n": 0, "d": 1}}],
            "q0": {"n": 0, "d": 1}, "empty_dict": {}, "empty_list": []}
        handle = dag.encode_json(value)
        result = dag.decode_json(handle)
        self.assertEqual(result, value)
        self.assertIs(type(result["entries"][1]), bool)
        self.assertIs(type(result["entries"][3]), int)
        self.assertEqual(result["entries"][9]["source_note_ids"], ["note-a", "note-a", "alias-b"])
        self.assertEqual(handle.stats()["expanded_bytes"], len(self.raw(value)))
        self.assertEqual(handle.stats()["codec_sha256"], hashlib.sha256(handle.json_bytes()).hexdigest())
        self.assertTrue(handle.stats()["original_logical_occurrences_preserved"])

    def test_repeated_rows_share_representation_not_occurrences(self):
        row = {"source_note_ids": ["note-1", "note-2"], "relation": "descending_resolution",
            "part_id": "part-1", "payload": "repeated evidence " * 60}
        value = {"entries": [{"selector_index": i, "row": deepcopy(row)} for i in range(50)]}
        handle = dag.encode_json(value)
        self.assertLess(handle.stats()["encoded_bytes"], len(self.raw(value)))
        self.assertEqual(len(dag.value_at(handle, ("entries",))), 50)
        self.assertEqual(dag.node_at(handle, ("entries", 0, "row")), dag.node_at(handle, ("entries", 49, "row")))
        self.assertNotEqual(dag.node_at(handle, ("entries", 0)), dag.node_at(handle, ("entries", 49)))
        self.assertEqual([dag.value_at(handle, ("entries", i, "selector_index")) for i in range(50)], list(range(50)))

    def test_same_source_different_request_roots_not_merged(self):
        value = [{"source_ref": "src", "completion_request_ref": "request-a", "selector_indices": [0, 2]},
            {"source_ref": "src", "completion_request_ref": "request-b", "selector_indices": [0, 2]}]
        handle = dag.encode_json(value)
        self.assertNotEqual(dag.node_at(handle, (0,)), dag.node_at(handle, (1,)))
        self.assertEqual(dag.node_at(handle, (0, "source_ref")), dag.node_at(handle, (1, "source_ref")))
        self.assertEqual(dag.decode_json(handle), value)

    def test_bool_integer_null_and_q0_never_coalesce(self):
        handle = dag.encode_json([False, 0, True, 1, None, {"n": 0, "d": 1}])
        self.assertEqual(len({dag.node_at(handle, (i,)) for i in range(6)}), 6)
        self.assertEqual([dag.subtree_stats(handle, (i,))["type"] for i in range(6)],
            ["bool", "int", "bool", "int", "null", "dict"])

    def test_dictionary_semantic_order_canonical_list_order_preserved(self):
        a = dag.encode_json({"b": [2, 1], "a": 0})
        b = dag.encode_json({"a": 0, "b": [2, 1]})
        c = dag.encode_json({"a": 0, "b": [1, 2]})
        self.assertEqual(a.json_bytes(), b.json_bytes())
        self.assertNotEqual(a.json_bytes(), c.json_bytes())
        self.assertEqual(list(dag.decode_json(a)), ["a", "b"])

    def test_floats_nonfinite_subclasses_and_nonstring_keys_rejected(self):
        class Integer(int):
            pass
        class List(list):
            pass
        class Dict(dict):
            pass
        class Text(str):
            pass
        for value in (1.0, float("nan"), float("inf"), Integer(1), List([1]), Dict(a=1),
                Text("x"), {1: "x"}, {Text("x"): 1}, b"x", (1, 2), "\ud800"):
            with self.subTest(value=repr(value)):
                with self.assertRaises(ValueError):
                    dag.encode_json(value)

    def test_cycles_rejected_before_table_encoding(self):
        a = []
        a.append(a)
        b = {"child": None}
        b["child"] = b
        for value in (a, b):
            with patch.object(dag, "_issue", side_effect=AssertionError("no issued table")):
                with self.assertRaisesRegex(ValueError, "cyclic"):
                    dag.encode_json(value)

    def test_python_alias_DAG_exponential_expansion_rejected_before_intern(self):
        value = [0]
        for _ in range(35):
            value = [value, value]
        limits = dag.DagLimits(max_expanded_bytes=10000, max_input_visits=10000)
        with patch.object(dag, "_issue", side_effect=AssertionError("no table serialization")):
            with self.assertRaises(dag.DagHold) as exc:
                dag.encode_json(value, limits=limits)
        self.assertIn("logical_expanded", str(exc.exception))
        self.assertTrue(any("lower_bound" in key for key in exc.exception.diagnostics))

    def test_preflight_exact_logical_bytes_visits_depth_and_multiplicity(self):
        shared = {"x": [1, True]}
        value = [shared, shared]
        report = dag.preflight_json(value)
        self.assertEqual(report["expanded_bytes"], len(self.raw(value)))
        self.assertEqual(report["expanded_visits"], 11)  # list + 2*(dict + key + list + two scalars)
        self.assertEqual(report["depth"], 4)
        self.assertLess(report["visited_input_values_and_keys"], report["expanded_visits"])
        self.assertEqual(report["charged_work_units"], report["expanded_bytes"] + report["expanded_visits"])
        handle = dag.encode_json(value)
        self.assertEqual(report["structural_sha256"], handle.stats()["structural_sha256"])

    def test_expanded_bytes_visits_depth_work_and_encoded_table_caps(self):
        value = ["long text", {"x": 3}]
        report = dag.preflight_json(value)
        limits = [dag.DagLimits(max_expanded_bytes=report["expanded_bytes"] - 1),
            dag.DagLimits(max_input_visits=report["expanded_visits"] - 1),
            dag.DagLimits(max_depth=1), dag.DagLimits(max_work_units=1),
            dag.DagLimits(max_nodes=1), dag.DagLimits(max_encoded_bytes=20)]
        for limit in limits:
            with self.subTest(limits=limit):
                with self.assertRaises(dag.DagHold):
                    dag.encode_json(value, limits=limit)

    def test_known_three_pass_work_hold_before_intern_or_exchange_serialization(self):
        value = {"entries": [{"source_ref": "same"}] * 20}
        one_pass = dag.preflight_json(value)["charged_work_units"]
        with patch.object(dag, "_node_record", side_effect=AssertionError("no intern serialization")):
            with self.assertRaises(dag.DagHold) as exc:
                dag.encode_json(value, limits=dag.DagLimits(max_work_units=2 * one_pass))
        self.assertEqual(exc.exception.diagnostics["charged_work_units_lower_bound"], 3 * one_pass)

    def test_oversized_escaped_dictionary_key_holds_before_copied_JSON_encoding(self):
        key = "\x00" * 8
        original = dag._bytes
        def guarded(value):
            if value == key:
                raise AssertionError("oversized key cannot reach JSON copying")
            return original(value)
        with patch.object(dag, "_bytes", guarded):
            with self.assertRaises(dag.DagHold):
                dag.preflight_json({key: 0}, limits=dag.DagLimits(max_expanded_bytes=32))

    def test_final_exchange_work_and_size_are_reserved_before_full_copy(self):
        value = [{"x": "same"}] * 5
        handle = dag.encode_json(value)
        stats = handle.stats()
        expected = stats["reserved_input_guard_and_intern_work_units"] + \
            stats["node_fragment_serialization_work_units"] + stats["encoded_bytes"]
        self.assertEqual(stats["charged_work_units"], expected)
        original = dag._record
        with patch.object(dag, "_record", side_effect=AssertionError("no final full-table copy")):
            with self.assertRaises(dag.DagHold):
                dag.encode_json(value, limits=dag.DagLimits(max_work_units=expected - 1))

    def test_limits_exact_int_and_owned_handles_no_foreign_authority(self):
        for value in (True, 1.5, -1):
            with self.assertRaises(ValueError):
                dag.DagLimits(max_nodes=value)
        with self.assertRaises(ValueError):
            dag.DagLimits(max_depth=257)
        with self.assertRaises(ValueError):
            dag.JsonDag()
        foreign = object.__new__(dag.JsonDag)
        for action in (lambda: foreign.record(), lambda: foreign.stats(), lambda: dag.decode_json(foreign),
                lambda: dag.node_at(foreign, ())):
            with self.assertRaises(ValueError):
                action()

    def test_export_and_decoded_values_are_independent_no_alias_mutation(self):
        original = [{"x": [1, 2]}, {"x": [1, 2]}]
        handle = dag.encode_json(original)
        original[0]["x"][0] = 99
        record = handle.record()
        record["nodes"].clear()
        decoded = dag.decode_json(handle)
        decoded[0]["x"][0] = 88
        self.assertEqual(decoded[1]["x"], [1, 2])
        self.assertEqual(dag.decode_json(handle), [{"x": [1, 2]}, {"x": [1, 2]}])
        with self.assertRaises(AttributeError):
            handle.changed = True

    def test_value_at_and_stats_path_are_exact_no_bool_or_negative_index(self):
        handle = dag.encode_json({"facets": [{"source_segments": {"sid": [[1, 2], [3, 4]]}}]})
        path = ("facets", 0, "source_segments", "sid", 1)
        self.assertEqual(dag.value_at(handle, path), [3, 4])
        self.assertEqual(dag.subtree_stats(handle, path)["expanded_bytes"], len(self.raw([3, 4])))
        for path in (["facets"], ("facets", True), ("facets", -1), ("facets", 1), ("missing",),
                ("facets", 0, "source_segments", 0)):
            with self.assertRaises(ValueError):
                dag.value_at(handle, path)

    def test_codec_exchange_roundtrip_still_only_structural_authority(self):
        value = {"entries": [None, False, 0, {"source_refs": ["a", "a"]}]}
        original = dag.encode_json(value)
        exchange = json.loads(original.json_bytes())
        imported = dag.import_record(exchange)
        self.assertEqual(dag.decode_json(imported), value)
        self.assertEqual(imported.json_bytes(), original.json_bytes())
        self.assertEqual(imported.stats()["origin"], "validated_codec_exchange_not_domain_authority")
        self.assertTrue(imported.stats()["codec_authority_only_not_archive_or_music"])

    def test_exchange_closed_schema_types_forward_dangling_duplicate_unreachable(self):
        base = dag.encode_json([0, 1]).record()
        malformed = []
        changed = deepcopy(base)
        changed["authority"] = "native"
        malformed.append(changed)
        changed = deepcopy(base)
        changed["root"] = True
        malformed.append(changed)
        changed = deepcopy(base)
        changed["nodes"][0]["type"] = "bool"
        malformed.append(changed)
        changed = deepcopy(base)
        changed["nodes"][-1]["children"] = [True, 1]
        malformed.append(changed)
        changed = deepcopy(base)
        changed["nodes"][-1]["children"] = [2]
        malformed.append(changed)
        changed = deepcopy(base)
        changed["nodes"][1]["value"] = 0
        malformed.append(changed)
        changed = deepcopy(base)
        changed["nodes"][-1]["children"] = [0]
        malformed.append(changed)
        for record in malformed:
            with self.subTest(record=record):
                with self.assertRaises(ValueError):
                    dag.import_record(record)

    def test_exchange_dictionary_duplicates_or_unsorted_keys_rejected(self):
        for pairs in ([["b", 0], ["a", 0]], [["a", 0], ["a", 0]]):
            record = {"schema_name": dag.SCHEMA_NAME, "schema_version": dag.VERSION, "root": 1,
                "nodes": [{"id": 0, "type": "int", "value": 0},
                    {"id": 1, "type": "dict", "children": pairs}]}
            with self.assertRaises(ValueError):
                dag.import_record(record)

    def test_exchange_header_and_schema_keys_cannot_use_subclasses(self):
        class Text(str):
            pass
        base = dag.encode_json(0).record()
        changed = deepcopy(base)
        changed["schema_version"] = Text(dag.VERSION)
        with self.assertRaises(ValueError):
            dag.import_record(changed)
        changed = {Text(key): value for key, value in base.items()}
        with self.assertRaises(ValueError):
            dag.import_record(changed)

    def test_import_work_hold_is_incremental_not_after_complete_exchange(self):
        record = dag.encode_json(list(range(20))).record()
        actual = dag._node_record
        calls = []
        def counted(index, node):
            calls.append(index)
            return actual(index, node)
        with patch.object(dag, "_node_record", counted):
            with self.assertRaises(dag.DagHold):
                dag.import_record(record, limits=dag.DagLimits(max_work_units=1))
        self.assertLessEqual(len(calls), 1)

    def test_exchange_exponential_bomb_rejected_before_decode(self):
        nodes = [{"id": 0, "type": "int", "value": 0}]
        for i in range(1, 36):
            nodes.append({"id": i, "type": "list", "children": [i - 1, i - 1]})
        record = {"schema_name": dag.SCHEMA_NAME, "schema_version": dag.VERSION, "root": 35, "nodes": nodes}
        with self.assertRaises(dag.DagHold):
            dag.import_record(record, limits=dag.DagLimits(max_expanded_bytes=10000, max_input_visits=10000))

    def test_input_mutation_between_guard_passes_cannot_issue(self):
        value = {"x": 1}
        real_preflight = dag._preflight
        calls = []
        def altered(obj, limits):
            calls.append(1)
            if len(calls) == 2:
                obj["x"] = 2  # Same bytes/visits; structural SHA must detect it.
            return real_preflight(obj, limits)
        with patch.object(dag, "_preflight", altered):
            with self.assertRaisesRegex(ValueError, "caller_input_changed"):
                dag.encode_json(value)

    def test_empty_container_and_scalar_root_costs(self):
        for value in ({}, [], None, "", -5, True):
            handle = dag.encode_json(value)
            self.assertEqual(dag.decode_json(handle), value)
            self.assertEqual(handle.stats()["expanded_bytes"], len(self.raw(value)))
            self.assertEqual(dag.preflight_json(value)["expanded_visits"], 1)


if __name__ == "__main__":
    unittest.main()
