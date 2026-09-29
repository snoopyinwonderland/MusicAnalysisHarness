import copy
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET
from musicanote_harness.engraving import musicxml_with_canonical_ids
from musicanote_harness.formal_ir import q, pitch_record
from musicanote_harness.source_enrichment import enrich_from_mapped_musicxml


def fixture(voices=('1','2'), durations=(4,1)):
    xml='<score-partwise><part id="P1"><measure number="1"><attributes><divisions>4</divisions></attributes>'
    notes=[]
    for index,(voice,duration) in enumerate(zip(voices,durations)):
        if index: xml+=f'<backup><duration>{durations[index-1]}</duration></backup>'
        xml+=f'<note><pitch><step>D</step><octave>3</octave></pitch><duration>{duration}</duration>'
        xml+=(f'<voice>{voice}</voice>' if voice is not None else '')+'</note>'
        notes.append({'note_id':f'n{index}','source_ref_id':'z' if index==0 else 'a',
            'part_id':'p','display_staff_id':'s','voice_id':f'v{index}','measure_id':'m',
            'onset_in_measure':q(0),'notated_duration_quarter':q(f'{duration}/4'),
            'written_pitch':pitch_record('D3'),'tie_role':'none','grace':{'is_grace':False}})
    xml+='</measure></part></score-partwise>'
    ir={'score':{'score_id':'score'},'parts':[{'part_id':'p','source_part_id':'P1','staff_ids':['s']}],
        'staves':[{'staff_id':'s','staff_number':1}], 'measures':[{'measure_id':'m','printed_measure_number':'1'}],
        'voices':[{'voice_id':f'v{i}','source_voice_number':v or 'voice_0'} for i,v in enumerate(voices)],
        'note_events':notes}
    return xml,ir


def mapped(xml,ir):
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)/'test.musicxml'; path.write_text(xml,encoding='utf-8')
        value,report=musicxml_with_canonical_ids(path,ir)
        return [n.get('id') for n in ET.fromstring(value).iter('note')],report


class SourceNoteMappingTest(unittest.TestCase):
    def test_same_pitch_onset_different_voice_and_duration(self):
        xml,ir=fixture()
        ids,r=mapped(xml,ir)
        self.assertEqual(ids,['n0','n1'])
        self.assertTrue(r['complete'])

    def test_same_duration_different_voice(self):
        xml,ir=fixture(durations=(4,4))
        self.assertEqual(mapped(xml,ir)[0],['n0','n1'])

    def test_unknown_voice_unique_duration(self):
        xml,ir=fixture()
        for v in ir['voices']: v['source_voice_number']='voice_0'
        self.assertEqual(mapped(xml,ir)[0],['n0','n1'])

    def test_unknown_voice_collision_abstains(self):
        xml,ir=fixture(durations=(4,4))
        for v in ir['voices']: v['source_voice_number']='voice_0'
        ids,r=mapped(xml,ir)
        self.assertEqual(ids,[None,None]); self.assertFalse(r['complete'])

    def test_identical_unison_same_voice_abstains(self):
        xml,ir=fixture(voices=('1','1'),durations=(4,4))
        ids,r=mapped(xml,ir)
        self.assertEqual(ids,[None,None]); self.assertFalse(r['complete'])

    def test_unique_geometry_reports_legacy_voice_conflict(self):
        xml,ir=fixture()
        ir['voices'][0]['source_voice_number']='9'
        ids,r=mapped(xml,ir)
        self.assertEqual(ids,['n0','n1']); self.assertTrue(r['complete'])
        self.assertEqual(r['voice_hint_disagreements'][0]['note_id'],'n0')

    def test_input_order_independence_and_no_mutation(self):
        xml,ir=fixture(); before=copy.deepcopy(ir)
        first=mapped(xml,ir); ir['note_events'].reverse()
        self.assertEqual(first,mapped(xml,ir)); ir['note_events'].reverse()
        self.assertEqual(ir,before)

    def test_wrong_duration_not_silently_matched(self):
        xml,ir=fixture(); ir['note_events'][0]['notated_duration_quarter']=q(2)
        self.assertEqual(mapped(xml,ir)[0],[None,'n1'])

    def test_corrupt_enriched_source_voice_not_authoritative(self):
        xml,ir=fixture(durations=(4,4))
        ir['source_references']=[{'source_ref_id':'z','source_voice':'2'}, {'source_ref_id':'a','source_voice':'1'}]
        self.assertEqual(mapped(xml,ir)[0],['n0','n1'])

    def test_enrichment_rejects_swapped_ids_before_mutation(self):
        xml,ir=fixture(); root=ET.fromstring(xml)
        for n,i in zip(root.iter('note'),['n1','n0']): n.set('id',i)
        before=copy.deepcopy(ir)
        with self.assertRaisesRegex(ValueError,'mapped_note_identity_mismatch'):
            enrich_from_mapped_musicxml(ir,ET.tostring(root,encoding='unicode'))
        self.assertEqual(ir,before)

    def test_tie_state_separates_same_voice_unisons(self):
        xml,ir=fixture(voices=('1','1'),durations=(4,4)); root=ET.fromstring(xml)
        ns=list(root.iter('note')); ET.SubElement(ns[0],'tie',{'type':'stop'})
        ir['note_events'][0]['tie_role']='stop'
        self.assertEqual(mapped(ET.tostring(root,encoding='unicode'),ir)[0],['n0','n1'])

    def test_known_voice_resolves_before_missing_voice(self):
        xml,ir=fixture(durations=(4,4)); ir['voices'][1]['source_voice_number']='voice_0'
        self.assertEqual(mapped(xml,ir)[0],['n0','n1'])

    def test_duplicate_ids_rejected(self):
        xml,ir=fixture(); ir['note_events'][1]['note_id']='n0'
        with self.assertRaisesRegex(ValueError,'duplicate_canonical_note_id'): mapped(xml,ir)

    def test_repeated_identical_grace_notes_remain_ambiguous(self):
        xml,ir=fixture(voices=('1','1'),durations=(0,0)); root=ET.fromstring(xml)
        for n in root.iter('note'): ET.SubElement(n,'grace')
        for n in ir['note_events']: n['grace']['is_grace']=True
        self.assertEqual(mapped(ET.tostring(root,encoding='unicode'),ir)[0],[None,None])

    def test_exact_fraction_not_rounded(self):
        xml,ir=fixture(); root=ET.fromstring(xml)
        root.find('.//divisions').text='3'
        ir['note_events'][0]['notated_duration_quarter']=q('4/3')
        ir['note_events'][1]['notated_duration_quarter']=q('1/3')
        self.assertEqual(mapped(ET.tostring(root,encoding='unicode'),ir)[0],['n0','n1'])

    def test_tie_mismatch_not_silently_matched(self):
        xml,ir=fixture(); ir['note_events'][0]['tie_role']='stop'
        self.assertEqual(mapped(xml,ir)[0],[None,'n1'])

    def test_enrichment_rejects_equal_duration_wrong_onset(self):
        xml,ir=fixture(); root=ET.fromstring(xml)
        list(root.iter('note'))[0].set('id','n0')
        ir['note_events'][0]['onset_in_measure']=q(1); before=copy.deepcopy(ir)
        with self.assertRaisesRegex(ValueError,'mapped_note_identity_mismatch'):
            enrich_from_mapped_musicxml(ir,ET.tostring(root,encoding='unicode'))
        self.assertEqual(ir,before)


if __name__=='__main__': unittest.main()
