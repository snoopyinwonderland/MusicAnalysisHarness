import {readFileSync,writeFileSync} from 'node:fs';
const dir='evaluation/reports/eighth-meter-60-v1',r=JSON.parse(readFileSync(dir+'/results.json'));
if(!r.complete||r.rows.some(x=>x.status!=='completed'))throw Error('Searches incomplete');
const groups=['6/8','3/8'].flatMap(meter=>[12,8].flatMap(length=>['original','ornament-delete','ornament-delete-preserve-time'].map(type=>{
 const a=r.rows.filter(x=>x.meter===meter&&x.originalNoteLength===length&&x.type===type);
 return {meter,length,type,total:a.length,top5:a.filter(x=>x.sourceRank&&x.sourceRank<=5).length,top10:a.filter(x=>x.sourceRank&&x.sourceRank<=10).length,found:a.filter(x=>x.sourceRank).length};
})));
const pairs=[...new Set(r.rows.map(x=>x.baseId))].map(baseId=>{const a=r.rows.filter(x=>x.baseId===baseId);return {baseId,meter:a[0].meter,title:a[0].title,length:a[0].originalNoteLength,conditions:a.map(x=>({type:x.type,rank:x.sourceRank,inCandidates:x.trace?.inCandidates,rejections:x.trace?.rejections,issues:x.issues}))};});
writeFileSync(dir+'/timing-comparison.json',JSON.stringify({schema:'musicanote-paired-meter-evaluation/v1',generatedAt:new Date().toISOString(),groups,pairs,limitations:['Five independent source works per meter; paired conditions are not independent melodies.','Time preservation also lengthens the preceding note.','Source-only convenience selection, no population accuracy or false-positive claims.']},null,2));
const names={'original':'원형','ornament-delete':'음+음가 삭제','ornament-delete-preserve-time':'삭제 후 앞 음에 음가 흡수'};
const md=['# 6/8·3/8 조건별 결과','','| 박자 | 원형 음수 | 조건 | Top5 | Top10 | 100위 내 회수 |','|---|---:|---|---:|---:|---:|',...groups.map(g=>'| '+[g.meter,g.length,names[g.type],g.top5+'/'+g.total,g.top10+'/'+g.total,g.found+'/'+g.total].join(' | ')+' |'),'','원본 파일 기준. 원곡 1위는 요구하지 않는다. 8→7음은 경계 사례다.','', '| 사례 | 박자 | 곡명 | 원형 | 시간 축소 | 박자 위치 유지 |','|---|---|---|---:|---:|---:|',...pairs.map(p=>'| '+[p.baseId,p.meter,p.title,...['original','ornament-delete','ornament-delete-preserve-time'].map(k=>p.conditions.find(c=>c.type===k).rank??'100위 내 없음')].join(' | ')+' |')];
writeFileSync(dir+'/TIMING-COMPARISON.md',md.join('\n'));console.log(JSON.stringify(groups));
