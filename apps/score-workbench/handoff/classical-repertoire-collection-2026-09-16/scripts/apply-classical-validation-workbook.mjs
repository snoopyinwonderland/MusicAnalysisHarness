import fs from 'node:fs/promises';
import { FileBlob, SpreadsheetFile } from '@oai/artifact-tool';

const [sourcePath, validationPath, outputPath, previewDir] = process.argv.slice(2);
if (!sourcePath || !validationPath || !outputPath || !previewDir) throw new Error('Usage: node apply-classical-validation-workbook.mjs <source.xlsx> <validation.json> <output.xlsx> <preview-dir>');
const data=JSON.parse(await fs.readFile(validationPath,'utf8'));
const workbook=await SpreadsheetFile.importXlsx(await FileBlob.load(sourcePath));
await fs.mkdir(previewDir,{recursive:true});
const before=await workbook.render({sheetName:'보유 현황',range:'A1:H33',scale:1.1,format:'png'});await fs.writeFile(`${previewDir}/before-coverage.png`,new Uint8Array(await before.arrayBuffer()));

const navy='#20364B',blue='#315B75',cream='#F5F1E8',lightRed='#F6DEDA',lightGold='#F8EBCB',green='#DDEBDD',lightBlue='#E8F0F4';
const title=(sheet,range,text)=>{sheet.getRange(range).merge();sheet.getRange(range.split(':')[0]).values=[[text]];sheet.getRange(range).format={fill:navy,font:{name:'Arial',size:15,bold:true,color:'#FFFFFF'},verticalAlignment:'center',rowHeight:30};};
const header=range=>{range.format={fill:blue,font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},horizontalAlignment:'center',verticalAlignment:'center',wrapText:true,rowHeight:32,borders:{preset:'inside',style:'thin',color:'#FFFFFF'}};};
const finish=(sheet,range,widths,freeze=2)=>{sheet.showGridLines=false;sheet.getRange(range).format.verticalAlignment='center';sheet.getRange(range).format.wrapText=true;for(const [col,width] of Object.entries(widths))sheet.getRange(`${col}:${col}`).format.columnWidth=width;sheet.freezePanes.freezeRows(freeze);};

const validation=data.validation;
const verify=workbook.worksheets.add('보유 검증 큐');title(verify,'A1:R1','자동 일치 결과 검증 큐');
verify.getRange('A2:R2').values=[['검증 순번','검증 우선순위','현재 상태','관계 분류','수동 검증','작품 등급','작곡가 등급','목록 작곡가','목록 작품','카탈로그','일치 작품','일치 작곡가','데이터셋','원본 경로','신뢰도','권리 분류','라이선스','검색 work ID']];header(verify.getRange('A2:R2'));
verify.getRange(`A3:R${validation.length+2}`).values=validation.map((v,i)=>[i+1,v.validation_priority,v.status,v.relation,v.manual_status,v.tier,v.composer_grade,v.composer,v.title,v.catalogue,v.matched_title,v.matched_composer,v.dataset,v.source,v.confidence,v.rights,v.license,v.work_id]);
verify.tables.add(`A2:R${validation.length+2}`,true,'ClassicalValidationQueueTable').style='TableStyleMedium2';
verify.getRange(`E3:E${validation.length+2}`).dataValidation={rule:{type:'list',values:['미검증','동일 작품 확인','악장 확인','편곡판 확인','다른 작품','보류']}};
verify.getRange(`O3:O${validation.length+2}`).setNumberFormat('0.0%');
verify.getRange(`D3:D${validation.length+2}`).conditionalFormats.add('containsText',{text:'동일 작품 후보',format:{fill:green,font:{bold:true,color:'#2E5C3B'}}});
verify.getRange(`D3:D${validation.length+2}`).conditionalFormats.add('containsText',{text:'편곡판 후보',format:{fill:lightGold,font:{bold:true,color:'#6B5018'}}});
verify.getRange(`P3:P${validation.length+2}`).conditionalFormats.add('containsText',{text:'충돌',format:{fill:lightRed,font:{bold:true,color:'#8A2F24'}}});
finish(verify,`A1:R${validation.length+2}`,{A:12,B:23,C:13,D:17,E:17,F:11,G:12,H:27,I:48,J:17,K:46,L:29,M:14,N:48,O:11,P:22,Q:18,R:29});verify.freezePanes.freezeColumns(5);

