export function MotifDiscoveryPanel({work,comparison,onSelect}:{work:any;comparison:any;onSelect:(number:number)=>void}){
 const discovery=work?.motifDiscovery;if(!discovery)return null;
 if(comparison.error)return <section className="analysis-block"><h3>Motif 가족 비교</h3><p role="status">계산 보류: {comparison.error}</p><p>기존 Motif 결과는 유지됩니다.</p></section>;
 const groups=new Map<number,any[]>();
 for(const span of comparison.spans){const group=groups.get(span.linkedFamily)||[];group.push(span);groups.set(span.linkedFamily,group)}
 return <section className="analysis-block"><h3>Motif 가족 연결 · 실험</h3>
  <p>비교 F는 새 가족 연결 가설입니다. 기존 Motif 구간·번호·피드백 ID는 그대로이며, 이 결과를 정답으로 저장하지 않습니다. 음정 간격과 리듬의 조옮김·역행 반복을 보조 근거로 씁니다.</p>
  <p>새 반복 가족 {discovery.families.length}개 · 기존 구간의 비교 가족 {groups.size}개 · {discovery.runtime?.cacheHit?'캐시':'첫 계산'} {Math.round(discovery.runtime?.durationMs||0)}ms</p>
  {[...groups].map(([family,spans])=><div key={family}><h4>비교 F{family} · {spans.length}구간</h4>{spans.map(span=><button type="button" key={span.motifNumber} onClick={()=>onSelect(span.motifNumber)}>{span.label} · {span.startNote.measure}–{span.endNote.measure}마디{span.linkSources.includes('discovery')?' · 반복 연결 후보':''}</button>)}</div>)}
  {!!discovery.inputWarnings?.length&&<p>붙임줄 입력 확인 {discovery.inputWarnings.length}건은 새 attack으로 처리했습니다.</p>}
  <p>기존 가족 관계와 반복 후보를 합치므로 다른 음형이 잘못 연결될 수 있습니다. 구간 추출 개선이나 화성·종지 분석의 대체가 아닙니다.</p>
 </section>;
}
