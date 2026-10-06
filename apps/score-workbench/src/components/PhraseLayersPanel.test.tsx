import {it,expect} from 'vitest';
import {phraseLayerRanges} from './PhraseLayersPanel';
it('uses server-bound ranges and IDs rather than remapping array indices',()=>{
 const range={rangeId:'span1',startIndex:0,endIndexExclusive:2,startEventId:'note1',endEventId:'note2',startMeasure:1,endMeasure:2,cadence:{type:'HC'},span:{start:{num:'0',den:'1'},end:{num:'8',den:'1'}}};
 const work={notes:[{id:'note1'},{id:'note2'}],phraseLayers:{breath:{starts:[],boundaries:[],ranges:[range]},phrases:null}};
 const result=phraseLayerRanges(work,'breath')[0];expect(result.rangeId).toBe('span1');expect(result.span).toEqual(range.span);
 expect(result.label).toBe('호흡 단위 1 · 1–2마디 · HC');
});
