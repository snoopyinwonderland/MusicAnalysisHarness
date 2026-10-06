import fs from 'node:fs/promises';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';

const outputPath=process.argv[2];
const previewDir=process.argv[3];
if(!outputPath||!previewDir)throw new Error('Usage: node build-classical-repertoire-workbook.mjs <output.xlsx> <preview-dir>');
const asOf=new Date().toLocaleDateString('en-CA',{timeZone:'Asia/Seoul'});

const epochs=['Medieval','Renaissance','Baroque','Classical','Early Romantic','Romantic','Late Romantic','20th Century','Post-War','21st Century'];
const epochKo={'Medieval':'중세','Renaissance':'르네상스','Baroque':'바로크','Classical':'고전주의','Early Romantic':'초기 낭만주의','Romantic':'낭만주의','Late Romantic':'후기 낭만주의','20th Century':'20세기','Post-War':'전후 현대음악','21st Century':'21세기'};
const base='https://api.openopus.org';
const get=async path=>{for(let attempt=0;attempt<3;attempt++){const response=await fetch(base+path);if(response.ok)return response.json();await new Promise(resolve=>setTimeout(resolve,400*(attempt+1)))}throw new Error(`Open Opus request failed: ${path}`)};
const limited=async(items,limit,fn)=>{const out=new Array(items.length);let next=0;await Promise.all(Array.from({length:Math.min(limit,items.length)},async()=>{while(true){const index=next++;if(index>=items.length)return;out[index]=await fn(items[index],index)}}));return out};

const [popularResponse,recommendedResponse,...epochResponses]=await Promise.all([
  get('/composer/list/pop.json'),get('/composer/list/rec.json'),...epochs.map(epoch=>get(`/composer/list/epoch/${encodeURIComponent(epoch)}.json`))
]);
const popularIds=new Set((popularResponse.composers||[]).map(item=>String(item.id)));
const recommendedIds=new Set((recommendedResponse.composers||[]).map(item=>String(item.id)));
const composersById=new Map();
for(const response of epochResponses)for(const composer of response.composers||[])composersById.set(String(composer.id),composer);
const rawComposers=[...composersById.values()];
const workResponses=await limited(rawComposers,12,composer=>get(`/work/list/composer/${composer.id}/genre/all.json`));

const catalogPattern=/\b(?:(?:BWV|KV|Hob\.?|RV|Op\.?|WoO|WAB|FP|WWV|HWV|TWV|BuxWV|Sz\.?|BB|RCT)\s*[A-Za-z0-9:.\-/]+|(?:K|D|S|L|M|R|H|JS|Z)\.?\s*\d[A-Za-z0-9:.\-/]*)/i;
const composerRows=rawComposers.map((composer,index)=>{
  const works=workResponses[index]?.works||[],popularWorks=works.filter(work=>String(work.popular)==='1').length,recommendedWorks=works.filter(work=>String(work.recommended)==='1').length;
  const id=String(composer.id),grade=popularIds.has(id)?'S':recommendedIds.has(id)?'A':popularWorks>=1||recommendedWorks>=3?'B':'C';
  return{...composer,id,works,popularWorks,recommendedWorks,grade,epochKo:epochKo[composer.epoch]||composer.epoch,birthYear:composer.birth?Number(String(composer.birth).slice(0,4)):null,deathYear:composer.death?Number(String(composer.death).slice(0,4)):null,scope:grade==='S'||grade==='A'?'Complete catalogue 우선':grade==='B'?'대표·필수 작품 우선':'특별히 유명한 작품부터'};
}).sort((a,b)=>epochs.indexOf(a.epoch)-epochs.indexOf(b.epoch)||(a.birthYear??9999)-(b.birthYear??9999)||a.complete_name.localeCompare(b.complete_name));

