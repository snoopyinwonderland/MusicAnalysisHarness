import {readFileSync,existsSync,mkdirSync,writeFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {resolve} from 'node:path';
import {analyzePhraseBoundaries} from '../server/phrase-boundaries.mjs';
import {notationStructureEvidence} from '../server/notation-structure-evidence.mjs';
import {sourceClosure} from '../server/phrase-source-closure.mjs';
import {sourceMeterTimeline,reviewClosureInMeter} from '../server/phrase-meter-review.mjs';
const run=process.argv[2];
if(!/^[a-zA-Z0-9-]+$/.test(run??''))throw Error('Run name required');
const output=resolve('evaluation/reports',run);
if(existsSync(output))throw Error('Refusing overwrite');
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
const dependencies=['scripts/audit-phrase-closure-cases.mjs','server/phrase-boundaries.mjs','server/phrase-breath-symbols.mjs','server/notation-structure-evidence.mjs','server/xml-target-verification.mjs','server/phrase-source-closure.mjs','server/phrase-meter-review.mjs'];
const report={createdAt:new Date().toISOString(),mode:'offline-no-ui-change',codeHashes:Object.fromEntries(dependencies.map(p=>[p,hash(readFileSync(p))])),cases:[]};
for(let n=1;n<=6;n++){
 const caseId=`S-STRUCT-${String(n).padStart(3,'0')}`,root=resolve('evaluation/case-assets',caseId);
 const missing=['context.musicxml','review-snapshot.json'].filter(f=>!existsSync(resolve(root,f)));
 if(missing.length){report.cases.push({caseId,status:'unavailable',missing});continue;}
 const snapshotBytes=readFileSync(resolve(root,'review-snapshot.json')),snapshot=JSON.parse(snapshotBytes),xml=readFileSync(resolve(root,'context.musicxml'),'utf8');
 if(hash(xml)!==snapshot.xmlSha256){report.cases.push({caseId,status:'source-hash-mismatch'});continue;}
 const notes=snapshot.work.notes,before=JSON.stringify(notes),analysis=analyzePhraseBoundaries(notes);
 const evidence=notationStructureEvidence(xml,snapshot.work.streamId,notes),timeline=sourceMeterTimeline(xml,snapshot.work.streamId.split(':')[0]);
 const boundaries=analysis.boundaries.filter(b=>b.supported&&b.index>0).map(b=>{
  const closure=sourceClosure(evidence,notes,b.index-1);
  return {index:b.index,previousEventId:notes[b.index-1].id,nextEventId:notes[b.index]?.id,closure,meter:reviewClosureInMeter(closure,evidence,timeline)};
 });
 if(before!==JSON.stringify(notes))throw Error('Input mutation');
 const reasons={};for(const b of boundaries){const reason=b.meter.status==='unknown'?b.closure.reason??b.meter.reason:null;if(reason)reasons[reason]=(reasons[reason]??0)+1;}
 report.cases.push({caseId,status:'audited',sourceHash:evidence.sourceHash,snapshotHash:hash(snapshotBytes),engineVersion:analysis.version,noteCount:notes.length,mapped:evidence.mappings.filter(m=>m.status==='mapped').length,warningCount:evidence.warnings.length,
  boundaryCount:boundaries.length,normalized:boundaries.filter(b=>b.meter.status==='normalized').length,protected:boundaries.filter(b=>b.meter.decision==='protect-boundary').length,unknownReasons:reasons,boundaries});
}
mkdirSync(output,{recursive:true});
writeFileSync(resolve(output,'audit.json'),JSON.stringify(report,null,2));
const lines=['# 既存 사례 경계 관찰 점검'.replace('既存','기존'),'','현재 엔진으로 저장 입력을 재분석한 오프라인 점검. 사용자 정답과의 정확도 평가나 병합 실행이 아니다.','', '| 사례 | 상태 | 음표 매핑 | 경계 | 박자 환산 가능 | 보호 |','|---|---|---:|---:|---:|---:|',...report.cases.map(c=>`| ${c.caseId} | ${c.status} | ${c.mapped??'-'}/${c.noteCount??'-'} | ${c.boundaryCount??'-'} | ${c.normalized??'-'} | ${c.protected??'-'} |`),'','## 보류 사유',...report.cases.map(c=>`- ${c.caseId}: ${JSON.stringify(c.unknownReasons??c.missing??c.status)}`),'','보호되지 않은 경계를 잘못된 경계나 병합 대상으로 자동 분류하지 않는다. 원본 파일은 기존 case-assets에 보존하고 hash로 연결했다. 001–003 입력은 현재 snapshot 형식으로 임의 복원하지 않았다.'];
writeFileSync(resolve(output,'review.md'),lines.join('\n'));console.log(lines.join('\n'));
