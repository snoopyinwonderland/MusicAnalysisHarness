"""Research-only static-input Voice lookup; production Canonical builder intact.

Keep music21's default context-site traversal, sort-position tests, derivation
sites and active-site return behavior. Only Voice trees of the same imported,
topologically immutable score are reused for the duration of one build.
"""
import hashlib
import inspect
from pathlib import Path

from music21 import base, stream
from music21.sites import SitesException

from .canonical import CanonicalIRBuilder, _voice_id
from .formal_ir import FormalIRAdapter
from .dcml_import import parse_score_without_imported_harmony
from .harmony_test_a import fraction
from .harmony_window_workspace import bind

VERSION = 'static-canonical-voice-context-0.1.0'
DEFAULT_CONTEXT_SHA = 'a9f4e0ac5912e9012177174d2a60d8c11289ded2b47dc1783eadb20545914e86'
RUNTIME_CONTEXT_SHA = hashlib.sha256(
    inspect.getsource(base.Music21Object.getContextByClass).encode()).hexdigest()


class VoiceLookup:
    """One serial, static imported-score lease. Never share across score builds."""
    def __init__(self):
        self.trees = {}
        self.calls = self.tree_builds = self.tree_hits = self.fallbacks = 0

    def tree(self, site, flatten):
        key = (site, flatten)
        if key not in self.trees:
            self.trees[key] = site.asTree(flatten=flatten, classList=(stream.Voice,))
            self.tree_builds += 1
        else:
            self.tree_hits += 1
        return self.trees[key]

    @staticmethod
    def well_formed(element, candidate, site):
        try:
            return element.sortTuple(site, raiseExceptionOnMiss=True) >= candidate.sortTuple(
                site, raiseExceptionOnMiss=True)
        except SitesException:
            return True

    def context(self, element):
        # This is the default AT_OR_BEFORE Voice case of the pinned installed
        # getContextByClass, NOT a replacement for general context lookup.
        if stream.Voice in element.classSet:
            return element
        for site, position, mode in element.contextSites(
                returnSortTuples=True, sortByCreationTime=False,
                followDerivation=True, priorityTargetOnly=False):
            flattenings = [False] if mode in ('elementsOnly', 'elementsFirst') else []
            if mode != 'elementsOnly':
                flattenings.append('semiFlat')
            for flatten in flattenings:
                node = self.tree(site, flatten).getNodeBefore(position)
                if node is not None and self.well_formed(element, node.payload, site):
                    try:
                        site.coreSelfActiveSite(node.payload)
                    except SitesException:
                        pass
                    return node.payload
            if mode != 'elementsOnly' and stream.Voice in site.classSet:
                return site
        return None

    def __call__(self, element):
        self.calls += 1
        if (RUNTIME_CONTEXT_SHA != DEFAULT_CONTEXT_SHA or
                type(element).getContextByClass is not base.Music21Object.getContextByClass):
            self.fallbacks += 1
            return _voice_id(element)
        voice = self.context(element)
        return str(voice.id) if voice is not None and voice.id is not None else 'voice_0'

    def receipt(self):
        return dict(version=VERSION, runtime_context_sha256=RUNTIME_CONTEXT_SHA,
            calls=self.calls, tree_builds=self.tree_builds, tree_hits=self.tree_hits,
            fallbacks=self.fallbacks, lease='one_serial_static_import',
            original_context_order=True, derivation_followed=True)


class ContextBuilder(CanonicalIRBuilder):
    def build(self, score, source):
        lookup = VoiceLookup()
        try:
            return bind(CanonicalIRBuilder.build, {'_voice_id': lookup})(self, score, source)
        finally:
            self.lookup_receipt = lookup.receipt()
            lookup.trees.clear()  # no retained music21 object graph beyond build


def read_score(path, *, receipt=None):
    path = Path(path)
    score, removed, _ = parse_score_without_imported_harmony(path)
    builder = ContextBuilder()
    ir = FormalIRAdapter().convert(builder.build(score, path), path)
    if receipt is not None:
        receipt.update(builder.lookup_receipt)
    total = max([fraction(ir['score']['duration_quarters'])] +
        [fraction(m['global_start_quarter']) + fraction(m['actual_duration_quarter'])
         for m in ir['measures']])
    if total <= 0:
        raise ValueError('empty_score')
    return ir, total, removed
