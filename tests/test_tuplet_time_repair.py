from copy import deepcopy
from fractions import Fraction
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET
from musicanote_harness.tuplet_time_repair import normalize_tree, repair, expected_duration, measure_extent


def fixture(ticks=69, actual=7, normal=4, note_type='16th', other=480, implicit=False):
    notes=''.join(f'<note><pitch><step>C</step><octave>4</octave></pitch><duration>{ticks}</duration><voice>1</voice><type>{note_type}</type><time-modification><actual-notes>{actual}</actual-notes><normal-notes>{normal}</normal-notes></time-modification>'+ ('<notations><tuplet type="start"/></notations>' if i==0 else '<notations><tuplet type="stop"/></notations>' if i==actual-1 else '')+'</note>' for i in range(actual))
    return ET.fromstring(f'<score-partwise><part-list/><part id="P1"><measure number="X1" implicit="{str(implicit).lower()}"><attributes><divisions>480</divisions></attributes>{notes}<direction><offset>120</offset></direction></measure><measure number="2"><note><rest/><duration>480</duration><voice>1</voice><type>quarter</type></note></measure></part><part id="P2"><measure number="X1" implicit="{str(implicit).lower()}"><attributes><divisions>480</divisions></attributes><note><rest/><duration>{other}</duration><voice>1</voice></note></measure><measure number="2"><note><rest/><duration>480</duration><voice>1</voice><type>quarter</type></note></measure></part></score-partwise>')


class TupletRepairTests(unittest.TestCase):
    def test_round_up_restores_all_seven_equally(self):
        root=fixture(); before=ET.tostring(root)
        fixed,report=normalize_tree(root)
        self.assertEqual(ET.tostring(root),before)
        self.assertEqual(len(report['edits']),7)
        self.assertEqual(report['divisions_multiplier'],7)
        self.assertEqual({n.findtext('duration') for n in fixed.findall('part')[0].findall('measure')[0].findall('note')},{'480'})
        self.assertEqual(measure_extent(fixed.findall('part')[0].findall('measure')[0],1)[0],1)
        self.assertEqual(fixed.findtext('part/measure/direction/offset'),'840')

    def test_round_down_implicit_measure_not_padded_to_meter(self):
        fixed,report=normalize_tree(fixture(ticks=17,note_type='64th',other=120,implicit=True))
        self.assertEqual(len(report['edits']),7)
        self.assertEqual(measure_extent(fixed.find('part/measure'),1)[0],Fraction(1,4))

    def test_already_exact_triplets_are_unchanged(self):
        _,report=normalize_tree(fixture(ticks=80,actual=3,normal=2,other=240))
        self.assertFalse(report['edits'])

    def test_real_gap_not_rounded_into_agreement(self):
        _,report=normalize_tree(fixture(other=960))
        self.assertFalse(report['edits'])

    def test_missing_tuplet_stop_abstains(self):
        root=fixture();notes=root.find('part/measure').findall('note')
        notes[-1].remove(notes[-1].find('notations'))
        self.assertFalse(normalize_tree(root)[1]['edits'])

    def test_missing_note_abstains(self):
        root=fixture();m=root.find('part/measure');m.remove(m.findall('note')[3])
        self.assertFalse(normalize_tree(root)[1]['edits'])

    def test_large_error_abstains(self):
        self.assertFalse(normalize_tree(fixture(ticks=60))[1]['edits'])

    def test_mixed_voice_abstains(self):
        root=fixture();root.find('part/measure').findall('note')[3].find('voice').text='2'
        self.assertFalse(normalize_tree(root)[1]['edits'])

    def test_no_independent_part_is_not_repaired(self):
        root=fixture();root.remove(root.findall('part')[1])
        with self.assertRaisesRegex(ValueError,'corroboration'):normalize_tree(root)

    def test_idempotent_and_preserves_unaffected_time(self):
        fixed,_=normalize_tree(fixture())
        again,report=normalize_tree(fixed)
        self.assertFalse(report['edits']);self.assertEqual(ET.tostring(fixed),ET.tostring(again))
        self.assertEqual(Fraction(fixed.findall('part')[0].findall('measure')[1].findtext('note/duration'))/3360,1)

    def test_dotted_tuplet_fraction(self):
        n=ET.fromstring('<note><type>eighth</type><dot/><time-modification><actual-notes>3</actual-notes><normal-notes>2</normal-notes></time-modification></note>')
        self.assertEqual(expected_duration(n),Fraction(1,2))

    def test_does_not_overwrite_source_or_existing_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'source.xml'; ET.ElementTree(fixture()).write(source)
            before=source.read_bytes();out=Path(tmp)/'candidate.xml'
            repair(source,out);self.assertEqual(source.read_bytes(),before)
            with self.assertRaisesRegex(ValueError,'output_exists'):repair(source,out)
            with self.assertRaisesRegex(ValueError,'output_exists'):repair(source,source)