const gradePoints={S:45,A:35,B:25,C:15};
const works=[];
for(const composer of composerRows){
  for(const work of composer.works){
    const popular=String(work.popular)==='1',recommended=String(work.recommended)==='1';
    if(!['S','A'].includes(composer.grade)&&!popular&&!recommended)continue;
    const score=gradePoints[composer.grade]+(popular?30:0)+(recommended?20:0)+(['S','A'].includes(composer.grade)?5:0);
    works.push({composer,work,popular,recommended,score,tier:score>=85?'A':score>=70?'B':score>=55?'C':'D',catalogue:work.title.match(catalogPattern)?.[0]||''});
  }
}
works.sort((a,b)=>epochs.indexOf(a.composer.epoch)-epochs.indexOf(b.composer.epoch)||(a.composer.birthYear??9999)-(b.composer.birthYear??9999)||b.score-a.score||a.composer.complete_name.localeCompare(b.composer.complete_name)||a.work.title.localeCompare(b.work.title));
const topWorks=[...works].sort((a,b)=>b.score-a.score||epochs.indexOf(a.composer.epoch)-epochs.indexOf(b.composer.epoch)||(a.composer.birthYear??9999)-(b.composer.birthYear??9999)||a.work.title.localeCompare(b.work.title)).slice(0,250);

const workbook=Workbook.create();
const summary=workbook.worksheets.add('우선 등록');
const workSheet=workbook.worksheets.add('작품 목록');
const composerSheet=workbook.worksheets.add('작곡가 목록');
const guide=workbook.worksheets.add('기준 및 출처');
for(const sheet of [summary,workSheet,composerSheet,guide])sheet.showGridLines=false;

const navy='#20364B',blue='#315B75',cream='#F5F1E8',gold='#C99A3D',lightBlue='#E8F0F4',lightGold='#F8EBCB',lightRed='#F6DEDA',green='#DDEBDD',border='#D8D2C7';
const title=(sheet,range,text)=>{sheet.getRange(range).merge();const cell=sheet.getRange(range.split(':')[0]);cell.values=[[text]];cell.format={fill:navy,font:{name:'Arial',size:15,bold:true,color:'#FFFFFF'},verticalAlignment:'center'};sheet.getRange(range).format.rowHeight=30};
const header=range=>{range.format={fill:blue,font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},horizontalAlignment:'center',verticalAlignment:'center',wrapText:true,borders:{preset:'inside',style:'thin',color:'#FFFFFF'}};range.format.rowHeight=30};
const section=range=>{range.format={fill:cream,font:{name:'Arial',size:11,bold:true,color:navy},borders:{bottom:{style:'medium',color:gold}}}};

title(summary,'A1:H1','클래식 레퍼토리 등록 우선순위');
summary.getRange('A2:H2').merge();summary.getRange('A2').values=[[`Open Opus 기준 초기 목록 · ${asOf} · 작곡 연도는 별도 검증 전까지 비워 둠`]];summary.getRange('A2').format={font:{italic:true,color:'#66615A'},rowHeight:22};
summary.getRange('A4:H4').values=[['지표','전체','S','A','B','C','등록 A','등록 B']];header(summary.getRange('A4:H4'));
summary.getRange('A5:H5').values=[['개수',composerRows.length,null,null,null,null,null,null]];
summary.getRange('C5:F5').formulas=[['=COUNTIFS(\'작곡가 목록\'!$A$2:$A$500,"S")','=COUNTIFS(\'작곡가 목록\'!$A$2:$A$500,"A")','=COUNTIFS(\'작곡가 목록\'!$A$2:$A$500,"B")','=COUNTIFS(\'작곡가 목록\'!$A$2:$A$500,"C")']];
summary.getRange('G5:H5').formulas=[['=COUNTIFS(\'작품 목록\'!$B$2:$B$20000,"A")','=COUNTIFS(\'작품 목록\'!$B$2:$B$20000,"B")']];
summary.getRange('A7:H7').values=[['시대','작곡가 수','선정 작품 수','S','A','B','C','시대 순서']];header(summary.getRange('A7:H7'));
summary.getRange(`A8:H${7+epochs.length}`).values=epochs.map((epoch,index)=>[epochKo[epoch],null,null,null,null,null,null,index+1]);
for(let row=8;row<8+epochs.length;row++)summary.getRange(`B${row}:G${row}`).formulas=[[`=COUNTIFS('작곡가 목록'!$B$2:$B$500,A${row})`,`=COUNTIFS('작품 목록'!$D$2:$D$20000,A${row})`,`=COUNTIFS('작곡가 목록'!$B$2:$B$500,A${row},'작곡가 목록'!$A$2:$A$500,"S")`,`=COUNTIFS('작곡가 목록'!$B$2:$B$500,A${row},'작곡가 목록'!$A$2:$A$500,"A")`,`=COUNTIFS('작곡가 목록'!$B$2:$B$500,A${row},'작곡가 목록'!$A$2:$A$500,"B")`,`=COUNTIFS('작곡가 목록'!$B$2:$B$500,A${row},'작곡가 목록'!$A$2:$A$500,"C")`]];
summary.getRange('A20:H20').values=[['초기 우선순위','등급','점수','시대','작곡가 등급','작곡가','작품','장르']];header(summary.getRange('A20:H20'));
summary.getRange(`A21:H${20+topWorks.length}`).values=topWorks.map((item,index)=>[index+1,item.tier,item.score,item.composer.epochKo,item.composer.grade,item.composer.complete_name,item.work.title,item.work.genre||'']);
summary.freezePanes.freezeRows(20);summary.getRange('A1:H270').format.verticalAlignment='center';summary.getRange('A:H').format.autofitColumns();summary.getRange('A:A').format.columnWidth=13;summary.getRange('F:F').format.columnWidth=24;summary.getRange('G:G').format.columnWidth=48;summary.getRange('G21:G270').format.wrapText=true;

