import {readFileSync,writeFileSync,mkdirSync,existsSync,statSync} from 'node:fs';
import {createHash} from 'node:crypto';
const oldDir='evaluation/runs/double-ornament-trial-v1',dir='evaluation/runs/double-ornament-trial-v2',suitePath='evaluation/reports/double-ornament-trial-v2/suite.json';
const old=JSON.parse(readFileSync('evaluation/reports/double-ornament-trial-v1/suite.json')),suite=JSON.parse(readFileSync(suitePath)),manifest=JSON.parse(readFileSync(oldDir+'/manifest.json'));
const hash=p=>createHash('sha256').update(readFileSync(p)).digest('hex'),db=statSync('data/search-index-v2/search.sqlite');
if(manifest.fingerprint.engine!==hash('server/search-api.mjs')||manifest.fingerprint.dbSize!==db.size||manifest.fingerprint.dbTime!==db.mtimeMs||!manifest.fingerprint.omission)throw Error('Reuse forbidden: changed engine/DB/config');
const signature=q=>JSON.stringify({...q,events:q.events.map(({id,...e})=>e)}),reused=[];mkdirSync(dir,{recursive:false});
writeFileSync(dir+'/manifest.json',JSON.stringify({...manifest,fingerprint:{...manifest.fingerprint,suite:hash(suitePath)},reusePolicy:'Only identical query excluding event IDs, same expected work, same engine/DB and successful completed response.'},null,2),{flag:'wx'});
for(const c of suite.cases){const b=suite.bases.find(x=>x.baseId===c.baseId),prior=old.cases.find(x=>signature(x.query)===signature(c.query)&&old.bases.find(y=>y.baseId===x.baseId).expected.workId===b.expected.workId);if(!prior)continue;const path=oldDir+'/'+prior.caseId+'.json';if(!existsSync(path))continue;const r=JSON.parse(readFileSync(path));if(r.status!=='completed')continue;
 const provenance={source:path,sha256:hash(path),reason:'Identical query except IDs, same expected work, same engine/DB.'};writeFileSync(dir+'/'+c.caseId+'.json',JSON.stringify({...r,caseId:c.caseId,kind:c.kind,reusedFrom:provenance}),{flag:'wx'});reused.push({caseId:c.caseId,...provenance});}
writeFileSync(dir+'/reuse.json',JSON.stringify(reused,null,2));console.log(JSON.stringify({reused:reused.length,newExecutions:suite.cases.length-reused.length}));
