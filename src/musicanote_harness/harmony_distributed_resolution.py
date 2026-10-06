"""Conservative temporal witnesses, alongside (never replacing) direct queries.

No chord/key selection: complete spelled membership through time plus a jointly
possible same-lane resolution is evidence, not proof of a single harmony.
"""
from collections import defaultdict
from copy import deepcopy
from .harmony_joint import f
from .harmony_catalog_resolution import pitch_pair
from .harmony_reading_voice_context import spelled_height
from .harmony_resolution_constraints import analyze as direct
from .harmony_voice_paths import partition
from .applied_chords import hypothesis

VERSION = 'distributed-resolution-0.1.0'


def profile(events, reading):
    start, end = f(reading['span']['start']), f(reading['span']['end'])
    sounds = [s for s in events.values() if f(s['span']['start']) < end and f(s['span']['end']) > start]
    members = {tuple(m) for m in reading['members']}
    refs = {str(m): sorted(s['sounding_event_id'] for s in sounds if tuple(pitch_pair(s['pitch'])) == m)
            for m in sorted(members)}
    foreign = sorted(s['sounding_event_id'] for s in sounds if tuple(pitch_pair(s['pitch'])) not in members)
    points = sorted({start, end} | {max(start, f(s['span']['start'])) for s in sounds}
                    | {min(end, f(s['span']['end'])) for s in sounds})
    gaps = [[str(a), str(b)] for a, b in zip(points, points[1:])
            if not any(f(s['span']['start']) < b and f(s['span']['end']) > a for s in sounds)]
    return {'member_event_refs': refs, 'missing_members': [list(m) for m in sorted(members) if not refs[str(m)]],
            'unexplained_event_refs': foreign, 'silence_spans_quarters': gaps}


def joint_paths(groups, required_covered, budget):
    """One nonbranching, nonmerging path per obligation; no foreign note ignored."""
    checks = 0
    exhausted = False
    tags = sorted(groups)

    def visit(index, chosen, edges, covered):
        nonlocal checks, exhausted
        if index == len(tags):
            return chosen if required_covered <= covered else None
        for option in groups[tags[index]]:
            if checks >= budget:
                exhausted = True
                return None
            checks += 1
            new = {tuple(e) for e in option['links']}
            union = edges | new
            if len({a for a, b in union}) != len(union) or len({b for a, b in union}) != len(union):
                continue
            found = visit(index + 1, chosen + [option], union, covered | set(option['carried_event_refs']))
            if found is not None or exhausted:
                return found
        return None

    selected = visit(0, [], set(), set())
    return {'status': 'temporal_resolution_possible' if selected is not None else
            'query_budget_abstention' if exhausted else 'no_joint_temporal_witness',
            'witness': selected, 'joint_checks': checks}