title(workSheet,'A1:Q1','작품 목록');
const workHeaders=['목록 순번','등록 등급','우선순위 점수','시대','정렬 기준 연도','작곡가 등급','작곡가','작품명','장르','인기 작품','필수 작품','작곡 연도','카탈로그 번호','수집 범위','XML 확보 상태','검증 상태','Open Opus ID'];
workSheet.getRange('A2:Q2').values=[workHeaders];header(workSheet.getRange('A2:Q2'));
const workStart=3,workEnd=workStart+works.length-1;
workSheet.getRange(`A${workStart}:Q${workEnd}`).values=works.map((item,index)=>[index+1,item.tier,item.score,item.composer.epochKo,item.composer.birthYear,item.composer.grade,item.composer.complete_name,item.work.title,item.work.genre||'',item.popular?'예':'아니오',item.recommended?'예':'아니오',null,item.catalogue,item.composer.scope,'미확인','미검증',String(item.work.id)]);
workSheet.getRange(`B${workStart}:B${workEnd}`).formulas=works.map((_,index)=>{const row=workStart+index;return[`=IF(C${row}>=85,"A",IF(C${row}>=70,"B",IF(C${row}>=55,"C","D")))`]});
workSheet.getRange(`C${workStart}:C${workEnd}`).formulas=works.map((_,index)=>{const row=workStart+index;return[`=IF(F${row}="S",45,IF(F${row}="A",35,IF(F${row}="B",25,15)))+IF(J${row}="예",30,0)+IF(K${row}="예",20,0)+IF(OR(F${row}="S",F${row}="A"),5,0)`]});
workSheet.tables.add(`A2:Q${workEnd}`,true,'ClassicalWorksTable').style='TableStyleMedium2';workSheet.freezePanes.freezeRows(2);workSheet.freezePanes.freezeColumns(2);
workSheet.getRange(`O${workStart}:O${workEnd}`).dataValidation={rule:{type:'list',values:['미확인','보유','부분 보유','미보유','권리 검토']}};
workSheet.getRange(`P${workStart}:P${workEnd}`).dataValidation={rule:{type:'list',values:['미검증','검증 중','검증 완료','수정 필요']}};
workSheet.getRange(`B${workStart}:B${workEnd}`).conditionalFormats.add('containsText',{text:'A',format:{fill:lightRed,font:{bold:true,color:'#8A2F24'}}});
workSheet.getRange(`B${workStart}:B${workEnd}`).conditionalFormats.add('containsText',{text:'B',format:{fill:lightGold,font:{bold:true,color:'#6B5018'}}});
workSheet.getRange(`F${workStart}:F${workEnd}`).conditionalFormats.add('containsText',{text:'S',format:{fill:lightRed,font:{bold:true,color:'#8A2F24'}}});
workSheet.getRange(`A${workStart}:Q${workEnd}`).format.verticalAlignment='center';workSheet.getRange(`H${workStart}:H${workEnd}`).format.wrapText=true;
workSheet.getRange('A:Q').format.autofitColumns();for(const [col,width] of Object.entries({A:11,B:10,C:12,D:14,E:12,F:11,G:25,H:52,I:16,J:11,K:11,L:12,M:18,N:25,O:15,P:13,Q:14}))workSheet.getRange(`${col}:${col}`).format.columnWidth=width;

