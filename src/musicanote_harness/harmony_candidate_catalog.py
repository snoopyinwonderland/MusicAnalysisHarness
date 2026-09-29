"""Versioned research candidate envelope, not Canonical Core or a winner.

Normalizes membership and time accounting without weakening provider-specific
assumptions. Raw providers are retained; absent spelling is not invented.
"""
from fractions import Fraction
from copy import deepcopy
import re
from .formal_ir import q
from .harmony_joint import f
from .harmony_augmented_candidates import propose as augmented
from .harmony_extended_candidates import propose as extended
from .augmented_sixth import pc
from .seventh_context import chord
from .harmony_path_contrast import token

VERSION = 'harmony-candidate-catalog-0.1.0'
STATES = ('member','nonmember_not_confirmed_nct','spelling_unresolved')


def additional_sevenths(base):
    """Observed root/third/major seventh gate; missing fifth remains explicit."""
    result=[]
    if {'unsupported_pitch','grace_timing'} & set(base['abstention_reasons']):return result
    spellings={sid:(u['pitch']['step'],int(f(u['pitch']['alter']))) for sid,u in base['event_units'].items()}
    observed=set(spellings.values())
    for root in sorted(observed):
        for quality in ('+M7','mM7'):
            h=chord(root,quality);members=h['members']
            if not all(tuple(members[i]) in observed for i in (0,1,3)):continue
            expected={tuple(p) for p in members}
            result.append({'candidate_id':'seven_' + token([base['window_id'],root,quality]),
                'quality':quality,'root_coordinate':list(root),'members':members,
                'missing_spellings':[list(p) for p in sorted(expected-observed)],
                'extra_spellings':[list(p) for p in sorted(observed-expected)],
                'event_states':{sid:'member' if p in expected else 'nonmember_not_confirmed_nct' for sid,p in spellings.items()},
                'proposal_gate':'observed_root_third_and_major_seventh',
                'abstention_reasons':base['abstention_reasons'],'selected':None})
    return result


def spelling(text):
    m=re.fullmatch(r'([A-G])([#b]*)',text)
    if not m:raise ValueError('invalid_provider_spelling')
    return [m[1],m[2].count('#')-m[2].count('b')]


def make_record(base,raw,provider,pointer,root_pc,root_spell,tonal_coordinate,alternatives,pcs,blockers):
    units=base['event_units'];observed=set(base['observed_pitch_classes'])
    states=raw['event_states'];totals={state:Fraction() for state in STATES};cells=[]
    if set(states)!=set(units):raise ValueError('provider_event_coverage_mismatch')
    for cell in base['cells']:
        duration=f(cell['span']['end'])-f(cell['span']['start'])
        grouped={state:[] for state in STATES}
        for sid in cell['event_refs']:
            state=states[sid]
            if state not in STATES:raise ValueError('invalid_membership_state')
            grouped[state].append(sid);totals[state]+=duration
        cells.append({'span':cell['span'],'state_event_refs':grouped,'bass_refs':cell['bass_refs']})
    missing=[]
    sound_spellings={(u['pitch'].get('step'),f(u['pitch']['alter'])) for u in units.values()
                     if isinstance(u['pitch'].get('alter'),dict)}
    for alt in alternatives:
        missing.append([p for p in alt['members'] if tuple(p) not in sound_spellings])
    return deepcopy({'candidate_id':raw['candidate_id'],'provider':provider,'origin_pointer':pointer,
        'span':base['span'],'root':{'pitch_class':root_pc,'spelling':root_spell},
        'tonal_coordinate':tonal_coordinate,'member_pitch_classes':sorted(set(pcs)),
        'spelling_alternatives':alternatives,'missing_spellings_by_alternative':missing,
        'missing_pitch_classes':sorted(set(pcs)-observed),'event_states':states,'cells':cells,
        'note_time_quarters':{state:q(value) for state,value in totals.items()},
        'total_note_time_quarters':q(sum(totals.values(),Fraction())),
        'abstention_reasons':blockers,'selected':None,'confidence':None,'function':None,
        'semantics':'membership_under_candidate_not_confirmed_harmonic_role'})


def resolve(document,pointer):
    if not pointer.startswith('/'):raise ValueError('invalid_origin_pointer')
    obj=document
    try:
        for part in pointer[1:].split('/'):
            key=part.replace('~1','/').replace('~0','~')
            obj=obj[int(key)] if isinstance(obj,list) else obj[key]
    except (KeyError,IndexError,ValueError,TypeError) as exc:raise ValueError('broken_origin_pointer') from exc
    return obj


