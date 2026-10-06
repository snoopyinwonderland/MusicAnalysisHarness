"""Applied-family evidence between adjacent common-catalog hypotheses.

No annotation, estimated key, winner, or automatic boundary is consumed. A key
may be supplied explicitly as a separate hypothesis for conditional projection.
"""
from copy import deepcopy
from .applied_chords import hypothesis
from .formal_ir import q
from .harmony_candidate_catalog import validate, resolve
from .harmony_joint import f
from .harmony_open_candidates import window
from .harmony_path_contrast import token
from .harmony_reading_voice_context import voice_links
from .harmony_voice_figures import octave_links
from .seventh_context import chord
from .tonal_foundations import scale_degree

VERSION = 'catalog-resolution-0.1.0'
FAMILY = {'major': 'V', 'dominant7': 'V7', 'diminished': 'vii',
          'diminished7': 'vii7', 'half-diminished7': 'vii_half7'}
ROMANS = ('I', 'II', 'III', 'IV', 'V', 'VI', 'VII')
PREFIX = {'V': 'V', 'V7': 'V7', 'vii': 'viio', 'vii7': 'viio7', 'vii_half7': 'viiø7'}


def pitch_pair(p):
    return [p['step'], int(f(p['alter']))]


def source_family(catalog, candidate):
    raw = resolve(catalog, candidate['origin_pointer'])
    if candidate['provider'] == 'base':
        return FAMILY.get(raw['label'].partition(':')[2])
    if candidate['provider'] == 'extended':
        return 'V7'  # Conditional on its underlying spelled dominant-seventh core.
    return None


def target_quality(alternative):
    root = alternative['root_spelling']
    if root is not None:
        for quality in ('M', 'm'):
            if alternative['members'][:3] == chord(root, quality)['members']:
                return quality
    return None


def keys_checked(keys):
    keys = list(keys)
    seen = set()
    for key in keys:
        if key['key_id'] in seen or not key.get('provenance'):
            raise ValueError('duplicate_or_unattributed_key_hypothesis')
        seen.add(key['key_id'])
        if key['mode'] not in ('major', 'minor'):
            raise ValueError('unsupported_key_mode')
        scale_degree(*key['tonic'], *key['tonic'])
    return deepcopy(list(keys))


def project(h, keys):
    result = []
    for key in keys:
        form = 'major' if key['mode'] == 'major' else 'natural_minor'
        coord = scale_degree(*h['target']['root'], *key['tonic'], form=form)
        alter = coord['alteration_from_scale']
        degree = ROMANS[coord['degree'] - 1]
        if h['target']['quality'] == 'm':
            degree = degree.lower()
        degree = ('#' * alter if alter > 0 else 'b' * -alter) + degree
        home_quality = 'M' if key['mode'] == 'major' else 'm'
        same_root = h['target']['root'] == key['tonic']
        kind = ('primary_target_hypothesis' if h['target']['quality'] == home_quality
                else 'parallel_tonic_target_hypothesis') if same_root else 'applied_target_hypothesis'
        chromatic = [p for p in h['chord']['members']
                     if not scale_degree(*p, *key['tonic'], form=form)['diatonic_to_candidate']]
        result.append({'key_hypothesis_ref': key['key_id'], 'target_coordinate': coord,
            'relation_to_key': kind, 'symbol_without_inversion': PREFIX[h['family']] + ('' if same_root else '/' + degree),
            'chromatic_core_spellings': chromatic, 'key_inferred': False,
            'chromatic_member_required_for_proposal': False, 'function_confirmed': False,
            'inversion_included': False})
    return result


def timing(catalog, candidate, alternative, required):
    base = catalog['providers']['base']
    cells = []
    for cell in base['cells']:
        groups = {role: [sid for sid in cell['event_refs']
                        if candidate['event_states'][sid] == 'member'
                        and pitch_pair(base['event_units'][sid]['pitch']) == pair]
                  for role, pair in required.items()}
        bass = []
        for sid in cell['bass_refs']:
            p = pitch_pair(base['event_units'][sid]['pitch'])
            members = alternative['members']
            bass.append({'event_ref': sid, 'spelling': p,
                         'member_index': members.index(p) if p in members else None})
        cells.append({'span': cell['span'], 'required_role_refs': groups,
                      'all_required_present': all(groups.values()), 'bass': bass})
    tail = []
    for cell in reversed(cells):
        if not cell['all_required_present']:
            break
        tail.insert(0, cell)
    return {'cells': cells, 'required_spellings': required,
            'terminal_support_span': {'start': tail[0]['span']['start'], 'end': tail[-1]['span']['end']} if tail else None,
            'terminal_support_is_harmony_span': False}


