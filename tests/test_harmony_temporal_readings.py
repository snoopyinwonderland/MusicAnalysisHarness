import unittest
from copy import deepcopy
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_joint import f
from musicanote_harness.harmony_temporal_readings import compare
from test_harmony_open_candidates import score


def run(ir, a=0, b=4):
    return compare(ir, {'start': q(a), 'end': q(b)}, {'start': q(0), 'end': q(4)})


def fixed(result, label):
    return next(r for r in result['fixed_readings'] if r['candidate']['label'] == label)


class TemporalReadingsTests(unittest.TestCase):
    def fixture(self):
        return score([('C3',0,4,'a'),('E3',0,4,'b'),('G3',0,4,'c'),
                      ('C4',0,1,'d'),('D4',1,2,'d'),('E4',2,4,'d')])

    def test_conditioned_passing_note_kept(self):
        r=run(self.fixture());c=fixed(r,'C:major')
        self.assertTrue(c['conditional_ornaments'])
        self.assertTrue(c['profile']['groups']['other']['nonmember_not_confirmed_nct']['event_refs'])
        self.assertEqual(len(r['event_units']),6)

    def test_all_stages_exact_common_time(self):
        r=run(self.fixture());cells=r['stages']
        self.assertEqual(cells[0]['span']['start'],q(0));self.assertEqual(cells[-1]['span']['end'],q(4))
        for a,b in zip(cells,cells[1:]):self.assertEqual(a['span']['end'],b['span']['start'])
        c=fixed(r,'C:major');label=c['candidate']['label']
        total=sum(f(s['span']['end'])-f(s['span']['start']) for s in cells)
        self.assertEqual(total,4)
        durations={}
        for s in cells:
            p=next(a for a in s['alternatives'] if a['label']==label)['profile']
            for state,e in p['groups']['other'].items():durations[state]=durations.get(state,0)+f(e['duration_quarters'])
        self.assertEqual(durations,{s:f(e['duration_quarters']) for s,e in c['profile']['groups']['other'].items()})

    def test_future_member_not_fill_cell(self):
        r=run(score([('C4',0,2,'a'),('E4',0,2,'b'),('G4',2,4,'a')]))
        first=next(a for a in r['stages'][0]['alternatives'] if a['label']=='C:major')
        self.assertIn('G',first['timeline']['missing_inside'])

    def test_sparse_arrival_keeps_hypothesis_not_invented_root(self):
        r=run(score([('C4',0,2,'a'),('E4',0,2,'b'),('G4',2,4,'a')]))
        last=next(a for a in r['stages'][-1]['alternatives'] if a['label']=='C:major')
        self.assertEqual(last['origin'],'carried_whole_window_hypothesis')
        self.assertIn('C',last['timeline']['missing_inside'])

    def test_whole_missing_member_survives(self):
        r=run(score([('C4',0,4,'a'),('E4',0,4,'b')]))
        self.assertIn('G',fixed(r,'C:major')['timeline']['missing_inside'])

    def test_rootless_spelling_abstains(self):
        r=run(score([('E4',0,4,'a'),('G4',0,4,'b')]))
        self.assertIn('root_spelling_unobserved_or_ambiguous',fixed(r,'C:major')['abstention_reasons'])

    def test_silence_cell_preserved(self):
        r=run(score([('C4',0,1,'a'),('E4',2,4,'a')]))
        self.assertTrue(any(s['silence'] for s in r['stages']))
        self.assertIn('silence_inside_window',fixed(r,'C:major')['abstention_reasons'])

    def test_held_not_reattack(self):
        r=run(self.fixture());s=r['stages'][1]
        self.assertEqual(len(s['continued_refs']),3)
        self.assertEqual(len(s['attack_refs']),1)

    def test_no_mutation_or_label_leak(self):
        ir=self.fixture();old=deepcopy(ir);r=run(ir)
        self.assertEqual(ir,old);ir['annotations']=['V7/V']
        self.assertEqual(run(ir),r);self.assertIsNone(r['selected']);self.assertFalse(r['ranking_performed'])

    def test_real_seventh_not_reduced(self):
        r=run(score([('C3',0,4,'a'),('E3',0,4,'b'),('G3',0,4,'c'),('B3',0,4,'d')]))
        self.assertTrue(fixed(r,'C:major')['candidate']['residual_event_refs'])
        self.assertFalse(fixed(r,'C:major7')['candidate']['residual_event_refs'])

    def test_transposition_candidate_invariance(self):
        a=run(score([('C4',0,2,'a'),('E4',0,2,'b'),('G4',2,4,'a')]))
        b=run(score([('D4',0,2,'a'),('F#4',0,2,'b'),('A4',2,4,'a')]))
        key=lambda r:{(x['candidate']['root'],x['candidate']['label'].split(':')[1]) for x in r['fixed_readings']}
        self.assertEqual({((r+2)%12,k) for r,k in key(a)},key(b))

    def test_invalid_context_rejected(self):
        with self.assertRaises(ValueError):compare(self.fixture(),{'start':q(0),'end':q(4)},{'start':q(1),'end':q(4)})
