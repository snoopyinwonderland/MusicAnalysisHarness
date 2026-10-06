import {it,expect} from 'vitest';
// @ts-expect-error Test-only Node import; app tsconfig intentionally excludes Node types.
import {readFileSync} from 'node:fs';

const source=readFileSync(new URL('./FullXmlNotation.tsx',import.meta.url),'utf8');
it('preserves source-note identity independently of playback and search IDs',()=>{
 expect(source).toContain("const sourceNoteIndices=new Map([...doc.getElementsByTagName('note')]");
 expect(source).toContain("setAttribute('data-source-note-index',String(index))");
 const panel=readFileSync(new URL('./PillarReviewPanel.tsx',import.meta.url),'utf8');
 expect(panel).toContain("targets.get(el.getAttribute('data-source-note-index')??'')");
});
it('keeps analysis-only props out of the engraving effect and its dependency list',()=>{
 const render=source.match(/useEffect\(\(\) => \{([\s\S]*?)\}, \[([^\]]+)\]\);/);
 expect(render).toBeDefined();
 expect(render![1]).toContain('tk.loadData(');
 const deps=render![2];
 for(const prop of ['phraseMarkers','phraseSpans','motifSpans','selectedMotifNumber','phraseVisible']){
  expect(deps).not.toContain(prop);
  expect(render![1]).not.toMatch(new RegExp(`\\b${prop}\\b`));
 }
 expect(deps).toContain('xml');expect(deps).toContain('streamId');
});
it('keeps rendered page DOM memoized independently of overlay state',()=>{
 expect(source).toContain('const RenderedScorePage=memo(');
 expect(source).toContain('<RenderedScorePage key={i} svg={svg} />');
 expect(source).toContain('useLayoutEffect');
});
it('passes a numeric semitone transpose on every render and explicitly clears it on reset',()=>{
 expect(source).toContain("transpose: transpose || ''");
 const render=source.match(/useEffect\(\(\) => \{([\s\S]*?)\}, \[([^\]]+)\]\);/);
 expect(render).toBeDefined();
 expect(render![2]).toContain('transpose');
});
it('filters the temporary render document when a subset of score parts is active',()=>{
 expect(source).toContain('applyScoreViewSelections(doc,selections)');
 expect(source).toContain('applyPartViewSelection(doc,partIds)');
 expect(source.indexOf("const sourceNoteIndices=new Map([...doc.getElementsByTagName('note')]")).toBeLessThan(source.indexOf('applyPartViewSelection(doc,partIds)'));
 const render=source.match(/useEffect\(\(\) => \{([\s\S]*?)\}, \[([^\]]+)\]\);/);
 expect(render).toBeDefined();
 expect(render![2]).toContain('partIds');
 expect(render![2]).toContain('selections');
});
it('uses pre-transform source lanes for search, playback, and analysis anchors',()=>{
 expect(source).toContain('const sourceNoteIdentities=sourceNoteIdentityMap(doc,measureOrdinalOffset)');
 expect(source.indexOf('sourceNoteIdentityMap(doc,measureOrdinalOffset)')).toBeLessThan(source.indexOf('applyScoreViewSelections(doc,selections)'));
 expect(source).toContain('findSourceStreamNote(ordered,sourceNoteIdentities,streamId,target,used)');
 expect(source).toContain('findSourceStreamNote(ordered,sourceNoteIdentities,streamId,target,playbackUsed)');
 expect(source).toContain('findSourceStreamNote(analysisOrdered,sourceNoteIdentities,analysisStreamId,target)');
});
