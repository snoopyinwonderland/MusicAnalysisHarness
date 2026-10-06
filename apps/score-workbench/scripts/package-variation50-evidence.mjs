import {readFileSync,writeFileSync,mkdirSync,existsSync} from 'node:fs';
import {join,resolve} from 'node:path';
import {structureHash} from '../server/structure-analysis-adapter.mjs';
import {getWork} from '../server/search-api.mjs';
import {validateEvaluationCase} from './evaluation-case-validation.mjs';
const [directory,out]=process.argv.slice(2);if(!directory||!out||existsSync(out))throw Error('Completed 50-directory NEW-evidence-directory');
const suite=JSON.parse(readFileSync(join(directory,'suite.json'),'utf8')),summary=JSON.parse(readFileSync(join(directory,'summary.json'),'utf8'));
if(summary.executed!==50||summary.remaining!==0)throw Error('All 50 attempts must finish before packaging');
mkdirSync(out,{recursive:true});const bases=new Map(),index=[];
for(const c of suite.cases){
 let base=bases.get(c.workId);
 if(!base){const id='B'+String(bases.size+1).padStart(2,'0'),folder=join(out,id);mkdirSync(folder);
  const min=Math.min(...c.sourceFocus.map(n=>n.measureOrdinal)),max=Math.max(...c.sourceFocus.map(n=>n.measureOrdinal)),start=Math.max(1,min-2),end=max+2;
  let xml=null,error=null;try{if(!Number.isFinite(start)||!Number.isFinite(end))throw Error('Source ordinal unavailable');const w=getWork(c.workId,{ordinalStart:start,ordinalEnd:end,targets:c.sourceFocus.map(n=>n.onset+':'+n.pitchMidi).join(','),excerpt:'1'});xml=w?.xml;if(!xml)throw Error('Source XML unavailable')}catch(e){error=e.message}
  const xmlPath=xml?join(folder,'context.musicxml'):'';if(xml)writeFileSync(xmlPath,xml,{flag:'wx'});
  const eventsPath=join(folder,'events.json');writeFileSync(eventsPath,JSON.stringify({schema:'musicanote-case-events/v1',identity:{sourceId:c.sourceId,workId:c.workId,streamId:c.streamId},sourceFocus:c.sourceFocus,events:c.context,reconstruction:c.reconstruction,xmlCaptureError:error},null,2),{flag:'wx'});
  base={id,musicXml:xmlPath,events:eventsPath,sourceHash:xml?structureHash(xml):null,eventHash:structureHash(c.context),xmlError:error};bases.set(c.workId,base);
 }
 const r=JSON.parse(readFileSync(join(directory,c.caseId+'.json'),'utf8'));
 const record={schema:'musicanote-evaluation-case/v1',caseId:c.caseId,createdAt:new Date().toLocaleDateString('sv-SE',{timeZone:'Asia/Seoul'}),status:'draft',replayable:true,tags:[c.category,c.variant],query:c.query,
  expected:{sourceId:c.sourceId,workId:c.workId,streamId:c.streamId,focus:c.sourceFocus.map(n=>({id:n.id,onset:n.onset,pitchMidi:n.pitchMidi,measure:n.measure,measureOrdinal:n.measureOrdinal})),status:'source-retrieval-probe-not-human-relevance-label'},
  observations:[{source:'automated-search',sourceRank:r.sourceRank??null,sourceWindowProxyRank:r.sourceWindowProxyRank??null,elapsedMs:r.elapsedMs,issues:r.issues,invalidAlignmentRanks:r.invalidAlignmentRanks??[]}],diagnoses:[],proposals:r.improvementDirections.map(text=>({text,status:'hypothesis-needs-review'})),
  runs:[{status:r.status,resultPath:resolve(directory,c.caseId+'.json'),fingerprint:suite.fingerprint}],humanReview:c.humanReview,
  knowledgeBase:{schema:'musicanote-case-knowledge/v1',status:'automatic-unreviewed',identity:{sourceId:c.sourceId,workId:c.workId,streamId:c.streamId},sourceSnapshot:{xmlHash:base.sourceHash,eventsHash:base.eventHash,xmlCaptureError:base.xmlError},focus:{events:c.sourceFocus},context:{policy:'source snapshot context plus up-to-two-ordinal-measures original XML'},assets:{musicXml:base.musicXml,events:base.events},
   classification:{phenomenonTypes:[c.category,c.variant],musicalFunctions:[],contextualConditions:[{meter:c.query.meter,noteCount:c.query.events.filter(n=>n.kind==='note').length}],exclusions:['Source retrieval is not proof of correct ranking or copyright infringement'],confidence:'automatic-unreviewed'},ruleLearning:{candidateRules:[],counterexamples:[],reusableFor:['retrieval-regression','alignment-review','transformation-comparison']}}};
 validateEvaluationCase(record);writeFileSync(join(out,c.caseId+'.json'),JSON.stringify(record,null,2),{flag:'wx'});index.push({caseId:c.caseId,path:join(out,c.caseId+'.json'),baseId:base.id});
}
const ordered=summary.runs.map(r=>({...r,...suite.cases.find(c=>c.caseId===r.caseId)})),completed=ordered.filter(r=>r.status==='completed'),times=completed.map(r=>r.elapsedMs).sort((a,b)=>a-b);
const perVariant=[...new Set(ordered.map(c=>c.variant))].map(variant=>{const rs=ordered.filter(r=>r.variant===variant);return {variant,attempts:rs.length,completed:rs.filter(r=>r.status==='completed').length,sourceRetrieved:rs.filter(r=>r.sourceRank!==null&&r.sourceRank!==undefined).length,top1:rs.filter(r=>r.sourceRank===1).length,top5:rs.filter(r=>r.sourceRank&&r.sourceRank<=5).length}});
const aggregate={attempts:50,completed:completed.length,failed:50-completed.length,sourceRetrieved:completed.filter(r=>r.sourceRank).length,top1:completed.filter(r=>r.sourceRank===1).length,top5:completed.filter(r=>r.sourceRank&&r.sourceRank<=5).length,medianMs:times[Math.floor(times.length/2)],p95Ms:times[Math.max(0,Math.ceil(times.length*.95)-1)],invalidAlignmentCases:completed.filter(r=>r.invalidAlignmentRanks?.length).map(r=>r.caseId),perVariant,baseAssets:[...bases.values()],sourceSuites:directory,index};
writeFileSync(join(out,'index.json'),JSON.stringify(aggregate,null,2),{flag:'wx'});console.log(JSON.stringify({...aggregate,index:undefined}));
const escape=s=>String(s??'').replaceAll('|','/').replaceAll('\n',' '),melody=es=>es.map(e=>e.kind==='rest'?`Rest(${e.durationRatio})`:`${['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'][e.pitchMidi%12]}${Math.floor(e.pitchMidi/12)-1}(${e.durationRatio})`).join(' ');
const md=['# 개발 후 멜로디 변형 50개 — 결과와 검토 자료','',`완료 ${aggregate.completed}/50, 원본 source 회수 ${aggregate.sourceRetrieved}/50, 1위 ${aggregate.top1}/50, 상위 5개 ${aggregate.top5}/50. 중앙 ${(aggregate.medianMs/1000).toFixed(2)}초, p95 ${(aggregate.p95Ms/1000).toFixed(2)}초.`, '',
 '5개 원본 구간 × 10개 변형의 paired 테스트다. 데이터베이스 전체의 대표 표본이나 저작권 침해 정답 집합은 아니다. 원본 미회수는 다른 판본 회수 여부와 음악적 타당성을 추가 검토해야 한다. 전체 Query와 검색 결과는 사례 JSON 및 원 실행 경로에 보존한다.','',
 '| 유형 | 실행 | source 회수 | 1위 | top 5 |','|---|---:|---:|---:|---:|',...perVariant.map(v=>`| ${v.variant} | ${v.completed}/${v.attempts} | ${v.sourceRetrieved} | ${v.top1} | ${v.top5} |`),'',
 '## 발견한 문제와 후속 검증 방향','',
 '- 원형/전조/전체 음가 변경이 안정적인지 먼저 보고, 개별 음 변경·옥타브 변경·삭제에서 회수가 무너지는지를 paired 비교한다.','- 같은 음 반복·음정 종류가 적은 구간은 작은 변경도 정보량과 후보 생성에 큰 영향을 줄 수 있다. 검색 후보 단계와 최종 순위 단계를 분리 진단한다.','- 원본이 순위에서 밀렸다는 것만으로 오류라고 확정하지 않는다. 상위 결과의 실제 선율·리듬·연속성·내성부 여부를 검토한다.','- API 참조 검증은 실제 SVG 전체의 강조/배치 검증이 아니다. 시각적 판정과 상위 결과의 음악적 정당성은 미검토로 남긴다.','- 아래 개선안은 후속 실험 후보이며 이번 결과에 맞춰 production 순위를 개별 조정하지 않았다.',''];
