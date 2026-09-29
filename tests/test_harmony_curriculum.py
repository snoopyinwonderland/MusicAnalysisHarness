import copy
import json
from pathlib import Path
import tempfile
import unittest

from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_curriculum import (
    build, concepts, current_annotation, link_case, observe)


def fixture():
    span = {"start": q(0), "end": q(3)}
    ir = {"ir_document_id": "ir1", "score": {"score_id": "s1"},
          "sounding_events": [{"sounding_event_id": f"e{i}",
              "pitch": {"midi_pitch": p, "spelling": name},
              "span": {"start": q(i), "end": q(i+1)}}
             for i, (p, name) in enumerate([(60,"C4"),(64,"E4"),(67,"G4")])]}
    provenance = {"source_locator": {"path": "a.tsv", "line": 5}, "source_asset_sha256": "hash"}
    ann = {**provenance, "annotation_id": "a5", "raw_label": "I", "raw_fields": {"chord_type": "M", "figbass": ""},
           "target": {"score_id": "s1", "ir_document_id": "ir1", "span": span}}
    ep = {"case_id": "c1", "identity": {"score_id": "s1", "split": "train", "work_family_id": "w1"},
          "provenance": provenance, "ir_path": "unused", "reference_progression": [],
          "episode": {"span": span, "context_span": span}}
    return ep, ann, ir


class CurriculumTest(unittest.TestCase):
    def test_prerequisites_and_pending_reading(self):
        rows = concepts()
        ids = {r['concept_id'] for r in rows}
        self.assertTrue(all(set(r['prerequisites']) <= ids for r in rows))
        self.assertTrue(all(r['reading_status'] != 'completed' for r in rows))

    def test_exact_source_not_first_neighbor(self):
        ep, ann, _ = fixture()
        other = copy.deepcopy(ann)
        other['source_locator']['line'] = 4
        self.assertEqual(current_annotation(ep, [other, ann])['annotation_id'], 'a5')
        with self.assertRaises(ValueError):
            current_annotation(ep, [ann, ann])
        other['target']['span']['end'] = q(2)
        with self.assertRaises(ValueError):
            current_annotation(ep, [other])

    def test_arpeggio_candidate_not_verdict(self):
        ep, ann, ir = fixture()
        link, reason = link_case(ep, ann, ir)
        self.assertIsNone(reason)
        self.assertFalse(link['training_eligible'])
        self.assertEqual(link['review_status'], 'candidate')
        match = next(c for c in link['observation']['surface_triad_candidates']
                     if c['quality']=='major' and c['root_pitch_class']==0)
        self.assertEqual(match['missing_pitch_classes'], [])
        self.assertEqual(link['link_id'], link_case(ep,ann,ir)[0]['link_id'])

    def test_quality_and_inversion(self):
        ep, ann, ir = fixture()
        for marker, quality in [('M','major'),('m','minor'),('o','diminished'),('+','augmented')]:
            for figure, inversion in [('',0),('6',1),('64',2)]:
                ann['raw_fields'] = {'chord_type':marker, 'figbass':figure}
                link, _ = link_case(ep,ann,ir)
                self.assertEqual(link['source_quality'],quality)
                self.assertEqual(link['source_inversion'],inversion)

    def test_seventh_and_modified_not_basic_triad(self):
        ep, ann, ir = fixture()
        ann['raw_fields']['chord_type'] = 'Mm7'
        self.assertIsNone(link_case(ep,ann,ir)[0])
        ann['raw_fields'] = {'chord_type':'M','changes':'#5'}
        self.assertIsNone(link_case(ep,ann,ir)[0])

    def test_half_open_and_microtonal(self):
        _, ann, ir = fixture()
        ir['sounding_events'].append({'sounding_event_id':'outside',
            'pitch':{'midi_pitch':61,'spelling':'Db4'},
            'span':{'start':q(3),'end':q(4)}})
        self.assertNotIn('outside', observe(ir,ann['target']['span'])['sounding_event_ids'])
        ir['sounding_events'][0]['pitch']['midi_pitch'] = 60.5
        with self.assertRaises(ValueError):
            observe(ir,ann['target']['span'])

    def test_build_skips_holdout_without_opening_ir(self):
        ep, ann, ir = fixture()
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            path = folder/'canonical_music_ir.json'
            path.write_text(json.dumps(ir),encoding='utf-8')
            (folder/'imported_annotations.jsonl').write_text(json.dumps(ann),encoding='utf-8')
            ep['ir_path'] = str(path)
            held = copy.deepcopy(ep)
            held['identity']['split'] = 'holdout'
            held['ir_path'] = 'does-not-exist'
            source = folder/'episodes.jsonl'
            source.write_text(json.dumps(ep)+'\n'+json.dumps(held),encoding='utf-8')
            report = build(source,folder/'out')
            self.assertEqual(report['links'],1)
            self.assertEqual(report['errors'],[])
            self.assertEqual(report['skipped']['non_train'],1)
            self.assertIn('augmented',report['coverage_gaps'])


if __name__ == '__main__':
    unittest.main()
