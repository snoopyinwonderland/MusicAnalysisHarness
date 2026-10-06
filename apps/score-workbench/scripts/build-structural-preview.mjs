import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {join} from 'node:path';
import createModule from 'verovio/wasm';
import {VerovioToolkit} from 'verovio/esm';
import {comparisonNotation,htmlEscape as esc} from '../server/preclearance-report.mjs';
import {structuralVariation,structuralKinds} from './structural-variation.mjs';
const dir=process.argv[2];if(!dir)throw Error('New output directory required');mkdirSync(dir,{recursive:false});
const old=JSON.parse(readFileSync('evaluation/runs/harder-100-2026-09-15/suite.json')),cases=[],bases=[];
for(const b of old.bases){
 const audit=JSON.parse(readFileSync(`evaluation/runs/structural-source-audit-v2/${b.baseId}.json`));
 const inferred=new Set(audit.analysis.anchors.flatMap(a=>a.sourceEventIds));
 const ns=b.query.events.filter(e=>e.kind==='note');
 const inferredIds=audit.indexLinks.flatMap((link,i)=>link.xmlEventIds.some(id=>inferred.has(id))?[ns[i].id]:[]);
 // Fixed positional controls are declared, not falsely presented as musicological truth.
 const protectedIds=[...new Set([ns[0].id,ns.at(-1).id,...inferredIds])];
 const base={...b,generatorProtectedIds:protectedIds,analyzerInferredIds:inferredIds,sourceLinks:audit.indexLinks,
  qualification:'Unreviewed source-derived scaffold; no verified harmonic analysis'};
 const variants=structuralKinds.map(kind=>({caseId:`S100-${String(cases.length+structuralKinds.indexOf(kind)+1).padStart(3,'0')}`,baseId:b.baseId,kind,
  ...structuralVariation(b.query.events,kind,protectedIds),query:null,reviewStatus:'unreviewed',searchStatus:'not-run'}));
 for(const c of variants)c.query={...b.query,events:c.events};bases.push(base);cases.push(...variants);
}
const suite={schema:'structural-variation-preview/1',createdAt:new Date().toISOString(),bases,cases,
 limitations:['100 draft variations, not adjudicated ornament equivalence.','Original ten-note convenience sample retained; not the planned final 12–32-note stratified suite.',
 'Anchors inferred without verified harmony; source endpoints added as test controls.','No retrieval results or legal conclusions.']};
writeFileSync(join(dir,'suite.json'),JSON.stringify(suite,null,2),{flag:'wx'});
const tk=new VerovioToolkit(await createModule());tk.setOptions({scale:32,pageWidth:1700,pageHeight:1800,adjustPageHeight:true,breaks:'auto',header:'none',footer:'none',svgViewBox:true});
const tracks=[],audit=[];
function render(events,meter,protectedIds,inferredIds,changedIds){
 const prefix='s'+tracks.length,track=tracks.push(events)-1;
 const notation=comparisonNotation(events,meter,prefix,protectedIds),inferred=comparisonNotation(events,meter,prefix,inferredIds),changed=comparisonNotation(events,meter,prefix,changedIds);
 if(!tk.loadData(notation.mei))throw Error('Verovio load failed');let svg='';for(let p=1;p<=tk.getPageCount();p++)svg+=tk.renderToSVG(p);
 for(const id of [...notation.redIds,...inferred.redIds,...changed.redIds])if(!svg.includes(`id="${id}"`))throw Error('Missing note ID '+id);
 if(!svg.includes('class="note"'))throw Error('Empty score');
 const style=(ids,color)=>ids.map(id=>`#${id},#${id} *{fill:${color}!important;stroke:${color}!important}`).join('');
 audit.push({track,pages:tk.getPageCount(),protectedIds:notation.redIds,inferredIds:inferred.redIds,changedIds:changed.redIds});
 return `<button data-play="${track}">▶ 재생</button><div class="score"><style>${style(notation.redIds,'#155dc0')}${style(inferred.redIds,'#7b3db8')}${style(changed.redIds,'#c53220')}</style>${svg}</div>`;
}
const names={'passing-insertion':'경과 형태 삽입','neighbor-insertion':'반음 보조 형태 삽입','repeat-split':'같은 음 재타격','internal-rhythm':'내부 음가 이동','combined':'경과·보조 형태 결합'};
const cards=cases.map(c=>{const b=bases.find(b=>b.baseId===c.baseId),changed=c.changes.flatMap(x=>[...(x.addedIds??[]),...(x.ids??[]),...(x.eventId?[x.eventId]:[])]);
 return `<section data-kind="${c.kind}"><h2>${c.caseId} · ${esc(b.expected.title)} — ${names[c.kind]}</h2><p>${esc(b.expected.streamId)} · 원본 ${b.focus[0].mn}–${b.focus.at(-1).mn}마디 · 검토 전 / 검색 미실행</p><div class="pair"><div><h3>원본 Query</h3>${render(b.query.events,b.query.meter,b.generatorProtectedIds,b.analyzerInferredIds,[])}</div><div><h3>변형 Query</h3>${render(c.events,c.query.meter,b.generatorProtectedIds,b.analyzerInferredIds,changed)}</div></div><details><summary>변형 기록 · Query JSON</summary><pre>${esc(JSON.stringify({changes:c.changes,query:c.query},null,2))}</pre></details></section>`}).join('');
