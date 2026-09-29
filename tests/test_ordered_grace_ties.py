import unittest
from copy import deepcopy
from musicanote_harness.ordered_grace_ties import resolve


def n(sid, start, end, role, ordinal, voice='1'):
    return {'segment_id': sid, 'part_id': 'P1', 'staff_id': '1', 'voice_id': voice, 'measure': 1,
            'onset_ql': str(start), 'end_ql': str(end), 'tie_role': role, 'pitch_spelling': 'F5', 'midi': 77,
            'source_order': (1, ordinal)}


class OrderedGraceTiesTest(unittest.TestCase):
    def fixture(self):
        return [n('a',0,2,'start',1), n('b',2,2,'stop',2), n('c',2,2,'start',6), n('d',2,3,'stop',23)]

    def test_two_distinct_ties_not_one_bypassing_grace(self):
        rows=self.fixture(); original=deepcopy(rows); r=resolve(rows)
        self.assertEqual(r['edges'], [('a','b'),('c','d')]); self.assertFalse(r['issues'])
        self.assertEqual({tuple(s['segment_ids']) for s in r['sounds']}, {('a','b'),('c','d')})
        self.assertEqual(rows,original); self.assertFalse(r['chain_problems'])

    def test_input_order_not_identity(self):
        a=resolve(self.fixture()); b=resolve(list(reversed(self.fixture())))
        self.assertEqual(a['sounds'],b['sounds']); self.assertEqual(a['edges'],b['edges'])

    def test_missing_order_abstains(self):
        rows=self.fixture(); rows[1].pop('source_order')
        self.assertFalse(resolve(rows)['edges'])

    def test_two_lanes_abstains(self):
        rows=self.fixture(); rows[1]['voice_id']='2'
        self.assertFalse(resolve(rows)['edges'])

    def test_competing_starts_abstains_whole_bucket(self):
        rows=self.fixture(); rows.insert(1,n('z',0,2,'start',0))
        self.assertFalse(resolve(rows)['edges'])

    def test_unclosed_bucket_abstains_all_not_partial(self):
        self.assertFalse(resolve(self.fixture()[:-1])['edges'])

    def test_zero_duration_continue_acyclic(self):
        rows=[n('a',0,2,'start',1),n('b',2,2,'continue',2),n('c',2,3,'stop',3)]
        self.assertEqual(resolve(rows)['sounds'][0]['segment_ids'],['a','b','c'])

    def test_duplicate_order_rejected(self):
        rows=self.fixture(); rows[1]['source_order']=rows[0]['source_order']
        self.assertFalse(resolve(rows)['edges'])

    def test_non_grace_cross_voice_still_supported(self):
        self.assertEqual(resolve([n('a',0,1,'start',1),n('b',1,2,'stop',2,'2')])['edges'],[('a','b')])
