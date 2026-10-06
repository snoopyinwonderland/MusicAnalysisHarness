import { FileBlob, SpreadsheetFile } from '@oai/artifact-tool';

const path=process.argv[2];
const workbook=await SpreadsheetFile.importXlsx(await FileBlob.load(path));
workbook.recalculate();
const sheets=await workbook.inspect({kind:'sheet',include:'id,name',maxChars:3000});
const summary=await workbook.inspect({kind:'table',sheetId:'우선 등록',range:'A1:H30',include:'values,formulas',tableMaxRows:30,tableMaxCols:8,maxChars:12000});
const composers=await workbook.inspect({kind:'table',sheetId:'작곡가 목록',range:'A1:N12',include:'values,formulas',tableMaxRows:12,tableMaxCols:14,maxChars:8000});
const works=await workbook.inspect({kind:'table',sheetId:'작품 목록',range:'A1:Q12',include:'values,formulas',tableMaxRows:12,tableMaxCols:17,maxChars:8000});
const errors=await workbook.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:100},summary:'final formula error scan',maxChars:5000});
console.log(JSON.stringify({sheets:sheets.ndjson,summary:summary.ndjson,composers:composers.ndjson,works:works.ndjson,errors:errors.ndjson},null,2));