const html=`<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>구조 변형 100개 검토</title><style>body{margin:0;background:#f3f5f8;color:#192532;font:16px system-ui}header,section{padding:22px;background:white;margin:18px;border-radius:12px}header{position:sticky;top:0;z-index:2;border-bottom:1px solid #ccd}h1{font-size:24px}h2{font-size:19px}.pair{display:grid;grid-template-columns:1fr 1fr;gap:18px}.pair>div{min-width:0}.score{overflow:auto}.score svg{display:block;min-width:600px;width:100%;height:auto}button,select{padding:9px;margin:4px}pre{white-space:pre-wrap;font-size:12px}@media(max-width:900px){.pair{grid-template-columns:1fr}}</style><header><h1>기둥 보존 변형 100개 — 검토용 초안</h1><p>파랑: 테스트 보존음 · 보라: 자동 기둥 후보 · 빨강: 추가/변경음(표시 우선). 기둥 후보는 확정 분석이 아닙니다.</p><p>비교용 재기보이며 그림의 마디 번호는 원본 번호가 아닙니다. 음높이·도착 시점을 보존해도 장식으로 자연스러운지는 검토가 필요합니다.</p><select id="filter"><option value="all">전체 100개</option>${structuralKinds.map(k=>`<option value="${k}">${names[k]}</option>`)}</select><button id="stop">■ 정지</button><span id="status">재생 대기</span> · <a href="suite.json">전체 Query와 원본 연결 데이터</a></header>${cards}<script>const tracks=${JSON.stringify(tracks).replaceAll('<','\\u003c')};let ctx,nodes=[],token=0,timer;function stop(){token++;clearTimeout(timer);for(const n of nodes)try{n.stop()}catch{}nodes=[];document.getElementById('status').textContent='재생 대기'}document.getElementById('stop').onclick=stop;document.getElementById('filter').onchange=e=>{stop();document.querySelectorAll('section').forEach(s=>s.hidden=e.target.value!=='all'&&s.dataset.kind!==e.target.value)};document.querySelectorAll('[data-play]').forEach(b=>b.onclick=async()=>{stop();const tkn=token;ctx??=new AudioContext();await ctx.resume();if(tkn!==token)return;let t=ctx.currentTime+.1;for(const e of tracks[+b.dataset.play]){const d=e.durationRatio*60/90;if(e.kind==='note'){const o=ctx.createOscillator(),g=ctx.createGain();o.type='triangle';o.frequency.value=440*2**((e.pitchMidi-69)/12);g.gain.setValueAtTime(0,t);g.gain.linearRampToValueAtTime(.08,t+Math.min(.01,d/4));g.gain.setValueAtTime(.08,t+d*.8);g.gain.linearRampToValueAtTime(0,t+d);o.connect(g);g.connect(ctx.destination);o.start(t);o.stop(t+d+.01);nodes.push(o)}t+=d}document.getElementById('status').textContent='재생 중 · 90 BPM';timer=setTimeout(stop,(t-ctx.currentTime)*1000+30)});</script></html>`;
new Function(html.match(/<script>([\s\S]*?)<\/script>/)[1]);writeFileSync(join(dir,'index.html'),html,{flag:'wx'});writeFileSync(join(dir,'render-audit.json'),JSON.stringify({cases:cases.length,rendered:audit.length,audit},null,2),{flag:'wx'});tk.destroy();console.log(JSON.stringify({cases:cases.length,rendered:audit.length,dir}));
