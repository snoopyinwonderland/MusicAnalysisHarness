// Two-layer phrase analysis (server/phrase-breath-layer.mjs, ported from musicomp) shown through the
// existing review-lane preview: the chosen layer is drawn as the dashed Phrase band above the score.
type LayerBoundary={index:number;strength:number;cadence?:{type:string;strength:number}|null;breathEnd?:boolean};
type PhraseLayers={version:string;breath:{starts:number[];boundaries:LayerBoundary[]};phrases:{starts:number[];boundaries:LayerBoundary[]}|null;cadenceSource?:string;error?:string};
type Layer='phrases'|'breath';
const LAYER_LABEL:Record<Layer,string>={phrases:'상위 Phrase',breath:'호흡 단위'};

export function phraseLayerRanges(work:any,layer:Layer){
 const layers:PhraseLayers=work.phraseLayers,notes=work.notes||[];
 const data=layer==='phrases'?layers.phrases:layers.breath;
 if(!data||!notes.length)return[];
 const boundRanges=(data as any).ranges;
 if(Array.isArray(boundRanges))return boundRanges.map((r:any,k:number)=>({...r,
  label:`${LAYER_LABEL[layer]} ${k+1} · ${r.startMeasure}–${r.endMeasure}마디${r.cadence?.type?` · ${r.cadence.type}`:''}`}));
 const cadenceAt=new Map((data.boundaries||[]).map(b=>[b.index,b.cadence?.type||null]));
 const starts=[0,...data.starts.filter(i=>i>0&&i<notes.length)];
 return starts.map((startIndex,k)=>{
  const endIndexExclusive=k+1<starts.length?starts[k+1]:notes.length,first=notes[startIndex],last=notes[endIndexExclusive-1];
  const cadence=k+1<starts.length?cadenceAt.get(endIndexExclusive):null;
  return {startIndex,endIndexExclusive,startEventId:first?.id,startMeasure:first?.measure,endMeasure:last?.measure,cadence,
   label:`${LAYER_LABEL[layer]} ${k+1} · ${first?.measure}–${last?.measure}마디${cadence?` · ${cadence}`:''}`};
 });
}

export function PhraseLayersPanel({work,active,onChange}:{work:any;active:any;onChange:(data:any)=>void}){
 const layers:PhraseLayers|undefined=work?.phraseLayers;
 if(!layers)return null;
 if(layers.error)return <section className="analysis-block"><h3>2층 Phrase 분석</h3><p role="alert">{layers.error}</p></section>;
 const current:Layer|null=active?.source==='phrase-layers'&&active.workId===work.workId?active.layer:null;
 const show=(layer:Layer|null)=>onChange(layer?{source:'phrase-layers',workId:work.workId,layer,ranges:phraseLayerRanges(work,layer)}:null);
 const ranges=current?phraseLayerRanges(work,current):[];
 const cadenceCount=(layers.phrases?.boundaries||[]).filter(b=>b.cadence).length;
 return <section className="analysis-block"><h3>2층 Phrase 분석</h3>
  <p>상위 끝 = 호흡 단위 끝 또는 화성 관문을 통과한 종지 후보 지점{cadenceCount?` (종지 후보를 쓴 Phrase ${cadenceCount}개)`:''}. 전 성부 화성을 읽기 전용으로 참조하며, 기존 경계 분석은 바뀌지 않습니다.</p>
  {(layers as any).inputWarnings?.length>0&&<p className="analysis-note">입력 확인: 이어지지 않는 붙임줄 {(layers as any).inputWarnings.length}건은 새 음으로 읽었습니다.</p>}
  <button type="button" aria-pressed={!current} onClick={()=>show(null)}>현재 경계</button>{' '}
  <button type="button" aria-pressed={current==='phrases'} onClick={()=>show('phrases')}>상위 Phrase {(layers.phrases?.starts.length??0)+1}</button>{' '}
  <button type="button" aria-pressed={current==='breath'} onClick={()=>show('breath')}>호흡 단위 {layers.breath.starts.length+1}</button>
  {current&&<><p>상단 점선 띠가 {LAYER_LABEL[current]}입니다. 비교 중에는 원래 Phrase 띠를 숨깁니다.</p><ol>{ranges.map(r=><li key={r.startIndex}>{r.label}</li>)}</ol></>}
  <p className="analysis-note">{layers.version} · 종지 근거: {layers.cadenceSource||'없음'}</p>
  <p className="analysis-note">미해결 종지 {(layers as any).unresolvedCadences??0}개 · 강도는 확률이 아닙니다. 비교층은 기존 피드백 저장 대상으로 사용하지 않습니다.</p>
 </section>;
}
