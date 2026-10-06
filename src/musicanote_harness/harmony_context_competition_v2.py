"""Compare held-chord anchor roles with selected-chord anchor roles, not veto.

V1 required BOTH melodic anchors to be members of the current selected path.
That circular condition can hide the very held-chord explanation competing
with an incorrect split. V2 requires anchors to be members of the HELD
hypothesis and records current selected roles as a separate alternative.
All original pitch, clock, voice, gap, grace and other-voice checks remain.
"""
from . import harmony_context_competition as control

VERSION = 'harmony-three-run-context-competition-0.2.0'
FEATURES = control.FEATURES
f, q = control.f, control.q


class Context(control.Context):
    @staticmethod
    def anchor_member(row, runs):
        # The inherited conflict() checks both anchors against held members.
        # Selected membership is reported BELOW, not a self-confirming veto.
        return any(row['start'] < b and a < row['end'] for a, b, _ in runs)

    def conflict(self, runs, index, total):
        result = super().conflict(runs, index, total)
        for figure in result['conditional_figures']:
            states = []
            for ident in (figure['event_ids'][0], figure['event_ids'][-1]):
                row = self.rows[ident]
                cells = [{'span': {'start': q(max(row['start'], a)), 'end': q(min(row['end'], b))},
                          'selected_signature': sig, 'is_selected_member': row['token'] in sig[1]}
                         for a, b, sig in runs if row['start'] < b and a < row['end']]
                states.append({'sounding_event_id': ident, 'selected_path_cells': cells,
                               'is_held_hypothesis_member': True})
            figure['anchor_role_alternatives'] = states
            figure['current_path_anchor_is_nonmember_somewhere'] = any(
                not c['is_selected_member'] for state in states for c in state['selected_path_cells'])
            figure['current_selected_anchor_membership_required'] = False
        result['held_explanation_anchor_membership_required'] = True
        result['selected_anchor_membership_is_alternative_not_veto'] = True
        return result


def observe_path(problem, ev, ids, *, context=None, **kwargs):
    ctx = context or Context(ev, **kwargs)
    if not isinstance(ctx, Context): raise ValueError('wrong_competing_anchor_contract')
    result = control.observe_path(problem, ev, ids, context=ctx)
    result['version'] = VERSION
    result['held_anchor_membership_required'] = True
    result['selected_anchor_membership_is_alternative_not_veto'] = True
    result['candidate_and_ornament_explanations_compete_without_current_label_veto'] = True
    return result
