"""Read-only voice provenance; not a migration or melodic voice inference.

The legacy context search can return a Voice in an earlier measure. Structural
containment must stop at the current Measure. A collapsed single-voice measure
does not establish an XML voice number; only a verified XML locator can do so.
"""
from collections import Counter
from music21 import stream
from .canonical import _part_id, _staff_id, _voice_id, _iter_pitch_members, fraction, stable_id

VERSION = 'voice-provenance-0.1.0'


def containing_voice(element):
    """Inspect current active containment, never temporal context or old sites."""
    site = element.activeSite
    visited = set()
    while site is not None:
        if id(site) in visited:
            return {'voice': None, 'basis': 'containment_cycle'}
        visited.add(id(site))
        if isinstance(site, stream.Voice):
            # music21's default numeric object id is not a stable source voice.
            value = site.id
            if value == id(site):
                return {'voice': None, 'basis': 'unnamed_containing_voice'}
            return {'voice': str(value), 'basis': 'containing_voice'}
        if isinstance(site, stream.Measure):
            return {'voice': None, 'basis': 'no_voice_container_in_measure'}
        if isinstance(site, (stream.Part, stream.Score)):
            break
        site = site.activeSite
    return {'voice': None, 'basis': 'no_voice_container'}


def parser_voice_inventory(score):
    """Key observations by existing legacy segment fingerprints, without edits.

    This intentionally reproduces the legacy identity recipe. Audit callers
    must check its key set against a freshly built legacy IR before using it.
    Chord members share their containing Chord's voice; rests are not migrated.
    """
    parts = list(score.parts)
    raw = [_part_id(p, i) for i, p in enumerate(parts)]
    counts = Counter(raw)
    rows = {}
    for i, part in enumerate(parts):
        pid = raw[i] if counts[raw[i]] == 1 else f'{raw[i]}__part_{i + 1}'
        for ordinal, element in enumerate(part.recurse().notesAndRests):
            measure = element.getContextByClass(stream.Measure)
            if measure is None:
                continue
            old = _voice_id(element)
            info = containing_voice(element)
            for member, pitch, _tie in _iter_pitch_members(element):
                key = 'seg_' + stable_id(pid, _staff_id(part, element), old,
                    int(measure.number or 0), fraction(element.getOffsetInHierarchy(score)),
                    pitch.nameWithOctave, ordinal, member)
                if key in rows:
                    raise ValueError('duplicate_segment_fingerprint')
                rows[key] = {'legacy_context_voice': old, **info}
    return rows


def assess(old_voice, containment, xml_voice, verified):
    """Separate temporal leakage from importer collapse and actual conflicts."""
    parent = containment['voice']
    if not verified:
        category = 'unresolved_source_mapping'
    elif parent is not None:
        category = ('explicit_container_matches_xml' if parent == xml_voice
                    else 'explicit_container_xml_conflict')
    elif containment['basis'] != 'no_voice_container_in_measure':
        category = 'unknown_container'
    elif old_voice not in (None, '', 'voice_0'):
        category = 'context_voice_without_container'
    else:
        category = 'single_voice_container_absent'
    return {
        'category': category,
        'legacy_xml_disagreement': bool(verified and old_voice not in (None, '', 'voice_0')
                                        and xml_voice is not None and old_voice != xml_voice),
        # Number is source-part scoped, not a globally inferred melodic lane.
        'proposed_source_voice': xml_voice if verified else None,
        'proposal_basis': 'verified_xml_locator' if verified else 'abstain',
        'logical_voice_migration': 'not_applied',
    }
