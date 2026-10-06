import unittest
from audit_tie_notation import split_notes,normalize

class TieNotationTests(unittest.TestCase):
    def xml(self,extra=''):
        return f'<score-partwise><part id="P1"><measure number="1"><attributes><divisions>4</divisions></attributes><note><pitch><step>C</step><octave>4</octave></pitch><duration>4</duration><type>quarter</type>{extra}</note></measure></part></score-partwise>'.encode()
    def test_split_preserves_sound(self):
        data=self.xml();variant,changes=split_notes(data)
        self.assertEqual(len(changes),1)
        self.assertEqual(normalize(data)['sounding'],normalize(variant)['sounding'])
        self.assertIn(b'type="start"',variant);self.assertIn(b'type="stop"',variant)
    def test_protected_notations_not_split(self):
        for extra in ['<beam number="1">begin</beam>','<tie type="start"/>','<notations><fermata/></notations>']:
            self.assertEqual(split_notes(self.xml(extra))[1],[])

if __name__=='__main__':unittest.main()
