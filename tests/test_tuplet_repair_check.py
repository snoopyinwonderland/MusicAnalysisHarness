import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET
from musicanote_harness.tuplet_time_repair import repair, digest
from musicanote_harness.tuplet_repair_check import verify_xml
from test_tuplet_time_repair import fixture


class RepairCheckTests(unittest.TestCase):
    def setup_pair(self, tmp):
        source=Path(tmp)/'source.xml'; derived=Path(tmp)/'derived.xml'
        ET.ElementTree(fixture()).write(source)
        return source,derived,repair(source,derived)

    def test_all_event_aliases_and_original_are_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            source,derived,proof=self.setup_pair(tmp)
            result=verify_xml(source,derived,proof)
            self.assertEqual(result['edited_duration_count'],7)
            self.assertEqual(result['event_count'],10)
            self.assertTrue(all(not a['automatic_external_annotation_retarget'] for a in result['coordinate_aliases']))
            self.assertEqual(digest(source),proof['source_sha256'])

    def test_hash_changes_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            source,derived,proof=self.setup_pair(tmp)
            proof['normalized_sha256']='invalid'
            with self.assertRaisesRegex(ValueError,'hash_changed'):verify_xml(source,derived,proof)

    def test_pitch_change_rejected_even_with_updated_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            source,derived,proof=self.setup_pair(tmp)
            tree=ET.parse(derived);tree.find('part/measure/note/pitch/step').text='D';tree.write(derived)
            proof['normalized_sha256']=digest(derived)
            with self.assertRaisesRegex(ValueError,'non_time_content_changed'):verify_xml(source,derived,proof)

    def test_unlisted_duration_change_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            source,derived,proof=self.setup_pair(tmp)
            tree=ET.parse(derived);tree.getroot().findall('part')[1].find('measure/note/duration').text='3361';tree.write(derived)
            proof['normalized_sha256']=digest(derived)
            with self.assertRaisesRegex(ValueError,'unlisted_time_change'):verify_xml(source,derived,proof)
