import fs from 'node:fs/promises';
import { FileBlob, SpreadsheetFile } from '@oai/artifact-tool';

const [sourcePath, coveragePath, outputPath, previewDir] = process.argv.slice(2);
if (!sourcePath || !coveragePath || !outputPath || !previewDir) throw new Error('Usage: node apply-classical-coverage-workbook.mjs <source.xlsx> <coverage.json> <output.xlsx> <preview-dir>');

const coverage = JSON.parse(await fs.readFile(coveragePath, 'utf8'));
const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(sourcePath));
await fs.mkdir(previewDir, { recursive: true });
const before = await workbook.render({ sheetName: '작품 목록', range: 'A1:Q18', scale: 1.1, format: 'png' });
await fs.writeFile(`${previewDir}/before-works.png`, new Uint8Array(await before.arrayBuffer()));

const navy='#20364B',blue='#315B75',cream='#F5F1E8',gold='#C99A3D',lightRed='#F6DEDA',lightGold='#F8EBCB',green='#DDEBDD',lightBlue='#E8F0F4';
const title=(sheet,range,text)=>{sheet.getRange(range).merge();sheet.getRange(range.split(':')[0]).values=[[text]];sheet.getRange(range).format={fill:navy,font:{name:'Arial',size:15,bold:true,color:'#FFFFFF'},verticalAlignment:'center',rowHeight:30};};
const header=range=>{range.format={fill:blue,font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},horizontalAlignment:'center',verticalAlignment:'center',wrapText:true,rowHeight:32,borders:{preset:'inside',style:'thin',color:'#FFFFFF'}};};
const finish=(sheet,range,widths,freeze=2)=>{sheet.showGridLines=false;sheet.getRange(range).format.verticalAlignment='center';sheet.getRange(range).format.wrapText=true;for(const [col,width] of Object.entries(widths))sheet.getRange(`${col}:${col}`).format.columnWidth=width;sheet.freezePanes.freezeRows(freeze);};

const works=workbook.worksheets.getItem('작품 목록');
const matches=coverage.matches;
const endRow=matches.length+2;
works.getRange(`O3:O${endRow}`).values=matches.map(m=>[m.status]);
works.getRange(`P3:P${endRow}`).values=matches.map(m=>[m.status==='보유'?'검증 중':'미검증']);
works.getRange(`O3:O${endRow}`).dataValidation={rule:{type:'list',values:['미확인','보유','부분 보유','검토 필요','미보유','권리 검토']}};
works.getRange(`P3:P${endRow}`).dataValidation={rule:{type:'list',values:['미검증','검증 중','검증 완료','수정 필요']}};
works.getRange(`O3:O${endRow}`).conditionalFormats.add('containsText',{text:'보유',format:{fill:green,font:{bold:true,color:'#2E5C3B'}}});
works.getRange(`O3:O${endRow}`).conditionalFormats.add('containsText',{text:'검토 필요',format:{fill:lightGold,font:{bold:true,color:'#6B5018'}}});
works.getRange(`O3:O${endRow}`).conditionalFormats.add('containsText',{text:'미보유',format:{fill:lightRed,font:{bold:true,color:'#8A2F24'}}});

