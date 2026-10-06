import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {pathToFileURL} from 'node:url';
import {analyzePhraseBoundaries} from 'file:///K:/MusicSearch/server/phrase-boundaries.mjs';
const hash=x=>createHash('sha256').update(x).digest('hex');

export function transposeInput(notes,semitones){
 if(!Number.isInteger(semitones))throw Error('Integer semitone shift required');
 return notes.map(note=>{
  const n=structuredClone(note);
  if(n.kind!=='rest'&&Number.isFinite(n.pitchMidi)){
   n.pitchMidi+=semitones;
   if(n.pitchMidi<0||n.pitchMidi>127)throw Error('MIDI out of range');
   // This is a pitch-input metamorphic test, not a respelled/transposed score.
   delete n.spelling;
  }
  return n;
 });
}

export function compareBoundaries(a,b){
 const differences=[];
 for(let i=0;i<Math.max(a.boundaries.length,b.boundaries.length);i++){
  const l=a.boundaries[i],r=b.boundaries[i];
  if(!l||!r||l.supported!==r.supported||l.state!==r.state||Math.abs(l.strength-r.strength)>1e-9||Math.abs(l.continuity-r.continuity)>1e-9)
   differences.push({index:i,before:l??null,after:r??null});
 }
 return differences;
}

export function run(inputRoot,output){
 if(fs.existsSync(output))throw Error('Refusing overwrite');
 fs.mkdirSync(output,{recursive:true});
 const shifts=[-12,-7,-2,-1,1,2,7,12],rows=[];
 for(const id of ['S-STRUCT-004','S-STRUCT-005','S-STRUCT-006','three-times-a-lady']){
  const sourceDir=path.join(inputRoot,id),snapshot=fs.readFileSync(path.join(sourceDir,'snapshot.json'));
  const work=JSON.parse(snapshot),notes=(work.work??work).notes;
  const xml=fs.readFileSync(path.join(sourceDir,'source.musicxml'));
  const previous=JSON.parse(fs.readFileSync(path.join(sourceDir,'report.json')));
  if(hash(xml)!==previous.sourceHash||hash(snapshot)!==previous.snapshotHash)throw Error('Frozen input mismatch');
  const dir=path.join(output,id);fs.mkdirSync(dir);
  fs.writeFileSync(path.join(dir,'snapshot.json'),snapshot);fs.writeFileSync(path.join(dir,'source.musicxml'),xml);
  const before=JSON.stringify(notes),baseline=analyzePhraseBoundaries(notes),results=[];
  for(const shift of shifts){
   const transformed=transposeInput(notes,shift),analysis=analyzePhraseBoundaries(transformed);
   const differences=compareBoundaries(baseline,analysis);
   const result={shift,pass:differences.length===0,differences,fullAnalysisEqual:JSON.stringify(baseline)===JSON.stringify(analysis),notes:transformed,analysis};
   fs.writeFileSync(path.join(dir,`shift-${shift}.json`),JSON.stringify(result));
   results.push({shift,pass:result.pass,differenceCount:differences.length,fullAnalysisEqual:result.fullAnalysisEqual});
  }
  if(before!==JSON.stringify(notes))throw Error('Source input mutated');
  fs.writeFileSync(path.join(dir,'baseline.json'),JSON.stringify(baseline));
  rows.push({id,noteCount:notes.length,boundaries:baseline.boundaries.length,sourceHash:hash(xml),snapshotHash:hash(snapshot),sourceUnchanged:true,results});
 }
 const dependencies=['phrase-boundaries.mjs','phrase-breath-symbols.mjs','repeated-breath-rule.mjs','short-cell-continuity.mjs'];
 fs.writeFileSync(path.join(output,'summary.json'),JSON.stringify({createdAt:new Date().toISOString(),shifts,rows,
  codeHashes:Object.fromEntries(dependencies.map(f=>[f,hash(fs.readFileSync(`K:/MusicSearch/server/${f}`))])),testHash:hash(fs.readFileSync(new URL(import.meta.url)))},null,2));
 const md=['# 음높이 이동에 대한 프레이즈 경계 불변성','','이 테스트는 경계 엔진의 pitchMidi 입력만 일정 반음 수만큼 이동한다. MusicXML을 이조해 재파싱하는 end-to-end 검사가 아니다. spelling은 잘못된 음이름 잔류를 피하려 제거하고 조표/화성은 변환하지 않는다. 이 필드들이 경계 분석에 영향을 주기 시작하면 음악적으로 일관된 전체 이조 테스트로 교체해야 한다.','','| 사례 | 입력 음 수 | 경계 불변 통과 | 전체 분석 동일 |','|---|---:|---:|---:|',...rows.map(r=>`| ${r.id} | ${r.noteCount} | ${r.results.filter(t=>t.pass).length}/8 | ${r.results.filter(t=>t.fullAnalysisEqual).length}/8 |`),'','- 이동량: -12, -7, -2, -1, +1, +2, +7, +12반음.','- supported/state/strength/continuity를 비교한다. 전체 분석 JSON 동일 여부도 별도 검사한다.','- 원본 불변성 및 저장 입력/XML hash 확인. 각 폴더에 원본/기준 결과/모든 변환 입력·결과 보존.','- 통과는 음높이 이동 안정성이지 프레이즈의 음악적 정답률이 아니다. 기존 과분할은 그대로 일관되게 남을 수 있다.','- 운영 코드/악보/UI 변경 없음. 다음은 tie 등 동등 기보의 정규화 검사다.','','재현: `node --test audit_phrase_transposition.test.mjs` 후 `node audit_phrase_transposition.mjs reports/phrase-consistency-2026-09-22 reports/phrase-transposition-new` (새 출력 폴더).'];
 fs.writeFileSync(path.join(output,'README.md'),md.join('\n'));console.log(md.join('\n'));
}
if(process.argv[1]&&import.meta.url===pathToFileURL(path.resolve(process.argv[1])).href)run(process.argv[2],process.argv[3]);
