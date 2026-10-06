import {readFileSync,writeFileSync} from 'node:fs';
import {prioritizePreclearance} from '../server/preclearance-priority.mjs';
import {structureHash} from '../server/structure-analysis-adapter.mjs';
const [input,output]=process.argv.slice(2);if(!input||!output)throw new Error('Input and NEW output report required');
const report=prioritizePreclearance(JSON.parse(readFileSync(input,'utf8')));
report.priorityReview.provenance={input,createdAt:new Date().toISOString(),codeHash:structureHash(readFileSync(new URL('../server/preclearance-priority.mjs',import.meta.url),'utf8'))};
writeFileSync(output,JSON.stringify(report,null,2),{flag:'wx'});
console.log(JSON.stringify(report.priorityReview.ranking));
