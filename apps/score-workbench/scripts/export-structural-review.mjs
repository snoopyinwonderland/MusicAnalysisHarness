import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {join} from 'node:path';
import createModule from 'verovio/wasm';
import {VerovioToolkit} from 'verovio/esm';
import {comparisonNotation,htmlEscape as esc} from '../server/preclearance-report.mjs';
import {getWork} from '../server/search-api.mjs';
import {markXmlTargets} from '../server/xml-target-verification.mjs';
const dir=process.argv[2];if(!dir)throw Error('New output directory required');mkdirSync(dir,{recursive:false});
const runDir='evaluation/runs/structural-baseline-v1',suite=JSON.parse(readFileSync('evaluation/reports/structural-100-preview-v1/suite.json')),summary=JSON.parse(readFileSync(join(runDir,'summary.json')));
const chosen=summary.runs.filter(r=>r.kind!=='original-control'&&(!r.sourceWindowProxyRank||r.sourceRank>5));
const tk=new VerovioToolkit(await createModule());tk.setOptions({scale:30,pageWidth:1800,pageHeight:2200,adjustPageHeight:true,breaks:'auto',header:'none',footer:'none',svgViewBox:true});
const tracks=[],audit=[],records=[];
const css=(ids,color)=>ids.map(id=>`[id="${id}"],[id="${id}"] *{fill:${color}!important;stroke:${color}!important}`).join('');
function svgFor(data){if(!tk.loadData(data))throw Error('Verovio failed');if(tk.getPageCount()>20)throw Error('Excerpt too large');let svg='';for(let p=1;p<=tk.getPageCount();p++)svg+=tk.renderToSVG(p);if(!svg.includes('class="note"'))throw Error('No notes');return svg}
function player(events){return `<button data-play="${tracks.push(events)-1}">▶ 재생</button>`}
function queryScore(events,meter,protectedIds,changed){
 const prefix='q'+tracks.length,a=comparisonNotation(events,meter,prefix,protectedIds),b=comparisonNotation(events,meter,prefix,changed),svg=svgFor(a.mei);
 for(const id of [...a.redIds,...b.redIds])if(!svg.includes(`id="${id}"`))throw Error('Missing Query note');
 audit.push({type:'query',notesPresent:true,markedIdsVerified:true});
 return player(events)+`<div class="score"><style>${css(a.redIds,'#215eae')}${css(b.redIds,'#be3524')}</style>${svg}</div>`;
}
function resultScore(m){
 const targets=m.alignment.filter(p=>p.queryIndex!==null&&p.candidateIndex!==null).map(p=>m.work.notes[p.candidateIndex]);
 if(!targets.length||targets.some(n=>!n||!Number.isFinite(n.measureOrdinal)))throw Error('Missing result coordinates');
 const a=Math.min(...targets.map(n=>n.measureOrdinal)),b=Math.max(...targets.map(n=>n.measureOrdinal));
 const work=getWork(m.work.workId,{start:m.startMeasure,end:m.endMeasure,ordinalStart:a,ordinalEnd:b,targets:targets.map(n=>`${n.onset}:${n.pitchMidi}`).join(','),excerpt:'1'});
 const marked=markXmlTargets(work?.xml||'',m.work.streamId,targets,Number(work?.previewOrdinalStart||a)-1);
 const svg=svgFor(marked.xml),missing=marked.ids.filter(id=>!svg.includes(`id="${id}"`));
 if(marked.unresolved||missing.length)throw Error('Unresolved highlight '+JSON.stringify({unresolved:marked.unresolved,missing}));
 const events=[];let t=m.work.notes[0]?.onset??0;
 for(const n of m.work.notes){if(n.onset>t+1e-6)events.push({kind:'rest',durationRatio:n.onset-t});events.push(n);t=Math.max(t,n.onset+n.durationRatio)}
 audit.push({type:'source-xml-result',workId:m.work.workId,requested:targets.length,resolved:marked.resolved,renderedIds:marked.ids.length});
 const url='/score?'+new URLSearchParams({workId:m.work.workId,start:String(m.startMeasure),end:String(m.endMeasure),source:'search',targets:targets.map(n=>`${n.onset}:${n.pitchMidi}`).join(',')});
 return `<p>${esc(m.work.title)} · ${esc(m.work.partName||m.work.streamId)} · ${m.startMeasure}–${m.endMeasure}마디 · 점수 ${m.ranking.toFixed(1)}</p>${player(events)} <a href="${esc(url)}" target="_blank">상세 악보</a><p class="small">재생은 저장된 검색 성부 음표 기준입니다. 원 XML 악보의 다른 성부까지 재생하지 않습니다.</p><div class="score">${svg}<style>${css(marked.ids,'#be3524')}</style></div>`;
}
const names={'passing-insertion':'경과 형태 삽입','neighbor-insertion':'반음 보조 형태 삽입','repeat-split':'같은 음 재타격','internal-rhythm':'내부 음가 이동','combined':'경과·보조 형태 결합'};
const cards=[];
for(const row of chosen){
 const c=suite.cases.find(c=>c.caseId===row.caseId),base=suite.bases.find(b=>b.baseId===c.baseId),run=JSON.parse(readFileSync(join(runDir,row.caseId+'.json'))),all=[...run.result.exact,...run.result.similar],m=all[row.sourceRank-1];
 if(m.work.sourceId!==base.expected.sourceId)throw Error('Wrong source');
 const changed=c.changes.flatMap(x=>[...(x.addedIds??[]),...(x.ids??[]),...(x.eventId?[x.eventId]:[])]);
 records.push({caseId:c.caseId,kind:c.kind,sourceRank:row.sourceRank,sourceWindowProxyRank:row.sourceWindowProxyRank,originalQuery:base.query,variantQuery:c.query,expected:base.expected,focus:base.focus,changes:c.changes,sourceMatch:m,top1:row.sourceRank>5?all[0]:null,diagnosis:'pending musical review'});
 let result;try{result=resultScore(m)}catch(e){audit.push({caseId:c.caseId,type:'error',message:e.message});result=`<p>원 XML 출력 검증 실패: ${esc(e.message)}</p>`}
 cards.push(`<section id="${c.caseId}"><h2>${c.caseId} · ${esc(base.expected.title)} — ${names[c.kind]}</h2><p>원곡 순위 <strong>${row.sourceRank}위</strong> · 기대 위치 ${esc(base.focus[0].mn)}–${esc(base.focus.at(-1).mn)}마디 / ${esc(base.expected.streamId)} · ${row.sourceWindowProxyRank?'원 구간 대응 기준 통과':'원 구간 대응 기준 미통과 — 잘못된 결과로 확정한 것은 아님'}</p><div class="pair"><div><h3>① 변형 전 멜로디</h3>${queryScore(base.query.events,base.query.meter,base.generatorProtectedIds,[])}</div><div><h3>② 검색에 사용한 변형</h3>${queryScore(c.events,c.query.meter,base.generatorProtectedIds,changed)}</div></div><h3>③ 실제로 검색된 원곡 구간 (${row.sourceRank}위)</h3>${result}${row.sourceRank>5?`<details><summary>④ 이 검색의 1위 결과와 비교</summary>${resultScore(all[0])}</details>`:''}<details><summary>Query·변형 기록</summary><pre>${esc(JSON.stringify({original:base.query,variant:c.query,changes:c.changes},null,2))}</pre></details></section>`);
}
const html=`<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>구조 변형 검색 검토 12개</title><style>body{margin:0;background:#eef2f5;color:#1c2937;font:16px system-ui}header,section{background:white;margin:20px;padding:24px;border-radius:12px}h1{font-size:25px}h2{font-size:21px}h3{font-size:17px}.pair{display:grid;grid-template-columns:1fr 1fr;gap:20px}.pair>div{min-width:0}.score{overflow:auto}.score svg{min-width:650px;width:100%;height:auto;display:block}button{padding:9px 16px;margin:6px 0}.small{font-size:13px;color:#586476}pre{white-space:pre-wrap;font-size:12px}nav a{display:inline-block;margin:5px}#controls{position:sticky;top:0;background:#fff;padding:8px 25px;border-bottom:1px solid #ccc;z-index:10}@media(max-width:900px){.pair{grid-template-columns:1fr}}</style><header><h1>추가 검토 사례 ${chosen.length}개</h1><p>원 구간 대응 미확인 11개 + 원곡 8위 사례 1개. 파랑: 테스트 보존음, 빨강: 변형된 음 또는 결과의 실제 정렬 음. 빨강이 완전 일치를 뜻하지는 않습니다.</p><p>①②는 Query 비교용 재기보여서 그림의 마디 번호는 원본 번호가 아닙니다. ③은 원 XML 발췌입니다. 다른 반복 구간을 찾았을 가능성도 있으므로 회수 실패로 단정하지 않습니다.</p><nav>${chosen.map(r=>`<a href="#${r.caseId}">${r.caseId}</a>`).join('')}</nav><a href="cases.json">전체 사례 데이터</a> · <a href="../structural-100-preview-v1/index.html">100개 전체 미리보기</a></header><div id="controls"><button id="stop">■ 정지</button> <span id="status">재생 대기 · 90 BPM</span></div>${cards.join('')}<script>const tracks=${JSON.stringify(tracks).replaceAll('<','\\u003c')};let ctx,nodes=[],token=0,timer;function stop(){token++;clearTimeout(timer);for(const n of nodes)try{n.stop()}catch{}nodes=[];document.getElementById('status').textContent='재생 대기'}document.getElementById('stop').onclick=stop;document.querySelectorAll('[data-play]').forEach(b=>b.onclick=async()=>{stop();const old=token;ctx??=new AudioContext();await ctx.resume();if(old!==token)return;let t=ctx.currentTime+.1;for(const e of tracks[+b.dataset.play]){const d=e.durationRatio*60/90;if(e.kind==='note'){const o=ctx.createOscillator(),g=ctx.createGain();o.type='triangle';o.frequency.value=440*2**((e.pitchMidi-69)/12);g.gain.setValueAtTime(0,t);g.gain.linearRampToValueAtTime(.08,t+Math.min(.01,d/4));g.gain.setValueAtTime(.08,t+d*.8);g.gain.linearRampToValueAtTime(0,t+d);o.connect(g);g.connect(ctx.destination);o.start(t);o.stop(t+d+.01);nodes.push(o)}t+=d}document.getElementById('status').textContent='재생 중 · 90 BPM';timer=setTimeout(stop,(t-ctx.currentTime)*1000+30)});</script></html>`;
new Function(html.match(/<script>([\s\S]*?)<\/script>/)[1]);
writeFileSync(join(dir,'index.html'),html,{flag:'wx'});writeFileSync(join(dir,'cases.json'),JSON.stringify(records,null,2),{flag:'wx'});writeFileSync(join(dir,'render-audit.json'),JSON.stringify(audit,null,2),{flag:'wx'});tk.destroy();console.log(JSON.stringify({cases:chosen.length,rendered:audit.filter(a=>a.type!=='error').length,errors:audit.filter(a=>a.type==='error')}));
