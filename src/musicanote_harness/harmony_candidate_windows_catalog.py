"""Additive candidate catalog adapter sharing caller-supplied windows.

Normalization, ordering, provider versions and validation reuse the original
catalog contract without changing its providers or selecting any candidate.
"""
from copy import deepcopy
from .harmony_candidate_catalog import (
    VERSION, additional_sevenths, make_record, spelling, validate, pc,
)
from .harmony_candidate_windows_augmented import from_windows as augmented
from .harmony_candidate_windows_extended import from_windows as extended


def from_windows(ir, span, context_span, base, context):
    aug=augmented(ir,span,context_span,base,context);ext=extended(ir,span,context_span,base,context)
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