def analyze(result, path, assignment_ref, ir, path_budget=4096, query_budget=4096,*,geometry_cache=None):
    for n in (path_budget, query_budget):
        if type(n) is not int or n < 1:
            raise ValueError('invalid_temporal_budget')
    # Validates full IR identity, positive timing, lane metadata and path contract.
    base = direct(result, path, assignment_ref, ir,geometry_cache=geometry_cache)
    out = {**base, 'temporal_version': VERSION, 'temporal_queries': []}
    if base['status'] != 'ready':
        return out
    events = {s['sounding_event_id']: s for s in result['events']}
    graph = defaultdict(list)
    for x, y in base['local_link_candidates']:
        graph[x].append(y)
    readings = [result['edges'][p['edge']]['readings'][p['reading']] for p in path]
    for rel in base['strict_explicit_result']['relations']:
        i, j = rel['source_path_index'], rel['target_path_index']
        q = {k: deepcopy(rel[k]) for k in ('source_path_index', 'target_path_index', 'family', 'target_quality')}
        q.update(function_confirmed=False, selected=False, witness_is_preferred=False)
        out['temporal_queries'].append(q)
        if rel['candidate_blockers']:
            q.update(status='blocked_context', blockers=rel['candidate_blockers'])
            continue
        if j != i + 1:
            q.update(status='nonadjacent_temporal_query_not_applicable')
            continue
        source, target = readings[i], readings[j]
        sp, tp = profile(events, source), profile(events, target)
        q.update(source_profile=sp, target_profile=tp)
        # A wide-window pitch union is never sufficient: no unexplained source
        # pitches or silence; target foreign sounds must belong to carried paths.
        blockers = []
        if sp['missing_members'] or tp['missing_members']: blockers.append('incomplete_spelled_identity')
        if sp['unexplained_event_refs']: blockers.append('source_nonmember_requires_separate_nct_evidence')
        if sp['silence_spans_quarters'] or tp['silence_spans_quarters']: blockers.append('silence_breaks_temporal_support')
        if blockers:
            q.update(status='temporal_identity_abstention', reasons=blockers)
            continue
        h = hypothesis(rel['target_root'], rel['target_quality'], rel['family'])
        roles = {'leading_tone_to_target_root': h['leading_tone']}
        if len(h['chord']['members']) == 4:
            roles['seventh_down_step_to_target_member'] = h['chord']['members'][3]
        groups = {tag: [] for tag in roles}
        cut, stop = f(source['span']['end']), f(target['span']['end'])
        start = f(source['span']['start'])
        steps_checked = 0
        exhausted = False
        for tag, pitch in roles.items():
            for sid, sound in sorted(events.items()):
                if pitch_pair(sound['pitch']) != pitch or not f(sound['span']['start']) < cut or f(sound['span']['end']) <= start:
                    continue
                stack = [[sid]]
                while stack and not exhausted:
                    chain = stack.pop()
                    for dest in graph[chain[-1]]:
                        if steps_checked >= path_budget:
                            exhausted = True
                            break
                        steps_checked += 1
                        d = events[dest]
                        at = f(d['span']['start'])
                        if at >= stop:
                            continue
                        p = pitch_pair(d['pitch'])
                        semitones = d['pitch']['midi_pitch'] - sound['pitch']['midi_pitch']
                        heights = (spelled_height(sound['pitch']), spelled_height(d['pitch']))
                        if None in heights: continue
                        steps = heights[1] - heights[0]
                        if p == pitch and semitones == 0:
                            stack.append(chain + [dest])
                            continue
                        if at < cut: continue
                        matches = (p == rel['target_root'] and semitones == 1 and steps == 1) if tag == 'leading_tone_to_target_root' else (
                            p in target['members'] and semitones in (-1, -2) and steps == -1)
                        if matches:
                            full = chain + [dest]
                            groups[tag].append({'relation': tag, 'source_ref': sid, 'target_ref': dest,
                                'arrival': deepcopy(d['span']['start']), 'delayed': at > cut,
                                'carried_event_refs': chain, 'links': [list(e) for e in zip(full, full[1:])]})
        q.update(required_path_options=groups, path_steps_checked=steps_checked)
        if exhausted:
            q.update(status='path_budget_abstention', witness=None)
            continue
        q.update(joint_paths(groups, set(tp['unexplained_event_refs']), query_budget))
        if q['witness'] is not None:
            links = sorted({tuple(e) for option in q['witness'] for e in option['links']})
            q['witness_tracks'] = partition(result['events'], links)
            q['has_delayed_arrival'] = any(option['delayed'] for option in q['witness'])
    out['temporal_limits'] = [
        'A possibility under one same-lane matching, not a selected harmony or actual contrapuntal voice.',
        'Complete membership is accumulated only inside supplied candidate intervals; not a segmentation rule.',
        'Silence, unexplained source tones and uncarried target nonmembers cause abstention, not rejection of music.',
        'Identical-pitch touching reattacks and held notes only; rest bridges, intervening embellishments and grace deferred.',
        'Nested subset harmonies, harmonic rhythm, key and independent musical correctness remain unresolved.']
    return out
