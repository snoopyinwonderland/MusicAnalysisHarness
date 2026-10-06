"""Short-lived immutable-score geometry cache, never a harmonic-result cache.

Sessions guard the complete input at entry/exit. Outside a session every lookup
checks it. Cached observations come from a private full-score snapshot and are
returned as fresh copies; candidate/assignment/budget decisions are not cached.
"""
from collections import OrderedDict
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json

from .harmony_joint import f, VERSION as PREPARE_VERSION
from .harmony_reading_voice_context import (
    VERSION as GEOMETRY_VERSION, prepare_voice_geometry, voice_links_from_geometry,
)

VERSION = 'voice-geometry-cache-0.1.0'


def fingerprint(ir):
    return hashlib.sha256(json.dumps(ir, sort_keys=True, separators=(',', ':'),
                                    ensure_ascii=False, allow_nan=False).encode('utf-8')).hexdigest()


class VoiceGeometryCache:
    """One score, bounded exact-span LRU, no global or persistent shared state."""

    def __init__(self, ir, max_spans=128):
        if type(max_spans) is not int or max_spans < 1:
            raise ValueError('invalid_geometry_cache_size')
        self._snapshot = deepcopy(ir)
        self._hash = fingerprint(self._snapshot)
        self._version = (VERSION, GEOMETRY_VERSION, PREPARE_VERSION)
        self._max_spans = max_spans
        self._geometry = None
        self._entries = OrderedDict()
        self._bound = None
        self._hits = self._misses = self._prepares = self._evictions = 0

    def _check(self, ir):
        if fingerprint(ir) != self._hash:
            raise ValueError('geometry_cache_ir_changed')

    @contextmanager
    def scope(self, ir):
        """Do not release a computed result if the bound input changed in scope."""
        if self._bound is not None:
            raise ValueError('geometry_cache_nested_scope')
        self._check(ir)
        self._bound = ir
        try:
            yield self
        finally:
            self._bound = None
            self._check(ir)

    def voice_links(self, ir, context_span):
        if self._bound is not None:
            if ir is not self._bound:
                raise ValueError('geometry_cache_scope_input_mismatch')
        else:
            self._check(ir)
        # Preparation was before span validation in the uncached engine too.
        # Lazy preparation preserves pair-budget and earlier identity gates.
        if self._geometry is None:
            self._geometry = prepare_voice_geometry(self._snapshot)
            self._prepares += 1
        start, end = f(context_span['start']), f(context_span['end'])
        if start < 0 or end < start:
            raise ValueError('invalid_context_span')
        key = (self._hash, self._version, start, end)
        if key in self._entries:
            value = self._entries.pop(key)
            self._entries[key] = value
            self._hits += 1
        else:
            value = voice_links_from_geometry(self._geometry, deepcopy(context_span))
            self._entries[key] = value
            self._misses += 1
            if len(self._entries) > self._max_spans:
                self._entries.popitem(last=False)
                self._evictions += 1
        result = deepcopy(value)
        # Equivalent fractions share geometry, but source display/extra span
        # fields must remain exactly as supplied by this individual query.
        result['context_span'] = deepcopy(context_span)
        return result

    def stats(self):
        return {'version':VERSION, 'ir_sha256':self._hash,
                'geometry_versions':list(self._version), 'prepares':self._prepares,
                'span_hits':self._hits, 'span_misses':self._misses,
                'evictions':self._evictions, 'cached_spans':len(self._entries),
                'max_spans':self._max_spans, 'harmonic_results_cached':False}
