import importlib.util, unittest, tempfile
from pathlib import Path
spec=importlib.util.spec_from_file_location('adapter',Path(__file__).with_name('structural-xml-source.py'))
adapter=importlib.util.module_from_spec(spec);spec.loader.exec_module(adapter)
class AdapterTests(unittest.TestCase):
    def parse(self,body):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'fixture.xml';p.write_text('<score-partwise><part id="P1">'+body+'</part></score-partwise>',encoding='utf8')
            return adapter.adapt(p)
    def test_pickup_and_rational_tie(self):
        r=self.parse('<measure number="0"><attributes><divisions>3</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes><note id="a"><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><tie type="start"/></note></measure><measure number="1"><note id="b"><pitch><step>C</step><octave>4</octave></pitch><duration>2</duration><tie type="stop"/></note></measure>')
        a,b=r['events'];self.assertTrue(a['pickup']);self.assertEqual(b['onsetQ'],{'n':1,'d':3});self.assertEqual(a['tieChainId'],b['tieChainId']);self.assertFalse(b['isAttack']);self.assertEqual(a['xmlNoteId'],'a')
    def test_voices_chords_and_rests_preserved(self):
        r=self.parse('<measure number="1"><attributes><divisions>1</divisions></attributes><note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice></note><note><chord/><pitch><step>E</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice></note><backup><duration>1</duration></backup><note><rest/><duration>1</duration><voice>2</voice></note></measure>')
        self.assertEqual(len(r['events']),3);self.assertEqual([e['onsetQ'] for e in r['events']],[{'n':0,'d':1}]*3);self.assertEqual(r['events'][2]['voiceId'],'2');self.assertIsNone(r['events'][0]['meter'])
    def test_orphan_tie_reported(self):
        r=self.parse('<measure><attributes><divisions>1</divisions></attributes><note><pitch><step>F</step><alter>1</alter><octave>4</octave></pitch><duration>1</duration><tie type="stop"/></note></measure>')
        self.assertEqual(r['adapterIssues'][0]['reason'],'orphan-tie-stop');self.assertEqual(r['events'][0]['pitchMidi'],66)
    def test_missing_divisions_rejected(self):
        with self.assertRaises(ValueError):self.parse('<measure><note><rest/><duration>1</duration></note></measure>')
if __name__=='__main__': unittest.main()
