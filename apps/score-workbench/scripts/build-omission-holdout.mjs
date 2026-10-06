import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {DatabaseSync} from 'node:sqlite';
import {singleOmissionAlignment} from '../server/single-omission.mjs';
const out=process.argv[2];if(!out)throw Error('New output required');mkdirSync(out,{recursive:true});
const prior=JSON.parse(readFileSync('evaluation/reports/structural-next40-v1/suite.json'));
const normalized=s=>s.toLowerCase().replace(/[^\p{L}\p{N}]/gu,'');
const seen=new Set(prior.bases.map(b=>normalized(b.expected.title))),bases=[],cases=[],diagnostics=[];
if(process.argv[3])for(const b of JSON.parse(readFileSync(process.argv[3])).bases)seen.add(normalized(b.expected.title));
const db=new DatabaseSync('data/search-index-v2/search.sqlite',{readOnly:true}),get=db.prepare('SELECT source,notes FROM works WHERE id=?');
for(const line of ['motif-350','motif-300','motif-200','motif-100'].flatMap(name=>readFileSync(`evaluation/${name}/cases.jsonl`,'utf8').trim().split('\n'))){
 const old=JSON.parse(line),e=old.expected;if(seen.has(normalized(e.title)))continue;
 const row=get.get(e.workId);if(!row||row.source!==e.sourceId)continue;
 const all=JSON.parse(row.notes),focus=all.slice(e.baseStartIndex,e.baseStartIndex+10);
 if(focus.length!==10||focus.some((n,i)=>n.p!==e.baseTargets[i]?.pitchMidi||Math.abs(n.o-e.baseTargets[i]?.onset)>1e-5)||focus.some((n,i)=>!(n.d>0)||i&&(n.o<focus[i-1].o+focus[i-1].d-1e-5||n.o-focus[i-1].o-focus[i-1].d>2)))continue;
 const events=[];let cursor=focus[0].o;for(const [i,n]of focus.entries()){if(n.o>cursor+1e-6)events.push({id:'r'+i,kind:'rest',pitchMidi:null,durationRatio:n.o-cursor});events.push({id:'n'+i,kind:'note',pitchMidi:n.p,spelling:n.s,durationRatio:n.d});cursor=n.o+n.d}
 const id=(process.argv[3]?'J':'H')+String(bases.length+1).padStart(2,'0'),query={version:1,mode:'melody_rhythm',meter:old.query.meter,startsOnDownbeat:old.query.startsOnDownbeat,includeRests:true,events};
 const base={baseId:id,expected:e,focus,query,context:all.filter(n=>n.m>=focus[0].m-2&&n.m<=focus.at(-1).m+2)};bases.push(base);seen.add(normalized(e.title));
 for(const kind of ['original-control','delete-one','delete-plus-wrong-pitch']){
  const q=structuredClone(query);if(kind!=='original-control')q.events=q.events.filter(n=>n.id!=='n5');
  if(kind==='delete-plus-wrong-pitch'){const n=q.events.find(n=>n.id==='n2');n.pitchMidi+=3;delete n.spelling}
  const c={caseId:`${id}-${kind}`,baseId:id,kind,query:q,changedSourceIds:kind==='original-control'?[]:kind==='delete-one'?['n5']:['n5','n2']};cases.push(c);
  let t=0;const timed=q.events.map(n=>{const v={...n,onset:t};t+=n.durationRatio;return v}).filter(n=>n.kind==='note');
  const match=singleOmissionAlignment(timed,focus.map(n=>({pitchMidi:n.p,durationRatio:n.d,onset:n.o})));
  diagnostics.push({caseId:c.caseId,kind,recognized:!!match,expectMechanism:kind==='delete-one',pass:!!match===(kind==='delete-one')});
 }
 if(bases.length===10)break;
}db.close();if(bases.length!==10)throw Error('Insufficient new sources');
writeFileSync(out+'/suite.json',JSON.stringify({schema:'omission-holdout/1',bases,cases,limitations:['New normalized titles relative to first 20, not verified canonical identities.','Wrong-pitch cases test strict omission mechanism; they need not disappear from general similarity search.','Convenience sample, not population precision estimate.']},null,2),{flag:'wx'});
writeFileSync(out+'/mechanism-diagnostic.json',JSON.stringify(diagnostics,null,2),{flag:'wx'});console.log(JSON.stringify({sources:bases.length,cases:cases.length,mechanismPassed:diagnostics.filter(x=>x.pass).length}));
