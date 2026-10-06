import {readFileSync,writeFileSync,existsSync} from 'node:fs';
import {withQueryCopy} from './evaluation-query-copy.mjs';
import {createServer} from 'vite';
import createModule from 'verovio/wasm';
import {VerovioToolkit} from 'verovio/esm';
import {comparisonNotation,htmlEscape as esc} from '../server/preclearance-report.mjs';
import {namespaceSvg,softTone} from './comparison-media.mjs';
const batch=process.argv[2]??'memory-variation-50-v1',dir='evaluation/reports/'+batch,runs='evaluation/runs/'+batch;
const suite=JSON.parse(readFileSync(dir+'/suite.json')),rows=[];
const server=await createServer({server:{middlewareMode:true},appType:'custom'});
try{
 const {suggestQueries}=await server.ssrLoadModule('/src/search/querySuggestions.ts');
 for(const c of suite.cases){
  const b=suite.bases.find(b=>b.baseId===c.baseId),path=runs+'/'+c.caseId+'.json',retry=runs+'/'+c.caseId+'.retry.json';
  const initial=existsSync(path)?JSON.parse(readFileSync(path)):null,r=existsSync(retry)?JSON.parse(readFileSync(retry)):initial;
  const all=[...(r?.result?.exact??[]),...(r?.result?.similar??[])],source=all.find(m=>m.work.sourceId===b.expected.sourceId);
  const pairs=m=>m.alignment.filter(a=>a.queryIndex!==null&&a.candidateIndex!==null);
  const targets=m=>pairs(m).map(a=>m.work.notes[a.candidateIndex]).filter(Boolean);
  const retained=b.indexLinks.filter(l=>!c.changedSourceIds.includes(b.query.events[b.xmlEvents.findIndex(e=>e.id===l.eventId)].id)).map(l=>l.note);
  const window=all.findIndex(m=>m.work.workId===b.expected.workId&&retained.filter(n=>targets(m).some(t=>Math.abs(n.o-t.onset)<1e-5&&n.p===t.pitchMidi)).length/retained.length>=.8);
  const invalid=all.flatMap((m,i)=>m.alignment.some(p=>p.candidateIndex!==null&&(!Number.isInteger(p.candidateIndex)||!m.work.notes[p.candidateIndex])||p.queryIndex!==null&&(p.queryIndex<0||p.queryIndex>=c.query.events.filter(e=>e.kind==='note').length))?[i+1]:[]);
  const issues=[];
  if(r?.status==='failed')issues.push('execution-error');
  if(c.positive&&r?.status==='completed'&&!r.sourceRank)issues.push(r.trace?.inCandidates?'source-candidate-not-returned':'source-not-in-candidates');
  if(c.positive&&source&&window<0)issues.push('representative-window-differs');
  if(source&&pairs(source).length<c.query.events.filter(e=>e.kind==='note').length)issues.push('partial-query-alignment');
  if(invalid.length)issues.push('invalid-alignment-reference');
  const suggestions=r?.result?suggestQueries(c.query,all):[];
  const queryNotes=c.query.events.filter(e=>e.kind==='note');
  const pitchEdit=c.transformation?.octave??c.transformation?.pitch;
  const changedNoteAlignment=pitchEdit?(()=>{const i=queryNotes.findIndex(e=>e.id===pitchEdit.eventId),a=source?.alignment.find(a=>a.queryIndex===i),n=a?.candidateIndex!=null?source.work.notes[a.candidateIndex]:null;return {queryNoteIndex:i,queryPitch:queryNotes[i]?.pitchMidi,originalPitch:pitchEdit.from,sourcePitch:n?.pitchMidi??null,sourceOnset:n?.onset??null,alignmentType:a?.type??null,unmatched:!n}})():null;
  const row={caseId:c.caseId,baseId:c.baseId,type:c.kind,description:c.description,title:b.expected.title,query:c.query,positive:c.positive,
   originalNoteLength:c.length??b.query.events.filter(e=>e.kind==='note').length,queryNoteLength:queryNotes.length,meter:c.query.meter,
   changedNoteAlignment,
   status:r?.status??'pending',initialStatus:initial?.status,retried:existsSync(retry),elapsedMs:r?.elapsedMs,sourceRank:r?.sourceRank??null,
   sourceScore:source?.ranking??null,sourceScores:source?.scores??null,sourceIsExact:(r?.result?.exact??[]).includes(source),
   returnedCount:all.length,exactCount:r?.result?.exact?.length??0,sameScoreBeforeSource:source?all.slice(0,all.indexOf(source)).filter(m=>Math.abs(m.ranking-source.ranking)<1e-6).length:0,
   representativeWindowRank:window<0?null:window+1,sourcePairedNotes:source?pairs(source).length:0,
   originalStartInOccurrences:source?.partOccurrences?.some(p=>p.streamId===b.expected.streamId&&p.measures?.includes(b.focus[0].m))??false,
   issues,invalidAlignmentRanks:invalid,suggestions,trace:r?.trace,error:r?.error,
   top:all.map((m,i)=>({rank:i+1,title:m.work.title,sourceId:m.work.sourceId,streamId:m.work.streamId,score:m.ranking,scores:m.scores,isExpectedSource:m===source,pairedNotes:pairs(m).length,
    url:'/score?'+new URLSearchParams({workId:m.work.workId,start:m.startMeasure,end:m.endMeasure,source:'search',targets:targets(m).map(n=>n.onset+':'+n.pitchMidi).join(',')})})).filter(t=>t.rank<=10||t.isExpectedSource)};
  rows.push(row);
 }
}finally{await server.close()}
for(const row of rows){
 const baseline=rows.find(r=>r.baseId===row.baseId&&r.type==='original');
 row.baselineRank=baseline?.sourceRank??null;
 row.rankChange=row.sourceRank&&row.baselineRank?row.sourceRank-row.baselineRank:null;
 row.reviewNotes=[];
 if(row.sourceIsExact&&row.type==='articulation-rest')row.issues.push('articulation-collapsed-to-exact');
 if(row.sourceIsExact&&row.type==='rhythm-even')row.issues.push('exact-variation-needs-duration-audit');
 if(row.issues.includes('partial-query-alignment'))row.reviewNotes.push(row.type==='repeat-split'?'One added repeated attack can legitimately align to no separate original attack; inspect split/merge semantics before treating this as a failure.':'Check omitted query attacks against source context; index validity alone does not establish correct highlighting.');
 if(row.issues.includes('representative-window-differs'))row.reviewNotes.push('Inspect equivalent repeated passages and occurrence links before declaring a wrong match.');
 if(row.sourceScore>=99&&!row.sourceIsExact&&row.type!=='original')row.reviewNotes.push('Near-maximum non-exact score: audit score saturation and user-facing exact/similar distinction.');
 if(!row.positive)row.reviewNotes.push('Reversed pitch order is a challenge probe, not a certified unrelated negative; human relevance review remains required.');
}
const types=[...new Set(rows.map(r=>r.type))];
const groups=types.map(type=>{const rs=rows.filter(r=>r.type===type);return {type,total:rs.length,completed:rs.filter(r=>r.status==='completed').length,errors:rs.filter(r=>r.status==='failed').length,found:rs.filter(r=>r.sourceRank).length,top5:rs.filter(r=>r.sourceRank&&r.sourceRank<=5).length,window:rs.filter(r=>r.representativeWindowRank).length,suggested:rs.filter(r=>r.suggestions.length).length}});
const lengthGroups=[...new Set(rows.map(r=>r.originalNoteLength))].sort((a,b)=>b-a).flatMap(length=>types.map(type=>{const a=rows.filter(r=>r.originalNoteLength===length&&r.type===type);return {length,type,total:a.length,completed:a.filter(r=>r.status==='completed').length,top5:a.filter(r=>r.sourceRank&&r.sourceRank<=5).length,top10:a.filter(r=>r.sourceRank&&r.sourceRank<=10).length,found:a.filter(r=>r.sourceRank).length}}));
writeFileSync(dir+'/results.json',JSON.stringify({generatedAt:new Date().toISOString(),complete:rows.every(r=>r.status!=='pending'),groups,lengthGroups,rows},null,2));
const md=['# '+(suite.title??'기억 입력 변형 50개')+' — 검색 결과','',
 '| 유형 | 완료/수 | 원본 회수 | Top5 | 대표 구간 대응 | 추천 발생 | 오류 |','|---|---:|---:|---:|---:|---:|---:|',
 ...groups.map(g=>'| '+[g.type,g.completed+'/'+g.total,g.found,g.top5,g.window,g.suggested,g.errors].join(' | ')+' |'),'',
 '원본 source 파일의 top100 회수다. 반복 구간 대표 선택과 마디 번호 표기 차이 때문에 대표 구간 대응은 보조 지표다. 역순 대조는 음악적으로 무관한 정답 집합이 아니다. 추천 발생 자체가 올바른 보완이라는 뜻은 아니다. 상위 후보의 음악적 순위 정당성과 실제 SVG 강조 배치는 사람의 검토가 필요하다.',''];
