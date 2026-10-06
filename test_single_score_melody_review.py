import unittest
from fractions import Fraction as F
from single_score_melody_review import q, hypotheses, parse_source, sounding

def note(i,p,d=1,ties=None):
    return dict(id=str(i),part='P9',staff='1',voice='1',onset=q(F(i)),duration=q(F(d)),pitch=p,spelling=str(p),rest=False,grace=False,chord=False,beams=[],ties=ties or [],sourceElementIndex=i,printedMeasure='1')

class ReviewTests(unittest.TestCase):
    def test_single_fill_keeps_source(self):
        ns=[note(0,72),note(1,60),note(2,74)];before=repr(ns);r=hypotheses(ns)
        self.assertEqual(r['candidates'][0]['excludedIds'],['1']);self.assertEqual(repr(ns),before)
    def test_legitimate_stepwise_short_notes_not_removed(self):
        self.assertFalse(hypotheses([note(0,60),note(1,62),note(2,64)])['relations'])
    def test_real_gap_blocks(self):
        self.assertFalse(hypotheses([note(0,72),note(1,60,F(1,2)),note(2,74)])['relations'])
    def test_beam_continuity_blocks(self):
        ns=[note(0,72),note(1,60),note(2,74)];ns[1]['beams']=[dict(value='continue')]
        self.assertFalse(hypotheses(ns)['relations'])
    def test_ties_preserved_before_projection(self):
        ns=[note(0,60,ties=['start']),note(1,72),note(1,60,ties=['stop'])];ns[2]['id']='tie'
        sounding_notes,warnings=sounding(ns)
        self.assertEqual(len(sounding_notes),2);self.assertEqual(sounding_notes[0]['duration'],q(F(2)));self.assertFalse(warnings)
    def test_xml_exact_triplet_and_source_ref(self):
        xml=b'<score-partwise><part id="P9"><measure number="0" implicit="yes"><attributes><divisions>3</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes><note><pitch><step>C</step><octave>5</octave></pitch><duration>1</duration></note></measure><measure number="1"><note><rest/><duration>3</duration></note></measure></part></score-partwise>'
        _,ns,_=parse_source(xml);self.assertEqual(ns[0]['duration'],q(F(1,3)));self.assertEqual(ns[1]['onset'],q(F(1,3)));self.assertIn(':m1:e1',ns[0]['id'])

if __name__=='__main__': unittest.main()
