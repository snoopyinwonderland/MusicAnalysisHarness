import {readFileSync,writeFileSync,mkdirSync,existsSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {resolve} from 'node:path';
import {analyzePhraseBoundaries} from '../server/phrase-boundaries.mjs';
import {structureRegistry} from '../server/phrase-structure-registry.mjs';
import {notationStructureEvidence} from '../server/notation-structure-evidence.mjs';
import {sourceClosure} from '../server/phrase-source-closure.mjs';
import {sourceMeterTimeline,reviewClosureInMeter} from '../server/phrase-meter-review.mjs';
const run=process.argv[2];if(!/^[a-z0-9-]+$/.test(run??''))throw Error('Run name required');
const out=resolve('evaluation/reports',run);if(existsSync(out))throw Error('Refusing overwrite');
const hash=s=>createHash('sha256').update(s).digest('hex');
// Offline fixture mappings from documented feedback, never production conditions.
const expectations={
 '005':{document:'evaluation/cases/s-struct-005-review.md',keep:[33,46,79],suppress:[31,37,43,77]},
 '006':{document:'evaluation/cases/s-struct-006-structure-baseline.md',keep:[13,29,42,57],suppress:[51]}
};
mkdirSync(out,{recursive:true});const summary=[];
for(const suffix of ['004','005','006']){
 const caseId=`S-STRUCT-${suffix}`,root=`evaluation/case-assets/${caseId}/`,bytes=readFileSync(root+'review-snapshot.json'),s=JSON.parse(bytes),xml=readFileSync(root+'context.musicxml','utf8');
 if(hash(xml)!==s.xmlSha256)throw Error('Source mismatch');
 const notes=s.work.notes,analysis=analyzePhraseBoundaries(notes),starts=[0,...analysis.boundaries.filter(b=>b.supported&&b.index>0&&b.index<notes.length-1).map(b=>b.index)];
 const spans=starts.map((startIndex,i)=>({startIndex,endIndexExclusive:starts[i+1]??notes.length}));
 const result=structureRegistry(notes,spans),e=notationStructureEvidence(xml,s.work.streamId,notes),t=sourceMeterTimeline(xml,s.work.streamId.split(':')[0]);
 for(const p of result.proposals){
  const idx=notes.findIndex(n=>n.id===p.internalBoundaryEventId);
  p.protection=reviewClosureInMeter(sourceClosure(e,notes,idx-1),e,t);
  if(p.protection.decision==='protect-boundary')p.decision='keep';
 }
 const expected=expectations[suffix];
 const checks=expected?['keep','suppress'].flatMap(want=>expected[want].map(index=>({nextEventId:notes[index].id,previousEventId:notes[index-1].id,sourceDocument:expected.document,sourceDocumentHash:hash(readFileSync(expected.document)),interpretation:'documented-user-preference-not-gold',expected:want,actual:analysis.boundaries[index].supported?'keep':'suppress',pass:analysis.boundaries[index].supported===(want==='keep')}))):[];
 const report={caseId,sourceHash:s.xmlSha256,snapshotHash:hash(bytes),version:analysis.version,feedbackChecks:checks,...result};
 writeFileSync(resolve(out,`${caseId}.json`),JSON.stringify(report));
 summary.push({caseId,comparisons:result.comparisons,status:result.status,proposals:result.proposals.length,protected:result.proposals.filter(p=>p.decision==='keep').length,checks:checks.length,passed:checks.filter(c=>c.pass).length,failures:checks.filter(c=>!c.pass)});
}
const dependencies=['scripts/evaluate-structure-feedback.mjs','server/phrase-structure-registry.mjs','src/music/structureTemplateAlignment.ts','src/music/motifSimilarity.ts','server/phrase-boundaries.mjs','server/phrase-breath-symbols.mjs','server/notation-structure-evidence.mjs','server/xml-target-verification.mjs','server/phrase-source-closure.mjs','server/phrase-meter-review.mjs'];
writeFileSync(resolve(out,'summary.json'),JSON.stringify({createdAt:new Date().toISOString(),codeHashes:Object.fromEntries(dependencies.map(p=>[p,hash(readFileSync(p))])),summary},null,2));
const lines=['# 反復 구조 / 사용자 피드백 검증'.replace('反復','반복'),'','모든 비교는 frozen baseline을 사용하며 새 병합안을 기준형으로 승격하지 않는다. 화면 적용 없음.','', '| 사례 | 정렬 수 | 인접 결합 검토 | 보호 | 의견 일치 | 상태 |','|---|---:|---:|---:|---|---|',...summary.map(r=>`| ${r.caseId} | ${r.comparisons} | ${r.proposals} | ${r.protected} | ${r.passed}/${r.checks} | ${r.status} |`),'','0/0은 검증할 event 기준 의견을 아직 정리하지 못한 상태다. 의견 일치는 확정 정답 정확도가 아니다.','',...summary.flatMap(r=>r.failures.map(f=>`- 미해결 ${r.caseId}: ${f.previousEventId} → ${f.nextEventId}, 요청 ${f.expected}, 현행 ${f.actual}.`)),'','001–003은 events.json 구간 발췌가 있지만 전체 review-snapshot과 동등하지 않아 제외했다. E(독립 검토·임계값 보정)가 끝나기 전 F 자동 적용은 하지 않는다.'];
writeFileSync(resolve(out,'review.md'),lines.join('\n'));console.log(lines.join('\n'));