def compare(ir, left, right, reference_keys=()):
    """Preserve every candidate; relate spelled alternatives, then inspect time.

    Non-adjacent windows are rejected; repeats, silence and unsupported input
    block contextual conclusions but retain shape-only relationships explicitly.
    """
    keys = keys_checked(reference_keys)
    for catalog in (left, right):
        validate(catalog)
        if window(ir, catalog['span']) != catalog['providers']['base']:
            raise ValueError('catalog_does_not_match_score')
    boundary = f(left['span']['end'])
    if boundary != f(right['span']['start']):
        raise ValueError('adjacent_windows_required')
    context = {'start': left['span']['start'], 'end': right['span']['end']}
    barriers = set(window(ir, context)['abstention_reasons'])
    voices = voice_links(ir, context)
    octaves = octave_links(ir, context)
    links = [l for l in voices['links'] + octaves['links']
             if f(l['source_span']['end']) == boundary == f(l['target_span']['start'])]
    edges = []
    target_options = [(c, i, alt, target_quality(alt)) for c in right['candidates']
                      for i, alt in enumerate(c['spelling_alternatives']) if target_quality(alt)]
    for source in left['candidates']:
        family = source_family(left, source)
        if family is None:
            continue
        for si, sa in enumerate(source['spelling_alternatives']):
            for target, ti, ta, tq in target_options:
                h = hypothesis(ta['root_spelling'], tq, family)
                if sa['members'][:len(h['chord']['members'])] != h['chord']['members']:
                    continue
                required = {'leading_tone': h['leading_tone']}
                if len(h['chord']['members']) == 4:
                    required['seventh'] = h['chord']['members'][3]
                else:
                    required['identity_partner'] = h['chord']['members'][0 if family == 'V' else 2]
                source_time = timing(left, source, sa, required)
                target_time = timing(right, target, ta, {'root': ta['members'][0], 'third': ta['members'][1]})
                blockers = sorted(barriers | set(source['abstention_reasons']) | set(target['abstention_reasons']))
                supports = []
                if not blockers:
                    for link in links:
                        a, b = link['source_refs']
                        if source['event_states'].get(a) != 'member' or target['event_states'].get(b) != 'member':
                            continue
                        p1, p2 = pitch_pair(link['source_pitch']), pitch_pair(link['target_pitch'])
                        if p1 not in sa['members'] or p2 not in ta['members']:
                            continue
                        tags = []
                        if p1 == h['leading_tone'] and p2 == h['target']['root'] and link['semitones'] == 1 and link['diatonic_steps'] == 1:
                            tags.append('leading_tone_to_target_root')
                        if required.get('seventh') == p1 and link['semitones'] in (-1, -2) and link['diatonic_steps'] == -1:
                            tags.append('seventh_down_step_to_target_member')
                        if tags:
                            supports.append({'source_refs': link['source_refs'], 'relations': tags,
                                'source_pitch': link['source_pitch']['spelling'], 'target_pitch': link['target_pitch']['spelling'],
                                'link_status': link['status'], 'dependency_group': link.get('dependency_group'),
                                'source_note_refs': [left['providers']['base']['event_units'][a]['source_note_ids'],
                                                     right['providers']['base']['event_units'][b]['source_note_ids']]})
                tags = {tag for s in supports for tag in s['relations']}
                required_tags = {'leading_tone_to_target_root'}
                if 'seventh' in required:
                    required_tags.add('seventh_down_step_to_target_member')
                onset = target_time['cells'][0]['all_required_present']
                ready = not blockers and bool(source_time['terminal_support_span']) and onset and required_tags <= tags
                edges.append({'edge_id': 'catres_' + token([source['candidate_id'], si, target['candidate_id'], ti]),
                    'source_candidate_ref': source['candidate_id'], 'target_candidate_ref': target['candidate_id'],
                    'source_alternative_index': si, 'target_alternative_index': ti,
                    'source_provider': source['provider'], 'target_provider': target['provider'],
                    'family': family, 'target_root': h['target']['root'], 'target_quality': tq,
                    'textbook_profile': h['textbook_profile'],
                    'boundary': q(boundary), 'source_span': left['span'], 'target_span': right['span'],
                    'source_time': source_time, 'target_time': target_time,
                    'target_identity_at_boundary': onset, 'direct_voice_support': supports,
                    'missing_direct_relations': sorted(required_tags - tags),
                    'source_missing_spellings': source['missing_spellings_by_alternative'][si],
                    'target_missing_spellings': target['missing_spellings_by_alternative'][ti],
                    'abstention_reasons': blockers, 'key_projections': project(h, keys),
                    'status': 'blocked_context' if blockers else 'resolution_supported_hypothesis' if ready else 'shape_relation_only',
                    'selected': None, 'function_confirmed': False, 'cadence_confirmed': False})
    result = {'version': VERSION, 'span': context, 'catalog_window_refs': [c['providers']['base']['window_id'] for c in (left, right)],
        'candidate_refs': [[c['candidate_id'] for c in catalog['candidates']] for catalog in (left, right)],
        'reference_key_hypotheses': keys, 'edges': edges, 'voice_abstentions': voices['abstentions'],
        'source_labels_used': False, 'production_enabled': False, 'selected': None,
        'limits': ['All candidate origins survive; no absence-of-edge penalty or ranking.',
            'Applied-family relations cover ordinary and added-tone dominant cores; augmented-sixth evidence stays in its provider.',
            'Shape matching does not prove tonicization, modulation, cadence, local key or inversion.',
            'Terminal simultaneous support is conservative; distributed-only and delayed resolution remain open.',
            'Direct voice links use IR identity; octave groups and overlapping hypotheses are not independent votes.',
            'A supplied key is a conditional projection; key signatures and reference annotations are not inferred keys.']}
    return deepcopy(result)