const overview=workbook.worksheets.add('보유 현황');
title(overview,'A1:H1','클래식 목록과 검색 DB 보유 현황');
overview.getRange('A2:H2').merge();overview.getRange('A2').values=[[`자동 대조 스냅샷 · ${new Date().toLocaleDateString('en-CA',{timeZone:'Asia/Seoul'})} · 자동 보유 판정도 수동 검증 전까지 확정값이 아님`]];overview.getRange('A2').format={font:{italic:true,color:'#66615A'},rowHeight:22};
overview.getRange('A4:H4').values=[['지표','값','비율','판정 기준','Music Analysis','PDMX','KYSing','비고']];header(overview.getRange('A4:H4'));
const counts=coverage.summary;
overview.getRange('A5:H10').values=[
 ['검색 DB 작품',coverage.inventory_works,null,'source+title+composer로 stream 통합',coverage.dataset_summary['Music Analysis']||0,coverage.dataset_summary.PDMX||0,coverage.dataset_summary.KYSing||0,`${coverage.stream_count.toLocaleString()} streams`],
 ['대조 대상',coverage.target_works,1,'클래식 작품 목록 전체',null,null,null,''],
 ['보유',counts['보유']||0,null,'카탈로그+작곡가/제목 또는 제목+작곡가',null,null,null,'수동 검증 필요'],
 ['부분 보유',counts['부분 보유']||0,null,'작곡가+핵심 제목 토큰 62% 이상',null,null,null,'판본·악장 확인'],
 ['검토 필요',counts['검토 필요']||0,null,'단일 강한 단서만 있음',null,null,null,'자동 보유 처리 안 함'],
 ['미보유',counts['미보유']||0,null,'엄격 기준 미충족',null,null,null,'우선 수집 큐 대상']
];
for(let row=6;row<=10;row++)overview.getRange(`C${row}`).formulas=[[`=B${row}/$B$6`]];
overview.getRange('C6:C10').setNumberFormat('0.0%');
overview.getRange('A13:F13').values=[['작곡가 등급','대상','보유','부분 보유','검토 필요','미보유']];header(overview.getRange('A13:F13'));
const grades=['S','A','B','C'];
overview.getRange('A14:F17').values=grades.map(g=>{const subset=matches.filter(m=>m.composer_grade===g);return[g,subset.length,subset.filter(m=>m.status==='보유').length,subset.filter(m=>m.status==='부분 보유').length,subset.filter(m=>m.status==='검토 필요').length,subset.filter(m=>m.status==='미보유').length]});
overview.getRange('A20:F20').values=[['시대','대상','보유','부분 보유','검토 필요','미보유']];header(overview.getRange('A20:F20'));
const eras=[...new Set(matches.map(m=>m.era))];
overview.getRange(`A21:F${20+eras.length}`).values=eras.map(e=>{const subset=matches.filter(m=>m.era===e);return[e,subset.length,subset.filter(m=>m.status==='보유').length,subset.filter(m=>m.status==='부분 보유').length,subset.filter(m=>m.status==='검토 필요').length,subset.filter(m=>m.status==='미보유').length]});
overview.getRange('A33:H33').values=[['주의','자동 대조는 동일 작품의 다른 악장·편곡·언어 제목을 완전히 해결하지 못합니다. `검토 필요`는 보유로 집계하지 않았고, `보유`도 카탈로그 번호와 작곡가를 수동 확인한 뒤 확정해야 합니다.','','','','','','']];overview.getRange('A33:H33').merge();overview.getRange('A33:H33').format={fill:cream,font:{color:'#6B5018',bold:true},wrapText:true,rowHeight:38};
finish(overview,'A1:H33',{A:23,B:14,C:12,D:48,E:17,F:17,G:17,H:34},4);

const detail=workbook.worksheets.add('대조 상세');
title(detail,'A1:P1','클래식 작품 자동 대조 상세');
const detailHeaders=['작품 목록 행','보유 상태','신뢰도','판정 방법','작품 등급','점수','시대','작곡가 등급','목록 작곡가','목록 작품','카탈로그','일치 작품','일치 작곡가','데이터셋','원본 경로','검색 work ID'];
detail.getRange('A2:P2').values=[detailHeaders];header(detail.getRange('A2:P2'));
detail.getRange(`A3:P${endRow}`).values=matches.map(m=>[m.row,m.status,m.confidence,m.method,m.tier,m.score,m.era,m.composer_grade,m.composer,m.title,m.catalogue,m.matched_title,m.matched_composer,m.dataset,m.source,m.work_id]);
detail.tables.add(`A2:P${endRow}`,true,'ClassicalCoverageDetailTable').style='TableStyleMedium2';
detail.getRange(`C3:C${endRow}`).setNumberFormat('0.0%');
detail.getRange(`B3:B${endRow}`).conditionalFormats.add('containsText',{text:'보유',format:{fill:green,font:{bold:true,color:'#2E5C3B'}}});
detail.getRange(`B3:B${endRow}`).conditionalFormats.add('containsText',{text:'검토 필요',format:{fill:lightGold,font:{bold:true,color:'#6B5018'}}});
detail.getRange(`B3:B${endRow}`).conditionalFormats.add('containsText',{text:'미보유',format:{fill:lightRed,font:{bold:true,color:'#8A2F24'}}});
finish(detail,`A1:P${endRow}`,{A:12,B:13,C:11,D:30,E:11,F:10,G:16,H:12,I:27,J:50,K:17,L:46,M:29,N:15,O:48,P:29});detail.freezePanes.freezeColumns(4);