md.push('## 길이별 성적','','| 원형 음수 | 유형 | 완료/수 | Top5 | Top10 | 반환 내 회수 |','|---:|---|---:|---:|---:|---:|',...lengthGroups.map(g=>'| '+[g.length,g.type,g.completed+'/'+g.total,g.top5,g.top10,g.found].join(' | ')+' |'),'');
for(const r of rows)md.push('## '+r.caseId+' · '+r.title,'',r.description,'',
 'Query: '+r.query.events.map(e=>(e.kind==='rest'?'Rest':String(e.pitchMidi))+'('+e.durationRatio+')').join(' '),'',
 '상태 '+r.status+' / 원본 순위 '+(r.sourceRank??'미회수')+' / Exact '+r.sourceIsExact+' / 관찰 '+(r.issues.join(', ')||'자동 경고 없음'),'',
 ...r.top.map(t=>'- '+t.rank+'위 '+t.title+' · '+t.score.toFixed(1)+' · '+t.pairedNotes+'음 대응'),'');
writeFileSync(dir+'/REPORT.md',md.join('\n'));
const tk=new VerovioToolkit(await createModule()),tracks=[],renderAudit=[];
tk.setOptions({scale:30,pageWidth:1700,pageHeight:2100,adjustPageHeight:true,breaks:'auto',header:'none',footer:'none',svgViewBox:true});
function draw(q,ids){
 const prefix='mem-'+tracks.length+'-',notation=comparisonNotation(q.events,q.meter,prefix,ids);
 if(!tk.loadData(notation.mei))throw Error('Verovio failed');let svg='';
 for(let p=1;p<=tk.getPageCount();p++)svg+=tk.renderToSVG(p);
 for(const id of notation.redIds)if(!svg.includes('id="'+id+'"'))throw Error('Missing note ID');
 svg=namespaceSvg(svg,prefix);renderAudit.push({notes:q.events.filter(e=>e.kind==='note').length,highlighted:notation.redIds.length,pages:tk.getPageCount()});
 const style=notation.redIds.map(id=>'[id="'+prefix+id+'"],[id="'+prefix+id+'"] *{fill:#b52d27!important;stroke:#b52d27!important}').join('');
 return '<button data-play="'+(tracks.push(q.events)-1)+'">▶ 재생</button><div class="notation"><style>'+style+'</style>'+svg+'</div>';
}
const rankText=(rank,status)=>rank?rank+'위':status==='failed'?'실행 오류':status==='pending'?'미실행':'반환 결과에 없음';
const scoreText=score=>Number.isFinite(score)?score.toFixed(1):'—';
const kindNames={'original':'원형','local-octave':'한 음 옥타브 이동','octave-plus-omission':'옥타브 + 장식음 삭제','absorb-ornament':'장식음 삭제·음가 합침','repeat-split':'동음 분할','rhythm-even':'리듬 균등화','articulation-rest':'음 끝 쉼표','start-shift':'첫 음 생략','reversed-control':'역순 대조'};
const rankStyle='<style>.rank-badge{font-size:22px;background:#eaf3fa;padding:16px;border-left:5px solid #2876a1}.rank-table{border-collapse:collapse;width:100%;font-size:14px}.rank-table th,.rank-table td{padding:10px;border-bottom:1px solid #d9e1e7;text-align:left}.rank-table th{background:#f1f5f8}.expected-row{background:#edf7ee}.table-scroll{overflow:auto}section{scroll-margin-top:65px}</style>';
Object.assign(kindNames,{'pitch-change':'한 음 반음·온음 변경','ornament-delete':'장식음 후보 삭제·시간 축소','ornament-delete-preserve-time':'장식음 삭제·뒤 음 박자 위치 유지'});
const overview=rankStyle+'<section><h2>테스트별 원곡 검색 순위</h2><p>원형과 입력 Query를 각각 검색했을 때 기대한 원본 파일이 나온 순위입니다. 변형 후 1위 유지가 필수는 아니며 상위권 회수를 긍정적으로 봅니다. 같은 작품의 다른 파일은 별도 순위일 수 있습니다.</p><div class="table-scroll"><table class="rank-table"><thead><tr><th>사례</th><th>곡명</th><th>박자</th><th>유형</th><th>원형 검색</th><th>이 Query 검색</th><th>원곡 점수</th></tr></thead><tbody>'+rows.map(r=>'<tr><td><a href="#'+esc(r.caseId)+'">'+esc(r.caseId)+'</a></td><td>'+esc(r.title)+'</td><td>'+esc(r.meter)+'</td><td>'+esc(kindNames[r.type]??r.type)+'</td><td>'+rankText(r.baselineRank,rows.find(b=>b.baseId===r.baseId&&b.type==='original')?.status)+'</td><td><strong>'+rankText(r.sourceRank,r.status)+'</strong></td><td>'+scoreText(r.sourceScore)+'</td></tr>').join('')+'</tbody></table></div></section>';
const cards=rows.map(r=>{
 const c=suite.cases.find(c=>c.caseId===r.caseId),b=suite.bases.find(b=>b.baseId===r.baseId);
 const resultTable='<h3>실제 검색 결과 — 상위 10개'+(r.sourceRank>10?' 및 원본 파일':'')+'</h3><div class="table-scroll"><table class="rank-table"><thead><tr><th>검색 순위</th><th>곡명</th><th>총점</th><th>Melody Interval</th><th>Rhythm</th></tr></thead><tbody>'+r.top.map(t=>'<tr class="'+(t.isExpectedSource?'expected-row':'')+'"><td><strong>'+t.rank+'위</strong></td><td><a target="_blank" href="'+esc(t.url)+'">'+esc(t.title)+'</a>'+(t.isExpectedSource?' · 기대한 원본 파일':'')+'</td><td>'+scoreText(t.score)+'</td><td>'+scoreText(t.scores?.interval)+'</td><td>'+scoreText(t.scores?.rhythm)+'</td></tr>').join('')+'</tbody></table></div>';
 return '<section id="'+esc(r.caseId)+'"><h2>'+esc(r.caseId+' · '+r.title)+'</h2><p>'+esc(r.description)+'</p><div class="rank-badge">이 Query의 원곡 검색 순위: <strong>'+rankText(r.sourceRank,r.status)+'</strong> · 원형 검색: '+rankText(r.baselineRank,rows.find(b=>b.baseId===r.baseId&&b.type==='original')?.status)+'</div><p>'+esc(r.issues.join(', '))+'</p><div class="grid"><article><h3>원형</h3>'+draw(b.query,c.changedSourceIds)+'</article><article><h3>입력 Query</h3>'+draw(c.query,c.changedSourceIds)+'</article></div>'+resultTable+'<details><summary>Query JSON</summary><pre>'+esc(JSON.stringify({schema:'musicanote-query',query:c.query},null,2))+'</pre></details></section>';
}).join('');
tk.destroy();
const html='<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>기억 입력 변형 50개</title><style>body{background:#edf1f5;color:#243448;font:16px system-ui;margin:0}header,section{background:white;margin:18px;padding:22px;border-radius:12px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}.grid>*{min-width:0}.notation{overflow:auto}.notation>svg{width:100%;min-width:600px;height:auto;display:block}h2{font-size:20px}button{padding:10px;margin:5px}pre{white-space:pre-wrap}#stop{position:sticky;top:0;z-index:3}@media(max-width:1000px){.grid{grid-template-columns:1fr}}</style><header><h1>기억 입력 변형 50개 + 대조 15개</h1><p>붉은 음은 변형 대상입니다. 악보는 입력 비교용 재기보이며 원본 마디 번호와 다릅니다.</p><a href="REPORT.md">결과 표</a> · <a href="results.json">결과 JSON</a> · <a href="suite.json">전체 Query</a></header><button id="stop">■ 재생 정지</button>'+cards+'<script>'+softTone.toString()+';const tracks='+JSON.stringify(tracks).replaceAll('<','\\u003c')+';let ctx,nodes=[],token=0;function stop(){token++;for(const n of nodes)try{n.stop()}catch{}nodes=[]}document.getElementById("stop").onclick=stop;document.querySelectorAll("[data-play]").forEach(b=>b.onclick=async()=>{stop();const old=token;ctx??=new AudioContext();await ctx.resume();if(old!==token)return;let t=ctx.currentTime+.1;for(const e of tracks[+b.dataset.play]){const d=e.durationRatio*60/90;if(e.kind==="note")softTone(ctx,ctx.destination,e.pitchMidi,t,d,nodes);t+=d}});</script></html>';
new Function(html.match(/<script>([\s\S]*?)<\/script>/)[1]);
const lengthSummary=lengthGroups.length>types.length?'<section><h2>길이별 회수 성적</h2><p>삭제 변형은 원형보다 한 음 적습니다. 완료 수를 먼저 확인하세요. 같은 원형의 paired 테스트이며 1위가 필수는 아닙니다.</p><div class="table-scroll"><table class="rank-table"><thead><tr><th>원형 음수</th><th>유형</th><th>완료/전체</th><th>Top5</th><th>Top10</th></tr></thead><tbody>'+lengthGroups.map(g=>'<tr><td>'+g.length+'</td><td>'+esc(kindNames[g.type]??g.type)+'</td><td>'+g.completed+'/'+g.total+'</td><td>'+g.top5+'</td><td>'+g.top10+'</td></tr>').join('')+'</tbody></table></div></section>':'';
writeFileSync(dir+'/index.html',withQueryCopy(html,suite).replace('</header>','</header>'+overview+lengthSummary).replaceAll('기억 입력 변형 50개 + 대조 15개',esc(suite.title??'기억 입력 변형 50개 + 대조 15개')).replaceAll('기억 입력 변형 50개',esc(suite.title??'기억 입력 변형 50개')));writeFileSync(dir+'/render-audit.json',JSON.stringify(renderAudit,null,2));console.log(JSON.stringify({groups,rendered:renderAudit.length}));
