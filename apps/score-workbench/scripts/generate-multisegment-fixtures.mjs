import {mkdirSync,writeFileSync,existsSync,readFileSync} from 'node:fs';
import {join,resolve} from 'node:path';
import {createHash} from 'node:crypto';
import createModule from 'verovio/wasm';
import {VerovioToolkit} from 'verovio/esm';
import {validateEvaluationCases} from './evaluation-case-validation.mjs';

const out=process.argv[2];if(!out||existsSync(out))throw Error('NEW output directory required');
const hash=x=>createHash('sha256').update(typeof x==='string'?x:JSON.stringify(x)).digest('hex');
const save=(p,x)=>writeFileSync(join(out,p),typeof x==='string'?x:JSON.stringify(x,null,2),{flag:'wx'});
for(const d of ['sources','uploads','evaluator','previews'])mkdirSync(join(out,d),{recursive:true});
const createdAt=new Date().toISOString().slice(0,10),recipes=[],assets=[],cases=[];
const families=[
 {meter:'4/4',p:[[60,64,67,65,69,62,64,60],[67,70,69,62,65,64,71,67],[72,67,68,64,65,62,67,60]],d:[.5,.5,1,1,.5,1,.5,3]},
 {meter:'3/4',p:[[62,69,65,64,67,61,64,62],[69,65,72,70,67,64,61,62],[74,70,67,69,65,64,61,62]],d:[.5,.5,1,.5,1,.5,.5,1.5]},
 {meter:'6/8',p:[[64,67,71,69,66,72,67,64],[71,66,69,67,74,72,66,64],[76,71,72,69,67,66,71,64]],d:[.5,.5,.5,1,1,.5,.5,1.5]},
 {meter:'5/4',p:[[65,69,72,70,64,67,73,65],[72,67,70,76,74,69,64,65],[77,73,70,72,67,69,64,65]],d:[1,.5,.5,2,1.5,.5,.5,3.5]}
];
const variants=['baseline','one-phrase','two-phrases','three-phrases','repeat-one','hard-negative'];
function at(events){let t=0;return events.map((e,i)=>{const r={...e,id:'e'+i,onset:t};t+=e.durationRatio;return r})}
function pitchName(p){const names=['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'];return names[p%12]+(Math.floor(p/12)-1)}
function scaffold(length,root,phase=0){
 const result=[];for(let i=0;i<length*2;i++)result.push({kind:i%8===7?'rest':'note',pitchMidi:i%8===7?null:root+[0,2,4,5,7,5,4,2][(i+phase)%8],durationRatio:.5});
 return result;
}
function phrase(f,n){return f.p[n].map((pitchMidi,i)=>({kind:'note',pitchMidi,durationRatio:f.d[i],sourceIndex:i,family:n}))}
function build(f,slots,totalBars,transform=false){
 const [beats,unit]=f.meter.split('/').map(Number),bar=beats*4/unit,parts=[[],[]],occurrences=[];
 for(let b=0;b<totalBars;){
  const slot=slots.find(s=>s.bar===b);
  if(slot){
   let p=phrase(f,slot.family).map(e=>({...e,pitchMidi:e.pitchMidi+(slot.transpose||0)}));
   if(slot.change==='semitone')p[3].pitchMidi++;
   if(slot.change==='rhythm'){p[1].durationRatio-=.25;p[2].durationRatio+=.25}
   if(slot.change==='ornament'){const e=p[3];p.splice(3,1,{...e,durationRatio:e.durationRatio/2},{...e,pitchMidi:e.pitchMidi+2,durationRatio:e.durationRatio/2,sourceIndex:null})}
   const part=slot.part||0,start=parts[part].length;
   parts[part].push(...p);parts[1-part].push({kind:'rest',pitchMidi:null,durationRatio:bar*2});
   occurrences.push({...slot,part:'P'+(part+1),startEvent:start,eventCount:p.length,startMeasure:b+1,endMeasure:b+2});b+=2;
  }else{parts[0].push(...scaffold(bar,f.p[0][0]-12,transform?3:0));parts[1].push({kind:'rest',pitchMidi:null,durationRatio:bar});b++}
 }
 return {meter:f.meter,bar,parts:parts.map(at),occurrences};
}
const clean=score=>({meter:score.meter,parts:score.parts.map((events,i)=>({partId:'P'+(i+1),staff:1,voice:1,events:events.map(({sourceIndex,family,...e})=>({...e,...(e.pitchMidi!==null?{spelling:pitchName(e.pitchMidi)}:{})}))}))});
const esc=x=>String(x).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');
function xml(score,title){
 const rows=[],eventMap={};
 const durations=[ [4,'whole',0],[3,'half',1],[2,'half',0],[1.5,'quarter',1],[1,'quarter',0],[.75,'eighth',1],[.5,'eighth',0],[.375,'16th',1],[.25,'16th',0],[.125,'32nd',0] ];
 score.parts.forEach((events,pi)=>{
  const bars=new Map();for(const e of events){
   let remaining=e.durationRatio,pos=e.onset,k=0;
   const fragments=[];while(remaining>1e-8){
    const m=Math.floor((pos+1e-8)/score.bar),room=score.bar-(pos-m*score.bar);
    const [d,type,dot]=durations.find(([d])=>d<=Math.min(room,remaining)+1e-8)||[];
    if(!d)throw Error('Unnotatable duration');
    fragments.push({m,d,type,dot,id:'n'+pi+'-'+e.id+'-'+k++});pos+=d;remaining-=d;
   }
   eventMap['P'+(pi+1)+':'+e.id]=fragments.map(x=>x.id);
   fragments.forEach((s,j)=>{
    const midi=e.pitchMidi,name=midi===null?null:pitchName(midi),pitch=name?'<pitch><step>'+name[0]+'</step>'+(name.includes('#')?'<alter>1</alter>':'')+'<octave>'+(Math.floor(midi/12)-1)+'</octave></pitch>':'<rest/>';
    const stop=midi!==null&&j>0,start=midi!==null&&j<fragments.length-1;
    const tie=(tag)=> (stop?'<'+tag+' type="stop"/>':'')+(start?'<'+tag+' type="start"/>':'');
    const note='<note id="'+s.id+'">'+pitch+'<duration>'+s.d*8+'</duration>'+tie('tie')+'<voice>1</voice><type>'+s.type+'</type>'+(s.dot?'<dot/>':'')+'<staff>1</staff>'+((start||stop)?'<notations>'+tie('tied')+'</notations>':'')+'</note>';
    if(!bars.has(s.m))bars.set(s.m,[]);bars.get(s.m).push(note);
   });
  }
  rows.push('<part id="P'+(pi+1)+'">'+[...bars].sort((a,b)=>a[0]-b[0]).map(([m,notes])=>'<measure number="'+(m+1)+'">'+(m===0?'<attributes><divisions>8</divisions><key><fifths>0</fifths></key><time><beats>'+score.meter.split('/')[0]+'</beats><beat-type>'+score.meter.split('/')[1]+'</beat-type></time><clef><sign>G</sign><line>2</line></clef></attributes>':'')+notes.join('')+'</measure>').join('')+'</part>');
 });
 return {text:'<?xml version="1.0" encoding="utf-8"?><score-partwise version="4.0"><work><work-title>'+esc(title)+'</work-title></work><part-list><score-part id="P1"><part-name>Line 1</part-name></score-part><score-part id="P2"><part-name>Line 2</part-name></score-part></part-list>'+rows.join('')+'</score-partwise>',eventMap};
}
function asset(path,score,title){
 const notation=xml(score,title),events=clean(score);save(path+'.musicxml',notation.text);save(path+'.events.json',events);
 const a={path:path+'.musicxml',events:path+'.events.json',hash:hash(notation.text),eventMap:notation.eventMap};assets.push(a);return a;
}
for(let si=0;si<families.length;si++){
 const f=families[si],source=build(f,[0,1,2].map((family,i)=>({bar:i*4,family})),12),sa=asset('sources/reference-'+(si+1),source,'Synthetic Reference '+(si+1));
 for(let vi=0;vi<variants.length;vi++){
  const type=variants[vi],id='U-'+hash('multisegment-v1:'+si+':'+vi).slice(0,12);
  let slots=[];
  if(vi===0)slots=source.occurrences.map(x=>({bar:x.bar,family:x.family}));
  if(vi===1)slots=[{bar:2,family:0,change:'semitone',transpose:2}];
  if(vi===2)slots=[{bar:2,family:0,change:'rhythm',transpose:-2},{bar:8,family:1,change:'semitone'}];
  if(vi===3)slots=[{bar:2,family:2,transpose:12},{bar:6,family:0,change:'ornament'},{bar:10,family:1,change:'rhythm',part:1}];
  if(vi===4)slots=[2,6,10].map(bar=>({bar,family:0,transpose:2}));
  const score=vi===0?source:build(f,slots,14,true),a=asset('uploads/'+id,score,vi===0?'Synthetic Reference '+(si+1):id);
  const occurrences=score.occurrences.map((o,oi)=>{
   const original=source.occurrences.find(x=>x.family===o.family),input=score.parts[Number(o.part.slice(1))-1].slice(o.startEvent,o.startEvent+o.eventCount);
   return {...o,id:'occ-'+oi,familyId:'reference-'+si+'-phrase-'+o.family,
    sourcePart:'P1',sourceStartMeasure:original.startMeasure,sourceEndMeasure:original.endMeasure,
    mapping:input.map(e=>({inputEventId:e.id,inputPart:o.part,inputOnset:e.onset,inputPitch:e.pitchMidi,inputDuration:e.durationRatio,
     sourceEventId:e.sourceIndex===null?null:source.parts[0][original.startEvent+e.sourceIndex].id,
     sourceOnset:e.sourceIndex===null?null:source.parts[0][original.startEvent+e.sourceIndex].onset,
     sourcePitch:e.sourceIndex===null?null:source.parts[0][original.startEvent+e.sourceIndex].pitchMidi,
     sourceDuration:e.sourceIndex===null?null:source.parts[0][original.startEvent+e.sourceIndex].durationRatio,
     inputXmlIds:a.eventMap[o.part+':'+e.id]}))};
  });
  const record={schema:'musicanote-evaluation-case/v1',caseId:id,createdAt,status:'draft',
   query:{format:'musicxml-upload',musicXml:a.path,events:a.events,meter:f.meter},
   expected:{sourceAsset:sa.path,sourceHash:sa.hash,distinctFamilies:new Set(occurrences.map(o=>o.familyId)).size,occurrenceCount:occurrences.length,occurrences,legalInfringement:null,groundTruth:'synthetic-source-provenance-not-legal-verdict'},
   observations:[{status:'generated-not-searched',note:'Source attribution ground truth; background coincidences and musical naturalness need human review.'}],
   diagnoses:[],proposals:[],runs:[],tags:['multisegment-v1',type,f.meter],
   provenance:{generator:'scripts/generate-multisegment-fixtures.mjs',recipeVersion:1,sourceKind:'newly-authored-synthetic-fixture',rightsStatus:'no-third-party-score-used; not a legal clearance opinion',uploadHash:a.hash,transformRecipe:slots,blindMetadata:vi!==0}};
  cases.push(record);recipes.push({caseId:id,type,meter:f.meter,source:sa.path,upload:a.path,families:record.expected.distinctFamilies,occurrences:occurrences.length});
 }
}
validateEvaluationCases(cases);save('evaluator/cases.json',cases);save('evaluator/index.json',recipes);
const tk=new VerovioToolkit(await createModule());tk.setOptions({scale:32,pageWidth:1600,pageHeight:2200,breaks:'auto',header:'none',footer:'none',svgViewBox:true});
const render=[];
for(const a of assets){
 if(!tk.loadData(readFileSync(join(out,a.path),'utf8')))throw Error('Verovio failed '+a.path);
 const pages=tk.getPageCount();if(!pages)throw Error('No pages');
 const prefix=a.path.replaceAll('/','-'),paths=[];let notes=0;
 for(let p=1;p<=pages;p++){const svg=tk.renderToSVG(p);notes+=(svg.match(/class="note"/g)||[]).length;const dest='previews/'+prefix+'-'+p+'.svg';save(dest,svg);paths.push(dest)}
 if(!notes)throw Error('No rendered notes');render.push({path:a.path,pages,svgNotes:notes,svgPaths:paths});
}
save('manifest.json',{schema:'musicanote-multisegment-fixtures/v1',createdAt,generatorHash:hash(readFileSync(new URL(import.meta.url),'utf8')),sourceCount:4,uploadCount:24,searchExecuted:false,productionDatabaseModified:false,assets,render,limitations:['synthetic only','no legal-positive labels','human listening/engraving review pending','baseline deliberately byte-identical','no existing corpus retrieval claim']});
save('README.md','# Multi-segment source-attribution fixtures\n\n4 newly authored synthetic references and 24 uploads. Not infringement findings.\n\nOnly uploads/*.musicxml are detector input. evaluator/ contains hidden source mappings, expected phrase family/occurrence counts and transformation recipes; never pass it to search. sources/ may be indexed in an isolated fixture database, never add uploads to the production corpus. Baseline files intentionally preserve source bytes.\n\nEach upload has an event snapshot. manifest.json lists hashes and all rendered SVG pages. XML round-trip audit is separate. No actual search or legal risk calibration has been performed.\n');
save('review.html','<!doctype html><meta charset="utf-8"><title>Fixture review — ground truth, not search results</title><style>body{font:16px system-ui;max-width:1100px;margin:auto}img{width:100%}article{border-top:1px solid #ccc;padding:20px}small{color:#555}</style><h1>24개 검증 샘플 — 정답 자료, 검색 결과 아님</h1><p>새로 만든 합성 원곡. 실제 침해 판정·검색 성능 검증 전입니다.</p>'+recipes.map(r=>{const a=render.find(a=>a.path===r.upload);return '<article><h2>'+r.caseId+' · '+r.type+' · '+r.meter+'</h2><p>정답: 고유 '+r.families+'구절 / '+r.occurrences+'곳 · <a href="'+r.source+'">원본 XML</a> · <a href="'+r.upload+'">입력 XML</a></p>'+a.svgPaths.map(p=>'<img loading="lazy" src="'+p+'">').join('')+'</article>'}).join(''));
console.log(JSON.stringify({out:resolve(out),sources:4,uploads:24,rendered:render.length,pages:render.reduce((s,a)=>s+a.pages,0)}));
