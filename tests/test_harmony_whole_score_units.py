import itertools
import unittest
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction as F
from unittest.mock import patch

from musicanote_harness.harmony_whole_score_units import BeatIndex, UnitScorer, UnitSearch, supported, infer
from musicanote_harness.harmony_whole_score_diagnosis import evidence
from musicanote_harness.harmony_whole_score import model_weights
from musicanote_harness.harmony_scored_decoder import Problem, Edge, feature_cost
from musicanote_harness.harmony_full_score import FEATURES, FIXED
from musicanote_harness.formal_ir import q
from test_harmony_whole_score import problem, C, G
from test_harmony_bounded_recovery import fixture


def source(specs, end):
    ir=fixture(specs,end=end)
    ev,points,_,args=evidence(ir,F(end))
    graph=Problem(points,(),len(points)-1,sum((e.end-e.start for e in ev.source.events),F()),'ready')
    return ir,ev,graph,args


class UnitTests(unittest.TestCase):
    def test_indexed_cost_matches_direct_exhaustive(self):
        p,ev,batches=problem()
        graph=replace(p,edges=tuple(e for batch in batches for e in batch))
        weights=model_weights();sc=UnitScorer(graph,ev,weights,{})
        expected=min((feature_cost(sc.path_features(tuple(e.group_id for e in path))[0],weights),
                      tuple(e.group_id for e in path)) for path in itertools.product(*batches))
        search=UnitSearch(p,ev,weights,beam_width=128)
        for batch in batches:search.consume(batch)
        result=search.finish()
        self.assertEqual((F(result['score_cost']),result['selected']),expected)
        self.assertTrue(result['independently_rescored'])
        self.assertEqual(result['states_discarded'],0)
        self.assertFalse(result['exact_optimum_claimed'])

    def test_constant_tail_does_not_dilute_local_fit_or_change_margin(self):
        margins=[]
        for end in (4,8):
            specs=[(t,a,b,lane) for a,b,ts in ((0,1,('C3','E3','G3')),
                (1,2,('G3','B3','D4')),(2,end,('C3','E3','G3')))
                for lane,t in enumerate(ts)]
            _,ev,p,args=source(specs,end)
            batches=[]
            for i,(a,b) in enumerate(zip(p.points,p.points[1:])):
                active=[e for e in ev.source.events if e.start<b and a<e.end]
                batches.append([Edge(f'{i}_{j}',i,i+1,a,b,sig,{},
                    frozenset(e.pitch for e in active if e.start==a),
                    tuple(e.event_id for e in active),(),{}) for j,sig in enumerate((C,G))])
            p=replace(p,edges=tuple(e for batch in batches for e in batch))
            weights=dict.fromkeys(FEATURES,F())
            weights.update({k:model_weights()[k] for k in FIXED})
            weights.update(nonmember_exposure=F(1),harmonic_run_count=F(1,10))
            sc=UnitScorer(p,ev,weights,args)
            flat=tuple(batch[0].group_id for batch in batches)
            progression=tuple(batch[int(e.start==1)].group_id for batch in batches for e in batch[:1])
            margins.append(feature_cost(sc.path_features(flat)[0],weights)-
                           feature_cost(sc.path_features(progression)[0],weights))
        # G is a shared member: flat C has 2/3 beat of nonmembers, while
        # the correct progression pays two extra 1/10 run costs.
        self.assertEqual(margins,[F(7,15),F(7,15)])

    def test_unrelated_thick_texture_cannot_dilute_original_cell(self):
        original=[('C3',0,4,'b'),('E3',0,4,'i'),('D4',0,4,'lead')]
        thick=original+[(t,4,8,str(i)) for i,t in enumerate(('C3','D3','E3','F3','G3','A3','B3','C4'))]
        values=[]
        for specs,end in ((original,4),(thick,8)):
            _,ev,p,_=source(specs,end);index=BeatIndex(ev,p.points)
            values.append(index.convert({},F(),F(4),C)['nonmember_exposure'])
        self.assertEqual(values,[F(4,3),F(4,3)])

    def test_compound_meter_and_meter_change_integrate_exact_beats(self):
        ir=fixture([('C3',0,8,'b'),('E3',0,8,'i'),('G3',0,8,'j')],end=8)
        ir['measures'][0]['time_signature'].update(beats=6,beat_type=8)
        ir['measures'][1]['time_signature'].update(beats=3,beat_type=4)
        ev,points,_,_=evidence(ir,F(8));index=BeatIndex(ev,points)
        self.assertEqual(index.delta(index.beats,F(),F(4)),F(8,3))
        self.assertEqual(index.total_beats,F(20,3))

    def test_unknown_meter_is_not_quarter_fallback(self):
        ir=fixture();ir['measures'][0]['time_signature']={}
        ev,points,_,_=evidence(ir,F(4))
        with self.assertRaisesRegex(ValueError,'meter_unavailable'):BeatIndex(ev,points)

    def test_unobserved_candidate_members_still_have_key_evidence(self):
        ir=fixture([('C3',0,4,'a'),('E3',0,4,'b')])
        ir['measures'][0]['key_signature']={'fifths':0}
        ev,points,_,_=evidence(ir,F(4));index=BeatIndex(ev,points)
        result=index.convert({},F(),F(4),G)
        self.assertEqual(result['key_signature_foreign_member'],0)
        self.assertEqual(result['missing_member_fraction'],4)
        altered=(('D',0),(('D',0),('F',1),('A',0)))
        self.assertEqual(index.convert({},F(),F(4),altered)['key_signature_foreign_member'],F(4,3))

    def test_unknown_key_remains_unavailable(self):
        ir=fixture();ir['measures'][0]['key_signature']={'fifths':None}
        ev,points,_,_=evidence(ir,F(4))
        self.assertIsNone(BeatIndex(ev,points).convert({},F(),F(4),C)['key_signature_foreign_member'])

    def test_silence_does_not_become_known_absent_chord_members(self):
        _,ev,p,_=source([('C3',0,1,'a'),('E3',3,4,'a')],4)
        index=BeatIndex(ev,p.points);result=index.convert({},F(1),F(3),C)
        self.assertEqual(result['nonmember_exposure'],0)
        self.assertIsNone(result['missing_member_fraction'])
        self.assertIsNone(result['absent_third_exposure'])

    def test_only_supported_domain_selected_full_catalog_preserved(self):
        expanded=(('C',0),(('C',0),('D',0),('E',0),('G',0),('B',0)))
        self.assertTrue(supported(C));self.assertFalse(supported(expanded))
        catalog={'candidates':[{'spelling_alternatives':[{'root_spelling':expanded[0],
            'members':expanded[1]}],'abstention_reasons':[]}],
            'providers':{'base':{'abstention_reasons':[]}}}
        ir=fixture();before=deepcopy(ir)
        with patch('musicanote_harness.harmony_whole_score_units.propose',return_value=catalog):
            spans,info,catalogs=infer(ir,F(4))
        self.assertEqual(spans,[]);self.assertEqual(info['status'],'no_supported_context_candidates')
        self.assertEqual(catalogs,[catalog]);self.assertEqual(ir,before)

    def test_partial_and_budget_abort_never_submit(self):
        p,ev,batches=problem();search=UnitSearch(p,ev,model_weights())
        search.consume(batches[0])
        with self.assertRaisesRegex(ValueError,'partial_path'):search.finish()
        search=UnitSearch(p,ev,model_weights(),operations=1);search.consume(batches[0])
        self.assertEqual(search.finish()['status'],'operation_budget_abstention')
        self.assertIsNone(search.finish()['selected'])

    def test_complete_source_only_inference_preserves_catalogs_and_core(self):
        ir=fixture([('C3',0,4,'b'),('E3',0,4,'i'),('G3',0,4,'j')])
        before=deepcopy(ir);spans,info,catalogs=infer(ir,F(4))
        self.assertEqual(info['status'],'complete')
        self.assertTrue(info['independently_rescored']);self.assertTrue(catalogs)
        self.assertEqual(ir,before);self.assertFalse(info['production_enabled'])
        self.assertTrue(info['score_semantics_changed']);self.assertFalse(info['source_labels_used'])
        self.assertEqual(spans[0]['start'],'0');self.assertEqual(spans[-1]['end'],'4')


if __name__=='__main__':unittest.main()