const gradeOrder={S:0,A:1,B:2,C:3};const tierOrder={A:0,B:1,C:2,D:3};
const missing=matches.filter(m=>m.status==='미보유').sort((a,b)=>tierOrder[a.tier]-tierOrder[b.tier]||gradeOrder[a.composer_grade]-gradeOrder[b.composer_grade]||Number(b.score||0)-Number(a.score||0)||String(a.composer).localeCompare(String(b.composer))||String(a.title).localeCompare(String(b.title)));
const queue=workbook.worksheets.add('수집 우선순위');title(queue,'A1:L1','미보유 클래식 XML 수집 우선순위');
queue.getRange('A2:L2').values=[['수집 순번','작품 등급','점수','작곡가 등급','시대','작곡가','작품','카탈로그','권장 확인처','수집 상태','권리 상태','메모']];header(queue.getRange('A2:L2'));
queue.getRange(`A3:L${missing.length+2}`).values=missing.map((m,i)=>[i+1,m.tier,m.score,m.composer_grade,m.era,m.composer,m.title,m.catalogue,'IMSLP·RISM·작곡가별 권위 카탈로그','대기','미확인','']);
queue.tables.add(`A2:L${missing.length+2}`,true,'MissingClassicalQueueTable').style='TableStyleMedium2';
queue.getRange(`J3:J${missing.length+2}`).dataValidation={rule:{type:'list',values:['대기','출처 확인','다운로드 중','파싱 중','등록 완료','보류']}};
queue.getRange(`K3:K${missing.length+2}`).dataValidation={rule:{type:'list',values:['미확인','퍼블릭 도메인','허가 필요','내부 검색만','공개 제외']}};
finish(queue,`A1:L${missing.length+2}`,{A:12,B:11,C:10,D:12,E:16,F:28,G:52,H:18,I:39,J:15,K:17,L:30});queue.freezePanes.freezeColumns(4);

const summary=workbook.worksheets.getItem('우선 등록');
summary.getRange('J12:N12').values=[['DB 대조','대상','보유','보유율','미보유']];header(summary.getRange('J12:N12'));
summary.getRange('J13:N13').values=[['클래식 작품',coverage.target_works,counts['보유']||0,null,counts['미보유']||0]];
summary.getRange('M13').formulas=[['=L13/K13']];summary.getRange('M13').setNumberFormat('0.0%');

workbook.recalculate();
const checks={
 overview:await workbook.inspect({kind:'table',range:'보유 현황!A1:H33',include:'values,formulas',tableMaxRows:35,tableMaxCols:8}),
 detail:await workbook.inspect({kind:'table',range:'대조 상세!A1:P12',include:'values,formulas',tableMaxRows:12,tableMaxCols:16}),
 queue:await workbook.inspect({kind:'table',range:'수집 우선순위!A1:L12',include:'values,formulas',tableMaxRows:12,tableMaxCols:12}),
 errors:await workbook.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:300},summary:'final formula error scan'})
};
for(const [sheetName,range,file] of [['보유 현황','A1:H33','coverage-overview.png'],['대조 상세','A1:P18','coverage-detail.png'],['수집 우선순위','A1:L18','collection-queue.png'],['우선 등록','J10:N14','summary-coverage.png'],['작품 목록','M1:Q18','works-status.png']]){const blob=await workbook.render({sheetName,range,scale:1.25,format:'png'});await fs.writeFile(`${previewDir}/${file}`,new Uint8Array(await blob.arrayBuffer()));}
await fs.mkdir(outputPath.replace(/[\\/][^\\/]+$/,''),{recursive:true});
const output=await SpreadsheetFile.exportXlsx(workbook);await output.save(outputPath);
console.log(JSON.stringify({outputPath,counts,inventoryWorks:coverage.inventory_works,targetWorks:coverage.target_works,missing:missing.length,checks:Object.fromEntries(Object.entries(checks).map(([k,v])=>[k,v.ndjson]))},null,2));
