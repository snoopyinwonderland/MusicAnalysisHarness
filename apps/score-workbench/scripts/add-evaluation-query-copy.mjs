import {readFileSync,writeFileSync} from 'node:fs';
import {withQueryCopy} from './evaluation-query-copy.mjs';
for(const batch of process.argv.slice(2)){
 const dir='evaluation/reports/'+batch,suite=JSON.parse(readFileSync(dir+'/suite.json')),path=dir+'/index.html';
 const html=withQueryCopy(readFileSync(path,'utf8'),suite);writeFileSync(path,html);console.log(JSON.stringify({batch,cases:suite.cases.length,copyControls:true}));
}
