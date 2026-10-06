import {it,expect} from 'vitest';
import {readFileSync} from 'node:fs';
import {notationStructureEvidence} from './notation-structure-evidence.mjs';
const xml='<score-partwise><part id="P1"><measure number="1"><attributes><divisions>3</divisions></attributes><note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice><staff>1</staff><beam number="1">begin</beam><tie type="start"/></note><note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice><staff>1</staff><beam number="1">end</beam><tie type="stop"/></note><note><rest/><duration>1</duration><voice>1</voice><staff>1</staff></note></measure></part></score-partwise>';
it('preserves rational durations, source positions, beam and tie marks separately',()=>{
 const a=notationStructureEvidence(xml,'P1:1:1');
 expect(a.observed[0].durationQuarter).toEqual({n:1,d:3});
 expect(a.observed[0].tie).toEqual(['start']);expect(a.observed[1].tie).toEqual(['stop']);
 expect(a.observed[2].kind).toBe('rest');expect(a.beamGroups[0].eventIds).toHaveLength(2);expect(a.beamGroups[0].complete).toBe(true);
 expect(xml.slice(a.observed[0].source.start,a.observed[0].source.end)).toContain('<beam');
 expect(notationStructureEvidence(xml,'P1:1:1')).toEqual(a);
});
it('does not invent groups when beams are absent',()=>{
 expect(notationStructureEvidence(xml.replace(/<beam[^>]*>.*?<\/beam>/g,''),'P1:1:1').beamGroups).toEqual([]);
});
it('reports missing mappings rather than selecting a nearby pitch',()=>{
 const a=notationStructureEvidence(xml,'P1:1:1',[{id:'n',measure:1,beat:1,pitchMidi:61}]);
 expect(a.mappings[0].status).toBe('unresolved');
});
it('extracts preserved real-score observations without changing the snapshot',()=>{
 const root='evaluation/case-assets/S-STRUCT-006/';const {work}=JSON.parse(readFileSync(root+'review-snapshot.json','utf8'));
 const before=JSON.stringify(work);const a=notationStructureEvidence(readFileSync(root+'context.musicxml','utf8'),work.streamId,work.notes);
 expect(JSON.stringify(work)).toBe(before);expect(a.beamGroups.length).toBeGreaterThan(0);
 expect(a.observed.some(n=>n.kind==='rest')).toBe(true);
 expect(a.mappings.filter(m=>m.status==='mapped').length).toBe(work.notes.length);
});