const wave=data.wave1;
const collect=workbook.worksheets.add('1차 수집');title(collect,'A1:N1','클래식 XML 1차 수집 목록');
collect.getRange('A2:N2').values=[['1차 순번','작품 등급','점수','작곡가 등급','시대','작곡가','작품','카탈로그','선정 기준','권장 확인처','수집 상태','권리 상태','XML 품질','메모']];header(collect.getRange('A2:N2'));
collect.getRange(`A3:N${wave.length+2}`).values=wave.map((v,i)=>[i+1,v.tier,v.score,v.composer_grade,v.era,v.composer,v.title,v.catalogue,`${v.composer_grade}등급 작곡가 · 작품 ${v.tier}등급 · 작곡가별 상한 적용`,'IMSLP·RISM·작곡가별 권위 카탈로그','대기','미확인','미검사','']);
collect.tables.add(`A2:N${wave.length+2}`,true,'ClassicalFirstWaveTable').style='TableStyleMedium2';
collect.getRange(`K3:K${wave.length+2}`).dataValidation={rule:{type:'list',values:['대기','출처 확인','다운로드 중','파싱 중','등록 완료','보류']}};
collect.getRange(`L3:L${wave.length+2}`).dataValidation={rule:{type:'list',values:['미확인','퍼블릭 도메인','허가 필요','내부 검색만','공개 제외']}};
collect.getRange(`M3:M${wave.length+2}`).dataValidation={rule:{type:'list',values:['미검사','정상','부분 파싱','렌더링 오류','검색 제외']}};
finish(collect,`A1:N${wave.length+2}`,{A:12,B:11,C:10,D:12,E:16,F:28,G:52,H:18,I:38,J:40,K:15,L:17,M:17,N:30});collect.freezePanes.freezeColumns(4);

const overview=workbook.worksheets.getItem('보유 현황');
overview.getRange('J1:N1').merge();overview.getRange('J1').values=[['검증·1차 수집 현황']];overview.getRange('J1:N1').format={fill:navy,font:{name:'Arial',size:13,bold:true,color:'#FFFFFF'},verticalAlignment:'center',rowHeight:30};
overview.getRange('J3:N3').values=[['항목','개수','비율','현재 상태','다음 조치']];header(overview.getRange('J3:N3'));
const ps=data.priority_summary,rs=data.rights_summary,vs=data.validation_summary;
overview.getRange('J4:N12').values=[
 ['검증 대상',validation.length,1,'큐 생성','수동 표본 검증'],['고신뢰 표본',ps['1. 고신뢰 표본 검증']||0,null,'미검증','카탈로그·원본 확인'],['관계 검증',ps['2. 관계 검증']||0,null,'미검증','악장·편곡 구분'],['부분 일치',ps['3. 부분 일치 검증']||0,null,'미검증','제목·작곡가 재확인'],['후보 재검토',ps['4. 후보 재검토']||0,null,'미검증','오탐 제거'],['동일 작품 후보',vs['동일 작품 후보']||0,null,'자동 분류','표본 검증'],['편곡판 후보',vs['편곡판 후보']||0,null,'자동 분류','원곡 관계 연결'],['라이선스 충돌',rs['라이선스 충돌 검토']||0,null,'공개 보류','권리 확인'],['1차 수집',wave.length,null,`${data.wave1_composers}명 작곡가`,'출처·권리 확인']
];
for(let row=5;row<=12;row++)overview.getRange(`L${row}`).formulas=[[`=K${row}/$K$4`]];overview.getRange('L4:L12').setNumberFormat('0.0%');
overview.getRange('J14:N14').merge();overview.getRange('J14').values=[['1차 수집은 목표 개수를 억지로 채우지 않고, 미보유 중 S/A 작곡가의 A/B 작품만 선정했습니다. 동일 작곡가 쏠림을 막기 위해 S는 최대 12곡, A는 최대 7곡으로 제한했습니다.']];overview.getRange('J14:N14').format={fill:cream,font:{color:'#6B5018',bold:true},wrapText:true,rowHeight:46};
for(const [col,width] of Object.entries({J:25,K:12,L:12,M:20,N:30}))overview.getRange(`${col}:${col}`).format.columnWidth=width;

const summary=workbook.worksheets.getItem('우선 등록');summary.getRange('J16:N16').values=[['다음 실행 큐','대상','작곡가','권리 충돌','상태']];header(summary.getRange('J16:N16'));summary.getRange('J17:N17').values=[['클래식 XML 1차 수집',wave.length,data.wave1_composers,rs['라이선스 충돌 검토']||0,'출처 확인 전']];

workbook.recalculate();
const checks={verify:await workbook.inspect({kind:'table',range:'보유 검증 큐!A1:R12',include:'values,formulas',tableMaxRows:12,tableMaxCols:18}),collect:await workbook.inspect({kind:'table',range:'1차 수집!A1:N15',include:'values,formulas',tableMaxRows:15,tableMaxCols:14}),overview:await workbook.inspect({kind:'table',range:'보유 현황!J1:N14',include:'values,formulas',tableMaxRows:16,tableMaxCols:6}),errors:await workbook.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:300},summary:'final formula error scan'})};
for(const [sheetName,range,file] of [['보유 검증 큐','A1:R18','validation.png'],['1차 수집','A1:N20','wave1.png'],['보유 현황','J1:N14','validation-summary.png'],['우선 등록','J15:N18','summary-next.png']]){const blob=await workbook.render({sheetName,range,scale:1.25,format:'png'});await fs.writeFile(`${previewDir}/${file}`,new Uint8Array(await blob.arrayBuffer()));}
await fs.mkdir(outputPath.replace(/[\\/][^\\/]+$/,''),{recursive:true});const output=await SpreadsheetFile.exportXlsx(workbook);await output.save(outputPath);
console.log(JSON.stringify({outputPath,validation:validation.length,wave1:wave.length,wave1Composers:data.wave1_composers,checks:Object.fromEntries(Object.entries(checks).map(([k,v])=>[k,v.ndjson]))},null,2));
