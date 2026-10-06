"""Exact, source-bound window reuse for the pinned research candidate graph.

No provider globals are patched. Private function bindings reuse the existing
code objects with only their window/catalog dependencies redirected. This is
an experimental adapter, not a new candidate algorithm or production engine.
"""
from collections import OrderedDict
from copy import deepcopy
from types import FunctionType

from . import harmony_augmented_candidates as augmented
from . import harmony_extended_candidates as extended
from . import harmony_candidate_catalog as catalog
from . import harmony_bounded_recovery as bounded
from . import harmony_batched_frontier as frontier
from .harmony_open_candidates import window
from .harmony_progression_search import _hash

VERSION = "harmony-window-workspace-0.1.0"


def bind(original, replacements):
    """Separate global dictionary, original bytecode/defaults/closure.

    Fail closed when a named dependency disappears. No module attribute or
    original globals dictionary is changed, including on exceptions.
    """
    if not isinstance(original, FunctionType):
        raise ValueError("unsupported_binding_callable")
    if not set(replacements) <= set(original.__code__.co_names):
        raise ValueError("binding_dependency_not_used")
    env = dict(original.__globals__)
    if not set(replacements) <= env.keys():
        raise ValueError("binding_dependency_missing")
    env.update(replacements)
    result = FunctionType(original.__code__, env, original.__name__,
                          original.__defaults__, original.__closure__)
    result.__kwdefaults__ = original.__kwdefaults__
    return result


class WindowWorkspace:
    """One immutable source lease; exact-span LRU, never an event projection.

    The full IR is hashed before/after each public operation. A detected source
    mutation invalidates the lease and discards cached evidence. Inside a graph
    build the source must be treated as immutable, just as in the old provider.
    Every window handed to a provider is a defensive copy. Eviction changes
    computation counts only; it cannot prune any musical candidate.
    """
    def __init__(self, ir, *, max_entries=8):
        if type(max_entries) is not int or max_entries < 1:
            raise ValueError("invalid_cache_entry_budget")
        self.ir = ir
        self.source_sha256 = _hash(ir)
        self.max_entries = max_entries
        self.cache = OrderedDict()
        self.valid = True
        self.stats = {"window_requests": 0, "window_computations": 0,
                      "cache_hits": 0, "evictions": 0, "peak_entries": 0}
        aug = bind(augmented.propose, {"window": self._window})
        ext = bind(extended.propose, {"window": self._window})
        self._catalog = bind(catalog.propose, {"augmented": aug, "extended": ext})
        self._build = bind(bounded.build_problem, {"propose": self._catalog})

    def check_source(self):
        if not self.valid or _hash(self.ir) != self.source_sha256:
            self.valid = False
            self.cache.clear()
            raise ValueError("workspace_source_changed")

    def _window(self, ir, span):
        if not self.valid or ir is not self.ir:
            raise ValueError("workspace_foreign_source")
        # Preserve even the original fraction representation and extra fields:
        # window() returns span verbatim, so numerical equivalence is not enough.
        key = _hash(span)
        self.stats["window_requests"] += 1
        if key in self.cache:
            self.stats["cache_hits"] += 1
            value = self.cache.pop(key)
            self.cache[key] = value
        else:
            value = window(ir, span)
            self.stats["window_computations"] += 1
            self.cache[key] = deepcopy(value)
            if len(self.cache) > self.max_entries:
                self.cache.popitem(last=False)
                self.stats["evictions"] += 1
            self.stats["peak_entries"] = max(self.stats["peak_entries"], len(self.cache))
        return deepcopy(value)

    def propose(self, span, context_span=None):
        self.check_source()
        try:
            return self._catalog(self.ir, span, context_span)
        finally:
            self.check_source()

    def build(self, plan, evidence):
        self.check_source()
        try:
            return self._build(self.ir, plan, evidence)
        finally:
            self.check_source()

    def receipt(self):
        self.check_source()
        return {"version": VERSION, "source_ir_sha256": self.source_sha256,
                "max_cache_entries": self.max_entries, **self.stats,
                "original_function_code_reused": True, "provider_globals_modified": False,
                "full_source_preserved": True, "candidate_pruning": False,
                "weights_changed": False, "production_modified": False}


def infer(ir, sample):
    """Same graph, same scores, same factorized decoder; only window reuse."""
    before = _hash(ir)
    view, grace = bounded.grace_projection(ir)
    permissible = {"nonpositive_duration"} if grace["grace_sounding_events"] else set()
    remaining = sorted(set(sample.get("abstention_reasons", [])) - permissible)
    plan = bounded.tile_plan(view, sample["span"])
    if remaining:
        plan.update(status="sample_scope_abstention", blockers=remaining)
    ev, functional, links = bounded.bound_evidence(view, sample["span"], grace)
    workspace = WindowWorkspace(view)
    graph, origins = workspace.build(plan, ev)
    graph, receipts = frontier.supply(graph, functional)
    chosen = frontier.decode(graph, functional, transition_budget=frontier.CONFIG["decoder_transition_budget"])
    if _hash(ir) != before or _hash(view) != grace["consumer_view_sha256"]:
        raise ValueError("workspace_inference_mutated_inputs")
    return {"version": VERSION, "status": chosen["status"], "selected_prediction": chosen["selected"],
            "transitions": chosen["transitions"],
            "exact_optimum_under_declared_graph": chosen["exact_optimum_under_declared_score"],
            "search_diagnostics": chosen["search_diagnostics"], "grace_projection": grace,
            "tile_plan": plan, "link_withholding": links, "lattice_edge_count": len(graph.edges),
            "functional_candidate_receipts": receipts, "candidate_origin_groups": origins,
            "window_reuse": workspace.receipt(), "source_labels_used_at_inference": False,
            "production_modified": False, "formal_core_modified": False}, graph
