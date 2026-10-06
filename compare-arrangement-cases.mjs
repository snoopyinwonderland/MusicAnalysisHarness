import {readFileSync,writeFileSync,mkdirSync,existsSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {join} from 'node:path';
const root='K:/Music Analysis',out=join(root,'reports/arrangement-gap-2026-09-22');
if(existsSync(out))throw Error('Refusing to overwrite audit');
mkdirSync(out,{recursive:true});
const hash=x=>createHash('sha256').update(x).digest('hex');
const pairs=[
 ['A Whole New World','A Whole New World.xml','3. A Whole New World, Piano Solo.musicxml.xml','positive'],
 ['The Last Night of the World','The Last Night of the World.musicxml.xml','3. The Last Night of the World, Piano Solo.musicxml.xml','positive-phrase'],
 ['Always With Me','Always With Me Melody.musicxml.xml','3. Always With Me, Piano Solo.musicxml.xml','reviewed-not-gold'],
 ['Find the Way','Find the Way Melody.musicxml.xml','4. Find the Way, Piano Solo.musicxml.xml','reviewed-not-gold'],
 ['Beauty and the Beast','Beauty and the Beast.musicxml.xml','3. Beauty and the Beast, Piano Solo.musicxml.xml','reviewed-not-gold'],
 ['The Whole Nine Yards','The Whole Nine Yards Melody.musicxml.xml','3. The Whole Nine Yards, Piano Solo.musicxml.xml','new-control']
];
async function get(url){const r=await fetch('http://127.0.0.1:5173'+url);if(!r.ok)throw Error(`${r.status} ${url}`);return r.json()}
function align(a,b,shift=0,trace=false){
 const m=b.length,n=a.length,w=m+1,dirs=trace?new Uint8Array((n+1)*w):null;let prev=Float64Array.from({length:w},(_,j)=>j*.8);
 if(dirs)for(let j=1;j<=m;j++)dirs[j]=3;
 for(let i=1;i<=n;i++){const cur=new Float64Array(w);cur[0]=i*.8;if(dirs)dirs[i*w]=2;
  for(let j=1;j<=m;j++){const x=a[i-1],y=b[j-1],delta=y.pitchMidi-x.pitchMidi-shift,pc=((delta%12)+12)%12;
   const pitch=pc===0?(delta===0?0:.15):1.4;
   const rhythm=.15*Math.min(2,Math.abs(Math.log2(Math.max(.001,y.durationRatio)/Math.max(.001,x.durationRatio))));
   const d=prev[j-1]+pitch+rhythm,u=prev[j]+.8,l=cur[j-1]+.8;
   cur[j]=Math.min(d,u,l);if(dirs)dirs[i*w+j]=cur[j]===d?1:cur[j]===u?2:3;
  }prev=cur;
 }
 if(!trace)return prev[m];
 const path=[];let i=n,j=m;while(i||j){const d=dirs[i*w+j];if(d===1){path.push([--i,--j])}else if(d===2){path.push([--i,null])}else{path.push([null,--j])}}return {cost:prev[m],path:path.reverse(),shift};
}
const coord=n=>n?`${n.measure}:${n.beat} ${n.spelling}(${n.durationRatio}q)`:null;
function stats(w,xml){const ns=w.notes,d=ns.map(n=>n.durationRatio).sort((a,b)=>a-b),bs=w.phraseAnalysis.boundaries.filter(b=>b.supported);return {workId:w.workId,stream:w.streamId,notes:ns.length,phrases:bs.length+1,version:w.phraseAnalysis.version,medianDuration:d[Math.floor(d.length/2)],graceTags:(xml.match(/<grace[\s/>]/g)||[]).length,chordTags:(xml.match(/<chord\s*\/>/g)||[]).length,boundaries:bs.map(b=>({index:b.index,after:coord(ns[b.index-1]),before:coord(ns[b.index]),strength:b.strength,cues:b.cues}))}}
const results=[];
for(const [title,ref,piano,status] of pairs){
 const catalog=await get('/api/catalog/search?q='+encodeURIComponent(title)+'&limit=50');const snapshots=[];
 for(const [side,file] of [['reference',ref],['piano',piano]]){
  const item=catalog.items.find(x=>x.source===file);if(!item)throw Error(`Missing catalog ${file}`);
  const response=await get('/api/work/'+item.workId+'?structure=1'),w=response.structureWork||response;
  const xml=readFileSync(join(root,'MusicXML',file));const dir=join(out,String(results.length+1),side);mkdirSync(dir,{recursive:true});
  writeFileSync(join(dir,'source.musicxml'),xml);writeFileSync(join(dir,'analysis.json'),JSON.stringify(w));
  snapshots.push({w,source:file,hash:hash(xml),stats:stats(w,xml.toString())});
 }
 const [a,b]=snapshots,an=a.w.notes,bn=b.w.notes;
 const trials=Array.from({length:12},(_,shift)=>({shift,cost:align(an,bn,shift)})).sort((x,y)=>x.cost-y.cost);
 const al=align(an,bn,trials[0].shift,true),mapped=al.path.filter(([i,j])=>i!==null&&j!==null),same=([i,j])=>((bn[j].pitchMidi-an[i].pitchMidi-al.shift)%12+12)%12===0;
 const exact=mapped.filter(same),mapping=new Map(exact);
 const support=i=>{let count=0;for(let k=Math.max(0,i-3);k<=Math.min(an.length-1,i+3);k++)if(mapping.has(k))count++;return count>=5};
 const ab=a.stats.boundaries,bb=b.stats.boundaries;
 const boundaryComparison=ab.map(x=>{const j=mapping.get(x.index);return {reference:x.index,referenceBefore:x.before,pianoIndex:j??null,pianoBefore:coord(bn[j]),supportedContext:j!==undefined&&support(x.index),sameBoundary:j!==undefined&&bb.some(y=>Math.abs(y.index-j)<=1),pianoContext:j===undefined?[]:bn.slice(Math.max(0,j-3),j+4).map(coord)}});
 const differences=exact.filter(([i,j])=>Math.abs(Math.log2(bn[j].durationRatio/an[i].durationRatio))>=.9).slice(0,12).map(([i,j])=>({reference:coord(an[i]),piano:coord(bn[j]),referenceId:an[i].id,pianoId:bn[j].id}));
 const report={title,status,reference:{source:a.source,hash:a.hash,...a.stats},piano:{source:b.source,hash:b.hash,...b.stats},alignment:{method:'global diagnostic pitch-class+duration edit alignment; not validated correspondence',shift:al.shift,cost:al.cost,runnerUpCost:trials[1].cost,referencePitchCoverage:exact.length/an.length,pianoPitchCoverage:exact.length/bn.length,octaveDifferences:exact.filter(([i,j])=>bn[j].pitchMidi-an[i].pitchMidi!==al.shift).length,insertions:al.path.filter(([i])=>i===null).length,deletions:al.path.filter(([,j])=>j===null).length,path:al.path},boundaryComparison,durationExamples:differences};
 results.push(report);writeFileSync(join(out,String(results.length),'comparison.json'),JSON.stringify(report,null,2));
 console.log(JSON.stringify({...report,reference:{...report.reference,boundaries:undefined},piano:{...report.piano,boundaries:undefined},alignment:{...report.alignment,path:undefined},boundaryComparison:boundaryComparison.filter(x=>x.supportedContext&&!x.sameBoundary).slice(0,4)}));
}
writeFileSync(join(out,'summary.json'),JSON.stringify({created:new Date().toISOString(),scriptHash:hash(readFileSync(new URL(import.meta.url))),limitations:['Reference versions are not gold labels.','Global alignment may choose the wrong repeated occurrence.','Chord/grace counts describe entire source, not just selected melody.','No phrase/motif production rule was modified.'],results},null,2));
