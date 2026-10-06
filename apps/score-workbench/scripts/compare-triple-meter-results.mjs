import {readFileSync,writeFileSync} from 'node:fs';
const batch='triple-meter-60-v1',dir='evaluation/reports/'+batch;
const r=JSON.parse(readFileSync(dir+'/results.json'));
if(!r.complete||r.rows.some(r=>r.status!=='completed'))throw Error('All searches must complete before final comparison');
const rows=[...new Set(r.rows.map(r=>r.baseId))].map(baseId=>{
 const a=r.rows.filter(r=>r.baseId===baseId),original=a.find(r=>r.type==='original'),compressed=a.find(r=>r.type==='ornament-delete'),preserved=a.find(r=>r.type==='ornament-delete-preserve-time');
 const summary=x=>({rank:x.sourceRank,score:x.sourceScore,inHits:x.trace?.inHits,inCandidates:x.trace?.inCandidates,rejections:x.trace?.rejections,issues:x.issues});
 return {baseId,title:original.title,length:original.originalNoteLength,original:summary(original),compressed:summary(compressed),preserved:summary(preserved)};
});
const result={schema:'musicanote-paired-timing-evaluation/v1',generatedAt:new Date().toISOString(),independentWorks:10,pairedLengths:[12,8],lengthGroups:r.lengthGroups,rows,limitations:['Paired convenience sample; not population accuracy or false-positive rate.','Absorbing deleted duration also lengthens preceding note.','Source-file ranks may differ from work-level retrieval.','No production scoring changes.']};
writeFileSync(dir+'/timing-comparison.json',JSON.stringify(result,null,2));
const rank=n=>n??'100위 내 없음';
const md=['# 3/4 삭제 시간 조건 비교','', '| 사례 | 작품 | 원형 | 시간 축소 | 뒤 음 위치 유지 |','|---|---|---:|---:|---:|',...rows.map(x=>'| '+[x.baseId,x.title,rank(x.original.rank),rank(x.compressed.rank),rank(x.preserved.rank)].join(' | ')+' |'),'','모든 순위는 원본 파일 기준. 상위 10위 회수를 긍정적으로 보되 8→7음 미회수 자체를 오류로 단정하지 않는다. 시간 유지 조건은 앞 음 길이도 달라지므로 순수 박자 효과로 해석하지 않는다.'];
writeFileSync(dir+'/TIMING-COMPARISON.md',md.join('\n'));console.log(JSON.stringify(result.lengthGroups));