for(const c of suite.cases){const r=JSON.parse(readFileSync(join(directory,c.caseId+'.json'),'utf8')),rs=[...(r.result?.exact??[]),...(r.result?.similar??[])];
 md.push(`## ${c.caseId} — ${c.category} / ${c.variant}`,'',`원본: ${escape(c.sourceId)} · ${escape(c.streamId)} · ${c.sourceFocus[0].measure}–${c.sourceFocus.at(-1).measure}마디`, '',`Query: ${melody(c.query.events)}`,'',`상태: ${r.status} · 원본 순위 ${r.sourceRank??'미회수'} · 시간 ${(r.elapsedMs/1000).toFixed(2)}초`, '', '| 순위 | 결과 | 유사도 | 마디 |','|---|---|---:|---|',...rs.slice(0,3).map((x,i)=>`| ${i+1} | ${escape(x.work.title)} / ${escape(x.work.streamId)} | ${Number(x.localSimilarity).toFixed(2)} | ${x.startMeasure}–${x.endMeasure} |`),'',`관찰: ${r.issues.length?r.issues.join('; '):'자동 회수 검사에서 경고 없음. 음악적 순위 적절성은 미검토.'}`,`개선 후보: ${r.improvementDirections.length?r.improvementDirections.join('; '):'현재 결과 보존 후 전문가 비교.'}`,'');
}
writeFileSync(join(out,'review.md'),md.join('\n'),{flag:'wx'});