title(composerSheet,'A1:N1','작곡가 목록');
composerSheet.getRange('A2:N2').values=[['작곡가 등급','시대','시대 원문','출생 연도','사망 연도','작곡가','작품 수','인기 작품 수','필수 작품 수','수집 정책','Complete Catalogue 상태','작품 연도 보완','Open Opus ID','출처 URL']];header(composerSheet.getRange('A2:N2'));
const composerStart=3,composerEnd=composerStart+composerRows.length-1;
composerSheet.getRange(`A${composerStart}:N${composerEnd}`).values=composerRows.map(item=>[item.grade,item.epochKo,item.epoch,item.birthYear,item.deathYear,item.complete_name,item.works.length,item.popularWorks,item.recommendedWorks,item.scope,'미확인','필요',item.id,`${base}/composer/list/ids/${item.id}.json`]);
composerSheet.tables.add(`A2:N${composerEnd}`,true,'ClassicalComposersTable').style='TableStyleMedium2';composerSheet.freezePanes.freezeRows(2);composerSheet.freezePanes.freezeColumns(2);
composerSheet.getRange(`K${composerStart}:K${composerEnd}`).dataValidation={rule:{type:'list',values:['미확인','자료 있음','수집 중','완료','해당 없음']}};
composerSheet.getRange(`A${composerStart}:A${composerEnd}`).conditionalFormats.add('containsText',{text:'S',format:{fill:lightRed,font:{bold:true,color:'#8A2F24'}}});
composerSheet.getRange(`A${composerStart}:A${composerEnd}`).conditionalFormats.add('containsText',{text:'A',format:{fill:lightGold,font:{bold:true,color:'#6B5018'}}});
composerSheet.getRange('A:N').format.autofitColumns();for(const [col,width] of Object.entries({A:12,B:15,C:18,D:11,E:11,F:28,G:10,H:12,I:12,J:27,K:22,L:16,M:14,N:55}))composerSheet.getRange(`${col}:${col}`).format.columnWidth=width;

