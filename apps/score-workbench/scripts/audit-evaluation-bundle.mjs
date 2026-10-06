import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import {validateEvaluationCases} from './evaluation-case-validation.mjs';
const batch=process.argv[2];assert.match(batch??'',/^[a-z0-9-]+$/);
const root=path.resolve('evaluation/exports',batch),index=JSON.parse(fs.readFileSync(path.join(root,'index.json')));
const records=index.cases.map(x=>JSON.parse(fs.readFileSync(path.join(root,x.path))));validateEvaluationCases(records);
function asset(dir,relative){const p=path.resolve(dir,relative);assert.ok(p.startsWith(root+path.sep),'Bundle reference escapes root: '+relative);assert.ok(fs.existsSync(p),relative);return p;}
for(const [i,c]of records.entries()){
 const dir=path.dirname(path.join(root,index.cases[i].path));
 for(const run of c.runs){asset(dir,run.resultPath);if(run.initialPath)asset(dir,run.initialPath);}
 for(const [key,file]of [['xmlHash',c.knowledgeBase.assets.musicXml],['eventsHash',c.knowledgeBase.assets.events]]){
  assert.ok(file,'Missing snapshot');const data=fs.readFileSync(asset(dir,file));assert.equal(crypto.createHash('sha256').update(data).digest('hex'),c.knowledgeBase.sourceSnapshot[key]);
 }
}
asset(root,index.sourceSuite);asset(root,index.executionManifest);
for(const file of index.supportingFiles??[])asset(root,file);
const report=JSON.parse(fs.readFileSync('evaluation/reports/'+batch+'/results.json'));
assert.equal(report.rows.length,records.length);
assert.ok(report.complete,'Incomplete results');
const audit={batch,validatedCases:records.length,complete:report.complete,errors:report.rows.filter(r=>r.status==='failed').length,retried:report.rows.filter(r=>r.retried).length,invalidAlignmentCases:report.rows.filter(r=>r.invalidAlignmentRanks.length).length,checkedAt:new Date().toISOString()};
fs.writeFileSync(path.join(root,'validation.json'),JSON.stringify(audit,null,2));console.log(JSON.stringify(audit));
