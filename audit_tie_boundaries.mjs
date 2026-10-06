import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {analyzePhraseBoundaries} from 'file:///K:/MusicSearch/server/phrase-boundaries.mjs';
import {compareBoundaries} from './audit_phrase_transposition.mjs';
const root='reports/phrase-tie-notation-2026-09-22',results=[];
for(const entry of fs.readdirSync(root,{withFileTypes:true}).filter(e=>e.isDirectory())){
 const folder=path.join(root,entry.name),input=JSON.parse(fs.readFileSync(path.join(folder,'normalization.json')));
 const before=analyzePhraseBoundaries(input.before.notes),after=analyzePhraseBoundaries(input.after.notes);
 const differences=compareBoundaries(before,after);
 const result={case:entry.name,splitCount:input.changes.length,tested:input.changes.length>0,differences,fullEqual:JSON.stringify(before)===JSON.stringify(after),before,after};
 fs.writeFileSync(path.join(folder,'boundary-check.json'),JSON.stringify(result));
 results.push({case:entry.name,splitCount:result.splitCount,tested:result.tested,fullEqual:result.fullEqual,differences:differences.length});
}
const hash=x=>createHash('sha256').update(x).digest('hex');
const files=['audit_tie_notation.py','single_score_melody_review.py','audit_tie_boundaries.mjs','audit_phrase_transposition.mjs',...['phrase-boundaries.mjs','phrase-breath-symbols.mjs','repeated-breath-rule.mjs','short-cell-continuity.mjs'].map(n=>'K:/MusicSearch/server/'+n)];
fs.writeFileSync(path.join(root,'boundary-summary.json'),JSON.stringify({results,codeHashes:Object.fromEntries(files.map(f=>[f,hash(fs.readFileSync(f))]))},null,2));
console.log(results);