title(guide,'A1:F1','등급 기준과 데이터 출처');
guide.getRange('A3:F3').values=[['작곡가 등급','판정 기준','기본 점수','권장 수집 범위','해석','검토 필요']];header(guide.getRange('A3:F3'));
guide.getRange('A4:F7').values=[
  ['S','Open Opus Popular Composer',45,'Complete catalogue 우선','가장 널리 알려진 핵심 작곡가','작품별 판본·편곡 중복 검토'],
  ['A','Open Opus Essential Composer',35,'Complete catalogue 우선','음악사·연주 레퍼토리의 핵심 작곡가','작곡가별 권위 작품목록 연결'],
  ['B','그 외 작곡가 중 인기 작품 1개 이상 또는 필수 작품 3개 이상',25,'대표·필수 작품 우선','주요 레퍼토리가 여러 곡 있는 작곡가','지역·장르 편향 검토'],
  ['C','그 밖의 등록 작곡가',15,'특별히 유명한 작품부터','확장 및 희귀 레퍼토리','대표작 여부 수동 검토']
];
guide.getRange('A9:F9').values=[['작품 등급','점수','우선순위','산식','XML 확보','주의']];header(guide.getRange('A9:F9'));
guide.getRange('A10:F13').values=[['A','85 이상','가장 먼저 등록','작곡가 점수 + 인기 30 + 필수 20 + 전작대상 5','즉시 확인','시대·편성 균형도 함께 검토'],['B','70–84','1차 확장','동일','우선 확인',''],['C','55–69','2차 확장','동일','순차 확인',''],['D','55 미만','후순위','동일','필요 시 확인','낮은 점수가 낮은 음악적 가치라는 뜻은 아님']];
guide.getRange('A15:F15').values=[['시대 순서','영문 분류','한글 분류','작곡 연도','정렬 기준','비고']];header(guide.getRange('A15:F15'));
guide.getRange(`A16:F${15+epochs.length}`).values=epochs.map((epoch,index)=>[index+1,epoch,epochKo[epoch],'미수록','작곡가 출생 연도(임시)','작품별 실제 연도는 Wikidata·작품 카탈로그로 후속 보완']);
guide.getRange('A27:F27').values=[['출처','용도','URL','접근일','제약','후속 보완']];header(guide.getRange('A27:F27'));
guide.getRange('A28:F31').values=[
  ['Open Opus','작곡가·시대·작품·인기·필수 분류','https://openopus.org/',new Date(),'작곡 연도·상세 편성 누락 가능','작곡가별 권위 카탈로그'],
  ['Open Opus API','본 파일의 초기 원자료','https://github.com/openopus-org/openopus_api/blob/master/USAGE.md',new Date(),'협업형 데이터이므로 검증 필요','정기 새로고침'],
  ['IMSLP','악보 존재·작품 정보·판본 확인','https://imslp.org/wiki/Category:Composers',new Date(),'모든 목록이 완전하지 않음','IMSLP ID와 공개 악보 상태 연결'],
  ['Wikidata Query Service','작곡 연도·식별자 보완','https://query.wikidata.org/',new Date(),'누락·오류 검증 필요','작품별 연도와 외부 ID 연결']
];guide.getRange('D28:D31').setNumberFormat('yyyy-mm-dd');
guide.getRange('A33:F34').values=[['사용 방법','작품 목록은 시대와 작곡가 출생 연도 순서로 정렬되어 있습니다. 등록 등급·작곡가 등급·시대 필터를 함께 사용하십시오.','','','',''],['한계','이 초기판의 우선순위는 Open Opus 분류를 기반으로 하며, 한국 음악대학·도서관 이용 빈도를 아직 반영하지 않았습니다.','','','','']];
guide.getRange('A3:F34').format.verticalAlignment='center';guide.getRange('A3:F34').format.wrapText=true;guide.getRange('A:F').format.autofitColumns();for(const [col,width] of Object.entries({A:22,B:42,C:46,D:25,E:35,F:42}))guide.getRange(`${col}:${col}`).format.columnWidth=width;guide.freezePanes.freezeRows(3);

workbook.recalculate();
const checks={summary:await workbook.inspect({kind:'table',sheetId:summary.sheetId,range:'A1:H30',include:'values,formulas',tableMaxRows:30,tableMaxCols:8}),composers:await workbook.inspect({kind:'table',sheetId:composerSheet.sheetId,range:'A1:N12',include:'values,formulas',tableMaxRows:12,tableMaxCols:14}),works:await workbook.inspect({kind:'table',sheetId:workSheet.sheetId,range:'A1:Q12',include:'values,formulas',tableMaxRows:12,tableMaxCols:17}),errors:await workbook.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:100},summary:'final formula error scan'})};
await fs.mkdir(previewDir,{recursive:true});
for(const [sheetName,range,file] of [['우선 등록','A1:H35','summary.png'],['작품 목록','A1:Q18','works.png'],['작곡가 목록','A1:N18','composers.png'],['기준 및 출처','A1:F34','guide.png']]){const blob=await workbook.render({sheetName,range,scale:1.4,format:'png'});await fs.writeFile(`${previewDir}/${file}`,new Uint8Array(await blob.arrayBuffer()))}
await fs.mkdir(outputPath.replace(/[\\/][^\\/]+$/,''),{recursive:true});
const output=await SpreadsheetFile.exportXlsx(workbook);await output.save(outputPath);
console.log(JSON.stringify({outputPath,composerCount:composerRows.length,workCount:works.length,topCount:topWorks.length,checks:Object.fromEntries(Object.entries(checks).map(([key,value])=>[key,value.ndjson]))},null,2));
