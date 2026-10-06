import {readFileSync,writeFileSync,existsSync} from 'node:fs';
import {join} from 'node:path';
import createModule from 'verovio/wasm';
import {VerovioToolkit} from 'verovio/esm';
import {getWork} from '../server/search-api.mjs';
import {markXmlTargets} from '../server/xml-target-verification.mjs';
const dir=process.argv[2],suite=JSON.parse(readFileSync(join(dir,'suite.json'))),summary=JSON.parse(readFileSync(join(dir,'summary.json')));if(summary.remaining)throw Error('Finish primary search first');
const tk=new VerovioToolkit(await createModule());tk.setOptions({pageWidth:2400,pageHeight:1800,scale:22,breaks:'auto',header:'none',footer:'none',svgViewBox:true});const rows=[];
for(const c of suite.cases){const file=join(dir,c.caseId+'-highlight.json');if(existsSync(file)){rows.push(JSON.parse(readFileSync(file)));continue}let r=JSON.parse(readFileSync(join(dir,c.caseId+'.json')));const retry=join(dir,'retry-180s',c.caseId+'.json');const attempt=r.status!=='completed'&&existsSync(retry)?'retry':'primary';if(attempt==='retry')r=JSON.parse(readFileSync(retry));let row={caseId:c.caseId,status:'not-checked'};
 try{if(r.status!=='completed'){row.status='search-failed'}else{const all=[...r.result.exact,...r.result.similar],match=all.find(x=>x.work.sourceId===c.expected.sourceId)||all[0];if(!match)row.status='no-results';else{
 const targets=match.alignment.filter(p=>p.queryIndex!==null&&p.candidateIndex!==null).map(p=>match.work.notes[p.candidateIndex]),ordinals=targets.map(n=>n.measureOrdinal);if(!targets.length||ordinals.some(n=>!Number.isFinite(n)))throw Error('Missing coordinates');
 const a=Math.min(...ordinals),b=Math.max(...ordinals),work=getWork(match.work.workId,{start:match.startMeasure,end:match.endMeasure,ordinalStart:a,ordinalEnd:b,targets:targets.map(n=>`${n.onset}:${n.pitchMidi}`).join(','),excerpt:'1'});
 const marked=markXmlTargets(work?.xml||'',match.work.streamId,targets,Number(work?.previewOrdinalStart||a)-1);const loaded=tk.loadData(marked.xml),pages=tk.getPageCount();if(pages>20)throw Error('Over 20 pages in excerpt');let svg='';if(loaded)for(let p=1;p<=pages;p++)svg+=tk.renderToSVG(p);
 row={caseId:c.caseId,status:loaded?'rendered':'load-failed',target:match.work.sourceId===c.expected.sourceId?'source-result':'top1-fallback',workId:match.work.workId,requested:targets.length,resolved:marked.resolved,unresolved:marked.unresolved,renderedTargets:marked.ids.filter(id=>svg.includes(`id="${id}"`)).length,noteGroups:(svg.match(/class="note"/g)||[]).length,pages,visualListeningReview:false};
 }} }catch(e){row.status='error';row.error=e.message}
 row.attempt=attempt;writeFileSync(file,JSON.stringify(row,null,2),{flag:'wx'});rows.push(row);console.log(JSON.stringify(row));
}tk.destroy();writeFileSync(join(dir,'highlight-summary.json'),JSON.stringify({rows,warning:'One chosen result per variant. SVG IDs and note presence, not human visual layout/listening validation.'},null,2));
