import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {pathToFileURL} from 'node:url';
import {analyzePhraseBoundaries} from 'file:///K:/MusicSearch/server/phrase-boundaries.mjs';

const hash=x=>createHash('sha256').update(x).digest('hex');
export function repeatedBoundaryChecks(notes,analysis){
 const attacks=notes.map((n,i)=>({n,i})).filter(({n})=>n.isAttack!==false&&!n.tieStop).map(x=>x.i);
 const found=new Map();
 for(const r of analysis.motifRelations??[]){
  const a=attacks.indexOf(r.previousIndex),b=attacks.indexOf(r.currentIndex);
  if(a<0||b<0)continue;
  // Only internal consecutive transitions; context outside a motif is not equivalent.
  for(let k=1;k<r.length;k++){
   const l=attacks[a+k],p=attacks[a+k-1],rr=attacks[b+k],pp=attacks[b+k-1];
   if(l!==p+1||rr!==pp+1)continue;
   const key=`${l}:${rr}`;
   const left=analysis.boundaries[l],right=analysis.boundaries[rr];
   found.set(key,{leftIndex:l,rightIndex:rr,leftEventId:notes[l].id,rightEventId:notes[rr].id,
    leftMeasure:notes[l].measure,rightMeasure:notes[rr].measure,
    mismatch:left.supported!==right.supported,leftCues:left.cues,rightCues:right.cues,
    verdict:'diagnostic-only-context-may-differ'});
  }
 }
 return [...found.values()];
}

export function alternativeChecks(notes,analysis,annotation,events){
 return annotation.alternatives.map(a=>{
  const last=events.find(e=>e.id===a.span.lastEventId);
  const onset=last.onset.n/last.onset.d;
  const index=notes.findIndex(n=>Math.abs(n.onset-onset)<1e-8&&n.pitchMidi===last.pitch);
  if(index<0)return {id:a.id,status:'unmapped-not-failed'};
  const next=index+1;
  const start=a.span.start.n/a.span.start.d;
  return {id:a.id,status:'alternative-report-only',lastIndex:index,lastEventId:notes[index].id,
   boundaryAfterLast:analysis.boundaries[next]?.supported??null,
   internalBoundaries:analysis.boundaries.filter(b=>b.supported&&b.index<next&&notes[b.index]?.onset>start).map(b=>b.index),
   note:'Boundary before next attack compared; note-release endpoint is not silently equated with next onset.'};
 });
}

