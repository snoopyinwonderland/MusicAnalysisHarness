import importlib.util
import json
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('production_index','K:/MusicSearch/scripts/build-musicxml-search-index.py')
parser=importlib.util.module_from_spec(spec);spec.loader.exec_module(parser)

class TieFixTests(unittest.TestCase):
    def parse(self,name):
        return parser.parse_musicxml(Path('reports/complex-ties-2026-09-22')/name/'source.musicxml')
    def test_barline(self):
        r=self.parse('across-barline');n=r['streams'][0]['notes'][0]
        self.assertEqual((n['d'],n['sd'],n['stm']),(5,5,2));self.assertFalse(r['tieWarnings'])
    def test_upper_chord(self):
        r=self.parse('upper-chord-tie');self.assertEqual(r['streams'][0]['notes'][0]['d'],2);self.assertFalse(r['tieWarnings'])
    def test_hidden_tie_separate_contract(self):
        r=self.parse('tie-hidden-by-higher-attack');n=r['streams'][0]['notes'][0]
        self.assertEqual(n['d'],1);self.assertEqual(n['sd'],2);self.assertFalse(r['tieWarnings'])
    def test_rest_never_sustained(self):
        r=self.parse('broken-tie-across-rest');ns=r['streams'][0]['notes']
        self.assertEqual([(n['o'],n['d']) for n in ns[:2]],[(0,1),(2,1)])
        self.assertEqual({w['code'] for w in r['tieWarnings']},{'unclosed-tie-start','unresolved-tie-stop'})

if __name__=='__main__':unittest.main()
