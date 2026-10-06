import {readFileSync,writeFileSync,mkdirSync,existsSync} from 'node:fs';
import createModule from 'verovio/wasm';
import {VerovioToolkit} from 'verovio/esm';
import {comparisonNotation,htmlEscape as esc} from '../server/preclearance-report.mjs';
import {getWork} from '../server/search-api.mjs';
import {markXmlTargets} from '../server/xml-target-verification.mjs';
import {namespaceSvg,softTone} from './comparison-media.mjs';
const out=process.argv[2];if(!out)throw Error('Output required');mkdirSync(out,{recursive:true});
const suite=JSON.parse(readFileSync('evaluation/reports/structural-next40-v1/suite.json'));
const tk=new VerovioToolkit(await createModule());tk.setOptions({scale:28,pageWidth:1800,pageHeight:2200,adjustPageHeight:true,breaks:'auto',header:'none',footer:'none',svgViewBox:true});
const tracks=[],audit=[],rows=[];let serial=0;
function render(data,ids,type){
 if(!tk.loadData(data))throw Error('Verovio load failed');if(tk.getPageCount()>20)throw Error('Oversized excerpt');let svg='';for(let p=1;p<=tk.getPageCount();p++)svg+=tk.renderToSVG(p);
 if(!svg.includes('class="note"'))throw Error('Empty notation');for(const id of ids)if(!svg.includes(`id="${id}"`))throw Error('Missing marked note '+id);
 const prefix='panel'+serial+++'-';svg=namespaceSvg(svg,prefix);
 audit.push({type,marked:ids.length,pages:tk.getPageCount()});
 return `<div class="score"><style>${ids.map(id=>`[id="${prefix}${id}"],[id="${prefix}${id}"] *{fill:#bd342c!important;stroke:#bd342c!important}`).join('')}</style>${svg}</div>`;
}
const player=events=>`<button data-play="${tracks.push(events)-1}">▶ 재생</button>`;
function queryScore(query,ids){const {mei,redIds}=comparisonNotation(query.events,query.meter,'query'+serial,ids);return player(query.events)+render(mei,redIds,'query')}
function resultScore(match){
 const targets=match.alignment.filter(p=>p.queryIndex!==null&&p.candidateIndex!==null).map(p=>match.work.notes[p.candidateIndex]);
 if(!targets.length||targets.some(n=>!n))throw Error('Missing alignment note');
 const a=Math.min(...targets.map(n=>n.measureOrdinal)),b=Math.max(...targets.map(n=>n.measureOrdinal));
 const params={workId:match.work.workId,start:String(match.startMeasure),end:String(match.endMeasure),source:'search',targets:targets.map(n=>`${n.onset}:${n.pitchMidi}`).join(',')};
 const work=getWork(match.work.workId,{...params,ordinalStart:a,ordinalEnd:b,excerpt:'1'}),marked=markXmlTargets(work?.xml||'',match.work.streamId,targets,Number(work?.previewOrdinalStart||a)-1);
 if(marked.unresolved)throw Error('Unresolved XML targets');
 const events=[];let cursor=match.work.notes[0]?.onset??0;for(const n of match.work.notes){if(n.onset>cursor+1e-6)events.push({kind:'rest',durationRatio:n.onset-cursor});events.push(n);cursor=Math.max(cursor,n.onset+n.durationRatio)}
 return `<p>${esc(match.work.title)} / ${esc(match.work.partName||match.work.streamId)} · ${match.startMeasure}–${match.endMeasure}마디 · 점수 ${match.ranking.toFixed(1)}</p>${player(events)} <a target="_blank" href="/score?${esc(new URLSearchParams(params).toString())}">상세 악보</a>${render(marked.xml,marked.ids,'result-xml')}`;
}
function load(phase,id){const path=`evaluation/runs/structural-next40-${phase}-v1/${id}.json`;return existsSync(path)?JSON.parse(readFileSync(path)):null}
function panel(run){if(!run)return '<p>아직 실행 중/대기 — 결과 없음</p>';if(run.status!=='completed')return `<p>실행 실패: ${esc(run.error)}. 미회수 판정과 구분합니다.</p>`;
 const all=[...run.result.exact,...run.result.similar],match=run.sourceRank?all[run.sourceRank-1]:all[0];
 const label=run.sourceRank?`원곡 회수: ${run.sourceRank}위`:'원곡 top100 미회수';
 if(!match)return `<h4>${label}</h4><p>검색 결과 없음</p>`;
 try{return `<h4>${label}</h4>${!run.sourceRank?'<p class="warning">아래는 원곡이 아닌 1위 경쟁 결과입니다.</p>':''}${resultScore(match)}`}catch(e){audit.push({type:'error',message:e.message,caseId:run.caseId});return `<h4>${label}</h4><p>악보 출력 오류: ${esc(e.message)}</p>`}
}
const cards=suite.cases.map(c=>{
 const b=suite.bases.find(b=>b.baseId===c.baseId),before=load('baseline',c.caseId),after=load('omission',c.caseId),state=!after?'pending':after.status!=='completed'?'failed':before?.status==='completed'&&!before.sourceRank&&after.sourceRank?'recovered':before?.sourceRank&&!after.sourceRank?'lost':after.sourceRank?'found':'missing';
 const changed=c.changes.flatMap(x=>[...(x.addedIds??[]),...(x.ids??[]),...(x.eventId?[x.eventId]:[]),...(x.id?[x.id]:[]),...(x.event?[x.event.id]:[])]);
 rows.push({caseId:c.caseId,state,kind:c.kind,original:b.query,query:c.query,changes:c.changes,before:before?{status:before.status,rank:before.sourceRank}:null,after:after?{status:after.status,rank:after.sourceRank}:null});
 return `<section data-state="${state}" id="${c.caseId}"><h2>${c.caseId} · ${esc(b.expected.title)}</h2><p>${c.kind==='delete-one'?'가운데 음 하나와 음가 삭제':'경과·보조 삽입 + 원래 음 하나 반음 변경'} · 원본 위치 ${esc(b.focus[0].mn)}–${esc(b.focus.at(-1).mn)}마디</p><div class="pair"><div><h3>① 변형 전 멜로디</h3>${queryScore(b.query,changed)}</div><div><h3>② 검색 Query</h3>${queryScore(c.query,changed)}</div><div><h3>③ 개선 전 검색</h3>${panel(before)}</div><div><h3>④ 개선판 실험</h3>${panel(after)}</div></div><details><summary>변형 상세 / Query</summary><pre>${esc(JSON.stringify({changes:c.changes,query:c.query},null,2))}</pre></details></section>`;
});
const counts=Object.fromEntries(['pending','failed','recovered','lost','found','missing'].map(k=>[k,rows.filter(r=>r.state===k).length]));
const html=`<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>음 삭제·추가 변형 검색 전후 비교</title><style>body{background:#eef2f6;color:#203044;font:16px system-ui;margin:0}header,section{background:white;margin:18px;padding:24px;border-radius:12px}.pair{display:grid;grid-template-columns:1fr 1fr;gap:20px}.pair>div{min-width:0;border-top:1px solid #ddd}h1{font-size:25px}h2{font-size:20px}h3{font-size:17px}.score{overflow:auto}.score svg{width:100%;min-width:650px;height:auto;display:block}pre{white-space:pre-wrap;font-size:12px}button,select{padding:9px;margin:5px}.warning{color:#a52a26}#controls{position:sticky;top:0;background:#fff;padding:9px 25px;border-bottom:1px solid #bbb;z-index:5}@media(max-width:950px){.pair{grid-template-columns:1fr}}</style><header><h1>검색된 사례 / 검색되지 않은 사례 — 악보 비교 40개</h1><p>생성 시각 ${esc(new Date().toISOString())}. 상태: ${esc(JSON.stringify(counts))}</p><p>①의 빨강은 삭제/변경 대상 원음, ②의 빨강은 추가/변경음, ③④의 빨강은 실제 검색 정렬 음입니다. 완전 일치 표시가 아닙니다. 원곡 미회수 시 1위 경쟁곡을 명시해 표시합니다.</p><p>①②는 비교용 재기보(그림의 마디 번호는 원본과 다름), ③④는 실제 XML 발췌입니다. 재생은 검색 성부이며 반주 전체가 아닙니다. 원곡 회수는 원래 구간 회수와 다를 수 있습니다. 개선판은 실험 설정이며 사이트 기본값은 OFF입니다.</p><a href="cases.json">사례 데이터</a> · <a href="../structural-review-12-v1/index.html">이전 12개 검토</a></header><div id="controls"><select id="filter"><option value="all">전체</option><option value="recovered">미회수 → 회수</option><option value="found">회수 유지 / 회수</option><option value="missing">개선판도 미회수</option><option value="lost">회수 → 미회수</option><option value="pending">대기</option><option value="failed">실행 오류</option></select><button id="stop">■ 정지</button><span id="status">재생 대기 · 90 BPM</span></div>${cards.join('')}<script>const tracks=${JSON.stringify(tracks).replaceAll('<','\\u003c')};let ctx,nodes=[],token=0,timer;function stop(){token++;clearTimeout(timer);nodes.forEach(n=>{try{n.stop()}catch{}});nodes=[];document.getElementById('status').textContent='재생 대기'}document.getElementById('stop').onclick=stop;document.getElementById('filter').onchange=e=>{stop();document.querySelectorAll('section').forEach(s=>s.hidden=e.target.value!=='all'&&s.dataset.state!==e.target.value)};document.querySelectorAll('[data-play]').forEach(b=>b.onclick=async()=>{stop();const old=token;ctx??=new AudioContext();await ctx.resume();if(old!==token)return;let t=ctx.currentTime+.1;for(const e of tracks[+b.dataset.play]){const d=e.durationRatio*60/90;if(e.kind==='note'){const o=ctx.createOscillator(),g=ctx.createGain();o.type='triangle';o.frequency.value=440*2**((e.pitchMidi-69)/12);g.gain.setValueAtTime(0,t);g.gain.linearRampToValueAtTime(.08,t+Math.min(.01,d/4));g.gain.setValueAtTime(.08,t+d*.8);g.gain.linearRampToValueAtTime(0,t+d);o.connect(g);g.connect(ctx.destination);o.start(t);o.stop(t+d+.01);nodes.push(o)}t+=d}document.getElementById('status').textContent='재생 중 · 90 BPM';timer=setTimeout(stop,(t-ctx.currentTime)*1000+30)});</script></html>`;
const renderedHtml=html.replace('<script>',`<script>${softTone.toString()};`)
 .replace(/const o=ctx\.createOscillator\(\),g=ctx\.createGain\(\);[\s\S]*?nodes\.push\(o\)/, 'softTone(ctx,ctx.destination,e.pitchMidi,t,d,nodes)')
 .replaceAll('90 BPM','90 BPM · 부드러운 피아노 합성음')
 .replace('(t-ctx.currentTime)*1000+30','(t-ctx.currentTime)*1000+150');
if(renderedHtml.includes("o.type='triangle'"))throw Error('Legacy audio replacement failed');
new Function(renderedHtml.match(/<script>([\s\S]*?)<\/script>/)[1]);writeFileSync(out+'/index.html',renderedHtml);writeFileSync(out+'/cases.json',JSON.stringify(rows,null,2));writeFileSync(out+'/render-audit.json',JSON.stringify(audit,null,2));tk.destroy();console.log(JSON.stringify({counts,rendered:audit.filter(a=>a.type!=='error').length,errors:audit.filter(a=>a.type==='error')}));
