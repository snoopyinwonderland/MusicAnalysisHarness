"""Unit28 dominant-seventh + observed added-tone proposals, without labels.

This classical-textbook profile does not claim a universal jazz 9/11/13 grammar.
Every added-tone subset remains a competitor to the unchanged base candidates.
"""
from itertools import combinations
from .added_dissonance import EXTENSIONS, observe as theory_observe
from .applied_chords import offset
from .augmented_sixth import pc
from .harmony_joint import f
from .harmony_open_candidates import window
from .harmony_path_contrast import token
from .seventh_context import chord

VERSION = 'blind-dominant-added-tone-candidates-0.1.0'


def propose(ir, span, context_span=None):
    context_span = context_span or span
    if not (0 <= f(context_span['start']) <= f(span['start']) < f(span['end']) <= f(context_span['end'])):
        raise ValueError('invalid_context')
    base = window(ir, span)
    context = base if context_span == span else window(ir, context_span)
    blockers = sorted(set(base['abstention_reasons'] + context['abstention_reasons']))
    candidates = []; references = []
    if not {'unsupported_pitch', 'grace_timing'} & set(blockers):
        spelling = {sid: (u['pitch']['step'], int(f(u['pitch']['alter']))) for sid,u in base['event_units'].items()}
        observed = set(spelling.values())
        # A root may be observed, or be a hypothetical major third below an
        # observed identity tone. Root absence is explicitly retained, never filled.
        roots = observed | {tuple(offset(p,-2,-4)) for p in observed}
        for root in sorted(roots):
            h = chord(root,'Mm7')
            core = dict(zip(('root','third','fifth','seventh'), h['members']))
            present = {role:tuple(p) in observed for role,p in core.items()}
            if not present['seventh']:continue
            added = {role:offset(root,*distance) for role,distance in EXTENSIONS.items()}
            available = sorted(role for role,p in added.items() if tuple(p) in observed)
            rid = 'addref_' + token([base['window_id'],root])
            root_candidates = []
            for size in range(1,len(available)+1):
                for roles in combinations(available,size):
                    if {'minor_ninth','major_ninth'} <= set(roles):continue
                    if {'minor_sixth_or_thirteenth','major_sixth_or_thirteenth'} <= set(roles):continue
                    ordinary = present['third']
                    replacement = present['root'] and (
                        'fourth_or_eleventh' in roles or any('thirteenth' in r for r in roles) or
                        (present['fifth'] and any('ninth' in r for r in roles)))
                    if not (ordinary or replacement):continue
                    required_roles = ['third','seventh'] if ordinary else ['root','seventh']
                    if not ordinary and all('ninth' in r for r in roles):required_roles.append('fifth')
                    required_roles += list(roles)
                    members = {**core,**{r:added[r] for r in roles}}
                    expected = {tuple(p) for p in members.values()}
                    support = {tuple(members[r]) for r in required_roles}
                    states = {sid:'member' if p in expected else 'nonmember_not_confirmed_nct' for sid,p in spelling.items()}
                    cells=[]
                    for cell in base['cells']:
                        actual = {spelling[sid] for sid in cell['event_refs']}
                        bass = {spelling[sid] for sid in cell['bass_refs']}
                        cells.append({'span':cell['span'],'event_refs':cell['event_refs'],
                            'member_roles_present':[r for r,p in members.items() if tuple(p) in actual],
                            'all_members_present':expected<=actual,'exact_members_only':expected==actual,
                            'proposal_support_present':support<=actual,
                            'bass_refs':cell['bass_refs'],
                            'bass_member_roles':[r for r,p in members.items() if tuple(p) in bass],
                            'bass_outside_candidate':bool(bass-expected)})
                    root_candidates.append({'candidate_id':'add_' + token([base['window_id'],root,roles]),
                        'family':'dominant_seventh_with_added_tones','root_coordinate':list(root),'root_pc':pc(root),
                        'added_roles':list(roles),'member_spellings':members,
                        'reference_id':rid,'identity_gate':'third_and_seventh' if ordinary else 'root_seventh_replacement_shape',
                        'proposal_support_roles':required_roles,
                        'root_observed':present['root'],'missing_core_roles':[r for r,v in present.items() if not v],
                        'missing_spellings':[list(p) for p in sorted(expected-observed)],
                        'extra_spellings':[list(p) for p in sorted(observed-expected)],
                        'event_states':states,'cells':cells,'pooled_complete':expected<=observed,
                        'simultaneous_complete':any(c['all_members_present'] for c in cells),
                        'proposal_support_simultaneous':any(c['proposal_support_present'] for c in cells),
                        'base_competitor_refs':[c['candidate_id'] for c in base['candidates']
                            if c['root']==pc(root) and c['label'].endswith(':dominant7')],
                        'selected':None,'function':None,'inversion':None,'nct_labels':None})
            if root_candidates:
                evidence=None
                if not blockers:
                    legacy=theory_observe(ir,span,context_span,h)
                    evidence={k:legacy[k] for k in ('version','paths','slices','excluded_grace_refs')}
                references.append({'reference_id':rid,'root_coordinate':list(root),'base_members':core,
                    'basis':'proposed_dominant_seventh_coordinate_not_a_function_or_bass_verdict',
                    'context_evidence':evidence,'abstention_reasons':blockers})
                candidates.extend(root_candidates)
    return {'version':VERSION,'span':span,'context_span':context_span,'base_window':base,
        'extended_candidates':candidates,'references':references,'abstention_reasons':blockers,
        'source_labels_used':False,'selected':None,'production_enabled':False,
        'limits':['Dominant-seventh textbook profile only; major/minor-seventh and jazz alterations deferred.',
            'Added names are spelled classes, not observed compound intervals or Roman functions.',
            'No automatic lower extensions: a thirteenth class does not invent a ninth/eleventh.',
            'Pooled identity gate is a proposal, not simultaneity, a pedal, or harmonic persistence.',
            'Conflicting ninth/sixth alterations kept as separate alternatives, not combined.',
            'Single-voice descent may be ornament or chord member: no role verdict or ranking.',
            'Legacy base candidates and their conditional ornaments remain unchanged.']}