export function run(output){
 if(fs.existsSync(output))throw Error('Refusing overwrite');
 fs.mkdirSync(output,{recursive:true});
 const expectations={
  '005':{keep:[33,46,79],suppress:[31,37,43,77],document:'s-struct-005-review.md'},
  '006':{keep:[13,29,42,57],suppress:[51],document:'s-struct-006-structure-baseline.md'}
 };
 const rows=[];
 function capture(id,notes,xml,snapshot,checksFn){
  const dir=path.join(output,id);fs.mkdirSync(dir);
  fs.writeFileSync(path.join(dir,'source.musicxml'),xml);fs.writeFileSync(path.join(dir,'snapshot.json'),snapshot);
  const analysis=analyzePhraseBoundaries(notes),repeated=repeatedBoundaryChecks(notes,analysis);
  const feedback=checksFn(analysis,dir);
  const rerun=analyzePhraseBoundaries(notes);
  const report={id,sourceHash:hash(xml),snapshotHash:hash(snapshot),analysis,
   deterministic:JSON.stringify(analysis)===JSON.stringify(rerun),feedback,repeated,
   limitations:['Only detected 4–8 attack motif relations; misses unrecognized repeats and broader variations.','Mismatch is not necessarily error; harmonic and surrounding context may differ.']};
  fs.writeFileSync(path.join(dir,'report.json'),JSON.stringify(report,null,2));
  rows.push({id,deterministic:report.deterministic,preferenceChecks:feedback.filter(f=>f.matchesPreference!==undefined).length,
   preferenceMismatches:feedback.filter(f=>f.matchesPreference===false).length,alternatives:feedback.filter(f=>f.status==='alternative-report-only').length,
   repeatTransitions:repeated.length,repeatMismatches:repeated.filter(r=>r.mismatch).length});
 }
 for(const id of ['004','005','006']){
  const dir=`K:/MusicSearch/evaluation/case-assets/S-STRUCT-${id}`;
  const snapshot=fs.readFileSync(path.join(dir,'review-snapshot.json')),s=JSON.parse(snapshot),xml=fs.readFileSync(path.join(dir,'context.musicxml'));
  if(hash(xml)!==s.xmlSha256)throw Error('Source mismatch');
  capture(`S-STRUCT-${id}`,s.work.notes,xml,snapshot,(analysis,target)=>{
   const expected=expectations[id];if(!expected)return [];
   const doc=fs.readFileSync(`K:/MusicSearch/evaluation/cases/${expected.document}`);fs.writeFileSync(path.join(target,'feedback-source.md'),doc);
   return ['keep','suppress'].flatMap(want=>expected[want].map(index=>({index,eventId:s.work.notes[index].id,
    expected:want,actual:analysis.boundaries[index].supported?'keep':'suppress',
    matchesPreference:analysis.boundaries[index].supported===(want==='keep'),
    status:'documented-preference-not-gold',documentHash:hash(doc)})));
  });
 }
 const root='reports/reviewer-cases/three-times-a-lady-phrase-alternatives-2026-09-22';
 const snapshot=fs.readFileSync(`${root}/automatic-snapshot.json`),work=JSON.parse(snapshot),xml=fs.readFileSync(`${root}/source.musicxml`);
 const annotation=JSON.parse(fs.readFileSync(`${root}/human-annotation.json`)),events=JSON.parse(fs.readFileSync(`${root}/events.json`));
 if(hash(xml)!==annotation.sourceHash)throw Error('Source mismatch');
 capture('three-times-a-lady',work.notes,xml,snapshot,(a,dir)=>{
  for(const name of ['human-annotation.json','events.json'])fs.copyFileSync(`${root}/${name}`,path.join(dir,name));
  return alternativeChecks(work.notes,a,annotation,events);
 });
 const files=['phrase-boundaries.mjs','phrase-breath-symbols.mjs','repeated-breath-rule.mjs','short-cell-continuity.mjs'];
 fs.writeFileSync(path.join(output,'summary.json'),JSON.stringify({createdAt:new Date().toISOString(),rows,
  codeHashes:Object.fromEntries(files.map(f=>[f,hash(fs.readFileSync(`K:/MusicSearch/server/${f}`))])),auditHash:hash(fs.readFileSync(new URL(import.meta.url)))},null,2));
 const md=['# 프레이즈 회귀·반복 일관성 자동 검사','','운영 변경 없음. 고정 입력을 현재 경계 엔진으로 재분석. UI 후처리 전체 검사는 아니다. 선호 불일치와 반복 불일치는 음악적 오류 확정이 아니다.','','| 사례 | 결정론 | 사용자 선호 불일치/검사 | 대안 수 | 반복 내부 경계 불일치/검사 |','|---|---|---:|---:|---:|',...rows.map(r=>`| ${r.id} | ${r.deterministic} | ${r.preferenceMismatches}/${r.preferenceChecks} | ${r.alternatives} | ${r.repeatMismatches}/${r.repeatTransitions} |`),'','0/0은 성공이 아니라 검증 대상 없음이다. 원본·입력·판정·양쪽 경계 근거는 각 사례 report.json에 보존했다. 사례별 위치는 테스트 라벨이며 운영 규칙이 아니다.'];
 fs.writeFileSync(path.join(output,'README.md'),md.join('\n'));console.log(md.join('\n'));
}
if(process.argv[1]&&import.meta.url===pathToFileURL(path.resolve(process.argv[1])).href)run(process.argv[2]);
