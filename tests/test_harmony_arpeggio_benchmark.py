import unittest
from collections import Counter
from fractions import Fraction as F
from xml.etree import ElementTree as ET
from musicanote_harness.harmony_arpeggio_benchmark import fixture,source_xml,metrics,signature,TEXTURES,FAMILIES
from musicanote_harness.formal_ir import q


def result(parts):
    return {'segments':[{'span':{'start':q(a),'end':q(b)},'selected':{'root':r,'label':f'root:{quality}'}} for a,b,r,quality in parts]}


class ArpeggioBenchmarkTests(unittest.TestCase):
    def test_balanced_matrix_and_retained_timeline(self):
        cases=[fixture(f,t,c,tr,scale) for f in FAMILIES for t in TEXTURES for c in (False,True)
               for tr,scale in [(0,F(1)),(2,F(1)),(0,F(1,2))]]
        self.assertEqual(len(cases),84)
        self.assertEqual(Counter(c['change'] for c in cases),{False:42,True:42})
        for c in cases:
            root=ET.fromstring(source_xml(c));cursor=F(0);last=F(0);observed=[]
            for e in root.findall('./part/measure/*'):
                if e.tag=='backup':cursor-=F(int(e.findtext('duration')),8)
                elif e.tag=='forward':cursor+=F(int(e.findtext('duration')),8)
                elif e.tag=='note':
                    d=F(int(e.findtext('duration')),8)
                    start=last if e.find('chord') is not None else cursor
                    observed.append((start,d))
                    if e.find('chord') is None:last=cursor;cursor+=d
            expected=[(F(e['start']['numerator'],e['start']['denominator']),F(e['duration']['numerator'],e['duration']['denominator'])) for e in c['events']]
            self.assertEqual(Counter(expected),Counter(observed))

    def test_duration_match_does_not_hide_wrong_boundary(self):
        expected=fixture('triad','block',False)['expected']
        m=metrics(expected,result([(0,2,0,'major'),(2,4,0,'major')]))
        self.assertEqual(m['duration_match'],1)
        self.assertFalse(m['exact_intention_match']);self.assertEqual(m['extra_boundaries'],[q(2)])

    def test_missing_change_detected(self):
        expected=fixture('triad','block',True)['expected']
        m=metrics(expected,result([(0,4,0,'major')]))
        self.assertEqual(m['duration_match'],.5)
        self.assertEqual(m['missing_boundaries'],[q(2)])

    def test_correct_change_and_partition_validation(self):
        expected=fixture('triad','block',True)['expected']
        self.assertTrue(metrics(expected,result([(0,2,0,'major'),(2,4,7,'dominant7')]))['exact_intention_match'])
        with self.assertRaises(ValueError):metrics(expected,result([(0,1,0,'major'),(2,4,7,'dominant7')]))
        with self.assertRaises(ValueError):metrics(expected,result([(0,3,0,'major')]))

    def test_signature_normalization(self):
        a=result([(0,2,0,'major'),(2,4,7,'dominant7')])
        b=result([(0,1,2,'major'),(1,2,9,'dominant7')])
        self.assertEqual(signature(a),signature(b,2,F(1,2)))

    def test_expected_labels_never_embedded_in_musicxml(self):
        text=source_xml(fixture('seventh','alberti',True))
        self.assertNotIn('<harmony',text);self.assertNotIn('dominant7',text)


if __name__=='__main__':unittest.main()
