import fs from 'node:fs';
import path from 'node:path';
import createModule from 'file:///K:/MusicSearch/node_modules/verovio/dist/verovio-module.mjs';
import {VerovioToolkit} from 'file:///K:/MusicSearch/node_modules/verovio/dist/verovio.mjs';

const root=process.argv[2];
const module=await createModule();
const escape=s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');
let body='';let checks=[];
for(const entry of fs.readdirSync(root,{withFileTypes:true}).filter(x=>x.isDirectory())){
 const dir=path.join(root,entry.name), manifest=JSON.parse(fs.readFileSync(path.join(dir,'notation.json'),'utf8'));
 const tk=new VerovioToolkit(module);
 tk.setOptions({inputFrom:'musicxml',pageWidth:1600,pageHeight:2200,scale:40,svgViewBox:true,breaks:'auto',header:'none',footer:'none',pageMarginTop:80,pageMarginBottom:80,mnumInterval:1});
 if(!tk.loadData(fs.readFileSync(path.join(dir,'render.musicxml'),'utf8')))throw Error('MusicXML load failed');
 body+=`<h2>${escape(manifest.source)}</h2>`;
 for(const card of manifest.cards){
  body+=`<section><h3>${escape(card.id)} · ${card.status==='review-only'?'미확정 검토 후보':'생략 차단'}</h3><p>${escape(card.description)}</p><p>${escape(card.blockers.join(', ')||'차단 조건 없음 ≠ 반주 확정')}</p><div class="pair">`;
  for(const side of ['context','counterpart']){
   const ids=card[side], highlighted=side==='context'?card.omitted:card.counterpartAnchors;
   const pages=[...new Set(ids.map(id=>{const p=tk.getPageWithElement(id);if(p<1)throw Error(`Missing anchor ${id}`);return p;}))].sort((a,b)=>a-b);
   body+=`<div><h4>${side==='context'?'원본 문맥 · 주황색은 생략 검토 음':'대응 반복 문맥 · 파란색은 대응 양 끝 음'}</h4>`;
   for(const page of pages){
    let svg=tk.renderToSVG(page,false);
    const css=highlighted.map(id=>`#${id},#${id} * {fill:${side==='context'?'#ba4900':'#0065bc'}!important;stroke:${side==='context'?'#ba4900':'#0065bc'}!important;}`).join('\n');
    svg=svg.replace(/(<svg\b[^>]*>)/,`$1<style>${css}</style>`);
    const file=`${card.id}-${side}-${page}.svg`;
    fs.writeFileSync(path.join(dir,file),svg);
    for(const id of highlighted.filter(id=>tk.getPageWithElement(id)===page)){
     if(!svg.includes(`id="${id}"`))throw Error(`SVG lost ${id}`);
     checks.push({case:entry.name,card:card.id,side,page,id});
    }
    body+=`<img src="${entry.name}/${file}" alt="${escape(side)} score page ${page}">`;
   }
   body+='</div>';
  }
  body+='</div></section>';
 }
 tk.destroy();
}
fs.writeFileSync(path.join(root,'index.html'),`<!doctype html><html lang="ko"><meta charset="utf-8"><title>선율 생략 후보 오선 검토</title><style>body{font:16px/1.6 sans-serif;margin:24px;background:#f7f7f7}section{background:white;padding:18px;margin:24px 0}.pair{display:grid;grid-template-columns:1fr 1fr;gap:20px}img{width:100%;height:auto;border:1px solid #ddd}h4{position:sticky;top:0;background:white} @media(max-width:900px){.pair{grid-template-columns:1fr}}</style><h1>원본과 반복 문맥 비교</h1><p>음표를 삭제하지 않은 원본 전체 페이지입니다. 주황색은 생략 검토 대상, 파란색은 대응 양 끝 음입니다. 차단 후보도 표시합니다. 모든 후보 미선택 · 운영 분석 변경 없음. 페이지의 나머지 음악은 앞뒤 문맥이며 후보 범위가 아닙니다.</p>${body}</html>`);
fs.writeFileSync(path.join(root,'render-checks.json'),JSON.stringify({highlightedAnchors:checks.length,checks},null,2));
console.log(`Verified ${checks.length} highlighted SVG anchors`);