def validate(catalog):
    """Executable cross-reference/time contract, in addition to JSON serialization."""
    if catalog['schema_name']!='musicanote-harmony-candidate-catalog' or catalog['schema_version']!='0.1.0':raise ValueError('unsupported_contract')
    if catalog['selected'] is not None or catalog['source_labels_used'] or catalog['production_enabled']:raise ValueError('unsupported_verdict')
    base=catalog['providers']['base'];units=base['event_units'];seen=set()
    if catalog['span']!=base['span']:raise ValueError('span_mismatch')
    for c in catalog['candidates']:
        cid=c['candidate_id']
        if cid in seen:raise ValueError('duplicate_candidate_id')
        seen.add(cid);raw=resolve(catalog,c['origin_pointer'])
        if raw['candidate_id']!=cid or raw['event_states']!=c['event_states']:raise ValueError('origin_mismatch')
        if set(c['event_states'])!=set(units) or c['span']!=base['span']:raise ValueError('event_or_span_mismatch')
        for alt in c['spelling_alternatives']:
            if {pc(p) for p in alt['members']}!=set(c['member_pitch_classes']):raise ValueError('spelling_pc_mismatch')
        if c['provider']=='augmented' and (c['root']['pitch_class'] is not None or c['root']['spelling'] is not None):raise ValueError('augmented_root_invented')
        if len(c['cells'])!=len(base['cells']):raise ValueError('cell_coverage_mismatch')
        totals={state:Fraction() for state in STATES}
        for cell,source in zip(c['cells'],base['cells']):
            if cell['span']!=source['span'] or cell['bass_refs']!=source['bass_refs']:raise ValueError('cell_mismatch')
            if set(cell['state_event_refs'])!=set(STATES):raise ValueError('invalid_membership_state')
            refs=[sid for ids in cell['state_event_refs'].values() for sid in ids]
            if len(refs)!=len(set(refs)) or set(refs)!=set(source['event_refs']):raise ValueError('cell_event_mismatch')
            for state,ids in cell['state_event_refs'].items():
                if any(c['event_states'][sid]!=state for sid in ids):raise ValueError('state_mismatch')
                totals[state]+=(f(cell['span']['end'])-f(cell['span']['start']))*len(ids)
        if c['note_time_quarters']!={s:q(v) for s,v in totals.items()} or c['total_note_time_quarters']!=q(sum(totals.values(),Fraction())):
            raise ValueError('note_time_mismatch')
        if any(c[k] is not None for k in ('selected','confidence','function')):raise ValueError('unsupported_verdict')
    # Every supplied candidate, including weak/unsupported base alternatives,
    # must survive normalization exactly once. Equal pitch-class sets are not merged.
    expected={c['candidate_id'] for c in base['candidates']}
    expected.update(c['candidate_id'] for c in catalog['providers']['augmented']['augmented_sixth_candidates'])
    expected.update(c['candidate_id'] for c in catalog['providers']['extended']['extended_candidates'])
    expected.update(c['candidate_id'] for c in catalog['providers']['additional_sevenths'])
    if seen!=expected:raise ValueError('provider_candidate_loss')
    return {'passed':True,'candidates_checked':len(seen),'ranked':False}


def propose(ir,span,context_span=None):
    aug=augmented(ir,span,context_span);ext=extended(ir,span,context_span)
    base=aug['base_window']
    if ext['base_window']!=base:raise ValueError('provider_base_mismatch')
    extra=additional_sevenths(base)
    providers={'base':base,'augmented':{k:v for k,v in aug.items() if k!='base_window'},
               'extended':{k:v for k,v in ext.items() if k!='base_window'},'additional_sevenths':extra}
    records=[]
    for i,c in enumerate(base['candidates']):
        alts=[{'root_spelling':spelling(h['root_spelling']),'members':[spelling(p) for p in h['expected_members']]}
              for h in c['root_hypotheses']]
        rs=alts[0]['root_spelling'] if len(alts)==1 else None
        records.append(make_record(base,c,'base',f'/providers/base/candidates/{i}',c['root'],rs,None,alts,c['pcs'],base['abstention_reasons']))
    for i,c in enumerate(extra):
        alts=[{'root_spelling':c['root_coordinate'],'members':c['members']}]
        records.append(make_record(base,c,'additional_seventh',f'/providers/additional_sevenths/{i}',
            pc(c['root_coordinate']),c['root_coordinate'],None,alts,[pc(p) for p in c['members']],c['abstention_reasons']))
    for i,c in enumerate(aug['augmented_sixth_candidates']):
        alts=[{'root_spelling':None,'members':c['members']}]
        records.append(make_record(base,c,'augmented',f'/providers/augmented/augmented_sixth_candidates/{i}',None,None,
            c['tonic_coordinate'],alts,[pc(p) for p in c['members']],c['abstention_reasons']))
    for i,c in enumerate(ext['extended_candidates']):
        members=list(c['member_spellings'].values());alts=[{'root_spelling':c['root_coordinate'],'members':members}]
        records.append(make_record(base,c,'extended',f'/providers/extended/extended_candidates/{i}',c['root_pc'],
            c['root_coordinate'],None,alts,[pc(p) for p in members],ext['abstention_reasons']))
    result={'schema_name':'musicanote-harmony-candidate-catalog','schema_version':'0.1.0','engine_version':VERSION,
        'span':span,'context_span':aug['context_span'],'providers':providers,'candidates':records,
        'source_labels_used':False,'production_enabled':False,'selected':None,
        'limits':['Analysis extension, not Canonical Core. This catalog does not choose harmony or local key.',
            'Tertian root, augmented-sixth tonic coordinate, bass and inversion are different concepts.',
            'Spelling uncertainty and multiple origins survive normalization; no PC-set deduplication.',
            'Note-time categories cover the same sounds; member duration is not a ranking objective.',
            'NCT evidence remains provider-specific; no transfer across candidate assumptions.',
            'New seventh gate requires observed root/third/seventh; rootless and third-absent cases deferred.']}
    result=deepcopy(result)
    result['validation']=validate(result)
    return result
