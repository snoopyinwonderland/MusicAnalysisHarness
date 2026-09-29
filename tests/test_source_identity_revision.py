import tempfile
import unittest
from pathlib import Path
from copy import deepcopy
from musicanote_harness.dcml_import import parse_score_without_imported_harmony
from musicanote_harness.canonical import CanonicalIRBuilder
from musicanote_harness.formal_ir import FormalIRAdapter
from musicanote_harness.source_sequence_audit import parser_rows, xml_rows, match_sequences
from musicanote_harness.source_identity_revision import revise, validate_revision, membership_aliases, alignment_membership
from musicanote_harness.formal_ir import q


XML='''<score-partwise version="4.0"><part-list><score-part id="P1"><part-name>Piano</part-name></score-part></part-list>
<part id="P1"><measure number="1"><attributes><divisions>1</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes>
<note><pitch><step>F</step><octave>5</octave></pitch><duration>2</duration><tie type="start"/><voice>1</voice></note>
<note><grace/><pitch><step>F</step><octave>5</octave></pitch><tie type="stop"/><voice>1</voice><type>eighth</type></note>
<note><grace/><pitch><step>F</step><octave>5</octave></pitch><tie type="start"/><voice>1</voice><type>eighth</type></note>
<note><pitch><step>F</step><octave>5</octave></pitch><duration>1</duration><tie type="stop"/><voice>1</voice></note>
</measure><measure number="X1" implicit="yes"><note><pitch><step>G</step><octave>5</octave></pitch><duration>1</duration><voice>1</voice></note>
</measure></part></score-partwise>'''


class IdentityRevisionTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.source=Path(self.temp.name)/'fixture.musicxml'; self.source.write_text(XML,encoding='utf-8')
        score,_,mapping=parse_score_without_imported_harmony(self.source)
        self.old=FormalIRAdapter().convert(CanonicalIRBuilder().build(score,self.source),self.source)
        refs={r['source_ref_id']:r for r in self.old['source_references']}
        by_fp={refs[n['source_ref_id']]['local_fingerprint']:n for n in self.old['note_events']+self.old['rest_events']}
        matches,rejected=match_sequences(parser_rows(score,mapping),xml_rows(self.source)[0])
        self.assertFalse(rejected)
        self.rows=[{'event_id':by_fp[p['fingerprint']].get('note_id',by_fp[p['fingerprint']].get('rest_id')),
                    'kind':p['kind'],'fingerprint':p['fingerprint'],'parser':p,'original':r} for p,r in matches]

    def test_preserves_notes_source_and_old_ir(self):
        old=deepcopy(self.old); xml=self.source.read_bytes()
        ir,log=revise(self.old,self.rows,self.source)
        validate_revision(self.old,ir)
        self.assertEqual(self.old,old); self.assertEqual(self.source.read_bytes(),xml)
        self.assertNotEqual(ir['ir_document_id'],old['ir_document_id'])
        self.assertEqual({n['note_id'] for n in ir['note_events']},{n['note_id'] for n in old['note_events']})
        self.assertFalse(log['graph']['issues']); self.assertEqual(len(log['graph']['resolved_grace_buckets']),1)

    def test_special_measure_gets_distinct_id_and_local_zero(self):
        ir,_=revise(self.old,self.rows,self.source)
        self.assertEqual([m['printed_measure_number'] for m in ir['measures']],['1','X1'])
        self.assertEqual(len({m['measure_id'] for m in ir['measures']}),2)
        last=next(n for n in ir['note_events'] if n['written_pitch']['step']=='G')
        self.assertEqual(last['onset_in_measure'],{'numerator':0,'denominator':1})

    def test_sequential_graces_not_a_chord(self):
        ir,_=revise(self.old,self.rows,self.source)
        self.assertFalse(ir['chord_onset_groups'])
        graces=[n for n in ir['note_events'] if n['grace']['is_grace']]
        self.assertEqual(sorted(n['grace']['order'] for n in graces),[0,1])
        self.assertTrue(all(n['grace']['anchor_note_id'] is None for n in graces))

    def test_missing_event_blocks_revision(self):
        with self.assertRaisesRegex(ValueError,'complete_bijective'):
            revise(self.old,self.rows[:-1],self.source)

    def test_altered_source_observation_blocks(self):
        rows=deepcopy(self.rows); rows[0]['original']['voice']='9'
        with self.assertRaisesRegex(ValueError,'source_observation_changed'): revise(self.old,rows,self.source)

    def test_deterministic_revision(self):
        a,log_a=revise(self.old,self.rows,self.source); b,log_b=revise(self.old,self.rows,self.source)
        self.assertEqual(a,b); self.assertEqual(log_a,log_b)

    def test_alias_split_not_automatic(self):
        rows=membership_aliases([{'id':'old','notes':['a','b']}],
            [{'id':'new1','notes':['a']},{'id':'new2','notes':['b']}],'id',lambda x:x['notes'])
        self.assertEqual(rows[0]['new_ids'],['new1','new2']); self.assertFalse(rows[0]['automatic_annotation_retarget'])

    def test_point_membership_keeps_sustained_not_just_attacked(self):
        sounds=[{'sounding_event_id':'a','span':{'start':q(0),'end':q(2)}},
                {'sounding_event_id':'b','span':{'start':q(1),'end':q(3)}},
                {'sounding_event_id':'c','span':{'start':q(0),'end':q(1)}}]
        self.assertEqual(alignment_membership(sounds,{'point':q(1)}),(['a','b'],['b']))

    def test_span_end_excludes_next_attack(self):
        sounds=[{'sounding_event_id':'a','span':{'start':q(0),'end':q(1)}},
                {'sounding_event_id':'b','span':{'start':q(1),'end':q(2)}}]
        self.assertEqual(alignment_membership(sounds,{'span':{'start':q(0),'end':q(1)}}),(['a'],['a']))

    def test_empty_span_is_not_a_point(self):
        sounds=[{'sounding_event_id':'a','span':{'start':q(0),'end':q(2)}}]
        self.assertEqual(alignment_membership(sounds,{'span':{'start':q(1),'end':q(1)}}),([],[]))
